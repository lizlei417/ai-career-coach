"""Verification recovery UI using explicitly MOCKED Supabase Auth responses.
Real built frontend/SDK/browser. Sends no emails and calls no model.
Set QA_MAIL_HOSTED=1 to run the same safely intercepted UI check on Render.
"""
import os,json
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence'
HOSTED=os.environ.get('QA_MAIL_HOSTED')=='1';BASE='https://ai-career-coach-three-versions.onrender.com/v4' if HOSTED else 'http://127.0.0.1:28649/v4'
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1100,'height':1000});p=ctx.new_page();p.set_default_timeout(15000)
 requests=[];status={'value':200};errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 def auth(route):
  req=route.request
  if req.method=='OPTIONS':route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'});return
  endpoint=req.url.split('/auth/v1/')[-1].split('?')[0]
  body=req.post_data_json if req.method=='POST' else None
  requests.append({'endpoint':endpoint,'body':body,'url':req.url})
  headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json','X-Supabase-Api-Version':'2024-01-01','Access-Control-Expose-Headers':'X-Supabase-Api-Version'}
  if endpoint=='signup':payload={'id':str(uuid4()),'email':'verification@example.test','identities':[],'aud':'authenticated','role':'authenticated','created_at':'2026-11-22T00:00:00Z','app_metadata':{},'user_metadata':{}};code=200
  elif endpoint=='token':payload={'code':'email_not_confirmed','msg':'Email not confirmed'};code=400
  elif endpoint=='resend':
   code=status['value'];payload={} if code==200 else {'code':'over_email_send_rate_limit' if code==429 else 'unexpected_failure','msg':'Synthetic mail failure'}
  else:payload={};code=200
  route.fulfill(status=code,headers=headers,body=json.dumps(payload))
 ctx.route('**/auth/v1/**',auth)
 try:
  p.clock.install();p.goto(BASE+'/signup');form=p.locator('.auth-card >form')
  form.locator('[name=email]').fill('verification@example.test');form.locator('[name=password]').fill('Verification123');form.locator('[name=confirm]').fill('Verification123');form.locator('button').click()
  expect(p.get_by_role('status')).to_contain_text('垃圾邮件');box=p.locator('.auth-verification');expect(box).to_contain_text('verification@example.test');expect(box).to_contain_text('Confirm your email address')
  button=box.get_by_role('button');expect(button).to_be_disabled();p.clock.fast_forward(61000);expect(button).to_be_enabled()
  button.evaluate('e=>{e.click();e.click()}');expect(p.get_by_role('status')).to_contain_text('重新发送请求已提交');expect(button).to_be_disabled()
  calls=[r for r in requests if r['endpoint']=='resend'];assert len(calls)==1,calls
  assert calls[0]['body']['type']=='signup' and calls[0]['body']['email']=='verification@example.test'
  assert parse_qs(urlsplit(calls[0]['url']).query)['redirect_to']==[BASE+'/auth/callback'],calls[0]['url']
  p.clock.fast_forward(61000);status['value']=503;button.click();expect(p.get_by_role('alert')).to_contain_text('暂时无法发送');expect(button).to_be_enabled();expect(p.get_by_role('status')).to_have_count(0)
  status['value']=429;button.click();expect(p.get_by_role('alert')).to_contain_text('发送过于频繁');expect(button).to_be_disabled()
  p.clock.fast_forward(61000);status['value']=200;button.click();expect(p.get_by_role('status')).to_contain_text('重新发送请求已提交')
  p.screenshot(path=str(OUT/('hosted-mail-recovery.png' if HOSTED else 'local-mail-recovery.png')))
  p.locator('.auth-card nav').get_by_role('button',name='登录',exact=True).click();form.locator('[name=email]').fill('verification@example.test');form.locator('[name=password]').fill('Verification123');form.locator('button').click();expect(p.get_by_role('alert')).to_contain_text('请先验证邮箱');expect(box).to_be_visible();expect(box).to_contain_text('verification@example.test')
  form.locator('[name=email]').fill('different@example.test');expect(box).to_have_count(0)
  for lang in ['zh-TW','en','zh-CN']:
   p.locator('.auth-card header select').select_option(lang);form.locator('button').click();expect(box).to_be_visible();assert box.get_by_role('button').inner_text()
  assert not errors,errors
  report={'environment':'Render frontend' if HOSTED else 'local built frontend','auth_mode':'explicit MOCK, no emails sent','signup_and_unconfirmed_login_recovery':True,'callback_correct':True,'cooldown_and_duplicate_click_one_request':True,'503_no_false_success_and_retry':True,'429_cooldown':True,'changing_address_hides_old_recovery':True,'three_languages':True,'page_errors':errors}
  (OUT/('hosted-mail-recovery.json' if HOSTED else 'local-mail-recovery.json')).write_text(json.dumps(report,indent=2));print('PASS verification recovery signup/login, SDK request, callback, duplicate/cooldown, 503, 429, retry and three languages; Auth explicitly MOCK, no emails sent')
 finally:
  if __import__('sys').exc_info()[0]:(OUT/'mail-recovery-failure.txt').write_text(p.locator('body').inner_text())
  b.close()
