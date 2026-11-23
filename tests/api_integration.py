"""Integration with real local PostgreSQL/RLS and quota, synthetic Auth/upstream."""
from pathlib import Path
from uuid import uuid4
import sys, json
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend/tests'))
from test_final_resume import state
BASE='http://127.0.0.1:28649/v4'
AUTH='http://127.0.0.1:28648'
def account():
 email='integration-'+uuid4().hex[:10]+'@example.test';password='IntegrationPass123'
 httpx.post(AUTH+'/auth/v1/signup',json={'email':email,'password':password}).raise_for_status()
 httpx.post(AUTH+'/qa/confirm',json={'email':email}).raise_for_status()
 token=httpx.post(AUTH+'/auth/v1/token',json={'email':email,'password':password}).json()['access_token']
 return httpx.Client(base_url=BASE,headers={'Authorization':'Bearer '+token},timeout=20)
a,b=account(),account()
name='integration-'+uuid4().hex
r=a.put('/api/workspaces/'+name,json={'name':'Isolation','revision':0,'state':state()});assert r.status_code==200,r.text
assert b.get('/api/workspaces/'+name).status_code==404
assert b.get('/api/workspaces/'+name+'/resume/export').status_code==404
assert a.get('/api/workspaces/'+name+'/resume/export?format=pdf').content.startswith(b'%PDF')
assert a.put('/api/workspaces/'+name,json={'name':'Conflict','revision':0,'state':{}}).status_code==409
before=a.get('/api/quota').json()['used']
assert a.get('/api/workspaces/'+name+'/resume/export?format=docx').status_code==200
assert a.get('/api/quota').json()['used']==before
httpx.post('http://127.0.0.1:28649/qa/control',json={'failure':None,'delay':0})
for _ in range(10):assert a.post('/api/settings/test').status_code==200
assert a.post('/api/settings/test').status_code==429
assert a.get('/api/quota').json()=={'limit':10,'used':10,'remaining':0,'blocked':False}
# All generation endpoints must enforce the same exhausted account reservation.
assert a.post('/api/explore/paths/'+name,json={'lang':'en','resume':'A fictional resume'}).status_code==429
review_url='/api/explore/review/'+str(uuid4())
created=a.post(review_url,json={'revision':0,'review':{'date':'2026-11-22','role':'QA','questions':[{'question':'How do you plan?'}]}})
assert created.is_success
assert a.post(review_url+'/analyze',json={'lang':'en','revision':created.json()['revision']}).status_code==429
assert b.get('/api/quota').json()['used']==0
assert a.delete('/api/workspaces/'+name).status_code==200
assert a.get('/api/quota').json()['used']==10
out={'owner_isolation':'PASS','revision_conflict':'PASS','pdf_docx_no_ai_calls':'PASS','ten_calls_enforced':'PASS','delete_preserves_quota':'PASS'}
(Path(__file__).resolve().parent/'evidence/api-integration.json').write_text(json.dumps(out,indent=2))
print('PASS owner/project RLS, 409 conflict, exports consume zero AI calls, 10-call quota and deletion preserves accounting')
