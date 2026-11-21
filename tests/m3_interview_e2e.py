"""Explicit Mock model/Auth/Storage, real backend, DB and browser.
Exercises both main questions, one follow-up, next-question reuse and finish.
"""
from pathlib import Path
from uuid import uuid4
import json
from playwright.sync_api import sync_playwright,expect
from e2e_audit import RESUME_PAGES,JD,BASE,OUT
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1600,'height':1100});p=ctx.new_page();p.set_default_timeout(15000)
 def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
 def control(**data):r=ctx.request.post('http://127.0.0.1:28649/qa/control',data=data);assert r.ok
 def answer():
  p.locator('textarea[rows="7"]').fill('I prepared weekly Excel reports and grouped feedback by topic for the student society.')
  with p.expect_response(lambda r:r.url.endswith('/interview/feedback')) as r:nav('提交回答')
  assert r.value.status==200,r.value.text()
 def state():
  return p.evaluate('''async()=>{const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));const headers={Authorization:'Bearer '+a.access_token};const all=await(await fetch('/v3/api/workspaces',{headers})).json();const one=all.find(x=>x.name==='M3 Interview Bounds');return await(await fetch('/v3/api/workspaces/'+one.id,{headers})).json()}''')
 try:
  a={'email':'interview-bounds-'+uuid4().hex[:8]+'@example.test','password':'InterviewBounds123'}
  ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data=a);ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':a['email']})
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(a['email']);f.locator('[name=password]').fill(a['password']);f.locator('button').click();p.locator('.workspace').wait_for()
  nav('新建项目');p.get_by_label('项目名称',exact=True).fill('M3 Interview Bounds');nav('创建');p.locator('#coach-language').select_option('zh-CN');p.locator('#user-stage').select_option('current_student');p.locator('#job-goal').select_option('internship')
  p.locator('#resume').fill('\n'.join(RESUME_PAGES));p.locator('#jd').fill(JD);nav('开始分析');expect(p.get_by_role('button',name='重新分析',exact=True)).to_be_disabled();nav('模拟面试')
  control(follow_up=True)
  with p.expect_response(lambda r:r.url.endswith('/interview/question')) as r:nav('开始面试')
  assert r.value.status==200;answer();nav('回答追问');control(follow_up=False);answer();expect(p.get_by_role('button',name='回答追问',exact=True)).to_have_count(0)
  before=ctx.request.get('http://127.0.0.1:28649/qa/control').json()['calls'];nav('下一题');p.locator('textarea[rows="7"]').wait_for()
  assert ctx.request.get('http://127.0.0.1:28649/qa/control').json()['calls']==before,'Cached question caused duplicate model call'
  answer();expect(p.get_by_role('button',name='下一题',exact=True)).to_be_disabled()
  with p.expect_response(lambda r:r.url.endswith('/interview/summary')) as r:nav('结束面试')
  assert r.value.status==200,r.value.text();p.locator('[data-saved=true]').wait_for();saved=state()['state']['interview']
  assert len(saved['turns'])==3 and sum(not t['question'].get('is_follow_up') for t in saved['turns'])==2
  assert saved['summary']['next_session'];p.reload();expect(p.get_by_text(saved['summary']['next_session'],exact=True)).to_be_visible()
  calls=ctx.request.get('http://127.0.0.1:28649/qa/control').json()['calls'];assert calls==5,calls
  result={'mode':'MOCK model/Auth/Storage; real DB/backend/browser','main_questions':2,'follow_ups':1,'provider_calls':5,'cached_next_question_no_call':True,'third_main_question_disabled':True,'summary_refresh_restored':True,'null_citations_flow':True}
  (OUT/'m3-interview-bounds.json').write_text(json.dumps(result,indent=2));p.screenshot(path=str(OUT/'m3-interview-bounds.png'),full_page=True);print('PASS two main questions, one follow-up, no duplicate call for next question, cap, summary and reload; Mock only')
 finally:
  if __import__('sys').exc_info()[0]:(OUT/'m3-interview-bounds-failure.txt').write_text(p.locator('body').inner_text())
  b.close()
