import json
from dataclasses import asdict
from pathlib import Path
import pytest
from studio.workflows import Generation,build,frames,resolution,preflight,MODES,STYLES
from studio.storage import Project,uid
from studio.comfy import execute,Comfy
from studio.deepseek import validate_action,chat

def test_h3_frame_alignment_and_short_test():
    for sec in (.2,1,2,5,15,60,149):
        n=frames(sec);assert n%17==5;assert n>=round(sec*24);assert n-round(sec*24)<17
    assert frames(2)==56
    assert resolution('16:9',.2)==(608,352)

@pytest.mark.parametrize('mode',list(MODES))
def test_graphs_closed_and_output(mode):
    n={'qwen_edit':1,'quad':1,'h3_i2v':1,'h3_ref':2,'h3_fl2v':2,'upscale':1}.get(mode,0)
    g=Generation(mode=mode,prompt='test',references=['a']*n)
    graph=build(g,['uploaded.png']*n)
    for node in graph.values():
        for x in node['inputs'].values():
            if isinstance(x,list):assert x[0] in graph
    assert graph['output']['class_type']==('SaveVideo' if mode.startswith('h3') else 'SaveImage')

def test_lora_disable_rewires_both_h3_consumers():
    g=Generation(mode='h3_i2v',prompt='test',references=['x'],cinema=True)
    on=build(g,['x']);assert on['guide']['inputs']['model']==['cinema',0];assert on['sigmas']['inputs']['model']==['cinema',0]
    g.cinema=False;off=build(g,['x']);assert 'cinema' not in off
    assert off['guide']['inputs']['model']==off['sigmas']['inputs']['model']==['model',0]

def test_style_switches_and_quad():
    g=Generation(mode='krea',prompt='test',styles=list(STYLES))
    assert len([n for n in build(g,[]).values() if n['class_type']=='LoraLoaderModelOnly'])==9
    g.styles=[];assert not any(n['class_type']=='LoraLoaderModelOnly' for n in build(g,[]).values())
    g=Generation(mode='quad',prompt='test',references=['x'],quad_lora=False)
    assert build(g,['x'])['patch']['inputs']['model']==['model',0]

def test_edit_geometry_and_reference_order():
    g=Generation(mode='qwen_edit',prompt='change hat',references=['a','b'])
    graph=build(g,['uploaded-a','uploaded-b'])
    assert graph['encode']['inputs']['images.image_1']==['resize',0]
    assert graph['encode']['inputs']['images.image_2']==['ref1',0]
    assert graph['sample']['inputs']['latent_image']==['encode',2]

def test_project_roundtrip_versions_and_path_safety(tmp_path):
    p=Project(tmp_path/'p',True);a=p.add('characters','robot');s=p.add('shots','01');s['materials']=[a['id']];p.save()
    with pytest.raises(ValueError):p.delete(a['id'])
    with pytest.raises(ValueError):p.file('../outside')
    j={'id':'job','target':s['id'],'generation':asdict(Generation(prompt='test'))}
    p.attach_output(j,'outputs/a.png');p.attach_output(j,'outputs/a.png')
    again=Project(p.root);assert len(again.get(s['id'])['versions'])==1

def test_missing_refs_and_models():
    with pytest.raises(ValueError):Generation(mode='h3_i2v',prompt='x').validate()
    with pytest.raises(ValueError):preflight(build(Generation(prompt='x'),[]),{})

def test_ai_bounded_tools_and_no_key():
    assert validate_action('set_story',{'text':'hello'})['text']=='hello'
    for name,args in [('delete_file',{}),('set_story',{'text':9}),('set_story',{'text':'x','command':'rm'}),('add_item',{'kind':'bad','name':'x','description':'x'})]:
        with pytest.raises(ValueError):validate_action(name,args)
    with pytest.raises(ValueError):chat('','model',[],{})

class Fake:
    def __init__(self,root):self.submits=0;self.root=root
    def history(self,pid):return {'status':{'completed':True},'outputs':{}}
    def download(self,h,d):
        d.mkdir(parents=True,exist_ok=True);f=d/'x.png';f.write_bytes(b'png');return [f]

