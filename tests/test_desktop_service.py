"""Real domain integration behind the Vue bridge; no generation network needed."""
import json
import time
from dataclasses import asdict
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest
from PIL import Image
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit

from studio import service as module
from studio.service import StudioService
from studio.storage import Project, atomic_json
from studio.workflows import Generation
from studio.media_server import MediaServer

app = QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'QSettings', lambda *args:QSettings(str(tmp_path/'settings.ini'), QSettings.IniFormat))
    monkeypatch.setattr(module.keyring, 'get_password', lambda *args:None)
    s = StudioService()
    s.load(tmp_path/'story', create=True, title='真实项目')
    yield s
    s.shutdown()


def call(s, command, **args): return s.dispatch(command, args)


def test_schema_ids_crud_history_and_reopen(service, tmp_path):
    s = service
    a = call(s,'asset.add',kind='characters',name='人物',description='原描述')
    b = call(s,'asset.add',kind='scenes',name='街道')
    shot = call(s,'asset.add',kind='shots')
    call(s,'asset.link',id=shot,ids=[a,b,a])
    assert s.project.get(shot)['materials']==[a,b]
    src=tmp_path/'source.png';Image.new('RGB',(64,96),'blue').save(src)
    first=call(s,'asset.import',id=a,paths=[str(src)])[0]
    second=call(s,'asset.import',id=a,paths=[str(src)])[0]
    versions=s.project.get(a)['versions']
    call(s,'version.use',id=a,version=versions[0]['id'])
    assert s.project.get(a)['image']==first and first!=second
    call(s,'asset.update',id=a,name='人物改名',description='新描述')
    assert s.project.get(shot)['needs_review']
    call(s,'asset.reviewed',id=shot)
    call(s,'project.story',text='保留故事')
    root=s.project.root
    assert s.load(root)==str(root)
    other=tmp_path/'other';s.load(other,create=True)
    s.load(root/'project.json')
    assert s.project.data['schema']==1
    assert s.project.get(a)['image']==first
    assert s.snapshot()['project']['shots'][0]['name']=='分镜 1'
    call(s,'asset.delete',id=a)
    assert s.project.get(shot)['materials']==[b] and s.project.file(first).exists()


def test_selection_toggle_is_atomic_without_clearing_pinned_context(service):
    s=service
    actor=call(s,'asset.add',kind='characters',name='角色')
    scene=call(s,'asset.add',kind='scenes',name='场景')
    shot=call(s,'asset.add',kind='shots')
    for ident in (actor,scene,shot):
        call(s,'selection',id=ident,toggle=True)
        assert s.snapshot()['selectedId']==ident
        call(s,'selection',id=ident,toggle=True)
        assert s.snapshot()['selectedId'] is None
    call(s,'selection',id=actor,pin=True)
    call(s,'selection',id=actor,toggle=True)
    assert s.selected is None and s.context_ids==[actor]
    call(s,'selection',id=shot);call(s,'selection',id=shot)
    assert s.selected==shot  # Timeline navigation remains idempotent.


def test_task_result_thumbnails_keep_each_output_after_version_changes_and_deletion(service):
    s=service;target=call(s,'asset.add',kind='scenes',name='舞台')
    s.project.data['queue_paused']=True
    for color in ('red','blue'):
        job=call(s,'generation.submit',target=target,generation=asdict(Generation(prompt=color)))
        j=s.project.data['jobs'][-1]
        relative=f'outputs/{job}.png';Image.new('RGB',(32,32),color).save(s.project.file(relative))
        j.update(status='completed',outputs=[relative]);s.project.attach_output(j,relative)
    item=s.project.get(target)
    call(s,'version.use',id=target,version=item['versions'][0]['id'])
    tasks=s.snapshot()['project']['tasks']
    assert [t['results'][0]['file'] for t in tasks]==[j['outputs'][0] for j in s.project.data['jobs']]
    assert tasks[0]['results'][0]['media']!=tasks[1]['results'][0]['media']
    call(s,'asset.delete',id=target)
    assert all(t['results'][0]['media'] for t in s.snapshot()['project']['tasks'])


