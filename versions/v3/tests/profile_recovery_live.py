"""One real DeepSeek call in a dedicated hosted QA account, fictional materials.
Seeds a NEW owned project with historical optional fields absent; never edits
another project. Credentials remain in the existing private QA configuration.
"""
import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from e2e_audit import RESUME_PAGES,JD
OUT=Path(__file__).resolve().parent/'evidence/profile-live';OUT.mkdir(exist_ok=True)
BASE='https://ai-career-coach-three-versions.onrender.com/v3'
a=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[0]
report={'mode':'REAL hosted Auth/Storage/DB/DeepSeek; fictional new QA project','provider_calls':0};requests=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1500,'height':1000});p=ctx.new_page();p.set_default_timeout(45000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('request',lambda r:requests.append(r.url) if r.url.endswith('/resume/optimize') else None)
 def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
 def save():p.locator('[data-saved=true]').wait_for()
 def api(path,method='GET',data=None):
  return p.evaluate('''async([path,method,data])=>{const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));const r=await fetch('/v3/api/'+path,{method,headers:{Authorization:'Bearer '+a.access_token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const body=await r.json();if(!r.ok)throw Error('QA request '+r.status);return body}''',[path,method,data])
 try:
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(a['email']);f.locator('[name=password]').fill(a['password']);f.locator('button').click();p.locator('.workspace').wait_for()
  report['quota_before']=api('quota');assert report['quota_before']['remaining']>=1
  name='Profile Recovery Live '+uuid4().hex[:6];nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.locator('main header').filter(has_text=name).wait_for();nav('工作台');p.locator('#resume').wait_for();save()
  cv='\n'.join(RESUME_PAGES);p.locator('#resume').fill(cv);p.locator('#jd').fill(JD);save()
  project=next(x for x in api('workspaces') if x['name']==name);record=api('workspaces/'+project['id'])
  record['state']['materials']=api('materials/prepare','POST',{'resume_text':cv,'jd_text':JD,'lang':'zh-CN','user_stage':'current_student','job_goal':'internship'})
  for k in ['pipeline_version','user_stage','job_goal']:record['state']['materials'].pop(k,None)
  for k in ['languageConfirmed','userStage','jobGoal']:record['state']['inputs'].pop(k,None)
  api('workspaces/'+project['id'],'PUT',record);p.reload();p.locator('#resume').wait_for();nav('简历优化');p.locator('section .scroll-thin').first.evaluate('e=>{e.scrollTop=e.scrollHeight}')
  nav('生成改写建议');expect(p.get_by_role('dialog')).to_be_visible();expect(p.locator('#analysis-language')).to_have_value('zh-CN');nav('取消');assert not requests
  expect(p.locator('#resume')).to_have_value(cv);expect(p.locator('#jd')).to_have_value(JD)
  nav('生成改写建议');p.locator('#analysis-stage').select_option('current_student');p.locator('#analysis-goal').select_option('internship');p.screenshot(path=str(OUT/'modal.png'),full_page=True)
  with p.expect_response(lambda r:r.url.endswith('/resume/optimize'),timeout=85000) as response:nav('确认并继续')
  data=response.value.json();assert response.value.status==200,data;assert data['m3']['prompt_version']=='M3_Prompt_v1';save()
  stored=api('workspaces/'+project['id'])['state'];assert stored['resume']['data']==data
  assert stored['inputs']['languageConfirmed'] and stored['inputs']['userStage']=='current_student' and stored['inputs']['jobGoal']=='internship'
  expect(p.locator('#resume')).to_have_value(cv);expect(p.locator('#jd')).to_have_value(JD)
  p.reload();p.locator('#resume').wait_for();expect(p.get_by_role('dialog')).to_have_count(0);restored=api('workspaces/'+project['id'])['state'];assert restored['resume']['data']==data;save();p.wait_for_timeout(250);p.screenshot(path=str(OUT/'recovered.png'),full_page=True)
  report.update(result='PASS',provider_calls=len(requests),cancel_no_call=True,automatic_continuation=True,materials_preserved=True,refresh_restored=True,items=len(data['items']),page_errors=errors,quota_after=api('quota'))
  assert len(requests)==1 and report['quota_after']['used']==report['quota_before']['used']+1 and not errors
  print('PASS live historical recovery: confirm auto-continued to real DeepSeek 200, exactly one call, materials/profile/result persisted',flush=True)
 finally:
  if __import__('sys').exc_info()[0]:report['result']='FAIL';p.screenshot(path=str(OUT/'failure.png'),full_page=True);(OUT/'failure.txt').write_text(p.locator('body').inner_text())
  (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));b.close()
