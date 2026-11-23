"""Local QA only. Real PostgreSQL and app endpoints; synthetic Auth/Storage/model.
Never import this module in production. No credential is needed for mock mode.
"""
import os, sys, json, re, asyncio, importlib.util, time, hashlib
from pathlib import Path
from uuid import uuid4
ROOT = Path(os.environ.get('QA_APP_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'backend'))
if not os.environ.get('DATABASE_URL', '').rsplit('/', 1)[-1].startswith('coachtest_v3_audit'):
    raise RuntimeError('Disposable audit database required')
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
spec = importlib.util.spec_from_file_location('fixture', ROOT / 'deploy/auth_fixture.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
fixture.app.user_middleware.clear()
from fastapi.middleware.cors import CORSMiddleware
fixture.app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:28649'], allow_methods=['*'], allow_headers=['*'])
@fixture.app.post('/auth/v1/signup')
async def signup(r: Request):
    data = await r.json(); email = data['email']
    u = dict(id=str(uuid4()), email=email, aud='authenticated', role='authenticated', app_metadata={}, user_metadata={}, created_at='2026-11-22T00:00:00Z')
    fixture.users[email] = u; fixture.pw[email] = data['password']
    return u
@fixture.app.post('/qa/confirm')
async def confirm(r: Request):
    fixture.users[(await r.json())['email']]['email_confirmed_at']='2026-11-22T00:00:00Z'
    return {'ok': True, 'mode':'synthetic email confirmation'}
from app.main import app as v2
from app import llm, job_import
original_resolve = job_import.PublicResolver.addresses
async def fixture_resolve(self, host, port):
    if host == 'qa-careers.example.test': return ['93.184.216.34']
    return await original_resolve(self, host, port)
job_import.PublicResolver.addresses = fixture_resolve
if os.environ.get('QA_PUBLIC_DNS') == '1':
    from public_dns import PublicDNSResolver
    job_import.PublicResolver = PublicDNSResolver
control = {'failure':None, 'delay':0, 'calls':0, 'requests':[]}
from app import m3
real_complete=m3.complete_json
async def audited_complete(system,user):
    payload=json.loads(user)
    control['requests'].append({'task':payload['task'],'ui_language':payload['ui_language'],
        'system_sha256':hashlib.sha256(system.encode()).hexdigest(),'official_prompt_sha256':hashlib.sha256(m3.system_prompt().encode()).hexdigest(),
        'chunk_ids':[c['chunk_id'] for c in payload['rag_chunks']],
        'resume_sha256':hashlib.sha256(payload['resume_text'].encode()).hexdigest()})
    out=await real_complete(system,user)
    if os.environ.get('QA_REAL_MODEL')=='1':
        dest=ROOT/'tests/evidence/m3';dest.mkdir(exist_ok=True)
        (dest/('raw-'+payload['task']+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
    return out
m3.complete_json=audited_complete
async def set_control(r: Request):
    control.update(await r.json()); return control
async def get_control(): return control
class ModelTransport(httpx.AsyncBaseTransport):
    def __init__(self): self.network = httpx.AsyncHTTPTransport()
    async def handle_async_request(self, request):
        if request.url.host == 'qa-careers.example.test':
            return httpx.Response(200, headers={'content-type':'text/html'}, text='<main><h1>QA Marketing Assistant</h1><h2>Responsibilities</h2><p>Support marketing campaigns, prepare weekly campaign reports using Excel, maintain content calendars and coordinate campus communications. Entry level applicants with strong written English and teamwork skills are welcome.</p></main>')
        if request.url.host != 'api.deepseek.com': return await self.network.handle_async_request(request)
        control['calls'] += 1
        await asyncio.sleep(control['delay'])
        if control['failure']=='timeout':raise httpx.ReadTimeout('QA timeout', request=request)
        if control['failure']:return httpx.Response(503, json={'error':{'message':'QA failure'}})
        body=json.loads(request.content); system=body['messages'][0]['content']; user=body['messages'][1]['content']
        payload=json.loads(user) if '"task"' in user else {}
        task=payload.get('task')
        if task=='resume_optimization':
            resume=payload['resume_text']
            lines=[x for x in resume.splitlines() if x.startswith(('Helped','Created','Worked'))][:3]
            if not lines:lines=[x for x in resume.splitlines() if x.startswith(('协助','参与'))][:3]
            out={'status':'ok','message':'','result':{'edits':[{'original':t,'jd_quote':'','rewrite':t.replace('Helped coordinate','Supported').replace('Worked','Collaborated').replace('Created','Prepared').replace('协助','支持',1).replace('参与','协助',1), 'reason':'Clarifies the original responsibility.'} for t in lines], 'questions_to_student':[]},'citations':[]}
        elif task=='job_matching':
            jdlines=payload['jd_text'].splitlines()
            evidence=next((x for x in payload['resume_text'].splitlines() if x.startswith('Helped')),'')
            out={'status':'ok','message':'','result':{'requirements':[{'jd_quote':t,'priority':'required','evidence_quotes':[evidence] if evidence else [],'status':'partial' if evidence else 'not_evidenced','reason':'Campaign reporting experience is relevant.','next_step':'Practise campaign reporting.'} for t in jdlines if len(t)>20]},'citations':[]}
        elif task=='mock_interview':
            action=payload['interview_action'];answer=payload.get('answer_text','')
            result={'phase':'question','question':'How did you prepare the campaign reports?','feedback':None,'summary':None}
            if action=='respond':result.update(feedback={'answer_quote':answer,'strength':'You described your actions.','next_try':'Explain your method.'},question='How did you collect attendee feedback?')
            if action=='respond' and control.get('follow_up'):result.update(phase='follow_up',question='What reporting method did you use?')
            if action=='finish':result.update(phase='summary',question=None,summary='You described campaign reporting. Practise explaining your method.')
            out={'status':'ok','message':'','result':result,'citations':[]}
        elif 'Recommend three distinct' in system:
            data=json.loads(user)
            out={"paths":[dict(name=x,category=k,reason="Practice from the resume",evidence=data["resume"].splitlines()[0],transfer="Coordination",gap="Quantify results") for x,k in [("Product operations","operations"),("Marketing","marketing"),("Analytics","analytics")]]}
        elif 'For each question in order' in system:
            data=json.loads(user)
            out=dict(items=[dict(question_id=q["question_id"],question_type="Behavioral",intent="Coordination",evaluation="Specific actions",improve="Explain your role",example="I would first clarify the scope.") for q in data["review"]["questions"]],strengths="Clear examples",priorities=["Scope","Evidence","Results"],practice="Behavioral questions",checklist="Rehearse once")
        else:out={'ok':True}
        if payload.get('task') and os.environ.get('QA_NULL_CITATIONS')=='1':out['citations']=None
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(out)}}], 'usage':{'total_tokens':10}})
    async def aclose(self):await self.network.aclose()
if os.environ.get('QA_REAL_MODEL') != '1':
    original=httpx.AsyncClient
    httpx.AsyncClient=lambda **kw: original(**kw) if os.environ.get('QA_REAL_JD_IMPORT') == '1' and isinstance(kw.get('transport'), job_import.PublicTransport) else original(transport=ModelTransport(), **{k:v for k,v in kw.items() if k != 'transport'})
root=FastAPI()
root.add_api_route('/qa/control', set_control, methods=['POST'])
root.add_api_route('/qa/control', get_control, methods=['GET'])
root.mount('/v4',v2)
if __name__=='__main__':
    import uvicorn
    uvicorn.run(fixture.app if sys.argv[-1]=='auth' else root,host='127.0.0.1',port=28648 if sys.argv[-1]=='auth' else 28649,access_log=False)