def test_chat_display_does_not_rewrite_internal_messages_or_hide_sources(service):
    s=service
    record={'type':'skill','skill':'h3','file':'SKILL.md'}
    message={'role':'assistant','content':'创作建议\n'+json.dumps(record),'_activity':[record,{'type':'search','sources':[{'title':'来源','url':'https://example.com/'}]}]}
    s.project.data['chat'].append(message)
    s.status='读取技能：h3/SKILL.md'
    dto=s.snapshot()
    assert 'SKILL.md' not in dto['project']['chat'][-1]['text']
    assert dto['project']['chat'][-1]['activity'][1]['sources'][0]['url']=='https://example.com/'
    assert dto['status']=='正在准备视频创作建议'
    assert s.project.data['chat'][-1]==message


def test_seed_exact_precision_and_cancelled_prompt_does_not_overwrite(service):
    s=service;a=call(s,'asset.add',kind='characters',name='角色')
    s.project.data['queue_paused']=True
    g=asdict(Generation(prompt='本次提示',seed=2**63-1));g['seed']=str(g['seed'])
    ident=call(s,'generation.submit',target=a,generation=g)
    task=s.snapshot()['project']['tasks'][0]
    assert task['generation']['seed']=='9223372036854775807'
    assert s.project.data['jobs'][0]['generation']['seed']==2**63-1
    assert call(s,'generation.defaults',target=a,mode='qwen')['prompt']=='本次提示'
    call(s,'task.cancel',id=ident)
    assert s.project.data['jobs'][0]['status']=='cancelled'
    for seed in ('1.5','-1',True,'9223372036854775808'):
        with pytest.raises(ValueError):call(s,'generation.submit',target=a,generation={**g,'seed':seed})


def test_journal_recovery_keeps_results_under_original_id(service, tmp_path):
    s=service
    ids=[call(s,'asset.add',kind=k,name=k) for k in ('characters','scenes','shots')]
    s.project.data['queue_paused']=True
    for ident in ids:
        job=call(s,'generation.submit',target=ident,generation=asdict(Generation(prompt=ident)))
        rel=f'outputs/{job}.png';Image.new('RGB',(32,32),'green').save(s.project.file(rel))
        data=s.project.data['jobs'][-1].copy();data.update(status='completed',prompt_id=job,outputs=[rel])
        atomic_json(s.project.file('jobs/'+job+'.json'),data)
    root=s.project.root
    s.load(tmp_path/'other',create=True);s.load(root)
    assert all(len(s.project.get(ident)['versions'])==1 for ident in ids)
    s.load(tmp_path/'other');s.load(root)
    assert all(len(s.project.get(ident)['versions'])==1 for ident in ids)
    assert [s.project.get(i)['versions'][0]['intent'] for i in ids]==ids


def test_review_create_alias_rejection_and_one_shot_approval(service):
    s=service;s.project.data['queue_paused']=True
    old=call(s,'asset.add',kind='characters',name='旧角色')
    calls=[{'id':'create','type':'function','function':{'name':'add_item','arguments':json.dumps({'kind':'characters','name':'新角色','description':'描写'})}},
           {'id':'gen','type':'function','function':{'name':'generate','arguments':json.dumps({'target':'@新角色','mode':'qwen','prompt':'a simple robot','references':[]})}}]
    s._accept_message({'role':'assistant','content':'建议','tool_calls':calls})
    first=s.pending['id'];call(s,'review.respond',id=first,accepted=True)
    target=s.pending['targetId'];assert target!=old
    second=s.pending['id'];call(s,'review.respond',id=second,accepted=True)
    assert s.project.data['jobs'][-1]['target']==target
    with pytest.raises(ValueError):call(s,'review.respond',id=second,accepted=True)
    assert len(s.project.data['jobs'])==1
    s._accept_message({'role':'assistant','content':'建议','tool_calls':calls})
    call(s,'review.respond',id=s.pending['id'],accepted=False)
    assert s.pending is None and len(s.project.data['jobs'])==1


def test_recovery_never_resubmits_without_known_id_and_delete_guard(service):
    s=service;s.project.data['queue_paused']=True
    target=call(s,'asset.add',kind='scenes',name='场景')
    job=call(s,'generation.submit',target=target,generation=asdict(Generation(prompt='scene')))
    with pytest.raises(ValueError):call(s,'asset.delete',id=target)
    with pytest.raises(ValueError):call(s,'task.resume',id=job)
    assert s.project.data['jobs'][0]['status']=='new'
    call(s,'task.cancel',id=job);call(s,'asset.delete',id=target)


