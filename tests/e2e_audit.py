"""Browser E2E against the local QA server. Auth and model are explicitly mocked;
workspace persistence/revisions, quota, PDF extraction and exports are real.
Run: QA_PYTHON tests/run_audit.py (see tests/README.md).
"""
import io, json, sys, time, re
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
from pypdf import PdfReader
from docx import Document
BASE='http://127.0.0.1:28649/v4/'
OUT=Path(__file__).resolve().parent/'evidence';OUT.mkdir(exist_ok=True)
RESUME_PAGES=[
 'ALEX TAYLOR\nalex.taylor@example.test | Hong Kong\nSUMMARY\nMarketing graduate with experience supporting campus communications and campaign reporting.\nEXPERIENCE\nStudent Marketing Volunteer | Example Student Society | 2025-2026\nHelped coordinate email campaigns and prepare weekly marketing reports using Excel for the student society.',
 'PROJECTS\nCampus Arts Campaign | Example University | 2025\nCreated social media posts and tracked event registrations with the campus communications team.\nWorked with student volunteers to organize event schedules and collect attendee feedback for planning.',
 'EDUCATION\nBBA Marketing, Example University, 2026\nSKILLS\nExcel, PowerPoint, English and Cantonese\nVOLUNTEERING\nAssisted the student community centre with event registration and maintained accurate attendance records.\nEND OF ORIGINAL RESUME'
]
JD='''Marketing Assistant - Example Harbour Studio
Responsibilities
Support marketing campaigns, coordinate email communications and maintain social media content calendars.
Prepare weekly campaign reports using Excel and collect customer feedback.
Requirements
Bachelor degree in Marketing or a related discipline. Clear written English and Cantonese communication.
Organized team player with experience coordinating events. Entry level candidates are welcome.
Preferred
Basic knowledge of digital marketing analytics.'''
results=[]
def record(name,details=''):
 results.append({'test':name,'result':'PASS','details':details});print('PASS',name,details,flush=True)

