"""Browser acceptance using an isolated port and synthetic model transport only.

The production app never imports this module. All semantic model calls, including
audits, are replaced in this test. The HTTP service, parser, validators, retrieval,
React app and interview state machine run normally.
"""
import os
import socket
import threading
import time
from io import BytesIO

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import server
from coach.config import ROOT
from coach.models import Audit, Extraction, Feedback, InterviewSummary, Matching, Optimization, Question
from test_workspace import JD, RESUME

OUT = ROOT / "tmp" / "workbench"
SECOND = "Presented the dashboard findings to my course team."
DOCUMENT = RESUME + "\n" + SECOND
FULL_JD = JD + " Responsibilities: present findings to the team."


class SyntheticTransport:
    extractions = 0
    def __init__(self, config):
        pass

    def generate(self, schema, system, payload):
        cn = payload["output_language"] != "English"
        quote = {"source_id": "R001", "quote": RESUME}
        if schema is Audit:
            obj = {"items": [{"id": c["id"], "supported": True, "reason": "Test only"} for c in payload["candidate_items"]]}
        elif schema is Extraction:
            type(self).extractions += 1
            clauses = ["build and document dashboards", "experience with SQL", "present findings to the team"]
            obj = {"resume_is_valid": True, "jd_is_valid": True, "issues": [], "requirements": [
                {"id": f"Q{i}", "source_id": "J001", "quote": text, "category": category}
                for i, (text, category) in enumerate(zip(clauses, ["required", "preferred", "responsibility"]), 1)]}
        elif schema is Optimization:
            obj = {"revisions": [{
                "id": "E1", "title": "项目经历表达" if cn else "Clarify the dashboard project", "requirement_ids": ["Q1"],
                "evidence": [quote], "optimized": "在大学项目中制作交互式仪表板，探索公开数据集。" if cn else "Developed an interactive dashboard for a university project to explore a public dataset.",
                "reason": "突出项目范围与具体行动。" if cn else "Leads with the deliverable and retains the scope of the coursework."
            }, {"id":"E2","title":"沟通经历" if cn else "Presenting findings","requirement_ids":["Q3"],
                "evidence":[{"source_id":"R002","quote":SECOND}],
                "optimized":"向课程团队汇报仪表板分析结果。" if cn else "Shared dashboard findings with the course team.",
                "reason":"明确沟通对象。" if cn else "Identifies the audience."
            }], "gaps": [{"requirement_id": "Q2", "explanation": "SQL 尚无原文证据。" if cn else "The resume does not mention SQL.", "suggestion": "如有 SQL 课程经历，可补充原文。" if cn else "Add a real SQL coursework example if available."}], "guide_ids": [payload["guides"][0]["id"]]}
        elif schema is Matching:
            obj = {"matches": [
                {"requirement_id": "Q1", "status": "partial", "evidence": [quote], "assessment": "Dashboard construction is evidenced. Documentation needs clarification.", "gap_type":"clarify_existing", "suggestion":"Describe what you documented.", "priority":"high"},
                {"requirement_id": "Q2", "status": "none", "evidence": [], "assessment": "SQL is not mentioned.", "gap_type":"not_in_material", "suggestion":"Add real coursework or practise SQL.", "priority":"medium"},
                {"requirement_id":"Q3","status":"direct","evidence":[{"source_id":"R002","quote":SECOND}],"assessment":"The resume identifies a presentation to the team.","gap_type":"sufficient","suggestion":"Retain the presentation example.","priority":"low"}], "guide_ids":[]}
        elif schema is Question:
            obj = {"text": payload.get("requested_follow_up") or ("Which validation method would you use?" if payload["history"] else "How did you explore the dataset in your dashboard project?"), "kind":"technical", "requirement_id":"Q1", "evidence":[quote], "guide_ids":[]}
        elif schema is Feedback:
            obj = {"strengths":["Names a data check."], "missing_information":["Explain the choice of method."], "action":"Give one reason for the check.", "answer_quotes":[payload["current_answer"]], "follow_up":"Why did you choose that check?", "guide_ids":[]}
        elif schema is InterviewSummary:
            obj = {"strengths":["Identifies validation steps."], "practice_priorities":["Explain your reasoning."], "next_steps":["Try a second dataset."], "guide_ids":[]}
        else:
            raise AssertionError(schema)
        return schema.model_validate(obj)


