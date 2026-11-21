"""Real source imports through real app endpoints and project persistence.
Local Auth is synthetic; --hosted uses an existing disposable hosted QA account.
No fake JD responses and no AI calls. Error probes use real public HTTP endpoints.
"""
import sys,json,re,time
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence/jd-import'
hosted='--hosted' in sys.argv
BASE='https://ai-career-coach-three-versions.onrender.com/v3/' if hosted else 'http://127.0.0.1:28649/v3/'
mode='hosted' if hosted else 'local'
sources=json.loads((ROOT/'tests/jd_sources.json').read_text())
resume='ALEX TAYLOR\nFictional applicant for JD import testing only.\nMarketing volunteer with experience preparing weekly reports using Excel and coordinating campus communications.'
results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True)
 ctx=browser.new_context(viewport={'width':1500,'height':1000});p=ctx.new_page();p.set_default_timeout(40000)
 page_errors=[];requests=[];native=[]
 p.on('pageerror',lambda e:page_errors.append(str(e)))
 p.on('request',lambda r:requests.append(r) if r.url.endswith('/api/extract/url') else None)
 p.on('dialog',lambda d:(native.append(d.type),d.dismiss()))
 def nav(name):p.get_by_role('button',name=name,exact=True).click()
 def saved():p.locator('[data-saved=true]').wait_for()
 def create(name):
  nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.locator('main header').filter(has_text=name).wait_for();saved()
 def show_url():
  field=p.locator('input[placeholder="https://…"]')
  if not field.is_visible():nav('从链接导入')
  return field
 def import_url(url,success=True):
  field=show_url();field.fill(url)
  before=len(requests)
  with p.expect_response(lambda r:r.url.endswith('/api/extract/url')) as event:
   nav('导入')
   # During a real external request, both editable URL and JD are protected.
   expect(field).to_be_disabled()
   assert p.locator('#jd').is_disabled()
  response=event.value;body=response.json()
  assert response.request.method=='POST'
  assert response.request.post_data_json=={'url':url}
  assert len(requests)==before+1,'duplicate import request'
  if success:
   assert response.status==200,body
   expect(p.locator('#jd')).to_have_value(body['text']);expect(p.locator('#jd')).to_be_enabled()
  else:
   assert response.status==422,body
   expect(p.get_by_role('alert').filter(has_text=re.compile('.*'))).to_be_visible()
   expect(p.get_by_role('button',name='导入',exact=True)).to_be_enabled()
  return response.status,body
 try:
  if hosted:
   account=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[1]
   email,password=account['email'],account['password']
  else:
   email='jd-live-'+uuid4().hex[:8]+'@example.test';password='ImportRealPages123'
   ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data={'email':email,'password':password});ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':email})
  p.goto(BASE);nav('开始使用');form=p.locator('.auth-card >form');form.locator('[name=email]').fill(email);form.locator('[name=password]').fill(password);form.locator('button').click();p.locator('.workspace').wait_for()
  # Independent, disposable projects only. No existing project is edited.
  suffix=uuid4().hex[:6];blank='JD Empty '+suffix;create(blank)
  for source in sources:
   name='JD '+source['name']+' '+suffix;create(name)
   p.locator('#resume').fill(resume)
   status,data=import_url(source['url'])
   assert data['source']==source['parser']
   assert data['title']==source['expected_title']
   assert len(data['text'])>80
   if source['name']=='html':assert 'More jobs in Developer' not in data['text']
   if source['name']=='nowcoder':
    assert '岗位职责' in data['text'] and '岗位要求' in data['text']
    assert '牛客安全提示' not in data['text'] and '登录 / 注册' not in data['text']
    assert '已结束' in data['text']
   edited=data['text']+'\n\nUser edit for persistence verification '+suffix
   p.locator('#jd').fill(edited);saved()
   nav(blank);expect(p.locator('#jd')).to_have_value('');nav(name);expect(p.locator('#jd')).to_have_value(edited);expect(p.locator('#resume')).to_have_value(resume)
   saved();p.reload();expect(p.locator('#jd')).to_have_value(edited);expect(p.locator('#resume')).to_have_value(resume)
   show_url();p.screenshot(path=str(OUT/(mode+'-'+source['name']+'.png')),full_page=True)
   results.append({'source':source['name'],'url':source['url'],'status':status,'parser':data['source'],'chars':len(data['text']),'title':data['title'],'import_id':data['import_id'],'edited_saved_switched_reloaded':True})
   print('PASS',mode,source['name'],status,len(data['text']),'edit/save/switch/reload',flush=True)
  preserved=p.locator('#jd').input_value()
  failures=[('format','not a URL','URL_INVALID'),('not_found','https://job-boards.greenhouse.io/globalizationpartners/jobs/99999999999999999','URL_NOT_FOUND'),('denied','https://httpbingo.org/status/403','URL_ACCESS_DENIED'),('timeout','https://httpbingo.org/delay/15','URL_TIMEOUT'),('no_job','https://www.python.org/about/','URL_NO_CONTENT'),('private','http://127.0.0.1/private','URL_UNSAFE')]
  for label,url,code in failures:
   status,data=import_url(url,False);assert data['error']['code']==code,(label,data)
   expect(p.locator('#jd')).to_have_value(preserved);expect(p.locator('#resume')).to_have_value(resume)
   results.append({'error_case':label,'url':url,'status':status,'code':code,'detail':data['error']['detail'],'existing_materials_preserved':True})
   print('PASS',mode,label,code,flush=True)
  # Retry control after failure: correct the URL, then use the visible retry action.
  show_url().fill(next(x['url'] for x in sources if x['name']=='greenhouse'))
  with p.expect_response(lambda r:r.url.endswith('/api/extract/url')) as event:nav('重试')
  assert event.value.status==200,event.value.text()
  expect(p.locator('#jd')).to_have_value(event.value.json()['text']);saved()
  assert not page_errors,page_errors
  assert not native,native
  out={'mode':mode,'real_external_http':True,'ai_calls':0,'results':results,'retry_after_failure':True,'page_errors':page_errors,'native_dialogs':native}
  (OUT/(mode+'-e2e.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
  print('PASS',mode,'all real URL imports and failure/retry scenarios',flush=True)
 finally:
  if sys.exc_info()[0]:
   p.screenshot(path=str(OUT/(mode+'-failure.png')),full_page=True);(OUT/(mode+'-failure-body.txt')).write_text(p.locator('body').inner_text())
  browser.close()
