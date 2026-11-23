"""Targeted browser regressions for snapshot races, request failure and retry."""
import json
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from e2e_audit import BASE,OUT,JD,RESUME_PAGES
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1500,'height':1000});p=ctx.new_page();p.set_default_timeout(15000)
 def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
 def ctl(**data):r=ctx.request.post('http://127.0.0.1:28649/qa/control',data=data);assert r.ok
 try:
  email='race-'+uuid4().hex[:8]+'@example.test';password='RaceTestPass123'
  ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data={'email':email,'password':password});ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':email})
  p.goto(BASE);nav('开始使用');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(email);f.locator('[name=password]').fill(password);f.locator('button').click();p.locator('.workspace').wait_for()
  nav('新建项目');p.get_by_label('项目名称',exact=True).fill('Race Regression');nav('创建');p.locator('#coach-language').select_option('zh-CN');p.locator('#user-stage').select_option('current_student');p.locator('#job-goal').select_option('internship');p.locator('#resume').fill('\n'.join(RESUME_PAGES));p.locator('#jd').fill(JD)
  ctl(delay=1,failure=None)
  with p.expect_request(lambda r:r.url.endswith('/materials/prepare')):nav('开始分析')
  p.locator('#jd').fill(JD+'\nPrepare content calendars.')
  expect(p.get_by_role('button',name='重新分析',exact=True)).to_be_enabled()
  assert p.get_by_text('材料已修改',exact=False).count()>0
  ctl(delay=0);nav('重新分析');expect(p.get_by_role('button',name='重新分析',exact=True)).to_be_disabled()
  nav('简历优化');ctl(delay=1)
  with p.expect_request(lambda r:r.url.endswith('/resume/optimize')):nav('生成改写建议')
  p.locator('#jd').fill(JD+'\nPrepare content calendars.\nMaintain campaign schedules.')
  expect(p.get_by_test_id('rewrite-O1')).to_be_visible()
  expect(p.get_by_text('简历、JD、岗位名称或求职选项已变更',exact=False)).to_be_visible()
  assert p.get_by_test_id('rewrite-O1').get_by_role('button',name='采用',exact=True).is_disabled()
  assert p.get_by_role('button',name='重新生成',exact=True).first.is_enabled()
  ctl(delay=0);p.get_by_role('button',name='重新生成',exact=True).first.click();expect(p.get_by_test_id('rewrite-O1').get_by_role('button',name='采用',exact=True)).to_be_enabled()
  ctl(failure='server');p.get_by_role('button',name='重新生成',exact=True).first.click();expect(p.get_by_role('alert')).to_contain_text('失败')
  ctl(failure=None);p.get_by_role('button',name='重试',exact=True).click();expect(p.get_by_test_id('rewrite-O1').get_by_role('button',name='采用',exact=True)).to_be_enabled()
  p.locator('[data-saved=true]').wait_for()
  p.evaluate("""async()=>{
   const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));
   const headers={Authorization:'Bearer '+a.access_token,'Content-Type':'application/json'};
   const all=await(await fetch('/v4/api/workspaces',{headers})).json();const project=all.find(x=>x.name==='Race Regression');
   const record=await(await fetch('/v4/api/workspaces/'+project.id,{headers})).json();delete record.state.materials.pipeline_version;
   const response=await fetch('/v4/api/workspaces/'+project.id,{method:'PUT',headers,body:JSON.stringify(record)});if(!response.ok)throw Error('fixture save failed');
  }""")
  p.reload();expect(p.get_by_text('材料解析已更新。',exact=False)).to_be_visible()
  expect(p.get_by_test_id('rewrite-O1').get_by_role('button',name='采用',exact=True)).to_be_enabled()
  with p.expect_request(lambda r:r.url.endswith('/materials/prepare')):p.get_by_role('button',name='重新生成',exact=True).first.click()
  expect(p.get_by_test_id('rewrite-O1').get_by_role('button',name='采用',exact=True)).to_be_enabled()
  p.locator('[data-saved=true]').wait_for();p.screenshot(path=str(OUT/'08-race-recovered.png'),full_page=True)
  (OUT/'race-results.json').write_text(json.dumps({'prepare_inflight_edit_marked_dirty':True,'optimize_inflight_edit_marked_stale':True,'regenerate_recovers':True,'server_failure_retry_recovers':True,'legacy_materials_refresh_before_new_analysis':True},indent=2))
  print('PASS prepare/optimize in-flight material edits correctly stale; regenerate and 503 retry recover')
 finally:
  ctl(delay=0,failure=None)
  if __import__('sys').exc_info()[0]:(OUT/'race-failure-body.txt').write_text(p.locator('body').inner_text())
  b.close()
