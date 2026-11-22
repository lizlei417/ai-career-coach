"""Real M3+RAG model/browser workflow. Local synthetic Auth, real disposable DB.
Set M3_HOSTED=1 for existing hosted disposable QA account (real Auth/Storage).
No model or URL responses are mocked; no original user projects are touched.
"""
import os,json,re,hashlib
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect,TimeoutError as BrowserTimeout
from pypdf import PdfReader
from docx import Document
from e2e_audit import RESUME_PAGES,JD
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence/m3';OUT.mkdir(exist_ok=True)
HOSTED=os.getenv('M3_HOSTED')=='1';BASE='https://ai-career-coach-three-versions.onrender.com/v3' if HOSTED else 'http://127.0.0.1:28649/v3'
mode='hosted' if HOSTED else 'local';stored=None;report={'mode':mode,'actual_model':True,'calls':[],'checks':[]};suffix=os.getenv('M3_CONTINUE_SUFFIX') or uuid4().hex[:6]
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome');ctx=b.new_context(viewport={'width':1640,'height':1120},accept_downloads=True);p=ctx.new_page();p.set_default_timeout(85000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
 def save():
  try:p.locator('[data-saved=true]').wait_for(timeout=25000)
  except BrowserTimeout:
   note=p.get_by_role('alert').filter(has_text=re.compile('Changes could not be saved|项目保存失败'))
   if note.count()!=1:raise
   note.get_by_role('button',name=re.compile('^(重试|重試|Retry)$')).click();p.locator('[data-saved=true]').wait_for(timeout=30000)
   report['save_retries']=report.get('save_retries',0)+1
 def snap(name):save();p.wait_for_timeout(250);p.screenshot(path=str(OUT/(mode+'-'+name+'.png')),full_page=True)
 def api(path):
  return p.evaluate('''async path=>{const key=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(key));const r=await fetch('/v3/api/'+path,{headers:{Authorization:'Bearer '+a.access_token}});return await r.json()}''',path)
 def create(name):nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.get_by_role('button',name=name,exact=True).wait_for();save();p.locator('#coach-language').select_option('zh-CN');p.locator('#user-stage').select_option('current_student');p.locator('#job-goal').select_option('internship')
 def call(route,button):
  for attempt in range(2):
   with p.expect_response(lambda r:r.url.endswith(route),timeout=85000) as response:
    nav(button) if attempt==0 else p.get_by_role('button',name=re.compile('^(重试|重試|Retry)$')).first.click()
   r=response.value;data=r.json();report['calls'].append({'route':route,'status':r.status,'language':data.get('lang'),'attempt':attempt+1})
   (OUT/(mode+'-'+str(len(report['calls']))+'-'+route.rsplit('/',1)[-1]+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
   if r.status!=200 and (data.get('error',{}).get('code')=='AI_FORMAT' or (r.status==503 and data.get('detail')=='Authentication unavailable')) and attempt==0:
    print('Observed request failure; testing one explicit UI retry',route,data.get('error',{}).get('code') or data.get('detail'),flush=True);continue
   assert r.status==200,data
   print('PASS real model',route,r.status,flush=True);return data

 try:
  if HOSTED:a=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[int(os.getenv('M3_ACCOUNT_INDEX','1'))]
  else:
   a={'email':'m3-real-'+suffix+'@example.test','password':'M3RealFlow123'}
   if not os.getenv('M3_CONTINUE_SUFFIX'):
    ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data=a);ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':a['email']})
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(a['email']);f.locator('[name=password]').fill(a['password']);f.locator('button').click();p.locator('.workspace').wait_for()
  report['quota_before']=api('quota')
  name='M3 Marketing '+suffix;report['first_project']=name
  if os.getenv('M3_CONTINUE_SUFFIX'):
   nav(name);record=next(x for x in api('workspaces') if x['name']==name);stored=api('workspaces/'+record['id'])['state'];original=stored['inputs']['resumeText'];optimized=stored['resume']['data'] if stored.get('resume') else None
   if optimized:report['calls'].append({'route':'/resume/optimize','status':200,'language':'en','reused_saved_actual_result':True})
  else:
   create(name)
   q=ctx.new_page();q.set_content(''.join('<section style="white-space:pre-wrap;break-after:page">'+x+'</section>' for x in RESUME_PAGES));pdf=q.pdf();q.close()
   p.locator('input[type=file]').first.set_input_files({'name':'m3-fictional.pdf','mimeType':'application/pdf','buffer':pdf});expect(p.locator('#resume')).to_contain_text('END OF ORIGINAL RESUME');p.locator('#jd').fill(JD);p.locator('#jobtitle').fill('Marketing Assistant')
   nav('预览');frame=p.locator('dialog iframe');frame.wait_for()
   raw=frame.evaluate('async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer()))');assert bytes(raw)==pdf
   report['original_pdf_preview_exact_bytes']=True;p.locator('dialog').get_by_role('button',name='关闭',exact=True).click()
   with p.expect_response(lambda r:r.url.endswith('/materials/prepare')) as preparation:nav('开始分析')
   prepared=preparation.value.json();assert preparation.value.status==200,prepared;report['prepared_requirements']=prepared['requirements']
   assert prepared['pipeline_version']=='m3-jd-sentences-v1'
   assert any(q['text']=='Bachelor degree in Marketing or a related discipline.' for q in prepared['requirements'])
   assert any(q['text']=='Clear written English and Cantonese communication.' for q in prepared['requirements'])
   expect(p.get_by_role('button',name='重新分析',exact=True)).to_be_disabled();save()
   original=p.locator('#resume').input_value();report['checks'].append('PDF extraction and deterministic preparation')
   p.get_by_role('radio',name='EN',exact=True).click();nav('Resume Optimization')
   optimized=call('/resume/optimize','Generate rewrites');assert optimized['m3']['prompt_version']=='M3_Prompt_v1';assert optimized['guidance']['sources'];assert optimized['items'],'No real edits returned'
  p.get_by_role('radio',name='EN',exact=True).click();nav('Resume Optimization')
  if optimized is None:optimized=call('/resume/optimize','Generate rewrites')
  assert all(re.sub(r'\s+','',x['original']) in re.sub(r'\s+','',original) for x in optimized['items']);snap('resume')
  for it in optimized['items']:
   if stored and stored.get('resume') and stored['resume']['decisions'].get(it['id'],{}).get('state') in ('adopted','kept','edited'):continue
   row=p.get_by_test_id('rewrite-'+it['id']);row.get_by_role('button',name='Adopt' if it['verification']['status']=='grounded' else 'Keep original',exact=True).click()
  save();p.get_by_role('radio',name='繁',exact=True).click();nav('職位配對')
  if stored and stored.get('match'):
   matched=stored['match']['data'];report['calls'].append({'route':'/api/match','status':200,'language':'zh-TW','reused_saved_actual_result':True})
  else:matched=call('/api/match','生成配對報告')
  assert matched['guidance']['sources'];assert any(x['evidence'] for x in matched['items']);assert all(x.get('priority_code') in ('required','preferred','unspecified') for x in matched['items']);snap('match')
  p.get_by_role('radio',name='简',exact=True).click();nav('模拟面试')
  if stored and stored['interview']['turns']:
   question=stored['interview']['turns'][0]['question'];report['calls'].append({'route':'/interview/question','status':200,'language':'zh-CN','reused_saved_actual_result':True})
  else:question=call('/interview/question','开始面试')
  assert question['question'];assert question['guidance']['sources'];snap('question')
  if not stored or not stored['interview']['turns'] or not stored['interview']['turns'][0]['attempts']:p.locator('textarea[placeholder]').last.fill('I prepared weekly campaign reports using Excel for the student society. I collected attendee feedback and organized the comments by topic to help the team plan campus communications.')
  if stored and stored['interview']['turns'] and stored['interview']['turns'][0]['attempts']:
   feedback=stored['interview']['turns'][0]['attempts'][-1]['feedback'];report['calls'].append({'route':'/interview/feedback','status':200,'language':'zh-CN','reused_saved_actual_result':True})
  else:feedback=call('/interview/feedback','提交回答')
  assert feedback['action'];snap('feedback')
  if stored and stored['interview'].get('summary'):
   summary=stored['interview']['summary'];report['calls'].append({'route':'/interview/summary','status':200,'language':'zh-CN','reused_saved_actual_result':True})
  elif not feedback.get('session_summary'):
   summary=call('/interview/summary','结束面试');assert summary['next_session'];assert summary['guidance']['sources']
  else:summary={'next_session':feedback['session_summary']}
  save();snap('summary');report['checks'].append('Three real M3 functions; English, traditional and simplified outputs')
  nav('简历优化');nav('预览完整简历');p.get_by_test_id('final-resume-text').wait_for();full=p.get_by_test_id('final-resume-text').inner_text();assert 'END OF ORIGINAL RESUME' in full and 'alex.taylor@example.test' in full
  for fmt in ['PDF','DOCX']:
   with p.expect_download() as download:nav(fmt)
   dest=OUT/(mode+'-final.'+fmt.lower());download.value.save_as(dest)
   text='\n'.join(x.extract_text() for x in PdfReader(dest).pages) if fmt=='PDF' else '\n'.join(x.text for x in Document(dest).paragraphs)
   assert re.sub(r'\s+','',full) in re.sub(r'\s+','',text)
  snap('final');nav('关闭预览');report['checks'].append('Adopt or keep; full PDF and DOCX reopen and contain preview')
  cv2='JORDAN MORGAN\nEXPERIENCE\nCreated Python scripts to clean inventory records for a university coursework project.\nTested data quality and documented validation methods with classmates.\nEDUCATION\nBSc Information Systems, Fictional University, 2026'
  jd2='Data Assistant\nResponsibilities\nClean inventory records using Python and document validation methods.\nRequirements\nAbility to explain data quality checks and work with a team.'
  second='M3 Data '+suffix;create(second);p.locator('#resume').fill(cv2);p.locator('#jd').fill(jd2);p.locator('#jobtitle').fill('Data Assistant');nav('开始分析');expect(p.get_by_role('button',name='重新分析',exact=True)).to_be_disabled();nav('岗位匹配');data2=call('/api/match','生成匹配报告');assert any(x['evidence'] for x in data2['items']);save()
  for _ in range(2):
   nav(name);expect(p.locator('#resume')).to_have_value(original);expect(p.locator('#jd')).to_have_value(JD);nav(second);expect(p.locator('#resume')).to_have_value(cv2);expect(p.locator('#jd')).to_have_value(jd2)
  p.reload();expect(p.locator('#resume')).to_have_value(cv2);expect(p.locator('#job-goal')).to_have_value('internship');nav(name);nav('模拟面试');expect(p.get_by_text(summary['next_session'],exact=True)).to_be_visible();save()
  report['checks'].append('Two projects analysed, saved, switched twice, reloaded; profiles, materials and interview restored')
  nav('设置');p.get_by_role('textbox',name='检索测试',exact=True).fill('STAR framework peers feedback')
  with p.expect_response(lambda r:r.url.endswith('/api/kb/search')) as retrieval:nav('检索测试')
  hits=retrieval.value.json();assert retrieval.value.status==200,hits;assert 'workshop-01' in [h['chunk_id'] for h in hits['results']];report['retrieval_sources']=[h['chunk_id'] for h in hits['results']];snap('rag-settings')
  health=api('health');assert health['llm']['connection']=='verified';assert health['kb']['integrity'] and health['kb']['chunks']==18;report['health']=health;report['quota_after']=api('quota')
  if not HOSTED:
   reqs=ctx.request.get('http://127.0.0.1:28649/qa/control').json()['requests'];assert len(reqs)==len(report['calls']);assert all(x['chunk_ids'] for x in reqs);report['request_metadata']=reqs
  assert not errors,errors;report['page_errors']=errors;report['result']='PASS';print('PASS complete real M3 browser workflow, two projects, exports and persisted results',flush=True)
 finally:
  if __import__('sys').exc_info()[0]:
   report['result']='FAIL';p.screenshot(path=str(OUT/(mode+'-failure.png')),full_page=True);(OUT/(mode+'-failure.txt')).write_text(p.locator('body').inner_text())
  (OUT/(mode+'-results.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));b.close()
