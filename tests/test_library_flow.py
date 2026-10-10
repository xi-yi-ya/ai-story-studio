"""The user chooses adoption; generation/replay never choose a new library result."""
import json
from dataclasses import asdict
import pytest
from PIL import Image
from PySide6.QtCore import QSettings, QMimeData, QUrl, Qt, QPointF
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QWidget
from studio import service as module
from studio.service import StudioService
from studio.storage import LIBRARY_TARGET, atomic_json, Project
from studio.workflows import Generation
from studio.asset_library import AssetLibrary
from studio.file_drop import NativeFileDrop

app=QApplication.instance() or QApplication([])
@pytest.fixture
def service(tmp_path,monkeypatch):
 monkeypatch.setattr(module,'QSettings',lambda *args:QSettings(str(tmp_path/'settings.ini'),QSettings.IniFormat))
 monkeypatch.setattr(module.keyring,'get_password',lambda *args:None)
 s=StudioService();s.load(tmp_path/'project',create=True);s.project.data['queue_paused']=True
 yield s
 s.shutdown()

def image(s,tmp_path,name='舞台',color='blue'):
 p=tmp_path/(name+'.png');Image.new('RGB',(96,64),color).save(p)
 return s.dispatch('library.import',{'kind':'image','paths':[str(p)]})[0]

def test_unassigned_generation_reopen_adopt_and_detach_preserve_identity(service,tmp_path):
 s=service;file=image(s,tmp_path)
 actor=s.dispatch('asset.from_media',{'kind':'characters','file':file})
 assert s.project.get(actor)['name']=='舞台'
 old=dict(s.project.get(actor))
 job_id=s.dispatch('generation.submit',{'generation':asdict(Generation(prompt='舞台新灯光'))})
 job=s.project.data['jobs'][-1];out='outputs/result.png';Image.new('RGB',(96,64),'green').save(s.project.file(out))
 job.update(status='completed',outputs=[out]);s.project.attach_output(job,out);atomic_json(s.project.file('jobs/'+job_id+'.json'),job)
 assert job['target']==LIBRARY_TARGET and s.project.get(actor)==old
 row=AssetLibrary(s.project).get(out);identity=row['id']
 assert not row['owners'] and not row['deletedOwner'] and row['name']=='图片 1'
 root=s.project.root;s.load(tmp_path/'other',create=True);s.load(root)
 assert s.project.get(actor)==old
 s.dispatch('asset.use_media',{'id':actor,'file':out})
 assert s.project.get(actor)['image']==out and len(s.project.get(actor)['versions'])==2
 s.dispatch('asset.use_media',{'id':actor,'file':out})
 assert len(s.project.get(actor)['versions'])==2
 assert AssetLibrary(s.project).get(out)['id']==identity
 s.dispatch('asset.delete',{'id':actor})
 assert s.project.file(file).exists() and s.project.file(out).exists()
 assert s.project.data['schema']==1

def test_again_restores_original_ordered_references_after_result_adopted(service,tmp_path):
 s=service;a=image(s,tmp_path,'人物');b=image(s,tmp_path,'舞台')
 g=asdict(Generation(mode='qwen_edit',prompt='把图1人物放入图2',references=[a,b],steps=40,qwen_int8=True))
 s.dispatch('generation.submit',{'generation':g});j=s.project.data['jobs'][-1]
 out='outputs/composite.png';Image.new('RGB',(96,64),'red').save(s.project.file(out));j.update(status='completed',outputs=[out])
 actor=s.dispatch('asset.from_media',{'kind':'characters','file':out,'name':'初音未来'})
 restored=s.dispatch('generation.defaults',{'mode':'qwen_edit'})
 assert restored['references']==[a,b] and restored['prompt']==g['prompt']
 assert restored['steps']==40 and restored['seed']!=str(g['seed'])
 preview=s.dispatch('library.preview',{'file':out})
 assert preview['generation']['references']==[a,b] and preview['generation']['seed']=='42'
 assert s.project.get(actor)['image']==out
 rows=s.dispatch('references.describe',{'files':[a,b]})
 assert [r['name'] for r in rows]==['人物','舞台'] and all(r['media'] for r in rows)

