"""Read/URL-extraction checks using an existing disposable hosted QA identity.
Does not mutate workspaces or call the model. Private credentials stay in RAM.
"""
from pathlib import Path
import json,time,hashlib,re
import httpx
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence/m3';BASE='https://ai-career-coach-three-versions.onrender.com'
a=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[1]
cfg=dotenv_values(Path.home()/'.config/ai-career-coach/cloud.env');key=cfg.get('SUPABASE_PUBLISHABLE_KEY') or cfg.get('SUPABASE_ANON_KEY')
r=httpx.post(cfg['SUPABASE_URL']+'/auth/v1/token?grant_type=password',headers={'apikey':key},json={'email':a['email'],'password':a['password']},timeout=30);r.raise_for_status()
headers={'Authorization':'Bearer '+r.json()['access_token']};deadline=time.monotonic()+300
while True:
 try:
  h=httpx.get(BASE+'/v3/api/health',headers=headers,timeout=15);h.raise_for_status();health=h.json()
  if health.get('kb',{}).get('integrity') and health['prompts'][0].get('protocol_adapter')=='m3-json-v1':break
 except httpx.HTTPError:pass
 if time.monotonic()>deadline:raise RuntimeError('New M3 release not available within deadline')
 time.sleep(8)
report={'health_after_start':health,'old_versions':{},'jd_imports':[]}
before=json.loads((OUT/'production-before.json').read_text())
for version in ['v1','v2','claude']:
 r=httpx.get(BASE+'/'+version+'/',timeout=30);r.raise_for_status();sha=hashlib.sha256(r.content).hexdigest()
 report['old_versions'][version]={'status':r.status_code,'sha256':sha,'unchanged':sha==before[version]['sha256']}
 assert report['old_versions'][version]['unchanged'],version
for url in ['https://www.nowcoder.com/jobs/detail/315366','https://job-boards.greenhouse.io/globalizationpartners/jobs/8207500003?gh_src=remoteitjobs.app&utm_source=chatgpt.com']:
 r=httpx.post(BASE+'/v3/api/extract/url',json={'url':url},headers=headers,timeout=40);data=r.json()
 report['jd_imports'].append({'url':url,'status':r.status_code,'chars':len(data.get('text','')),'title':data.get('title'),'error':data.get('error')})
 print('JD public import:',url.split('/')[2],r.status_code,len(data.get('text','')),flush=True)
report['quota']=httpx.get(BASE+'/v3/api/quota',headers=headers,timeout=20).json()
(OUT/'hosted-read-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS hosted startup RAG integrity, official prompt, unchanged V1/V2/Claude; JD results saved',flush=True)
