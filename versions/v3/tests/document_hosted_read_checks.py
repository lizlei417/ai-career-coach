"""Read-only hosted document regression. Dedicated fictional QA identity only.
No AI request and no production workspace mutation; credentials are never printed.
"""
import hashlib,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence'
BASE='https://ai-career-coach-three-versions.onrender.com/v3'
account=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[1]
result=json.loads((OUT/'hosted-documents-results.json').read_text());name=result['project']
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1600,'height':1050});p=ctx.new_page();p.set_default_timeout(30000);console=[];errors=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
 def api(path):
  return p.evaluate('''async path=>{const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));const r=await fetch('/v3/api/'+path,{headers:{Authorization:'Bearer '+a.access_token}});if(!r.ok)throw Error('Read check '+r.status);return r.json()}''',path)
 try:
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(account['email']);f.locator('[name=password]').fill(account['password']);f.locator('button').click();p.locator('.workspace').wait_for()
  p.get_by_role('button',name=name,exact=True).click();p.locator('main header').get_by_role('button',name='简历优化',exact=True).click();expect(p.get_by_test_id('final-resume-text')).to_contain_text('DOCUMENT_ACCEPTANCE_END')
  quota=api('quota');pid=next(x['id'] for x in api('workspaces') if x['name']==name);state=api('workspaces/'+pid)['state'];health=api('health')
  assert health['kb']['connected'] and health['kb']['integrity'] and len(health['kb']['files'])==4
  assert state['resume']['data']['guidance']['connected'] and state['resume']['data']['guidance']['sources']
  p.get_by_role('button',name='预览',exact=True).click();frame=p.locator('dialog iframe');frame.wait_for()
  data=frame.evaluate('async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer()))')
  original=Path('/Users/zhouli/Desktop/IS5542 生成式商业AI/product/林知夏_模拟简历_AI产品运营实习生.pdf').read_bytes()
  assert hashlib.sha256(bytes(data)).digest()==hashlib.sha256(original).digest()
  p.locator('dialog').get_by_role('button',name='关闭',exact=True).click()
  assert api('quota')==quota;assert not errors,errors;assert not console,console
  (OUT/'hosted-document-read-checks.json').write_text(json.dumps({'model_connection':health['llm'].get('connection'),'kb_integrity':True,'kb_files':len(health['kb']['files']),'kb_chunks':health['kb']['chunks'],'real_result_guidance_sources':len(state['resume']['data']['guidance']['sources']),'original_pdf_preview_bytes_unchanged':True,'quota_unchanged':True,'page_errors':errors,'console_errors':console},ensure_ascii=False,indent=2))
  print('PASS hosted real RAG/model health, original PDF preview bytes, saved full resume, zero new AI usage and zero console/page errors')
 finally:b.close()