def test_video_asset_guard_and_path_escape(service):
    s=service;target=call(s,'asset.add',kind='characters',name='人物')
    with pytest.raises(ValueError):call(s,'generation.submit',target=target,generation=asdict(Generation(mode='h3_t2v',prompt='video')))
    with pytest.raises(ValueError):s.media_url('../secret.png')
    with pytest.raises(ValueError):call(s,'asset.link',id=target,ids=[])
    assert not s.project.data['jobs']


def test_media_server_token_range_and_no_business_http(service, tmp_path):
    s=service;frontend=tmp_path/'frontend';frontend.mkdir();(frontend/'index.html').write_text('<html>Vue</html>')
    (frontend/'media').mkdir();(frontend/'media/xy-logo.jpg').write_bytes(b'logo')
    path=s.project.file('assets/range.webm');path.write_bytes(b'0123456789')
    server=MediaServer(s,frontend)
    try:
        url=s.media_url('assets/range.webm')
        with urlopen(Request(url,headers={'Range':'bytes=2-5'})) as r:
            assert r.status==206 and r.read()==b'2345' and r.headers['Content-Range']=='bytes 2-5/10'
        assert urlopen(server.base+'/media/xy-logo.jpg').read()==b'logo'
        for suffix in ('/project-media/wrong/assets/range.webm','/api/project','/%2e%2e/secret'):
            with pytest.raises(HTTPError):urlopen(server.base+suffix)
        with pytest.raises(HTTPError) as e:urlopen(Request(url,headers={'Range':'bytes=50-60'}))
        assert e.value.code==416
        assert 'key' not in s.snapshot()['config']
    finally:server.close()


def test_duplicate_project_lock_and_virtual_legacy_version(service):
    s=service;other=StudioService()
    try:
        with pytest.raises(ValueError):other.load(s.project.root)
        target=call(s,'asset.add',kind='characters',name='旧条目')
        s.project.get(target)['image']='assets/legacy.png'
        Image.new('RGB',(32,32)).save(s.project.file('assets/legacy.png'))
        dto=s.snapshot()['project']['assets'][0]
        call(s,'version.use',id=target,version=dto['current'])
        assert s.project.get(target)['versions']==[]
    finally:other.shutdown()


def test_file_picker_entrypoints_with_actual_qt_dialog(service, tmp_path):
    # Exercise the actual dialog return path. Qt fallback enables deterministic
    # offscreen input; the Windows native picker remains the production default.
    s=service;root=s.project.root
    old=app.testAttribute(Qt.AA_DontUseNativeDialogs)
    app.setAttribute(Qt.AA_DontUseNativeDialogs,True)
    def choose(path):
        found=[]
        picker=None
        deadline=time.monotonic()+3
        def select():
            nonlocal picker
            if picker is None:
                picker=next((w for w in app.topLevelWidgets() if isinstance(w,QFileDialog) and w.isVisible()),None)
                if picker is None:
                    if time.monotonic()<deadline:QTimer.singleShot(10,select)
                    return
                found.append(picker.windowTitle());picker.setDirectory(str(path.parent))
            try:
                if not picker.isVisible():return
                if time.monotonic()>=deadline:
                    found.append({'selected':picker.selectedFiles(),'directory':picker.directory().absolutePath(),'filters':picker.nameFilters(),'mode':str(picker.fileMode())})
                    picker.reject();return
                picker.selectFile(str(path))
                # ExistingFiles does not always populate the filename editor
                # through selectFile once its asynchronous model is visible.
                # Enter the actual filename as a user would, then accept the
                # real dialog; do not mock its return value.
                editor=picker.findChild(QLineEdit,'fileNameEdit')
                if editor and path.is_file():editor.setText('"'+str(path)+'"')
                picker.accept()
                # QFileSystemModel may still be loading the directory. Retry
                # this same dialog, never select an unrelated later picker.
                if picker.isVisible():QTimer.singleShot(20,select)
            except RuntimeError:return  # The accepted dialog was deleted.
        QTimer.singleShot(10,select)
        return found
    try:
        new=tmp_path/'selected';new.mkdir()
        seen=choose(new);call(s,'project.new',title='对话框创建');assert seen and s.project.root==new.resolve()
        seen=choose(root/'project.json');call(s,'project.open');assert seen and s.project.root==root
        target=call(s,'asset.add',kind='scenes',name='选择图片')
        png=tmp_path/'import.png';Image.new('RGB',(32,32)).save(png)
        seen=choose(png);call(s,'asset.import',id=target);assert seen and s.project.get(target)['image'], seen
    finally:app.setAttribute(Qt.AA_DontUseNativeDialogs,old)