def test_agent_video_opens_review_without_creating_shot_or_image(service,tmp_path):
 s=service;file=image(s,tmp_path)
 args={'mode':'h3_i2v','prompt':'integrated_multimodal_description: Slow camera.\noverall_soundscape: N/A\nnon_diegetic_music: N/A','references':[file]}
 s._accept_message({'role':'assistant','content':'请确认视频参数','tool_calls':[{'id':'video','type':'function','function':{'name':'generate','arguments':json.dumps(args)}}]})
 assert s.pending and s.pending['generation']['mode']=='h3_i2v'
 assert s.pending['generation']['references']==[file] and s.pending['targetName']=='视频库'
 s.dispatch('review.respond',{'id':s.pending['id'],'accepted':True})
 assert len(s.project.data['jobs'])==1 and s.project.data['jobs'][0]['target']==LIBRARY_TARGET
 assert not s.project.data['shots'] and not s.project.data['characters'] and not s.project.data['scenes']

def test_adopt_name_and_legacy_description_are_independent_from_library(service,tmp_path):
 s=service;file=image(s,tmp_path,'原图片名')
 actor=s.dispatch('asset.from_media',{'kind':'characters','file':file,'name':'角色名'})
 s.project.get(actor)['description']='旧项目资料需要保留'
 s.dispatch('asset.rename',{'id':actor,'name':'新名称'})
 assert s.project.get(actor)['description']=='旧项目资料需要保留'
 assert AssetLibrary(s.project).get(file)['name']=='原图片名'
 s.dispatch('asset.rename',{'id':actor,'name':''})
 assert s.project.get(actor)['name']=='原图片名'
 with pytest.raises(ValueError):s.dispatch('asset.use_media',{'id':actor,'file':'../escape.png'})

def test_legacy_pending_resume_preserves_ids_but_requires_adoption(service,tmp_path,monkeypatch):
 s=service;file=image(s,tmp_path)
 actor=s.dispatch('asset.from_media',{'kind':'characters','file':file})
 job={'id':'old-job','target':actor,'prompt_id':'known-comfy-id','generation':asdict(Generation(prompt='旧任务')),'status':'detached'}
 s.project.data['jobs'].append(job);s.project.save()
 monkeypatch.setattr(s,'_spawn',lambda *args:None)
 s.start_job(job)
 assert job['library_only'] and job['id']=='old-job' and job['target']==actor
 out='outputs/resumed.png';Image.new('RGB',(96,64),'green').save(s.project.file(out));job.update(status='completed',outputs=[out])
 s.project.attach_output(job,out)
 assert s.project.get(actor)['image']==file
 assert not AssetLibrary(s.project).get(out)['owners']
 assert Project(s.project.root).data['jobs'][-1]['library_only']

def test_native_file_drop_passes_original_paths_and_zoom_coordinates_without_navigation():
 class Page:
  def __init__(self):self.scripts=[]
  def runJavaScript(self,script):self.scripts.append(script)
 class View(QWidget):
  def __init__(self):super().__init__();self.browser=Page()
  def page(self):return self.browser
  def zoomFactor(self):return 1.25
 view=View();filter=NativeFileDrop(view);mime=QMimeData()
 mime.setUrls([QUrl.fromLocalFile('D:/素材/人物.png'),QUrl.fromLocalFile('D:/素材/视频.mp4')])
 event=QDropEvent(QPointF(125,250),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
 assert filter.eventFilter(view,event) and event.isAccepted()
 script=view.browser.scripts[-1]
 wire=script.split('detail:',1)[1].split('}));',1)[0]
 data=json.loads(wire)
 assert data['paths']==['D:/素材/人物.png','D:/素材/视频.mp4'] and data['x']==100 and data['y']==200
 mime.setUrls([QUrl('https://example.com/image.png')])
 assert not filter.eventFilter(view,QDropEvent(QPointF(0,0),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier))
 view.deleteLater()
