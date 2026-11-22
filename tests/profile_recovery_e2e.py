"""Regression: historical projects lacking M3 profile flags, scrolled sidebar.
MOCK Auth/Storage/model; real DB/backend/browser. No production user data.
"""
from uuid import uuid4
import json
from playwright.sync_api import sync_playwright,expect
from e2e_audit import BASE,OUT,RESUME_PAGES,JD
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1500,'height':900});p=ctx.new_page();ctx.route('**/api/health',lambda r:r.fulfill(status=503,json={'detail':'Synthetic health unavailable'}));p.set_default_timeout(15000);calls=[]
 p.on('request',lambda r:calls.append(r.url) if r.url.endswith(('/materials/prepare','/resume/optimize')) else None)
 def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
 def api(path,method='GET',data=None):
  return p.evaluate('''async ([path,method,data])=>{const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));const r=await fetch('/v3/api/'+path,{method,headers:{Authorization:'Bearer '+a.access_token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});if(!r.ok)throw Error('Fixture API '+r.status);return await r.json()}''',[path,method,data])
 def save():p.locator('[data-saved=true]').wait_for()
 def create(name):nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.get_by_role('button',name=name,exact=True).wait_for();save()
 try:
  a={'email':'profile-legacy-'+uuid4().hex[:8]+'@example.test','password':'ProfileLegacy123'}
  ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data=a);ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':a['email']})
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(a['email']);f.locator('[name=password]').fill(a['password']);f.locator('button').click();p.locator('.workspace').wait_for();create('Legacy Profile')
  p.locator('#resume').fill('\n'.join(RESUME_PAGES));p.locator('#jd').fill(JD);save()
  project=next(x for x in api('workspaces') if x['name']=='Legacy Profile');record=api('workspaces/'+project['id'])
  for k in ['languageConfirmed','userStage','jobGoal']:record['state']['inputs'].pop(k,None)
  # A genuine historical shape, without the optional newer profile fields.
  record['state']['materials']=api('materials/prepare','POST',{'resume_text':'\n'.join(RESUME_PAGES),'jd_text':JD,'lang':'zh-CN','user_stage':'current_student','job_goal':'internship'})
  record['state']['materials'].pop('pipeline_version',None)
  api('workspaces/'+project['id'],'PUT',record);p.reload();p.locator('#resume').wait_for();original=p.locator('#resume').input_value();jd=p.locator('#jd').input_value();calls.clear()
  p.locator('section .scroll-thin').first.evaluate('e=>{e.scrollTop=e.scrollHeight}')
  nav('重新分析');dialog=p.get_by_role('dialog');expect(dialog).to_be_visible();expect(dialog.locator('#analysis-language')).to_have_value('zh-CN')
  expect(dialog.get_by_role('button',name='确认并继续',exact=True)).to_be_disabled();dialog.get_by_role('button',name='取消',exact=True).click();expect(dialog).to_have_count(0)
  assert not calls;assert api('quota')['used']==0;expect(p.locator('#resume')).to_have_value(original);expect(p.locator('#jd')).to_have_value(jd)
  nav('简历优化');p.get_by_role('button',name='生成改写建议',exact=True).evaluate('e=>{e.click();e.click()}');expect(p.get_by_role('dialog')).to_have_count(1)
  p.locator('#analysis-stage').select_option('current_student');p.locator('#analysis-goal').select_option('internship');p.screenshot(path=str(OUT/'profile-recovery-modal.png'),full_page=True);nav('确认并继续')
  expect(p.get_by_test_id('rewrite-O1')).to_be_visible();save();assert sum(x.endswith('/resume/optimize') for x in calls)==1,calls
  assert api('quota')['used']==1;stored=api('workspaces/'+project['id'])['state'];assert stored['inputs']['languageConfirmed'] and stored['inputs']['userStage']=='current_student' and stored['inputs']['jobGoal']=='internship'
  expect(p.locator('#resume')).to_have_value(original);expect(p.locator('#jd')).to_have_value(jd)
  p.reload();p.get_by_test_id('rewrite-O1').wait_for();nav('重新生成');expect(p.get_by_role('dialog')).to_have_count(0)
  expect(p.get_by_test_id('rewrite-O1')).to_be_visible();save()
  create('Other Profile');nav('开始分析');expect(p.get_by_role('dialog')).to_be_visible();p.keyboard.press('Escape');expect(p.get_by_role('dialog')).to_have_count(0)
  nav('Legacy Profile');expect(p.locator('#user-stage')).to_have_value('current_student');expect(p.locator('#job-goal')).to_have_value('internship')
  nav('求职选项');expect(p.locator('#analysis-language')).to_have_value('zh-CN');nav('取消');save()
  p.screenshot(path=str(OUT/'profile-recovery.png'),full_page=True)
  (OUT/'profile-recovery.json').write_text(json.dumps({'mode':'MOCK model/Auth/Storage, real browser/backend/DB','health_failure_does_not_block':True,'legacy_missing_fields':True,'scrolled_sidebar_modal':True,'cancel_no_calls_no_data_loss':True,'confirm_auto_continues':True,'double_click_one_model_call':True,'refresh_persists':True,'project_isolation':True,'escape_closes':True},indent=2))
  print('PASS historical profile gate: visible modal, cancel, automatic continuation, no duplicate calls, persistence and isolation')
 finally:
  if __import__('sys').exc_info()[0]:(OUT/'profile-recovery-failure.txt').write_text(p.locator('body').inner_text())
  b.close()
