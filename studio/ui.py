import copy,json,os,sys,html,re
from dataclasses import asdict
from pathlib import Path
import keyring
from PySide6.QtCore import Qt,QThread,Signal,QUrl,QSettings,QTimer
from PySide6.QtGui import QPixmap,QDesktopServices,QAction,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QPushButton,QLabel,QLineEdit,QTextEdit,QPlainTextEdit,QTabWidget,QScrollArea,QGroupBox,QDialog,QFormLayout,QComboBox,QDoubleSpinBox,QSpinBox,QCheckBox,QDialogButtonBox,QFileDialog,QMessageBox,QInputDialog,QMenu,QDockWidget,QListWidget,QListWidgetItem,QAbstractItemView,QTextBrowser,QProgressBar,QTableWidget,QTableWidgetItem,QHeaderView)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from .storage import Project,uid,now,atomic_json
from .workflows import Generation,MODES,RATIOS,STYLES,resolution,frames
from .comfy import Comfy,execute
from .deepseek import chat,validate_action,list_models,DEFAULT_MODELS
from .research import safe_link
from .media import video_poster
from . import __version__
from .action_targets import resolve_target

def button(text,fn):
    b=QPushButton(text); b.clicked.connect(fn);return b
def message(parent,e): QMessageBox.warning(parent,'提示',str(e))
def scroll(widget):
    s=QScrollArea();s.setWidgetResizable(True);s.setWidget(widget);return s

class Worker(QThread):
    progress=Signal(str); result=Signal(object); failed=Signal(str)
    def __init__(self,fn): super().__init__();self.fn=fn
    def run(self):
        try:self.result.emit(self.fn(self))
        except Exception as e:self.failed.emit(str(e))

