import os,sys,time,subprocess,socket,signal
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import urllib.request
base=Path.cwd()
if not os.getenv('QA_PYTHON'):
 raise RuntimeError('Set QA_PYTHON to the isolated Python environment with backend dependencies')
env=dict(os.environ,COACH_APPS='/tmp/coachcloudtest/apps',DATABASE_URL='postgresql://postgres@127.0.0.1:28547/coachtestbrowser2',SUPABASE_URL='http://127.0.0.1:28548',SUPABASE_PUBLISHABLE_KEY='sb_publishable_offline',SUPABASE_SECRET_KEY='sb_secret_offline',DEEPSEEK_API_KEY='offline-test-only')
log=open('/tmp/coachcloudtest/browser-gateway.log','w')
def start(name,port,cwd):
 proc=subprocess.Popen([os.environ['QA_PYTHON'],'-m','uvicorn',name+':app','--port',str(port),'--no-access-log'],cwd=cwd,env=env,stdout=log,stderr=log)
 for i in range(120):
  if proc.poll()!=None:raise RuntimeError(name+' exited')
  try:
   with socket.create_connection(('127.0.0.1',port),.5):return proc
  except OSError:time.sleep(.1)
 raise TimeoutError(name)
def stop(proc):
 proc.terminate();proc.wait(timeout=8)
fixture=start('auth_fixture',28548,'/tmp/coachcloudtest');gw=start('gateway',28549,base/'auth-v2/deploy')
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel="chrome",headless=True)
  ctx=browser.new_context(viewport={'width':1366,'height':900})
  page=ctx.new_page()
  page.set_default_timeout(9000)
  page.on('pageerror',lambda e:print('PAGE ERROR',e,flush=True))
  def openapp(version,who='a',password='fixture-password'):
   page.goto('http://127.0.0.1:28549/'+version+'/')
   form=page.locator('.account-enter form')
   form.locator('[name=email]').fill(who+'@example.test')
   form.locator('[name=password]').fill(password)
   form.locator('button').click()
   page.locator('.account-tools').wait_for()
  def signout():
   page.locator('.account-tools >button').click()
   page.locator('.account-tools section > button').click()
   page.locator('.account-enter').wait_for()
  for ver in ['v1','claude','v2']:
   openapp(ver)
   page.get_by_role('button',name='开始使用',exact=True).or_(page.get_by_role('button',name='Get started',exact=True)).first.click()
   print('Opened private workbench',ver,flush=True)
   if ver=='v2':break
   if ver=='v1':
    page.locator('#resume').fill('Account A, version one.')
    page.wait_for_timeout(700)
    page.reload();expect(page.locator('#resume')).to_have_value('Account A, version one.')
   signout()
  page.locator('#jd').fill('Fictional role, project one.')
  pdfpage=ctx.new_page()
  pdfpage.set_content(''.join('<section style="break-after:page">Synthetic experience on page '+str(i)+'. Documenting volunteer research and analysis.</section>' for i in range(1,4)))
  pdf=pdfpage.pdf();pdfpage.close()
  page.locator('input[type=file]').first.set_input_files(dict(name='demo.pdf',mimeType='application/pdf',buffer=pdf))
  expect(page.locator('#resume')).to_contain_text('page 3')
  page.get_by_role('button',name='新建项目',exact=True).click()
  page.get_by_label('项目名称').fill('Second fixture');page.get_by_role('button',name='创建',exact=True).click()
  expect(page.locator('#jd')).to_have_value('')
  page.get_by_role('button',name='我的第一个项目').click()
  page.locator('[data-saved=true]').wait_for()
  stop(gw);gw=start('gateway',28549,base/'auth-v2/deploy')
  page.reload()
  expect(page.locator('#jd')).to_have_value('Fictional role, project one.')
  page.get_by_role('button',name='预览',exact=True).click()
  frame=page.locator('dialog iframe')
  data=frame.evaluate("async el=>Array.from(new Uint8Array(await (await fetch(el.src)).arrayBuffer()))")
  assert bytes(data)==pdf
  page.get_by_role('button',name='关闭',exact=True).click()
  for lang in ['EN','繁','简']:
   page.get_by_role('radio',name=lang,exact=True).click()
   page.locator('[data-saved=true]').wait_for()
  signout()
  openapp('v2','b')
  page.get_by_role('button',name='开始使用',exact=True).click()
  expect(page.locator('#jd')).to_have_value('')
  page.locator('#jd').fill('B private fixture');page.locator('[data-saved=true]').wait_for()
  signout();openapp('v2')
  page.get_by_role('button',name='设置',exact=True).click()
  expect(page.get_by_text('5 / 5',exact=False)).to_be_visible()
  dialogs=[]
  def confirm(d):
   dialogs.append(d.type);d.accept()
  page.on('dialog',confirm)
  page.get_by_role('button',name='清除我的数据',exact=True).click()
  page.get_by_role('button',name='开始使用',exact=True).wait_for()
  assert dialogs[:3]==['confirm','confirm','alert'],dialogs
  page.locator('.account-tools >button').click()
  page.locator('.account-tools input[name=password]').fill('fixture-changed')
  page.locator('.account-tools form button').click()
  expect(page.locator('.account-tools [role=status]')).to_be_visible()
  page.locator('.account-tools section >button').click()
  page.locator('.account-enter').wait_for()
  openapp('v2','b');expect(page.locator('#jd')).to_have_value('B private fixture')
  signout();openapp('v1','a','fixture-changed');expect(page.locator('#resume')).to_have_value('Account A, version one.')
  print('PASS browser sign-in/out/account switch/password change, V1+V2 persistence, two V2 projects, PDF byte equality after server restart, three languages, confirmed deletion and B survived.')
  browser.close()
finally:
 stop(gw);stop(fixture)