@pytest.fixture
def local_app(monkeypatch,tmp_path):
    (tmp_path/"Synthetic-writing-guide.md").write_text("Resume optimization: identify the action, scope and audience in a dashboard project.")
    monkeypatch.setenv("KNOWLEDGE_DIR",str(tmp_path))
    monkeypatch.setattr(SyntheticTransport,"extractions",0)
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-test-only")
    monkeypatch.setattr(server,"AIClient",SyntheticTransport)
    sock = socket.socket()
    sock.bind(("127.0.0.1",0))
    port = sock.getsockname()[1]
    app = uvicorn.Server(uvicorn.Config(server.app,log_level="error", access_log=False))
    thread = threading.Thread(target=app.run, kwargs={"sockets":[sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if app.started:
            break
        time.sleep(.03)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        app.should_exit=True
        thread.join(5)
        sock.close()


def pdf_fixture():
    pdf=PdfWriter()
    page=pdf.add_blank_page(700,800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):pdf._add_object(font)})})
    stream=DecodedStreamObject()
    stream.set_data(f"BT /F1 11 Tf 20 700 Td ({RESUME}) Tj 0 -18 Td ({SECOND}) Tj ET".encode())
    page[NameObject('/Contents')]=pdf._add_object(stream)
    buf=BytesIO()
    pdf.write(buf)
    return buf.getvalue()


