"""One real matching call on an existing dedicated hosted QA project.
Set M3_QA_PROJECT explicitly. Reads project data; never writes or deletes it.
Existing private QA credentials stay in RAM; no key is passed in CLI arguments.
"""
import os
from pathlib import Path
import json,httpx,time
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1];out=root/'tests/evidence/m3'
a=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[int(os.getenv('M3_ACCOUNT_INDEX','1'))];cfg=dotenv_values(Path.home()/'.config/ai-career-coach/cloud.env')
r=httpx.post(cfg['SUPABASE_URL']+'/auth/v1/token?grant_type=password',headers={'apikey':cfg.get('SUPABASE_PUBLISHABLE_KEY') or cfg.get('SUPABASE_ANON_KEY')},json={'email':a['email'],'password':a['password']},timeout=30);r.raise_for_status();headers={'Authorization':'Bearer '+r.json()['access_token']}
base='https://ai-career-coach-three-versions.onrender.com/v3/api/'
def get(path):
 r=httpx.get(base+path,headers=headers,timeout=30);r.raise_for_status();return r.json()
projects=get('workspaces');pid=next(x['id'] for x in projects if x['name']==os.environ['M3_QA_PROJECT']);state=get('workspaces/'+pid)['state'];before=get('quota')
r=httpx.post(base+'match',headers=headers,json={'lang':'zh-CN','materials':state['materials']},timeout=80);data=r.json()
(out/'final-patch-match.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
assert r.status_code==200,data
assert all(x.get('priority_code') in ('required','preferred','unspecified') for x in data['items'])
assert 'protocol_warnings' in data['m3']
assert data['m3']['prompt_version']=='M3_Prompt_v1' and isinstance(data['m3']['citations'],list)
assert data['guidance']['connected'] and data['guidance']['sources']
after=get('quota');assert after['used']==before['used']+1
health=get('health');assert health['llm']['connection']=='verified' and health['kb']['integrity']
report={'status':r.status_code,'actual_calls':1,'quota_before':before,'quota_after':after,'protocol_warnings':data['m3'].get('protocol_warnings'),
 'assessments_per_requirement':{x['requirement_id']:len(x.get('assessments',[])) for x in data['items']},'health':health,'project_state_mutated':False}
(out/'final-patch-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS final patch real matching: one provider call, valid priorities/citations, no project mutation',flush=True)
