"""Small real DeepSeek workflow. Requires qa_server with QA_REAL_MODEL=1.
Authentication and Storage stay synthetic and PostgreSQL is disposable.
The server loads the existing private key; no key is passed here or printed.
"""
import json, re
from uuid import uuid4
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfReader
from docx import Document
from e2e_audit import BASE, OUT, RESUME_PAGES, JD
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome',headless=True)
 ctx=b.new_context(viewport={'width':1600,'height':1050},accept_downloads=True)
 p=ctx.new_page();p.set_default_timeout(75000);errors=[];calls=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 def response(r):
  if any(r.url.endswith(s) for s in ['/materials/prepare','/match','/resume/optimize']):calls.append({'path':r.url.split('/v3/')[-1],'status':r.status})
 p.on('response',response)
 def nav(name):p.get_by_role('button',name=name,exact=True).click()
 def save():p.locator('[data-saved=true]').wait_for()
 try:
  email='real-model-'+uuid4().hex[:10]+'@example.test';password='RealFlowPass123'
  ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data={'email':email,'password':password})
  ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':email})
  p.goto(BASE);nav('开始使用');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(email);f.locator('[name=password]').fill(password);f.locator('button').click()
  p.locator('.workspace').wait_for();nav('新建项目');p.get_by_label('项目名称',exact=True).fill('Real DeepSeek Marketing');nav('创建');p.locator('#resume').wait_for()
  q=ctx.new_page();q.set_content(''.join('<section style="white-space:pre-wrap;break-after:page">'+x+'</section>' for x in RESUME_PAGES));pdf=q.pdf();q.close()
  p.locator('input[type=file]').first.set_input_files({'name':'real-fictional.pdf','mimeType':'application/pdf','buffer':pdf});expect(p.locator('#resume')).to_contain_text('END OF ORIGINAL RESUME')
  p.locator('#jd').fill(JD);p.locator('#jobtitle').fill('Marketing Assistant')
  with p.expect_response(lambda r:r.url.endswith('/materials/prepare')) as prepare:nav('开始分析')
  result=prepare.value.json();assert prepare.value.status==200,result
  assert result['requirements'] and all(x['source_ids'] for x in result['requirements'])
  assert any(any(word in x['text'].lower() for word in ['marketing','campaign','营销','市场','行銷','營銷']) for x in result['requirements'])
  nav('岗位匹配')
  with p.expect_response(lambda r:r.url.endswith('/api/match')) as match:nav('生成匹配报告')
  matched=match.value.json();assert match.value.status==200,matched
  assert any(x['evidence'] for x in matched['items'])
  assert set(x['requirement_id'] for x in matched['items'])==set(x['id'] for x in result['requirements'])
  save();p.screenshot(path=str(OUT/'06-real-deepseek-match.png'),full_page=True)
  nav('简历优化')
  with p.expect_response(lambda r:r.url.endswith('/resume/optimize')) as resume:nav('生成改写建议')
  optimized=resume.value.json();assert resume.value.status==200,optimized;assert optimized['items']
  sources={x['id']:x['text'] for x in result['resume_lines']}
  assert all(x['original']==sources[x['source_id']] for x in optimized['items'])
  adopted=0
  for item in optimized['items']:
   row=p.get_by_test_id('rewrite-'+item['id'])
   if item['verification']['status']=='grounded' and adopted==0:
    row.get_by_role('button',name='采用',exact=True).click();adopted+=1
   else:row.get_by_role('button',name='保留原句',exact=True).click()
  assert adopted==1,'No grounded proposal to adopt'
  save()
  with p.expect_response(lambda r:r.url.endswith('/resume/final')) as final:nav('预览完整简历')
  full=final.value.json()['text'];expect(p.get_by_test_id('final-resume-text')).to_have_text(full)
  assert 'alex.taylor@example.test' in full and 'END OF ORIGINAL RESUME' in full
  expect(p.get_by_role('button',name='PDF',exact=True)).to_be_enabled()
  p.screenshot(path=str(OUT/'07-real-deepseek-final.png'),full_page=True)
  for fmt in ['PDF','DOCX']:
   with p.expect_download() as d:nav(fmt)
   path=OUT/('real-deepseek-final.'+fmt.lower());d.value.save_as(path)
   text='\n'.join(x.extract_text() for x in PdfReader(path).pages) if fmt=='PDF' else '\n'.join(x.text for x in Document(path).paragraphs)
   assert re.sub(r'\s+','',full) in re.sub(r'\s+','',text)
  p.reload();p.get_by_test_id('rewrite-'+optimized['items'][0]['id']).wait_for()
  with p.expect_response(lambda r:r.url.endswith('/resume/final')) as restored:nav('预览完整简历')
  assert restored.value.json()['text']==full
  assert len(calls)==3 and all(x['status']==200 for x in calls),calls
  assert not errors,errors
  (OUT/'real-deepseek-results.json').write_text(json.dumps({'mode':'REAL DeepSeek, synthetic Auth/Storage, real local PostgreSQL','calls':calls,'requirements':len(result['requirements']),'suggestions':len(optimized['items']),'adopted':adopted,'refresh_restored':True,'pdf_docx_complete':True,'page_errors':errors,'email':email},ensure_ascii=False,indent=2))
  print('PASS real DeepSeek: prepare, match, optimize; source-related results, adopt/keep, full PDF+DOCX, reload. Exactly 3 business calls.',flush=True)
 finally:
  if __import__('sys').exc_info()[0]:p.screenshot(path=str(OUT/'real-failure.png'),full_page=True);(OUT/'real-failure-body.txt').write_text(p.locator('body').inner_text())
  b.close()