def test_desktop_mobile_workflows(local_app):
    OUT.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel=os.environ.get("CAREER_TEST_BROWSER"),args=["--disable-gpu"])
        page=browser.new_page(viewport={"width":1440,"height":900})
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.on("dialog",lambda dialog:dialog.accept())
        page.set_default_timeout(6500)
        def btn(name):
            return page.get_by_role("button",name=name,exact=True)
        def tab(name):
            return page.get_by_role("tab",name=name,exact=True)
        def shot(name):
            page.locator(".working").wait_for(state="hidden")
            page.evaluate("window.scrollTo(0,0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),name
            page.screenshot(path=OUT/(name+".png"),animations="disabled")
        page.goto(local_app)
        btn("Get started").wait_for()
        shot("welcome-1440-en")
        btn("Get started").click()
        expect(page.get_by_label("Resume",exact=True)).to_be_visible()
        expect(page.get_by_label("Job Description",exact=True)).to_be_visible()
        expect(btn("Analyze resume")).to_be_disabled()
        assert page.locator(".wizard,.steps").count()==0
        assert page.get_by_role("textbox").count()==2
        tab("Resume Optimization").focus()
        page.keyboard.press("ArrowRight")
        expect(tab("Job Matching")).to_have_attribute("aria-selected","true")
        page.keyboard.press("Home")
        expect(tab("Resume Optimization")).to_have_attribute("aria-selected","true")
        shot("empty-1440-en")
        page.locator('input[type=file]').set_input_files({"name":"test-resume.pdf","mimeType":"application/pdf","buffer":pdf_fixture()})
        expect(page.get_by_label("Resume",exact=True)).to_have_value(DOCUMENT)
        btn("Import a link").click()
        page.get_by_label("Public job posting URL").fill("http://127.0.0.1/")
        btn("Import").click()
        expect(page.get_by_role("alert")).to_contain_text("public HTTP")
        btn("Import a link").click()
        page.get_by_label("Job Description",exact=True).fill(FULL_JD)
        expect(btn("Analyze resume")).to_be_enabled()
        assert SyntheticTransport.extractions==0
        shot("ready-1440-en")
        btn("Analyze resume").click()
        btn("Next item").click()
        expect(page.get_by_role("heading",name="Presenting findings")).to_be_visible()
        btn("Previous item").click()
        page.get_by_text("Reference guides · 1",exact=True).click()
        expect(page.get_by_text("Synthetic-writing-guide.md",exact=True)).to_be_visible()
        btn("Use this revision").click()
        expect(page.get_by_text("Adopted",exact=True)).to_be_visible()
        btn("Edit revision").click()
        page.get_by_label("Your revision").fill("Documented my dashboard.")
        btn("Save changes").click()
        expect(page.get_by_text("Edited by you",exact=True)).to_be_visible()
        btn("Keep original").click()
        expect(page.get_by_text("Original kept",exact=True)).to_be_visible()
        page.get_by_label("Language").select_option("zh-CN")
        expect(page.get_by_text("已保留原句",exact=True)).to_be_visible()
        btn("重新分析").click()
        expect(page.get_by_role("heading",name="项目经历表达")).to_be_visible()
        shot("revision-1440-zh-test")
        page.set_viewport_size({"width":1280,"height":800})
        shot("revision-1280-zh-test")
        page.get_by_label("语言").select_option("en")
        tab("Job Matching").click()
        btn("Compare requirements").click()
        btn("build and document dashboards").click()
        expect(page.get_by_text("Dashboard construction is evidenced. Documentation needs clarification.")).to_be_visible()
        shot("matching-1280-en-test")
        tab("Mock Interview").click()
        btn("Start interview").click()
        editor=page.locator(".interview-sheet textarea")
        editor.fill("I checked for missing values.")
        tab("Job Matching").click()
        tab("Mock Interview").click()
        expect(editor).to_have_value("I checked for missing values.")
        btn("Get feedback").click()
        btn("Try again").click()
        editor.fill("I counted missing values in the source rows.")
        btn("Get feedback").click()
        btn("Answer follow-up").click()
        expect(page.get_by_role("heading",name="Why did you choose that check?")).to_be_visible()
        editor.fill("I wanted to compare missing entries before aggregating records.")
        btn("Get feedback").click()
        shot("interview-1280-en-test")
        btn("Next question").click()
        expect(page.get_by_role("heading",name="Which validation method would you use?")).to_be_visible()
        btn("End & summarize").click()
        expect(page.get_by_role("heading",name="Practice summary")).to_be_visible()
        page.reload()
        tab("Mock Interview").click()
        expect(page.get_by_text("Try a second dataset.",exact=True)).to_be_visible()
        page.get_by_label("Language").select_option("zh-TW")
        for width,height in [(760,850),(390,844)]:
            page.set_viewport_size({"width":width,"height":height})
            tab("履歷優化").click()
            shot(f"revision-{width}-tw-test")
            btn("收合資料區").click()
            expect(page.get_by_label("履歷",exact=True)).not_to_be_visible()
            tab("職位配對").click()
            shot(f"matching-{width}-tw-test")
            btn("展開資料區").click()
            expect(page.get_by_label("履歷",exact=True)).to_have_value(DOCUMENT)
            btn("開啟導覽列").click()
            page.locator(".rail").get_by_role("button",name="模擬面試",exact=True).click()
            expect(page.get_by_role("heading",name="練習總結",exact=True)).to_be_visible()
        assert SyntheticTransport.extractions == 1
        page.set_viewport_size({"width":1280,"height":800})
        page.get_by_label("語言").select_option("en")
        modified=DOCUMENT+"\nChecked the dashboard against the source records."
        page.get_by_label("Resume",exact=True).fill("short")
        expect(btn("Start interview")).to_be_disabled()
        page.get_by_label("Resume",exact=True).fill(modified)
        expect(page.get_by_role("heading",name="Practice summary")).not_to_be_visible()
        tab("Job Matching").click()
        expect(page.get_by_role("table")).not_to_be_visible()
        page.get_by_label("Resume",exact=True).fill(DOCUMENT)
        expect(page.get_by_role("table")).to_be_visible()
        page.get_by_label("Resume",exact=True).fill(modified)
        btn("Compare requirements").click()
        expect(page.get_by_role("table")).to_be_visible()
        assert SyntheticTransport.extractions == 2
        tab("Mock Interview").click()
        expect(btn("Start interview")).to_be_enabled()
        expect(page.get_by_role("heading",name="Practice summary")).not_to_be_visible()
        tab("Resume Optimization").click()
        expect(page.get_by_role("heading",name="项目经历表达")).not_to_be_visible()
        page.get_by_label("Language").select_option("zh-CN")
        btn("收起材料区").click()
        btn("分析简历").click()
        expect(page.get_by_role("heading",name="项目经历表达")).to_be_visible()
        assert SyntheticTransport.extractions == 2
        btn("展开材料区").click()
        shot("updated-1280-zh-test")
        btn("设置").click()
        btn("刷新状态").click()
        btn("清空工作台").click()
        expect(btn("开始使用")).to_be_visible()
        assert not errors
        browser.close()