def test_resume_never_resubmits(tmp_path):
    p=Project(tmp_path/'p',True);f=Fake(p.root)
    j={'id':uid(),'prompt_id':'existing','generation':asdict(Generation(prompt='x')),'status':'running'}
    assert execute(f,p,j);assert f.submits==0;assert j['status']=='completed'

def test_cancel_only_selected_prompt(monkeypatch):
    c=Comfy();calls=[]
    monkeypatch.setattr(c,'queue',lambda:{'queue_running':[[0,'other']], 'queue_pending':[[1,'ours']]})
    monkeypatch.setattr(c,'call',lambda *a,**k:calls.append((a,k)))
    c.cancel('ours');assert calls==[(('POST','/queue'),{'json':{'delete':['ours']}})]

def test_deepseek_mocked_request_contract(monkeypatch):
    calls=[]
    class Response:
        ok=True
        def json(self):return {'choices':[{'message':{'role':'assistant','content':'计划','tool_calls':[{'id':'c1','type':'function','function':{'name':'set_story','arguments':'{"text":"故事"}'}}]}}]}
    def post(url,**kw):calls.append((url,kw));return Response()
    monkeypatch.setattr('studio.deepseek.requests.post',post)
    msg=chat('test-only-key','test-model',[{'role':'user','content':'写故事'}],{'story':''})
    assert msg['tool_calls'][0]['id']=='c1'
    assert calls[0][0]=='https://api.deepseek.com/chat/completions'
    assert calls[0][1]['json']['tools'] and calls[0][1]['json']['thinking']=={'type':'disabled'}

def test_cancelled_job_not_registered_as_success(tmp_path):
    p=Project(tmp_path/'p',True)
    class Interrupted:
        def history(self,pid):return {'status':{'status_str':'error','messages':[['execution_interrupted',{}]]}}
    j={'id':uid(),'prompt_id':'p','status':'running'}
    assert execute(Interrupted(),p,j)==[];assert j['status']=='cancelled'

def test_asset_change_marks_only_referencing_shots(tmp_path):
    p=Project(tmp_path/'p',True);a=p.add('characters','a');s=p.add('shots','1');other=p.add('shots','2');s['materials']=[a['id']]
    p.mark_dependents(a['id']);assert s['needs_review'];assert not other.get('needs_review')

def test_video_max_length_is_legal():
    assert frames(149)<=3600
    with pytest.raises(ValueError):frames(150)

def test_h3_prompt_repair_is_bounded(monkeypatch):
    import copy,json
    calls=[]
    complete='integrated_multimodal_description: [Shot 1] robot waves\noverall_soundscape: quiet room\nnon_diegetic_music: N/A'
    args={'target':'shot','mode':'h3_i2v','prompt':'incomplete','references':['image.png']}
    class Response:
        ok=True
        def json(self):
            args['prompt']=complete if len(calls)==2 else 'incomplete'
            return {'choices':[{'message':{'role':'assistant','tool_calls':[{'id':'t','function':{'name':'generate','arguments':json.dumps(args)}}]}}]}
    def post(*a,**kw):calls.append(copy.deepcopy(kw['json']));return Response()
    monkeypatch.setattr('studio.deepseek.requests.post',post)
    assert chat('test','model',[],{})['tool_calls']
    assert len(calls)==2 and '未通过' in calls[1]['messages'][-1]['content']

def test_h3_reference_prompt_uses_six_sections():
    from studio.deepseek import validate_prompt
    args={'mode':'h3_ref','prompt':'integrated_multimodal_description: x\noverall_soundscape: y\nnon_diegetic_music: N/A'}
    with pytest.raises(ValueError):validate_prompt(args)
    args['prompt']='subject_definitions: x\nsummary: x\nretention_analysis: x\ndetailed_description: x\noverall_soundscape: x\nnon_diegetic_music: N/A'
    validate_prompt(args)