class GenerationDialog(QDialog):
    def __init__(self,project,g,parent=None,target=None):
        super().__init__(parent);self.project=project;self.g=g
        self.target=target;self.prompt_mode=g.mode;self.prompt_drafts={g.mode:g.prompt}
        self.setWindowTitle('生成参数 · 提交前检查');self.resize(640,760)
        outer=QVBoxLayout(self);body=QWidget();form=QFormLayout(body);self.form=form;outer.addWidget(scroll(body))
        self.target_label=QLabel('归属条目：'+project.get(target)['name']+'（'+target[:8]+'）' if target else '未指定条目')
        self.target_label.setWordWrap(True);form.addRow(self.target_label)
        self.mode=QComboBox()
        self.is_video=g.mode.startswith('h3')
        for k,v in MODES.items():
            if k.startswith('h3')==self.is_video:self.mode.addItem(v,k)
        self.mode.setCurrentIndex(self.mode.findData(g.mode));form.addRow('视频工作流' if self.is_video else '图片工作流',self.mode)
        self.prompt=QPlainTextEdit(g.prompt);self.prompt.setMinimumHeight(110);form.addRow('提示词',self.prompt)
        self.ratio=QComboBox();self.ratio.addItems(RATIOS);self.ratio.setCurrentText(g.ratio);form.addRow('图片 / 视频比例',self.ratio)
        self.mp=QDoubleSpinBox();self.mp.setRange(.1,16);self.mp.setSingleStep(.1);self.mp.setValue(g.megapixels);form.addRow('分辨率（MP）',self.mp)
        self.seconds=QDoubleSpinBox();self.seconds.setRange(.2,149);self.seconds.setValue(g.seconds);form.addRow('H3 时长（秒）',self.seconds)
        self.scale=QDoubleSpinBox();self.scale.setRange(1,8);self.scale.setSingleStep(.1);self.scale.setValue(g.scale);form.addRow('高清放大倍数',self.scale)
        self.seed=QLineEdit(str(g.seed));form.addRow('种子',self.seed)
        self.steps=QSpinBox();self.steps.setRange(0,100);self.steps.setSpecialValueText('沿用工作流默认');self.steps.setValue(g.steps);form.addRow('采样步数',self.steps)
        self.cinema=QCheckBox('启用电影质感 LoRA（普通 H3）');self.cinema.setChecked(g.cinema);form.addRow(self.cinema)
        self.strength=QDoubleSpinBox();self.strength.setRange(0,2);self.strength.setSingleStep(.1);self.strength.setValue(g.cinema_strength);form.addRow('电影 LoRA 强度',self.strength)
        self.quad=QCheckBox('启用角色四视图 LoRA');self.quad.setChecked(g.quad_lora);form.addRow(self.quad)
        self.int8=QCheckBox('Qwen 使用本机 INT8 模型（省显存）');self.int8.setChecked(g.qwen_int8);form.addRow(self.int8)
        self.styles={}
        group=QGroupBox('Krea2 风格 LoRA · 可分别启停');self.style_group=group;gl=QGridLayout(group)
        for i,name in enumerate(STYLES):
            cb=QCheckBox(name);cb.setChecked(name in g.styles);gl.addWidget(cb,i//3,i%3);self.styles[name]=cb
        form.addRow(group)
        self.refs=QListWidget();self.refs.setMinimumHeight(90)
        for r in g.references:self.refs.addItem(r)
        form.addRow('参考图（按顺序；首尾帧为前两张）',self.refs)
        self.available=QComboBox()
        for kind in ('characters','scenes','shots'):
            for item in project.data[kind]:
                if item['image']:self.available.addItem(item['name'],item['image'])
        source_row=QWidget();sl=QHBoxLayout(source_row);sl.addWidget(self.available);sl.addWidget(button('加入参考',self.add_existing));form.addRow('项目素材',source_row)
        row=QWidget();rl=QHBoxLayout(row);rl.addWidget(button('导入图片',self.add_refs));rl.addWidget(button('移除所选',self.remove_ref));rl.addWidget(button('上移',lambda:self.move_ref(-1)));rl.addWidget(button('下移',lambda:self.move_ref(1)));form.addRow(row)
        self.reference_rows=(self.refs,source_row,row)
        self.summary=QLabel();self.summary.setWordWrap(True);form.addRow(self.summary)
        for w in (self.mp,self.seconds,self.scale):w.valueChanged.connect(self.preview)
        self.ratio.currentTextChanged.connect(self.preview);self.mode.currentIndexChanged.connect(self.preview)
        self.mode.currentIndexChanged.connect(self.restore_prompt)
        self.cinema.toggled.connect(self.preview)
        self.preview()
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('加入生成队列');buttons.accepted.connect(self.accept_valid);buttons.rejected.connect(self.reject);outer.addWidget(buttons)
    def add_refs(self):
        paths,_=QFileDialog.getOpenFileNames(self,'选择参考图片','','图片 (*.png *.jpg *.jpeg *.webp)')
        for p in paths:self.refs.addItem(self.project.import_file(p))
        self.preview()
    def restore_prompt(self):
        self.prompt_drafts[self.prompt_mode]=self.prompt.toPlainText();self.prompt_mode=self.mode.currentData()
        saved=self.project.last_prompt(self.target,self.prompt_mode) if self.target else ''
        self.prompt.setPlainText(self.prompt_drafts.get(self.prompt_mode,saved or self.prompt.toPlainText()))
    def add_existing(self):
        if self.available.currentData():self.refs.addItem(self.available.currentData());self.preview()
    def remove_ref(self):
        if self.refs.currentRow()>=0:self.refs.takeItem(self.refs.currentRow());self.preview()
    def move_ref(self,offset):
        i=self.refs.currentRow();j=i+offset
        if i>=0 and 0<=j<self.refs.count():self.refs.insertItem(j,self.refs.takeItem(i));self.refs.setCurrentRow(j);self.preview()
    def preview(self,*_):
        mode=self.mode.currentData();w,h=resolution(self.ratio.currentText(),self.mp.value(),32 if mode.startswith(('h3','qwen')) else 8)
        is_video=mode.startswith('h3')
        self.seconds.setEnabled(is_video);self.cinema.setEnabled(is_video);self.strength.setEnabled(is_video and self.cinema.isChecked())
        self.quad.setEnabled(mode=='quad');self.int8.setEnabled(mode.startswith('qwen'))
        self.scale.setEnabled(mode=='upscale');self.mp.setEnabled(mode!='upscale');self.ratio.setEnabled(mode!='upscale')
        for cb in self.styles.values():cb.setEnabled(mode=='krea')
        for widget,visible in ((self.seconds,is_video),(self.cinema,is_video),(self.strength,is_video),(self.quad,mode=='quad'),(self.int8,mode.startswith('qwen')),(self.scale,mode=='upscale'),(self.style_group,mode=='krea'),(self.mp,mode!='upscale'),(self.ratio,mode!='upscale'),(self.prompt,mode!='upscale')):
            self.form.setRowVisible(widget,visible)
        for widget in self.reference_rows:self.form.setRowVisible(widget,mode not in ('qwen','krea','h3_t2v'))
        text=f'输出 {w} × {h}。'
        if is_video:text+=f'H3 {frames(self.seconds.value())} 帧 / 24fps ≈ {frames(self.seconds.value())/24:.2f} 秒。修改时长后请核对提示词时间线。视频建议先低分辨率、短时长测试；高规格未验证。'
        if mode=='upscale':text='请选择一张图片，按原图尺寸放大。'
        if mode=='upscale' and self.refs.count():
            pix=QPixmap(str(self.project.file(self.refs.item(0).text())))
            text=f'预计放大至 {int(pix.width()*self.scale.value())} × {int(pix.height()*self.scale.value())}（以实际输出为准）。'
        if mode=='qwen_edit':text+=' 主参考图按此尺寸居中裁剪后编辑。'
        self.summary.setText(text)
    def accept_valid(self):
        try:
            self.g=Generation(mode=self.mode.currentData(),prompt=self.prompt.toPlainText(),ratio=self.ratio.currentText(),megapixels=self.mp.value(),seconds=self.seconds.value(),seed=int(self.seed.text()),steps=self.steps.value(),cinema=self.cinema.isChecked(),cinema_strength=self.strength.value(),quad_lora=self.quad.isChecked(),qwen_int8=self.int8.isChecked(),styles=[k for k,v in self.styles.items() if v.isChecked()],scale=self.scale.value(),references=[self.refs.item(i).text() for i in range(self.refs.count())])
            if self.g.mode in ('qwen','krea','h3_t2v'):self.g.references=[]
            self.g.validate()
            for r in self.g.references:
                if not self.project.file(r).is_file():raise ValueError('参考图不存在：'+r)
            self.accept()
        except Exception as e:message(self,e)

class TaskDialog(QDialog):
    def __init__(self,studio):
        super().__init__(studio);self.studio=studio;self.setWindowTitle('任务管理 · 当前项目全部角色 / 场景 / 分镜');self.resize(980,650)
        layout=QVBoxLayout(self);self.summary=QLabel();layout.addWidget(self.summary)
        self.filter=QComboBox();self.filter.addItems(['全部','未完成','已完成','失败 / 未知','已取消']);self.filter.currentIndexChanged.connect(self.refresh_jobs);layout.addWidget(self.filter)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['条目','工作流','状态','当前节点进度','创建时间']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);layout.addWidget(self.table)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);layout.addWidget(self.details);self.table.itemSelectionChanged.connect(self.show_details)
        row=QHBoxLayout();layout.addLayout(row)
        for label,fn in [('暂停 / 继续待执行队列',self.pause),('取消所选',self.cancel),('恢复查询',self.resume),('再次生成（审阅参数）',self.retry),('打开结果',self.open_result)]:row.addWidget(button(label,fn))
        self.refresh_jobs()
    def chosen(self):
        cell=self.table.item(self.table.currentRow(),0)
        return next((j for j in self.studio.project.data['jobs'] if cell and j['id']==cell.data(Qt.UserRole)),None)
    def refresh_jobs(self):
        current=self.chosen();ident=current['id'] if current else None
        jobs=self.studio.project.data['jobs'];f=self.filter.currentIndex()
        shown=[j for j in jobs if f==0 or (f==1 and j['status'] not in ('completed','cancelled')) or (f==2 and j['status']=='completed') or (f==3 and j['status'] in ('failed','unknown','detached')) or (f==4 and j['status']=='cancelled')]
        self.summary.setText(f"总任务 {len(jobs)} · 已完成 {sum(j['status']=='completed' for j in jobs)} · 待执行 {sum(j['status']=='new' for j in jobs)} · "+('队列已暂停（当前任务继续）' if self.studio.project.data.get('queue_paused') else '队列可执行'))
        self.table.blockSignals(True);self.table.setRowCount(len(shown))
        for i,j in enumerate(shown):
            try:name=self.studio.project.get(j['target'])['name']
            except ValueError:name='已删除条目'
            p=j.get('progress');progress=f"{j.get('node','')} {p['value']}/{p['max']}" if p else '—'
            state={'new':'待执行','queued':'后端排队','submitting':'提交中','running':'运行中','downloading':'保存结果','completed':'完成','failed':'失败','unknown':'状态未知','detached':'已断开','cancelled':'已取消','cancel_requested':'正在取消'}.get(j['status'],j['status'])
            for k,value in enumerate((name,MODES.get(j['generation']['mode'],j['generation']['mode']),state,progress,j.get('created','')[:19])):
                cell=QTableWidgetItem(value);cell.setData(Qt.UserRole,j['id']);self.table.setItem(i,k,cell)
            if j['id']==ident:self.table.selectRow(i)
        self.table.blockSignals(False)
        if not ident and shown:self.table.selectRow(0)
        self.show_details()
    def show_details(self):
        j=self.chosen();text=json.dumps(j,ensure_ascii=False,indent=2) if j else ''
        if self.details.toPlainText()!=text:self.details.setPlainText(text)
    def pause(self):
        p=self.studio.project;p.data['queue_paused']=not p.data.get('queue_paused',False);p.save();self.studio.start_next();self.refresh_jobs()
    def cancel(self):
        j=self.chosen()
        if j:
            try:self.studio.cancel_job(j)
            except Exception as e:message(self,e)
        self.refresh_jobs()
    def resume(self):
        j=self.chosen()
        if j and j.get('prompt_id') and not self.studio.active and j['status'] in ('failed','unknown','detached','queued','running'):self.studio.start_job(j)
    def retry(self):
        j=self.chosen()
        if not j:return
        if j['status'] not in ('completed','cancelled'):
            message(self,'状态不确定或失败的任务请先恢复查询，核对后再手动生成，避免重复提交。');return
        try:self.studio.generate(self.studio.project.get(j['target']),j['generation']['mode'],Generation(**j['generation']))
        except Exception as e:message(self,e)
    def open_result(self):
        j=self.chosen()
        if j and j.get('outputs'):QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.studio.project.file(j['outputs'][0]))))

