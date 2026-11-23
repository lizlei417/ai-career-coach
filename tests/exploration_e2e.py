"""Chrome user journeys. Auth and AI use fixtures; database, ATS and JD are real."""

from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from e2e_audit import BASE, OUT, RESUME_PAGES, JD
import re

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    p = b.new_page(viewport={"width": 1440, "height": 960})
    p.set_default_timeout(22000)
    expect.set_options(timeout=22000)
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))

    def click(name):
        p.get_by_role("button", name=name, exact=True).first.click()

    def nav(name):
        p.locator("aside nav").get_by_role("button", name=name, exact=True).click()

    p.goto(BASE + "login")
    f = p.locator(".auth-card > form")
    f.locator("[name=email]").fill("a@example.test")
    f.locator("[name=password]").fill("fixture-password")
    f.locator("button").click()
    p.locator(".workspace").wait_for()
    # Hold the initial server read and then the first write independently.
    held_reads,held_writes=[],[]
    def slow_draft(route):
        if route.request.method=="GET" and not held_reads:
            held_reads.append(route)
        elif route.request.method=="POST" and not held_writes:
            held_writes.append(route)
        else:
            route.continue_()
    p.route("**/api/explore/draft",slow_draft)
    nav("职业测评")
    for i in range(6):
        expect(p.locator(".explore small").first).to_have_text(f"{i+1} / 12")
        click("较同意")
        if i==1:
            expect(p.locator(".explore small").first).to_have_text("3 / 12",timeout=800)
            assert held_reads
            held_reads[0].continue_()
            for _ in range(50):
                if held_writes:break
                p.wait_for_timeout(50)
            assert held_writes
    expect(p.locator(".explore small").first).to_have_text("7 / 12")
    # Simulate a failed upload: the six answers must survive a full reload.
    held_writes[0].abort()
    p.unroute("**/api/explore/draft",slow_draft)
    p.reload()
    expect(p.locator(".explore small").first).to_have_text("7 / 12")
    click("上一题")
    expect(p.get_by_role("button", name="较同意", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    click("较同意")
    for i in range(6):
        expect(p.locator(".explore small").first).to_have_text(f"{i+7} / 12")
        click("很同意")
    click("查看结果")
    expect(p.get_by_text("测评历史", exact=True)).to_be_visible()
    click("查看适合我的岗位")
    expect(p.get_by_text("测评方向", exact=False).first).to_be_visible()
    nav("职业测评")
    click("重新测试")
    for i in range(12):
        expect(p.locator(".explore small").first).to_have_text(f"{i+1} / 12")
        click("较不同意")
    click("查看结果")
    expect(p.get_by_role("button", name="删除", exact=True)).to_have_count(2)
    print(
        "PASS questionnaire resume, past answers, history, no-project handoff",
        flush=True,
    )
    click("新建项目")
    p.get_by_label("项目名称", exact=True).fill("V4 QA")
    click("创建")
    nav("岗位匹配")
    p.locator("#coach-language").select_option("zh-CN")
    p.locator("#user-stage").select_option("current_student")
    p.locator("#job-goal").select_option("internship")
    p.locator("#resume").fill("\n".join(RESUME_PAGES))
    p.locator("#jd").fill(JD)
    click("分析职业方向")
    expect(p.locator(".discovery summary").first).to_have_text("Product operations")
    p.reload()
    expect(p.locator(".discovery summary").first).to_have_text("Product operations")
    p.get_by_label("岗位类型", exact=True).select_option("")
    p.get_by_label("岗位方向", exact=True).select_option("product")
    p.locator(".job").first.wait_for()
    job = p.locator(".job").first
    title = job.locator("h3").inner_text()
    job.get_by_role("button", name="查看岗位").click()
    expect(p.locator("dialog h2")).to_have_text(title)
    assert len(p.locator("dialog p").inner_text()) > 100
    click("关闭")
    job.get_by_role("button", name="分析匹配").click()
    expect(p.locator("dialog")).to_be_visible()
    p.locator("dialog").get_by_role("button", name="取消").click()
    expect(p.locator("#jd")).to_have_value(JD)
    job.get_by_role("button", name="分析匹配").click()
    p.locator("dialog").get_by_role("button", name="确认", exact=True).click()
    expect(p.locator("#jobtitle")).to_have_value(title)
    expect(p.locator("#jd")).not_to_have_value(JD)
    expect(p.get_by_role("button", name="重新生成", exact=True).first).to_be_visible()
    for width in (1366, 1440, 1920, 820, 390):
        p.set_viewport_size({"width": width, "height": 900})
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), width
    p.set_viewport_size({"width": 1440, "height": 960})
    p.screenshot(path=str(OUT / "v4-match.png"))
    print(
        "PASS real vacancy details and JD, overwrite cancel/confirm, existing matching and five widths",
        flush=True,
    )
    nav("面经复盘")
    click("＋ 新建面经")
    p.get_by_label("应聘岗位", exact=True).fill("Operations intern")
    p.get_by_label("公司", exact=True).fill("QA Company")
    click("添加问题")
    click("添加问题")
    for i, q in enumerate(
        [
            "How did you coordinate volunteers?",
            "How would you measure retention?",
            "What did the feedback change?",
        ]
    ):
        p.get_by_label("面试官的问题", exact=True).nth(i).fill(q)
        if i != 1:
            p.get_by_label("当时的回答", exact=True).nth(i).fill(
                "I shared a weekly plan and revised the schedule."
            )
    click("保存草稿")
    expect(p.get_by_text("草稿已保存", exact=True)).to_be_visible()
    p.reload()
    click("查看详情")
    click("AI 复盘分析")
    expect(p.get_by_text("复盘报告", exact=False).first).to_be_visible()
    click("编辑")
    p.get_by_label("当时的回答", exact=True).first.fill("I wrote the event plan.")
    click("保存草稿")
    expect(p.get_by_text("面经已修改，这份报告对应旧版本。")).to_be_visible()
    click("重新分析")
    expect(p.get_by_text("复盘报告", exact=False)).to_have_count(2)
    p.get_by_role("radio", name="EN", exact=True).click()
    expect(p.locator(".explore h1")).to_have_text("Interview Review")
    p.get_by_role("radio", name="繁", exact=True).click()
    expect(p.locator(".explore h1")).to_have_text("面經復盤")
    p.get_by_role("radio", name="简", exact=True).click()
    nav("模拟面试")
    click("开始面试")
    click("保存至面经复盘")
    expect(p.locator(".explore h1")).to_have_text("面经复盘")
    card = p.locator(".explore article").filter(has_text=title).first
    card.get_by_role("button", name="查看详情").click()
    expect(p.locator(".explore small").filter(has_text="模拟面试")).to_be_visible()
    click("删除")
    p.locator("dialog").get_by_role("button", name="取消").click()
    click("删除")
    p.locator("dialog").get_by_role("button", name="确认", exact=True).click()
    expect(p.locator(".explore article")).to_have_count(1)
    print(
        "PASS mock interview import, source label, confirmed record deletion",
        flush=True,
    )
    assert not errors, errors
    print(
        "PASS interview creation, three questions, unanswered question, restore, stale history, reanalysis, languages",
        flush=True,
    )
    b.close()
