"""Real browser acceptance for complete resume documents and editing.
Run with the isolated REAL-model server, or QA_DOCUMENTS_HOSTED=1 against Render.
Only dedicated fictional QA accounts/projects are used. Never logs credentials.
"""
import io,json,os,re,sys
from pathlib import Path
from uuid import uuid4
from docx import Document
from pypdf import PdfReader
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tests/evidence';OUT.mkdir(exist_ok=True)
HOSTED=os.environ.get('QA_DOCUMENTS_HOSTED')=='1'
BASE='https://ai-career-coach-three-versions.onrender.com/v3' if HOSTED else 'http://127.0.0.1:28649/v3'
MOCK=os.environ.get('QA_DOCUMENTS_MOCK')=='1'
MODE='hosted' if HOSTED else 'local-mock' if MOCK else 'local-real'
REUSE=os.environ.get('QA_DOCUMENTS_REUSE')=='1'
CACHE=OUT/(MODE+'-documents-session.json')
PDF=Path('/Users/zhouli/Desktop/IS5542 生成式商业AI/product/林知夏_模拟简历_AI产品运营实习生.pdf')
JD='''AI 产品运营实习生
公司名称：星河智能科技（模拟公司）
工作地点：深圳 / 远程混合办公
岗位类型：实习，每周至少4天，实习期3至6个月。
岗位职责
协助 AI 产品的日常运营与用户增长，维护用户反馈数据库。
整理用户需求及竞品信息，协助产品经理提出功能改进建议。
参与新用户引导流程优化，跟进活动上线和跨部门执行进度。
使用 Excel 分析用户注册、活跃和留存数据，制作运营周报。
参与社交媒体内容运营，撰写产品介绍和活动文案。
任职要求
本科或硕士在读，市场营销、商业信息系统或相关专业。
熟悉 Excel 数据分析，具有用户调研、活动策划和团队协作经验。
对人工智能产品感兴趣，能够快速学习新工具。
加分项：了解 SQL，拥有互联网产品运营实习或项目经验。
'''
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome');ctx=browser.new_context(viewport={'width':1600,'height':1050},accept_downloads=True)
 p=ctx.new_page();p.set_default_timeout(30000);errors=[];calls=[];native=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('dialog',lambda d:(native.append(d.type),d.dismiss()))
 p.on('request',lambda r:calls.append(r.url) if r.url.endswith(('/resume/optimize','/api/match','/interview/question','/interview/feedback')) else None)
 def nav(label):p.get_by_role('button',name=label,exact=True).first.click()
 def save():p.locator('[data-saved=true]').wait_for()
 def api(path,method='GET',data=None):
  return p.evaluate('''async ([path,method,data])=>{const k=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));const a=JSON.parse(localStorage.getItem(k));const r=await fetch('/v3/api/'+path,{method,headers:{Authorization:'Bearer '+a.access_token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});if(!r.ok)throw Error('Test API '+r.status);return r.json()}''',[path,method,data])
 def login():
  p.goto(BASE+'/login');f=p.locator('.auth-card >form');f.locator('[name=email]').fill(account['email']);f.locator('[name=password]').fill(account['password']);f.locator('button').click();p.locator('.workspace').wait_for()
 def create(name):
  nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.get_by_role('button',name=name,exact=True).wait_for();save()
 def preview_files(expected,suffix):
  files={}
  nav('预览完整简历')
  with p.expect_popup() as pop:nav('PDF 预览')
  pdfpage=pop.value;pdfpage.wait_for_url('blob:**');pdfpage.wait_for_timeout(1400)
  pdfpage.screenshot(path=str(OUT/f'{MODE}-pdf-{suffix}.png'))
  pdfpage.close()
  nav('预览完整简历')
  with p.expect_popup() as pop:nav('Word（DOCX）预览')
  word=pop.value;word.set_default_timeout(60000);word.locator('section.docx').first.wait_for()
  word.wait_for_function('document.fonts.status === "loaded"');word.wait_for_timeout(500)
  assert expected in word.locator('body').inner_text()
  heights=word.locator('section.docx').evaluate_all('es=>es.map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,content:e.querySelector("article").scrollHeight}))')
  assert all(x['width']>700 and x['height']>1000 for x in heights),heights
  word.screenshot(path=str(OUT/f'{MODE}-word-{suffix}.png'),full_page=True)
  with word.expect_download() as d:word.get_by_role('link',name='下载 DOCX',exact=True).click()
  docx=OUT/f'{MODE}-complete-{suffix}.docx';d.value.save_as(docx);files['docx']=str(docx)
  text='\n'.join(x.text for x in Document(docx).paragraphs);assert expected in text
  word.close()
  with p.expect_download() as d:p.get_by_role('button',name='PDF',exact=True).click()
  pdf=OUT/f'{MODE}-complete-{suffix}.pdf';d.value.save_as(pdf);files['pdf']=str(pdf)
  parsed=PdfReader(pdf);pdftext='\n'.join(x.extract_text() for x in parsed.pages)
  assert re.sub(r'\s+','',expected) in re.sub(r'\s+','',pdftext)
  assert all(abs(float(x.mediabox.width)-595.28)<1 for x in parsed.pages)
  return {'files':files,'pdf_pages':len(parsed.pages),'word_pages':len(heights),'layout':heights}
 try:
  if REUSE:account=json.loads(CACHE.read_text())['account']
  elif HOSTED:account=json.loads((Path.home()/'.config/ai-career-coach/qa-accounts.json').read_text())[1]
  else:
   account={'email':'documents-'+uuid4().hex[:8]+'@example.test','password':'DocumentsQA123'}
   ctx.request.post('http://127.0.0.1:28648/auth/v1/signup',data=account);ctx.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':account['email']})
  login();name=json.loads(CACHE.read_text())['name'] if REUSE else '文档验收 '+uuid4().hex[:6]
  if REUSE:nav(name)
  else:create(name)
  if not p.locator('#resume').is_visible():nav('工作台')
  if not REUSE:
   p.locator('#coach-language').select_option('zh-CN');p.locator('#user-stage').select_option('current_student');p.locator('#job-goal').select_option('internship')
   p.locator('input[type=file]').first.set_input_files(str(PDF));expect(p.locator('#resume')).to_contain_text('林知夏');original=p.locator('#resume').input_value();p.locator('#jd').fill(JD);save()
   original_file=api('workspaces/'+next(x['id'] for x in api('workspaces') if x['name']==name))['state']['inputs']['resumeFile']
   quota=api('quota')['used'];assert quota<10
   nav('开始分析');p.get_by_text('项岗位要求',exact=False).first.wait_for();nav('简历优化')
   with p.expect_response(lambda r:r.url.endswith('/resume/optimize'),timeout=120000) as response:nav('生成改写建议')
   assert response.value.status==200,response.value.status
   model_status=response.value.status
   CACHE.write_text(json.dumps({'account':account,'name':name,'quota':quota,'status':model_status}))
   CACHE.chmod(0o600)
  else:
   cached=json.loads(CACHE.read_text());quota=cached['quota'];model_status=cached['status']
   project_id=next(x['id'] for x in api('workspaces') if x['name']==name)
   reset=api('workspaces/'+project_id);reset['state'].pop('finalResume',None);reset['state'].pop('finalResumeHistory',None);reset['state']['resume']['decisions']={};api('workspaces/'+project_id,'PUT',reset);p.reload()
   original=api('workspaces/'+project_id)['state']['inputs']['resumeText'];original_file=api('workspaces/'+project_id)['state']['inputs']['resumeFile']
   p.locator('main header').get_by_role('button',name='简历优化',exact=True).click()
  rows=p.locator('[data-testid^=rewrite-]');expect(rows.first).to_be_visible(timeout=120000)
  adopt=rows.get_by_role('button',name='采用',exact=True)
  available=[adopt.nth(i) for i in range(adopt.count()) if adopt.nth(i).is_enabled()]
  assert available,'Actual AI produced no safely adoptable suggestion; do not pretend passed'
  available[0].click();save();expect(p.get_by_test_id('final-resume-text')).to_contain_text('林知夏')
  project_id=next(x['id'] for x in api('workspaces') if x['name']==name)
  initial_text=api('workspaces/'+project_id+'/resume/final')['text']
  expect(p.get_by_test_id('final-resume-text')).to_have_text(initial_text)
  initial_files=preview_files('林知夏','adopted')
  edit=p.get_by_test_id('edit-complete-resume');preview=p.get_by_role('button',name='预览完整简历',exact=True)
  eb,pb=edit.bounding_box(),preview.bounding_box();assert abs((eb['x']+eb['width'])-(pb['x']+pb['width']))<1;assert eb['width']<pb['width'];assert abs(eb['y']-(pb['y']+pb['height'])-8)<1
  color=edit.evaluate('e=>getComputedStyle(e).backgroundColor');assert color=='rgb(17, 24, 39)',color
  edit.click();editor=p.get_by_test_id('final-resume-editor');expect(editor).to_have_value(initial_text)
  edited=initial_text.replace('林知夏','林知夏（文档测试）',1)+'\n补充技能\nSQL 数据整理；繁體中文：使用者研究與團隊協作。\nDOCUMENT_ACCEPTANCE_END'
  editor.fill(edited)
  expect(p.locator('main header [data-saved=false]')).to_contain_text('尚未保存')
  p.locator('main').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(OUT/f'{MODE}-resume-editing.png'))
  # Unsaved tab switch and regeneration must use custom dialogs; cancel preserves draft.
  p.locator('main header').get_by_role('button',name='岗位匹配',exact=True).evaluate('e=>{e.click();e.click()}');expect(p.get_by_role('dialog')).to_have_count(1);expect(p.get_by_role('dialog')).to_contain_text('尚未保存');nav('取消');expect(editor).to_have_value(edited)
  nav('重新生成');expect(p.get_by_role('dialog')).to_contain_text('替换');nav('确认');expect(p.get_by_role('dialog')).to_contain_text('尚未保存');nav('取消');expect(editor).to_have_value(edited)
  # Failed save retains the textarea and all user content.
  def fail(route):
   if route.request.method=='PUT':route.fulfill(status=503,json={})
   else:route.continue_()
  p.route('**/api/workspaces/*',fail);edit.click();expect(p.get_by_role('alert').filter(has_text='草稿已保留')).to_be_visible();expect(editor).to_have_value(edited)
  p.unroute('**/api/workspaces/*',fail);p.get_by_role('button',name='重试',exact=True).first.click();expect(p.get_by_role('alert').filter(has_text='项目保存失败')).to_have_count(0);expect(editor).to_have_value(edited)
  assert api('workspaces/'+project_id)['state']['finalResume']['version']==1
  edit.click();expect(editor).to_have_count(0);save();expect(p.get_by_role('status').filter(has_text='简历已保存')).to_be_visible()
  assert api('workspaces/'+project_id)['state']['finalResume']['version']==2
  expect(p.locator('#resume')).to_have_value(original)
  document_files=preview_files('DOCUMENT_ACCEPTANCE_END','edited')
  expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  p.reload();expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  other_name='独立项目 '+uuid4().hex[:6];create(other_name);p.locator('#resume').fill('Other fictional candidate');save();nav(name);expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  # Recovery draft persists an intentional browser reload without a fake custom reload dialog.
  edit.click();editor.fill(edited+'\nRECOVERABLE_DRAFT');nav(other_name);expect(p.get_by_role('dialog')).to_contain_text('尚未保存');nav('确认');nav(name);expect(p.get_by_test_id('final-resume-editor')).to_have_value(edited+'\nRECOVERABLE_DRAFT');p.reload();expect(p.get_by_test_id('final-resume-editor')).to_have_value(edited+'\nRECOVERABLE_DRAFT');p.get_by_test_id('final-resume-editor').fill(edited);edit.click();save()
  for feature in ['岗位匹配','模拟面试','简历优化']:
   p.locator('main header').get_by_role('button',name=feature,exact=True).click();expect(p.locator('main header [aria-current=page]')).to_have_text(feature);expect(p.locator('aside nav [aria-current=page]')).to_contain_text(feature)
  expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  # Further review decisions must never replace the saved full-document edit.
  rows=p.locator('[data-testid^=rewrite-]');undo=rows.get_by_role('button',name='撤销',exact=True)
  if undo.count():undo.first.click();save();expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  record=api('workspaces/'+next(x['id'] for x in api('workspaces') if x['name']==name));assert record['state']['finalResume']['text']==edited
  assert record['state']['inputs']['resumeText']==original and record['state']['inputs']['resumeFile']==original_file
  assert api('quota')['used']==quota+1;assert len(calls)==(0 if REUSE else 1),calls
  # Three interface languages, using existing global language controls.
  for label,expected in [('繁','編輯'),('EN','Edit'),('简','编辑')]:
   p.get_by_role('radio',name=label,exact=True).click();expect(edit).to_have_text(expected);save()
  p.locator('main').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(OUT/f'{MODE}-resume-editor-complete.png'),full_page=True)
  p.locator('.account-tools >button').click();nav('退出登录');p.get_by_role('button',name='开始使用',exact=True).wait_for();login();nav(name);p.locator('main header').get_by_role('button',name='简历优化',exact=True).click();expect(p.get_by_test_id('final-resume-text')).to_have_text(edited)
  assert not errors,errors;assert not native,native
  result={'mode':MODE,'model_mode':'explicit MOCK' if MOCK else 'real DeepSeek','model_calls_this_run':len(calls),'reused_prior_real_analysis':REUSE,'model_status':model_status,'project':name,'adopted_files':initial_files,'edited_files':document_files,'inline_edit':True,'failed_save_retains_draft':True,'reload_recovery':True,'refresh_project_logout_persistence':True,'source_unchanged':True,'navigation_zero_extra_model_calls':True,'three_languages':True,'button_right_alignment_gap_8px_fixed_96px':True,'errors':errors,'native_dialogs':native}
  (OUT/f'{MODE}-documents-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('PASS',MODE,'MOCK optimize' if MOCK else 'real AI optimize', '→ adopt → PDF/DOCX rendered previews → edit/save/failure recovery → persistence; quota +1 only',flush=True)
 finally:
  if sys.exc_info()[0]:
   p.screenshot(path=str(OUT/f'{MODE}-documents-failure.png'),full_page=True);(OUT/f'{MODE}-documents-failure.txt').write_text(p.locator('body').inner_text())
  browser.close()