class Studio(QMainWindow):
    def __init__(self,project_path=None):
        super().__init__();self.settings=QSettings('XiYi','AIStoryStudio');self.project=None;self.active=None;self.chat_worker=None;self.model_worker=None;self.context_ids=[]
        self.jobs_dialog=None
        self.progress_bar=QProgressBar();self.progress_bar.setMinimumWidth(360);self.statusBar().addPermanentWidget(self.progress_bar)
        self.task_timer=QTimer(self);self.task_timer.timeout.connect(self.update_task_status);self.task_timer.start(700)
        self.setWindowTitle('XY Studio · v'+__version__);self.resize(1440,920)
        self.tabs=QTabWidget();self.setCentralWidget(self.tabs)
        toolbar=self.addToolBar('项目')
        for title,fn in [('新建项目',self.new_project),('打开项目',self.open_project),('保存',self.save),('设置',self.configure),('任务管理',self.show_jobs),('AI 对话',self.toggle_chat)]:
            a=QAction(title,self);a.triggered.connect(fn);toolbar.addAction(a)
        self.dock=QDockWidget('AI 创作助手 · DeepSeek',self);self.dock.setMinimumWidth(300)
        chatbox=QWidget();cl=QVBoxLayout(chatbox)
        options=QHBoxLayout();self.model_picker=QComboBox();self.model_picker.addItems(self.settings.value('model_list',DEFAULT_MODELS,type=list))
        current=self.settings.value('model','deepseek-flash')
        if self.model_picker.findText(current)<0:self.model_picker.addItem(current)
        self.model_picker.setCurrentText(current);self.model_picker.currentTextChanged.connect(lambda m:self.settings.setValue('model',m))
        options.addWidget(self.model_picker);self.model_refresh=button('刷新模型',self.refresh_models);options.addWidget(self.model_refresh);cl.addLayout(options)
        self.online=QCheckBox('允许 AI 联网检索');self.online.setChecked(self.settings.value('online_search',True,type=bool));self.online.toggled.connect(lambda value:self.settings.setValue('online_search',value));cl.addWidget(self.online)
        self.agent_status=QLabel('技能按需读取 · 联网使用同一 DeepSeek Key');self.agent_status.setWordWrap(True);cl.addWidget(self.agent_status)
        self.transcript=QTextBrowser();self.transcript.setOpenLinks(False);self.transcript.anchorClicked.connect(lambda url:QDesktopServices.openUrl(url) if safe_link(url.toString()) else None);cl.addWidget(self.transcript)
        self.context_label=QLabel('右击素材卡可发送给 AI');self.context_label.setWordWrap(True);cl.addWidget(self.context_label)
        self.input=QPlainTextEdit();self.input.setMaximumHeight(120);self.input.setPlaceholderText('描述故事或修改目标……');cl.addWidget(self.input)
        self.send=button('发送',self.send_chat);cl.addWidget(self.send)
        cl.addWidget(button('导入子 agent 建议（临时测试）',self.import_agent))
        self.dock.setWidget(chatbox);self.addDockWidget(Qt.RightDockWidgetArea,self.dock)
        if project_path:self.load_project(project_path)
        else:self.refresh()
    def busy(self):return bool(self.active or self.chat_worker or self.model_worker)
    def guard(self):
        if self.busy():message(self,'任务运行期间请等待完成再切换项目');return False
        return True
    def new_project(self):
        if not self.guard():return
        path=QFileDialog.getExistingDirectory(self,'选择新项目文件夹')
        if path:
            try:
                if self.jobs_dialog:self.jobs_dialog.close()
                self.project=Project(path,True);self.context_ids=[];self.refresh()
            except Exception as e:message(self,e)
    def open_project(self):
        if not self.guard():return
        path,_=QFileDialog.getOpenFileName(self,'打开项目','','项目 (project.json)')
        if path:self.load_project(Path(path).parent)
    def load_project(self,path):
        try:
            if self.jobs_dialog:self.jobs_dialog.close()
            self.project=Project(path);self.context_ids=[]
            # Job journals are authoritative for crash recovery.
            for j in self.project.data['jobs']:
                jp=self.project.file('jobs/'+j['id']+'.json')
                if jp.exists():j.update(json.loads(jp.read_text(encoding='utf-8')))
                if j.get('status')=='completed':
                    for p in j.get('outputs',[]):self.project.attach_output(j,p)
            self.refresh()
        except Exception as e:message(self,e)
    def save(self):
        if self.project:self.project.save();self.statusBar().showMessage('项目已保存',3000)
    def toggle_chat(self):self.dock.setVisible(not self.dock.isVisible())
    def refresh(self):
        index=self.tabs.currentIndex()
        while self.tabs.count():
            old=self.tabs.widget(0);self.tabs.removeTab(0);old.deleteLater()
        if not self.project:
            self.tabs.addTab(QLabel('请新建或打开一个本地项目。素材、生成记录和对话均保存在项目文件夹中。'),'开始');return
        self.setWindowTitle(f'XY Studio · {self.project.data["title"]} · v{__version__}')
        for kind,label in [('characters','角色'),('scenes','场景'),('shots','分镜板')]:
            container=QWidget();layout=QVBoxLayout(container)
            if kind=='shots':
                story=QPlainTextEdit(self.project.data['story']);story.setPlaceholderText('短故事描述');story.setMaximumHeight(120)
                story.textChanged.connect(lambda s=story:self.set_story(s.toPlainText()));layout.addWidget(story)
            layout.addWidget(button('+ 新增'+('分镜' if kind=='shots' else label),lambda checked=False,k=kind:self.edit_item(k)))
            cards=QWidget();grid=QGridLayout(cards)
            for i,item in enumerate(self.project.data[kind]):grid.addWidget(self.card(kind,item),i,0)
            layout.addWidget(cards);layout.addStretch();self.tabs.addTab(scroll(container),label)
        self.tabs.setCurrentIndex(max(0,min(index,2)));self.render_chat()
    def set_story(self,text):self.project.data['story']=text;self.project.save()
    def thumbnail(self,relative,empty):
        label=QLabel(empty);label.setAlignment(Qt.AlignCenter);label.setFixedSize(240,240);label.setStyleSheet('QLabel {background:#edf0f4;border:1px solid #b7bcc6;border-radius:5px;}')
        if relative:
            pix=QPixmap(str(self.project.file(relative)))
            if not pix.isNull():label.setPixmap(pix.scaled(228,228,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        return label
    def card(self,kind,item):
        box=QGroupBox(item['name']);box.setMinimumWidth(240)
        layout=QHBoxLayout(box)
        details=QWidget();dl=QVBoxLayout(details);desc=QLabel(item['description']);desc.setWordWrap(True);desc.setMaximumWidth(340);dl.addWidget(desc)
        if kind=='shots':
            names=[]
            for ident in item['materials']:
                try:names.append(self.project.get(ident)['name'])
                except ValueError:names.append('已移除')
            dl.addWidget(QLabel('使用素材：'+('、'.join(names) or '尚未关联')))
            if item.get('needs_review'):
                dl.addWidget(QLabel('关联素材已有修改 · 请检查此分镜'))
                dl.addWidget(button('已检查，保留当前结果',lambda:self.clear_review(item)))
            dl.addWidget(button('关联角色 / 场景',lambda:self.link_materials(item)))
        dl.addWidget(button('编辑描述',lambda:self.edit_item(kind,item)));layout.addWidget(details)
        dl.addWidget(button('生成历史',lambda:self.versions(item)))
        dl.addWidget(button('删除'+{'characters':'角色','scenes':'场景','shots':'分镜'}[kind],lambda:self.delete(item)))
        imagebox=QWidget();il=QVBoxLayout(imagebox);il.addWidget(self.thumbnail(item['image'],'分镜图' if kind=='shots' else '参考图'),0,Qt.AlignHCenter)
        il.addWidget(button('生成 / 编辑图片',lambda:self.generate(item,self.image_mode(item))));il.addWidget(button('导入图片',lambda:self.import_image(item)))
        layout.addWidget(imagebox)
        if kind=='shots':
            vb=QWidget();vl=QVBoxLayout(vb)
            poster=''
            if item['video']:
                try:poster=video_poster(self.project,item['video'])
                except Exception:pass
            vl.addWidget(self.thumbnail(poster,'首帧读取失败' if item['video'] else '待生成视频'),0,Qt.AlignHCenter)
            if item['video']:vl.addWidget(QLabel('视频首帧预览'))
            vl.addWidget(button('生成视频',lambda:self.generate(item,'h3_i2v')))
            if item['video']:vl.addWidget(button('播放视频',lambda:self.play(item['video'])))
            layout.addWidget(vb)
        box.setContextMenuPolicy(Qt.CustomContextMenu);box.customContextMenuRequested.connect(lambda pos:self.card_menu(box,pos,kind,item));return box
    def card_menu(self,box,pos,kind,item):
        m=QMenu(self)
        for name,fn in [('发送给 AI',lambda:self.add_context(item)),('生成历史',lambda:self.versions(item)),('删除条目',lambda:self.delete(item))]:m.addAction(name,fn)
        m.exec(box.mapToGlobal(pos))
    def delete(self,item):
        if any(j['target']==item['id'] and j['status'] in ('new','submitting','queued','running','downloading') for j in self.project.data['jobs']):
            message(self,'此条目仍有生成任务，请先完成或取消任务。');return
        affected=[s['name'] for s in self.project.data['shots'] if item['id'] in s['materials']]
        text='删除“'+item['name']+'”？素材文件和历史输出仍保留。'
        if affected:text+='\n同时解除以下分镜的素材引用，已有图片和视频保留：'+', '.join(affected)
        if QMessageBox.question(self,'删除条目',text)!=QMessageBox.Yes:return
        try:
            self.project.delete(item['id'],detach=True)
            self.context_ids=[i for i in self.context_ids if i!=item['id']]
            self.context_label.setText('右击素材卡可发送给 AI');self.refresh()
        except Exception as e:message(self,e)
    def clear_review(self,item):item['needs_review']=False;self.save();self.refresh()
    def edit_item(self,kind,item=None):
        if kind=='shots' and item is None:
            self.project.add('shots','');self.refresh();return
        d=QDialog(self);d.setWindowTitle('编辑条目');f=QFormLayout(d);name=QLineEdit(item['name'] if item else '');desc=QPlainTextEdit(item['description'] if item else '')
        if kind!='shots':f.addRow('名称',name)
        f.addRow('描述',desc)
        bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);f.addRow(bb)
        if d.exec():
            if item:item.update(name=name.text() or '未命名',description=desc.toPlainText());self.project.mark_dependents(item['id'])
            else:self.project.add(kind,name.text(),desc.toPlainText())
            self.refresh()
    def import_image(self,item):
        path,_=QFileDialog.getOpenFileName(self,'导入图片','','图片 (*.png *.jpg *.jpeg *.webp)')
        if path:
            try:
                r=self.project.import_file(path);item['image']=r;item['versions'].append({'id':uid(),'time':now(),'kind':'image','file':r,'intent':'导入图片'});self.project.mark_dependents(item['id']);self.save();self.refresh()
            except Exception as e:message(self,e)
    def link_materials(self,item):
        d=QDialog(self);d.setWindowTitle('关联素材');v=QVBoxLayout(d);checks=[]
        for a in self.project.data['characters']+self.project.data['scenes']:
            cb=QCheckBox(a['name']);cb.setChecked(a['id'] in item['materials']);v.addWidget(cb);checks.append((a['id'],cb))
        bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);v.addWidget(bb)
        if d.exec():item['materials']=[i for i,c in checks if c.isChecked()];self.save();self.refresh()
    def versions(self,item):
        d=QDialog(self);d.setWindowTitle(item['name']+' · 生成历史');d.resize(820,650);v=QVBoxLayout(d);ls=QListWidget();v.addWidget(ls)
        detail=QPlainTextEdit();detail.setReadOnly(True);v.addWidget(detail)
        for x in item['versions']:
            row=QListWidgetItem(x['time'][:19]+' · '+x['kind']+' · '+x.get('intent','')[:90])
            try:
                path=video_poster(self.project,x['file']) if x['kind']=='video' else x['file']
                row.setIcon(QIcon(str(self.project.file(path))))
            except Exception:pass
            ls.addItem(row)
        if not item['versions']:v.addWidget(QLabel('还没有生成结果；生成成功后会自动保存到这里。'))
        def selected():return item['versions'][ls.currentRow()] if ls.currentRow()>=0 else None
        def details():
            x=selected()
            if x:
                job=next((j for j in self.project.data['jobs'] if j['id']==x.get('job')),None)
                detail.setPlainText(json.dumps({'version':x,'generation':job.get('generation') if job else None},ensure_ascii=False,indent=2))
        ls.currentRowChanged.connect(details)
        if ls.count():ls.setCurrentRow(ls.count()-1)
        pending=[j for j in self.project.data['jobs'] if j['target']==item['id'] and j['status']!='completed']
        if pending:
            v.addWidget(QLabel('其他生成记录（未产生可用版本）'))
            records=QPlainTextEdit('\n'.join(j.get('created','')[:19]+' · '+j['generation']['mode']+' · '+j['status']+' · '+j.get('error','')[:200] for j in pending));records.setReadOnly(True);records.setMaximumHeight(100);v.addWidget(records)
        def preview():
            x=selected()
            if x:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.file(x['file']))))
        def restore():
            x=selected()
            if x:item[x['kind']]=x['file'];self.project.mark_dependents(item['id']);self.save();d.accept();self.refresh()
        v.addWidget(button('查看文件',preview));v.addWidget(button('设为当前版本',restore));d.exec()
    def play(self,path):
        d=QDialog(self);d.setWindowTitle('视频预览');d.resize(900,600);v=QVBoxLayout(d);screen=QVideoWidget();v.addWidget(screen)
        player=QMediaPlayer(d);audio=QAudioOutput(d);player.setAudioOutput(audio);player.setVideoOutput(screen);player.setSource(QUrl.fromLocalFile(str(self.project.file(path))))
        v.addWidget(button('播放 / 暂停',lambda:player.pause() if player.playbackState()==QMediaPlayer.PlayingState else player.play()));player.play();d.exec();player.stop()
    def generate(self,item,mode,g=None):
        if mode.startswith('h3') and not any(s['id']==item['id'] for s in self.project.data['shots']):raise ValueError('视频只能在分镜中生成，请先新增分镜并关联素材。')
        if g is None:
            refs=[item['image']] if item['image'] and mode in ('h3_i2v','upscale','quad','qwen_edit') else []
            g=Generation(mode=mode,prompt=self.project.last_prompt(item['id'],mode) or item['description'],references=refs,megapixels=.2 if mode.startswith('h3') else 1,seconds=2 if mode.startswith('h3') else 5)
        d=GenerationDialog(self.project,g,self,target=item['id'])
        if d.exec():
            j={'id':uid(),'target':item['id'],'generation':asdict(d.g),'materials':copy.deepcopy([self.project.get(i) for i in item['materials']]),'status':'new','created':now()}
            item.setdefault('last_prompts',{})[d.g.mode]=d.g.prompt
            self.project.data['jobs'].append(j);self.save();self.start_next()
            return j
        return None
    def image_mode(self,item):
        for j in reversed(self.project.data['jobs']):
            if j['target']==item['id'] and j['generation']['mode'] in ('qwen','qwen_edit','krea','quad'):return j['generation']['mode']
        return 'qwen_edit' if item['image'] else 'qwen'
    def start_next(self):
        if self.active or self.project.data.get('queue_paused'):return
        j=next((j for j in self.project.data['jobs'] if j['status']=='new'),None)
        if not j:return
        self.start_job(j)
    def start_job(self,j):
        self.active=j;client=Comfy(self.settings.value('comfy','http://127.0.0.1:8188'))
        # Worker owns a snapshot, main thread owns mutable project and UI.
        snapshot=Project(self.project.root);job=copy.deepcopy(j)
        self.worker=Worker(lambda w:execute(client,snapshot,job,w.progress.emit,w.isInterruptionRequested))
        self.worker.progress.connect(lambda s:self.job_progress(j,s))
        self.worker.result.connect(lambda outputs:self.job_result(j,job,outputs));self.worker.failed.connect(lambda e:self.job_error(j,job,e));self.worker.finished.connect(self.job_finished);self.worker.start()
    def job_progress(self,j,status):
        journal=self.project.file('jobs/'+j['id']+'.json')
        if journal.exists():j.update(json.loads(journal.read_text(encoding='utf-8')))
        self.project.save();self.statusBar().showMessage('生成任务：'+status)
    def job_result(self,j,snapshot,outputs):
        j.update(snapshot)
        if j.get('cancelled_by_user') and not outputs:j['status']='cancelled';atomic_json(self.project.file('jobs/'+j['id']+'.json'),j)
        for p in outputs:self.project.attach_output(j,p)
        self.save();self.refresh()
    def job_error(self,j,snapshot,e):j.update(snapshot);self.save();message(self,e)
    def job_finished(self):self.active=None;self.worker.deleteLater();self.start_next()
    def update_task_status(self):
        jobs=self.project.data['jobs'] if self.project else []
        pending=sum(j['status']=='new' for j in jobs)
        if self.active:
            j=self.active;p=j.get('progress');stage={'submitting':'提交中','queued':'后端排队','running':'运行中','downloading':'保存结果'}.get(j['status'],j['status'])
            if p and p.get('max',0)>0:
                self.progress_bar.setRange(0,int(p['max']));self.progress_bar.setValue(int(p['value']));self.progress_bar.setFormat(f"当前节点 {j.get('node','')}：%v/%m (%p%)")
            else:self.progress_bar.setRange(0,0);self.progress_bar.setFormat(stage)
            self.statusBar().showMessage(f'{stage} · 本地待执行 {pending}')
        else:
            self.progress_bar.setRange(0,1);self.progress_bar.setValue(0)
            self.progress_bar.setFormat(('队列已暂停' if self.project and self.project.data.get('queue_paused') else '空闲')+f' · 待执行 {pending}')
        if self.jobs_dialog and self.jobs_dialog.isVisible():self.jobs_dialog.refresh_jobs()
    def cancel_job(self,j):
        if j['status']=='new':
            j['status']='cancelled';self.save();return
        if not j.get('prompt_id') or j['status'] not in ('queued','running','cancel_requested'):return
        result=Comfy(self.settings.value('comfy','http://127.0.0.1:8188')).cancel(j['prompt_id'])
        if result=='cancelled':
            j['cancelled_by_user']=True;j['status']='cancelled'
            if self.active and self.active['id']==j['id']:self.worker.requestInterruption()
            else:atomic_json(self.project.file('jobs/'+j['id']+'.json'),j)
        elif result=='cancel_requested':j['status']='cancel_requested'
        self.save()
    def show_jobs(self):
        if not self.project:return
        if self.jobs_dialog:self.jobs_dialog.close()
        self.jobs_dialog=TaskDialog(self);self.jobs_dialog.show()
    def add_context(self,item):
        if item['id'] not in self.context_ids:self.context_ids.append(item['id'])
        self.context_label.setText('发送上下文：'+', '.join(self.project.get(i)['name'] for i in self.context_ids));self.dock.show()
    def configure(self):
        d=QDialog(self);d.setWindowTitle('设置');f=QFormLayout(d)
        url=QLineEdit(self.settings.value('comfy','http://127.0.0.1:8188'));model=QComboBox();model.addItems([self.model_picker.itemText(i) for i in range(self.model_picker.count())]);model.setCurrentText(self.model_picker.currentText());key=QLineEdit();key.setEchoMode(QLineEdit.Password);key.setPlaceholderText('留空保留现有密钥；保存到 Windows 凭据管理器')
        f.addRow('ComfyUI 地址',url);f.addRow('DeepSeek 模型',model);f.addRow('DeepSeek API Key',key)
        f.addRow(QLabel('对话会将故事、条目描述和相对文件名发送给 DeepSeek；不上传图片像素。'))
        bb=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);f.addRow(bb)
        if d.exec():
            try:
                if key.text():keyring.set_password('AIStoryStudio','deepseek',key.text().strip())
                self.settings.setValue('comfy',url.text().strip());self.model_picker.setCurrentText(model.currentText())
            except Exception as e:message(self,e)
    def refresh_models(self):
        if self.model_worker:return
        key=keyring.get_password('AIStoryStudio','deepseek')
        if not key:message(self,'请先在设置中保存 DeepSeek API Key');return
        self.model_refresh.setEnabled(False);self.agent_status.setText('正在读取账户可用模型……')
        self.model_worker=Worker(lambda w:list_models(key));self.model_worker.result.connect(self.models_loaded);self.model_worker.failed.connect(lambda e:message(self,e));self.model_worker.finished.connect(self.models_finished);self.model_worker.start()
    def models_loaded(self,models):
        current=self.model_picker.currentText();self.model_picker.blockSignals(True);self.model_picker.clear();self.model_picker.addItems(models)
        if current in models:self.model_picker.setCurrentText(current)
        self.model_picker.blockSignals(False);self.settings.setValue('model_list',models);self.settings.setValue('model',self.model_picker.currentText());self.agent_status.setText('账户模型列表已更新')
    def models_finished(self):
        self.model_worker.deleteLater();self.model_worker=None;self.model_refresh.setEnabled(True)
    def render_chat(self):
        def markup(text):
            escaped=html.escape(text)
            return re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',lambda m:'<a href="'+m[2]+'">'+m[1]+'</a>' if safe_link(html.unescape(m[2])) else m[0],escaped).replace('\n','<br>')
        self.transcript.clear()
        if self.project:
            for m in self.project.data['chat']:
                if m.get('content') and m['role']!='tool':self.transcript.append(markup(('你：' if m['role']=='user' else 'AI：')+m['content']))
                for a in m.get('_activity',[]):
                    if a['type']=='skill':self.transcript.append(markup('已读取技能：'+a['skill']+'/'+a['file']))
                    elif a['type']=='search':
                        self.transcript.append(markup('已联网检索：'+a['query']))
                        for source in a['sources'][:5]:
                            if safe_link(source['url']):self.transcript.append('<a href="'+html.escape(source['url'],quote=True)+'">'+html.escape(source['title'])+'</a>')
                    elif a['type']=='error':self.transcript.append(markup('工具未完成：'+a['message']))
    def send_chat(self):
        if not self.project or self.chat_worker:return
        text=self.input.toPlainText().strip()
        if not text:return
        try:
            key=keyring.get_password('AIStoryStudio','deepseek')
            if not key:raise ValueError('请先在设置中填写 DeepSeek API Key；目前可手动创建素材和生成。')
        except Exception as e:message(self,e);return
        self.project.data['chat'].append({'role':'user','content':text});self.save();self.input.clear();self.render_chat();self.send.setEnabled(False)
        context=copy.deepcopy({k:self.project.data[k] for k in ('story','characters','scenes','shots')});context['selected_ids']=list(self.context_ids)
        history=copy.deepcopy(self.project.data['chat']);model=self.model_picker.currentText();online=self.online.isChecked()
        self.chat_worker=Worker(lambda w:chat(key,model,history,context,online=online,notify=w.progress.emit))
        self.chat_worker.progress.connect(self.agent_status.setText)
        self.chat_worker.result.connect(self.chat_result);self.chat_worker.failed.connect(lambda e:message(self,e));self.chat_worker.finished.connect(self.chat_finished);self.chat_worker.start()
    def chat_finished(self):self.chat_worker.deleteLater();self.chat_worker=None;self.send.setEnabled(True);self.agent_status.setText('本轮结束 · 技能按需读取')
    def chat_result(self,msg):
        self.project.data['chat'].append(msg)
        calls=msg.get('tool_calls',[]);created={}
        for call in calls:
            name=call['function']['name'];args=json.loads(call['function']['arguments']);result='用户未采用此建议'
            try:args=resolve_target(name,args,calls,created)
            except ValueError as e:
                result='操作未执行：'+str(e)
                self.project.data['chat'].append({'role':'tool','tool_call_id':call['id'],'content':result})
                message(self,e);continue
            d=QMessageBox(self);d.setWindowTitle('AI 操作建议');d.setText(name);d.setInformativeText(json.dumps(args,ensure_ascii=False,indent=2));d.setStandardButtons(QMessageBox.Apply|QMessageBox.Cancel)
            if d.exec()==QMessageBox.Apply:
                try:
                    result=self.apply_action(name,args)
                    if name=='add_item':
                        created[call['id']]=json.loads(result)['id']
                        alias=args['name']
                        matching=[c for c in calls if c['function']['name']=='add_item' and json.loads(c['function']['arguments']).get('name')==alias]
                        if alias and len(matching)==1:created[alias]=json.loads(result)['id']
                except Exception as e:result='操作失败：'+str(e);message(self,e)
            self.project.data['chat'].append({'role':'tool','tool_call_id':call['id'],'content':result})
        self.save();self.refresh()
    def import_agent(self):
        if not self.project or self.chat_worker:return
        path,_=QFileDialog.getOpenFileName(self,'导入子 agent 建议','','建议 (*.json)')
        if not path:return
        try:
            bundle=json.loads(Path(path).read_text(encoding='utf-8'))
            if bundle.get('project_id')!=self.project.data['id']:raise ValueError('建议属于其他项目，请在对应项目中导入。')
            msg=bundle['message']
            if msg.get('role')!='assistant':raise ValueError('建议消息格式错误')
            for call in msg.get('tool_calls',[]):validate_action(call['function']['name'],json.loads(call['function']['arguments']))
            msg=copy.deepcopy(msg);msg['content']='[临时子 agent：'+str(bundle.get('provider','未知'))+']\n'+(msg.get('content') or '')
            self.chat_result(msg)
        except Exception as e:message(self,e)
    def apply_action(self,name,args):
        validate_action(name,args)
        if name=='set_story':self.set_story(args['text']);return '故事已保存'
        if name=='add_item':return json.dumps(self.project.add(args['kind'],args['name'],args['description']),ensure_ascii=False)
        if name=='update_item':
            item=self.project.get(args['id'])
            if 'materials' in args:
                if not any(s['id']==item['id'] for s in self.project.data['shots']):raise ValueError('只有分镜可以关联角色和场景')
                valid={a['id'] for a in self.project.data['characters']+self.project.data['scenes']}
                if any(i not in valid for i in args['materials']):raise ValueError('分镜只能关联已有角色或场景')
            item['description']=args['description']
            if 'materials' in args:item['materials']=args['materials']
            self.project.mark_dependents(item['id']);self.save();return '条目已更新'
        if name=='generate':
            item=self.project.get(args['target']);job=self.generate(item,args['mode'],Generation(mode=args['mode'],prompt=args['prompt'],references=args['references'],megapixels=.2 if args['mode'].startswith('h3') else 1,seconds=2))
            return '已加入队列，任务 '+job['id']+'；尚未完成生成' if job else '用户取消了生成，未提交任务'
    def closeEvent(self,event):
        if self.busy():message(self,'仍有任务运行，请等待完成或在任务记录中取消后关闭。');event.ignore();return
        self.save();event.accept()

def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('XiYi.XYStudio')
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setApplicationName('XY Studio')
    app.setWindowIcon(QIcon(str(Path(__file__).parent/'assets'/'xy-studio.ico')))
    app.setStyleSheet('QGroupBox{font-weight:600;margin-top:12px;padding:12px;border:1px solid #b7bcc6;border-radius:6px} QPushButton{padding:7px} QTabBar::tab{padding:12px 32px} QTextEdit,QPlainTextEdit{font-size:14px}')
    window=Studio(sys.argv[1] if len(sys.argv)>1 else None);window.show();return app.exec()
