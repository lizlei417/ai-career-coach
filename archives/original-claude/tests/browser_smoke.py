"""Exercise real UI controls without a key or mock analysis data."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfWriter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/ui-v2'
OUT.mkdir(parents=True,exist_ok=True)


def idle(page):
    expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning')


def language(page,label,expected_tab):
    page.get_by_role('combobox').first.click()
    page.get_by_role('option',name=label,exact=True).click()
    expect(page.get_by_role('tab',name=expected_tab,exact=True)).to_have_attribute('aria-selected','true')
    idle(page)


def overflow(page):
    return page.evaluate("document.querySelector('[data-testid=stMain]').scrollWidth > innerWidth")


with sync_playwright() as p:
    browser=p.chromium.launch(channel='chromium',args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8501',wait_until='networkidle')
    page.get_by_role('tab',name='Resume Optimization',exact=True).wait_for();idle(page)
    expect(page.locator('.connection')).to_contain_text('Not connected')
    assert page.get_by_role('button',name='Analyze',exact=True).is_disabled()
    page.screenshot(path=str(OUT/'desktop-en.png'),animations='disabled')
    assert not overflow(page)
    resume='Built a Python dashboard for a university project.\nAnalyzed a public dataset and documented validation methods.'
    jd='Required: Python programming and data validation.\nPreferred: SQL experience.'
    page.get_by_role('textbox',name='Resume text',exact=True).fill(resume)
    page.get_by_role('textbox',name='Job Description',exact=True).fill(jd)
    page.get_by_role('textbox',name='Job Description',exact=True).press('Tab')
    page.get_by_text('Materials ready',exact=False).wait_for();idle(page)
    assert page.get_by_role('button',name='Analyze',exact=True).is_disabled()
    for tab in ['Job Matching','Mock Interview','Resume Optimization']:
        page.get_by_role('tab',name=tab,exact=True).click()
        expect(page.get_by_role('tab',name=tab,exact=True)).to_have_attribute('aria-selected','true');idle(page)
        assert page.get_by_role('textbox',name='Resume text',exact=True).input_value()==resume
    page.get_by_role('tab',name='Job Matching',exact=True).click();idle(page)
    language(page,'简体中文','岗位匹配')
    expect(page.locator('.connection')).to_contain_text('未连接')
    assert page.get_by_role('textbox',name='简历正文',exact=True).input_value()==resume
    assert page.get_by_role('textbox',name='岗位描述',exact=True).input_value()==jd
    assert page.get_by_role('button',name='开始分析',exact=True).is_disabled()
    assert page.evaluate('document.documentElement.lang')=='zh-CN'
    page.get_by_text('上传 PDF',exact=True).click();page.get_by_test_id('stFileUploader').wait_for();idle(page)
    # Actual file upload; the original parser supplies the error, the UI localizes it.
    blank=OUT/'blank-test.pdf';writer=PdfWriter();writer.add_blank_page(400,500);writer.write(str(blank))
    file_input=page.get_by_test_id('stFileUploader').locator('input[type=file]')
    expect(file_input).to_have_attribute('aria-label','简历 PDF')
    file_input.set_input_files(str(blank))
    page.get_by_text('PDF 未提取到足够文字',exact=False).wait_for();idle(page)
    page.screenshot(path=str(OUT/'desktop-zh-CN.png'),animations='disabled')
    file_input.set_input_files({'name':'oversized.pdf','mimeType':'application/pdf','buffer':b'x'*(10*1024*1024+1)})
    expect(page.get_by_test_id('stFileUploader')).to_contain_text('请上传不超过 10 MB 的 PDF。')
    language(page,'繁體中文','職位配對')
    expect(page.get_by_test_id('stFileUploader')).to_contain_text('請上傳不超過 10 MB 的 PDF。')
    page.get_by_text('PDF 未擷取到足夠文字',exact=False).wait_for()
    remove_buttons=page.get_by_test_id('stFileUploader').get_by_role('button',name='移除檔案',exact=True)
    assert remove_buttons.count()>=1
    remove_buttons.first.click();idle(page)
    page.get_by_text('貼上文字',exact=True).click()
    expect(page.get_by_role('textbox',name='履歷正文',exact=True)).to_have_value(resume);idle(page)
    page.get_by_role('tab',name='模擬面試',exact=True).click();idle(page)
    expect(page.get_by_role('button',name='開始面試',exact=True)).to_be_disabled()
    page.screenshot(path=str(OUT/'desktop-zh-TW.png'),animations='disabled')
    language(page,'English','Mock Interview')
    expect(page.get_by_role('button',name='Start interview',exact=True)).to_be_disabled()
    page.set_viewport_size({'width':1024,'height':900});idle(page)
    page.screenshot(path=str(OUT/'tablet.png'),animations='disabled');assert not overflow(page)
    page.set_viewport_size({'width':390,'height':844});idle(page)
    page.locator('.brand').scroll_into_view_if_needed()
    page.screenshot(path=str(OUT/'mobile.png'),animations='disabled');assert not overflow(page)
    page.get_by_role('tab',name='Mock Interview',exact=True).scroll_into_view_if_needed()
    expect(page.get_by_role('tab',name='Mock Interview',exact=True)).to_be_visible()
    page.screenshot(path=str(OUT/'mobile-workspace.png'),animations='disabled')
    assert not errors
    print(json.dumps({'real_tab_navigation':True,'three_locales':True,'original_inputs_preserved':True,
        'pdf_errors_localized':True,'no_key_blocks_ai':True,'viewport_widths':[1440,1024,390],
        'horizontal_overflow':False,'browser_errors':errors}))
    browser.close()