def exercise(baseline=False):
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  context=browser.new_context(viewport={'width':1600,'height':1050},accept_downloads=True)
  context.tracing.start(screenshots=True,snapshots=True,sources=True)
  p=context.new_page();p.set_default_timeout(12000)
  page_errors=[];native=[]
  p.on('pageerror',lambda e:page_errors.append(str(e)))
  p.on('response', lambda r: print('HTTP ERROR',r.status,r.url.split('?')[0],flush=True) if r.status>=400 else None)
  p.on('dialog',lambda d:(native.append(d.type),d.dismiss()))
  def save():p.locator('[data-saved=true]').wait_for()
  def snap(name):p.screenshot(path=str(OUT/(name+'.png')),full_page=True)
  def nav(name):p.get_by_role('button',name=name,exact=True).first.click()
  def api(path,method='GET',data=None):
   return p.evaluate('''async ([path,method,data])=>{
     const key=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));
     const auth=JSON.parse(localStorage.getItem(key));
     const r=await fetch('/v4/'+path,{method,headers:{Authorization:'Bearer '+auth.access_token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});
     return {status:r.status,body:await r.json()};
   }''',[path,method,data])
  def project_state():
   projects=api('api/workspaces')['body']
   return api('api/workspaces/'+next(x['id'] for x in projects if x['name']=='Marketing Assistant'))['body']
  def create(name):
   nav('新建项目');p.get_by_label('项目名称',exact=True).fill(name);nav('创建');p.get_by_role('button',name=name,exact=True).wait_for();save()
  def review_row(i):return p.get_by_test_id('rewrite-O'+str(i))
  def preview():
   save()
   expected=api('api/workspaces/'+project_state()['id']+'/resume/final')['body']['text']
   expect(p.get_by_test_id('final-resume-text')).to_have_text(expected)
   return p.get_by_test_id('final-resume-text').inner_text()
  def control(**settings):p.request.post('http://127.0.0.1:28649/qa/control',data=settings)
  try:
   p.goto(BASE);nav('开始使用')
   # Form validation plus synthetic signup and confirmation, never real inboxes.
   if not baseline:
    p.locator('.auth-card nav').get_by_role('button',name='注册',exact=True).click()
    form=p.locator('.auth-card > form')
    form.locator('[name=email]').fill('invalid-email');form.locator('[name=password]').fill('StrongPass123');form.locator('[name=confirm]').fill('StrongPass123')
    form.locator('button').click();assert not form.locator('[name=email]').evaluate('(e)=>e.validity.valid')
    email='career-audit-'+uuid4().hex[:8]+'@example.test'
    form.locator('[name=email]').fill(email);form.locator('[name=confirm]').fill('Mismatch123');form.locator('button').click();expect(p.get_by_role('alert')).to_contain_text('两次密码不一致')
    form.locator('[name=password]').fill('abcdefghij');form.locator('[name=confirm]').fill('abcdefghij');form.locator('button').click();expect(p.get_by_role('alert')).to_contain_text('至少 10')
    form.locator('[name=password]').fill('StrongPass123');form.locator('[name=confirm]').fill('StrongPass123');form.locator('button').click();expect(p.get_by_role('status')).to_contain_text('请检查邮箱')
    context.request.post('http://127.0.0.1:28648/qa/confirm',data={'email':email})
    p.locator('.auth-card nav').get_by_role('button',name='登录',exact=True).click()
    form=p.locator('.auth-card > form');form.locator('[name=email]').fill(email);form.locator('[name=password]').fill('wrong');form.locator('button').click();expect(p.get_by_role('alert')).to_be_visible()
    form.locator('[name=password]').fill('StrongPass123');form.locator('button').click()
   else:
    form=p.locator('.auth-card > form');form.locator('[name=email]').fill('a@example.test');form.locator('[name=password]').fill('fixture-password');form.locator('button').click()
   p.locator('.workspace').wait_for();create('Marketing Assistant');p.locator('#coach-language').select_option('zh-CN');p.locator('#user-stage').select_option('current_student');p.locator('#job-goal').select_option('internship')
   if not baseline:record('账户注册、验证、登录及表单错误（模拟 Auth）')
   # Real multi-page PDF generated from fictional source only.
   q=context.new_page();q.set_content(''.join('<section style="break-after:page;font:14px Arial;white-space:pre-wrap">'+x+'</section>' for x in RESUME_PAGES));pdf=q.pdf();q.close();(OUT/'original-fictional.pdf').write_bytes(pdf)
   if not baseline:
    nav('开始分析');expect(p.get_by_role('alert')).to_contain_text('上传或粘贴')
   p.locator('input[type=file]').first.set_input_files({'name':'fictional.pdf','mimeType':'application/pdf','buffer':pdf})
   expect(p.locator('#resume')).to_contain_text('END OF ORIGINAL RESUME')
   original=p.locator('#resume').input_value()
   if not baseline:
    nav('开始分析');expect(p.get_by_role('alert').filter(has_text='粘贴')).to_be_visible()
    record('无简历、无 JD 的分析校验；三页 PDF 全文提取')
    nav('预览');iframe=p.locator('dialog iframe');iframe.wait_for()
    actual=iframe.evaluate('async e=>Array.from(new Uint8Array(await(await fetch(e.src)).arrayBuffer()))');assert bytes(actual)==pdf
    snap('01-original-preview')
    for number in [2,3]:
     box=iframe.bounding_box()
     # Chrome's built-in PDF toolbar, observed at this fixed test viewport.
     p.mouse.click(box['x']+box['width']/2-190,box['y']+28)
     p.keyboard.press('Meta+A');p.keyboard.type(str(number));p.keyboard.press('Enter')
     p.wait_for_timeout(500)
     snap('01-original-preview-page'+str(number))
    p.locator('dialog').get_by_role('button',name='关闭',exact=True).click()
    p.locator('input[type=file]').first.set_input_files({'name':'wrong.txt','mimeType':'text/plain','buffer':b'not a PDF'})
    expect(p.get_by_role('alert').filter(has_text='PDF')).to_be_visible()
   p.locator('#jd').fill(JD);p.locator('#jobtitle').fill('Marketing Assistant');nav('开始分析')
   p.get_by_text('材料已就绪',exact=False).wait_for() if False else p.get_by_text('项岗位要求',exact=False).first.wait_for()
   nav('简历优化');nav('生成改写建议')
   if baseline:
    p.get_by_text('采用',exact=True).first.wait_for()
    p.locator('#jd').fill(JD+'\nAdditional responsibility: maintain schedules.')
    assert p.get_by_role('button',name='采用',exact=True).first.is_disabled()
    assert p.get_by_role('button',name='重新生成',exact=True).first.is_disabled()
    snap('00-baseline-disabled');record('旧版本禁用缺陷已在真实浏览器复现','JD 变更后审核与重新生成同时 disabled')
    return
   review_row(1).wait_for();assert p.get_by_test_id(re.compile('rewrite-O')).count()>=3
   save();snap('02-ai-review')
   # Keep all, then preserve every byte of extracted text in final output.
   for i in range(1,4):review_row(i).get_by_role('button',name='保留原句',exact=True).click()
   save();assert preview()==original;record('全部拒绝时最终简历保留完整原文')
   for i in range(1,4):review_row(i).get_by_role('button',name='撤销',exact=True).click()
   review_row(1).get_by_role('button',name='采用',exact=True).click()
   review_row(2).get_by_role('button',name='修改',exact=True).click();review_row(2).locator('textarea').fill('Cancelled content');review_row(2).get_by_role('button',name='取消',exact=True).click()
   assert 'Cancelled content' not in p.locator('main').inner_text()
   review_row(2).get_by_role('button',name='修改',exact=True).click();manual='Created social media posts and tracked event registrations with the campus communications team.'
   review_row(2).locator('textarea').fill(manual);review_row(2).get_by_role('button',name='保存修改',exact=True).click()
   review_row(3).get_by_role('button',name='保留原句',exact=True).click();save()
   state=project_state()['state'];assert state['resume']['decisions']['O2']=={'state':'edited','text':manual}
   final=preview();assert manual in final and 'END OF ORIGINAL RESUME' in final
   assert state['inputs']['resumeText']==original
   p.reload();review_row(2).wait_for();assert '已采用（经修改）' in review_row(2).inner_text();assert preview()==final
   record('采纳、保留、编辑、保存、取消及刷新后恢复；部分采纳正确整合')
   review_row(2).get_by_role('button',name='撤销',exact=True).click();save()
   state=project_state()['state'];assert state['resume']['decisions']['O2']['state']=='pending'
   preview();review_row(2).get_by_role('button',name='修改',exact=True).click();review_row(2).locator('textarea').fill(manual);review_row(2).get_by_role('button',name='保存修改',exact=True).click();save();final=preview()
   record('手动编辑后撤销决定及再次编辑')
   # Download actual server-generated binaries, reopen and compare full content.
   expect(p.get_by_role('button',name='PDF',exact=True)).to_be_enabled()
   snap('03-final-resume')
   for fmt in ['PDF','DOCX']:
    with p.expect_download() as info:p.get_by_role('button',name=fmt,exact=True).click()
    target=OUT/('final-fictional.'+fmt.lower());info.value.save_as(target)
    if fmt=='PDF':
     reader=PdfReader(target);text='\n'.join(x.extract_text() for x in reader.pages)
     assert re.sub(r'[\s•]+','',final) in re.sub(r'[\s•]+','',text)
    else:
     text='\n'.join(x.text for x in Document(target).paragraphs);assert text==final
   record('PDF、DOCX 下载后重新打开，完整内容与预览一致')
   # A failed project write must not be called Saved or export older decisions.
   failed_write = {'done':False}
   def fail_save(route):
    if route.request.method=='PUT' and not failed_write['done']:
     failed_write['done']=True;route.fulfill(status=503,content_type='application/json',body='{}')
    else:route.continue_()
   p.route('**/api/workspaces/*',fail_save)
   review_row(3).get_by_role('button',name='撤销',exact=True).click()
   expect(p.get_by_role('alert').filter(has_text='项目保存失败')).to_be_visible()
   assert p.locator('[data-saved=false]').count()==1
   nav('预览完整简历');nav('PDF 预览')
   expect(p.get_by_role('alert').filter(has_text='无法保存或准备文件')).to_be_visible()
   p.unroute('**/api/workspaces/*',fail_save)
   p.get_by_role('button',name='重试',exact=True).first.click();save();p.reload();review_row(1).wait_for();preview()
   record('保存失败不显示已保存、阻止旧决定导出，重试后恢复')
   # Language must not mutate data or trigger another AI call.
   before=project_state()['state']['resume'];calls=p.request.get('http://127.0.0.1:28649/qa/control').json()['calls']
   p.get_by_role('radio',name='EN',exact=True).click();save();p.reload();expect(p.get_by_role('radio',name='EN',exact=True)).to_have_attribute('aria-checked','true')
   p.get_by_role('radio',name='繁',exact=True).click();save();p.get_by_role('radio',name='简',exact=True).click();save()
   assert project_state()['state']['resume']==before
   assert p.request.get('http://127.0.0.1:28649/qa/control').json()['calls']==calls
   record('中英繁语言切换、刷新保留语言；分析与审核不变')
   # Stale lock now has explanation, cancellation stays possible, regenerate works.
   review_row(3).get_by_role('button',name='修改',exact=True).click()
   p.locator('#jd').fill(JD+'\nAdditional responsibility: maintain schedules.')
   expect(p.get_by_text('简历、JD、岗位名称或求职选项已变更',exact=False)).to_be_visible()
   assert review_row(3).get_by_role('button',name='保存修改',exact=True).is_disabled()
   review_row(3).get_by_role('button',name='取消',exact=True).click()
   assert p.get_by_role('button',name='重新生成',exact=True).first.is_enabled()
   snap('04-stale-recovery')
   # Old result cannot be exported via API either.
   save();pid=project_state()['id'];assert api('api/workspaces/'+pid+'/resume/export')['status']==409
   p.get_by_role('button',name='重新生成',exact=True).first.click();p.locator('dialog').get_by_role('button',name='确认',exact=True).click();review_row(1).get_by_role('button',name='采用',exact=True).wait_for()
   expect(review_row(1).get_by_role('button',name='采用',exact=True)).to_be_enabled();save();record('JD 变更标记过期、取消可用、重新生成恢复审核，旧结果导出被后端拒绝')
   # Failure and timeout use genuine backend and genuine error mapping, mocked upstream only.
   control(failure='timeout');p.get_by_role('button',name='重新生成',exact=True).first.click();expect(p.get_by_role('alert')).to_contain_text('超时')
   control(failure=None);p.get_by_role('button',name='重试',exact=True).click();expect(review_row(1).get_by_role('button',name='采用',exact=True)).to_be_enabled()
   record('AI 超时、错误提示、loading 释放及手动重试')
   # Server model quota is unchanged and mock attempts consume the same ledger.
   quota=api('api/quota')['body'];assert quota['limit']==10 and quota['used']>0
   # Project isolation, switching, rename and deletion.
   save();create('Second Project');assert p.locator('#resume').input_value()=='' and p.locator('#jd').input_value()==''
   p.locator('#jd').fill('Only second project data');save()
   for _ in range(3):
    nav('Marketing Assistant');expect(p.locator('#resume')).to_have_value(original)
    nav('Second Project');expect(p.locator('#jd')).to_have_value('Only second project data')
   p.get_by_role('button',name='Second Project · 项目菜单',exact=True).click();p.get_by_role('menuitem',name='修改项目名称',exact=True).click();p.get_by_label('项目名称',exact=True).fill('Renamed Test Project');p.locator('dialog').get_by_role('button',name='保存修改',exact=True).click();p.get_by_role('button',name='Renamed Test Project',exact=True).wait_for()
   p.reload();expect(p.locator('#jd')).to_have_value('Only second project data')
   p.get_by_role('button',name='Renamed Test Project · 项目菜单',exact=True).click();p.get_by_role('menuitem',name='删除项目',exact=True).click();p.locator('dialog').get_by_role('button',name='取消',exact=True).click()
   p.get_by_role('button',name='Renamed Test Project · 项目菜单',exact=True).click();p.get_by_role('menuitem',name='删除项目',exact=True).click();snap('05-delete-confirmation');p.locator('dialog').get_by_role('button',name='确认删除',exact=True).click();expect(p.locator('#resume')).to_have_value(original)
   record('两个项目反复切换、隔离、重命名持久化、自定义删除确认与取消')
   # URL failures and scans in a separate project, no overwriting original resume.
   create('PDF Edge Cases')
   p.locator('input[type=file]').first.set_input_files({'name':'valid.pdf','mimeType':'application/pdf','buffer':pdf});expect(p.locator('#resume')).to_have_value(original)
   p.get_by_role('button',name='清空',exact=True).first.click();expect(p.locator('#resume')).to_have_value('')
   q=context.new_page();q.set_content('<div style="height:10px"></div>');scan=q.pdf();q.close()
   p.locator('input[type=file]').first.set_input_files({'name':'scan.pdf','mimeType':'application/pdf','buffer':scan});expect(p.get_by_role('alert').filter(has_text='扫描')).to_be_visible();assert p.locator('#resume').input_value()==''
   nav('预览');p.locator('dialog iframe').wait_for();p.locator('dialog').get_by_role('button',name='关闭',exact=True).click()
   p.locator('input[type=file]').first.set_input_files({'name':'again.pdf','mimeType':'application/pdf','buffer':pdf});expect(p.locator('#resume')).to_have_value(original)
   nav('从链接导入');p.locator('input[placeholder*="http"]').fill('http://127.0.0.1/private');nav('导入');expect(p.get_by_role('alert').filter(has_text='内网')).to_be_visible();assert p.locator('#jd').input_value()==''
   p.locator('input[placeholder*="http"]').fill('https://qa-careers.example.test/marketing');nav('导入')
   expect(p.locator('#jd')).to_contain_text('QA Marketing Assistant')
   assert 'campaign reports' in p.locator('#jd').input_value()
   save();record('PDF 删除、重传、扫描件提示及预览；URL 受控 HTML 导入成功、内网拒绝且无假成功')
   # Browser history and session restoration.
   nav('Marketing Assistant');nav('岗位匹配');nav('生成匹配报告');p.get_by_text('Campaign reporting experience is relevant.',exact=True).first.wait_for();save();p.reload();expect(p.get_by_text('Campaign reporting experience is relevant.',exact=True).first).to_be_visible()
   nav('简历优化');p.go_back();expect(p.get_by_text('Campaign reporting experience is relevant.',exact=True).first).to_be_visible()
   record('岗位匹配实际后端链路（Mock 上游）、结果持久化、浏览器返回')
   p.get_by_role('button',name='账号',exact=True).click();nav('退出登录');p.get_by_role('button',name='开始使用',exact=True).wait_for();nav('开始使用')
   form=p.locator('.auth-card > form');form.locator('[name=email]').fill(email);form.locator('[name=password]').fill('StrongPass123');form.locator('button').click();p.locator('.workspace').wait_for();nav('Marketing Assistant');nav('简历优化');preview()
   assert not native,native;assert not page_errors,page_errors
   record('退出与重新登录恢复、无原生弹窗、无严重浏览器异常')
   (OUT/'e2e-results.json').write_text(json.dumps({'mode':'mock auth/storage/model; real PostgreSQL/backend/browser/export','results':results,'page_errors':page_errors,'native_dialogs':native,'quota':quota},ensure_ascii=False,indent=2))
  finally:
   if sys.exc_info()[0]:snap('failure');(OUT/'failure-body.txt').write_text(p.locator('body').inner_text())
   context.tracing.stop(path=str(OUT/('baseline-trace.zip' if baseline else 'e2e-trace.zip')))
   browser.close()
if __name__=='__main__':exercise('--baseline' in sys.argv)
