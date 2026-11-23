"""Interview report journeys against the isolated QA backend and model fixture."""
from playwright.sync_api import sync_playwright, expect
from e2e_audit import BASE

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="chrome")
    context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE + "login")
    form = page.locator(".auth-card > form")
    form.locator("[name=email]").fill("a@example.test")
    form.locator("[name=password]").fill("fixture-password")
    form.locator("button").click()
    def click(label):
        page.get_by_role("button", name=label, exact=True).first.click()
    page.locator("aside nav").get_by_role("button", name="面经复盘").click()
    for name, answers in [("Sparse", ["忘了"]), ("Complete", ["I interviewed six users and revised our onboarding form."]),
                          ("Empty", [""]), ("Five", ["I made the prototype.", "", "忘了", "I compared two drafts.", "I showed the decision log."])]:
        click("＋ 新建面经")
        page.get_by_label("公司", exact=True).fill(name)
        page.get_by_label("应聘岗位", exact=True).fill("Research")
        for i, answer in enumerate(answers):
            if i: click("添加问题")
            page.get_by_label("面试官的问题", exact=True).nth(i).fill(f"Describe your contribution to project {i+1}.")
            page.get_by_label("当时的回答", exact=True).nth(i).fill(answer)
        click("保存草稿")
        click("AI 复盘分析")
        expect(page.locator(".interview-summary")).to_be_visible(timeout=20000)
        questions=page.locator(".interview-question")
        expect(questions).to_have_count(len(answers))
        for i, answer in enumerate(answers):
            question=questions.nth(i)
            if i: question.locator("summary").click()
            expect(question.locator(".actual-answer p")).to_have_text(answer or "尚未记录当时的回答")
            expect(question.locator(".suggested-answer")).to_be_visible()
            if answer=="忘了": expect(question.get_by_text("这条记录没有描述具体做法",exact=False)).to_be_visible()
        click("复制回答")
        expect(page.get_by_text("已复制", exact=True)).to_be_visible()
        assert page.evaluate("navigator.clipboard.readText()")==questions.first.locator(".suggested-answer p").inner_text()
        for width in (390, 820, 1440):
            page.set_viewport_size({"width":width,"height":900})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        click("返回列表")
    def legacy(route):
        response=route.fetch()
        rows=response.json()
        row=next(row for row in rows if row["review"]["company"]=="Sparse")
        row["history"][0]["result"]="Legacy report text preserved."
        route.fulfill(response=response,json=rows)
    page.route("**/api/explore/review",legacy)
    page.reload()
    page.locator(".explore article").filter(has_text="Sparse").get_by_role("button",name="查看详情").click()
    expect(page.get_by_text("Legacy report text preserved.")).to_be_visible()
    for lang in ("繁","EN","简"): page.get_by_role("radio",name=lang,exact=True).click()
    assert not errors,errors
    print("PASS sparse, complete, empty and five-question reports, copy, three widths, legacy text, locale changes")
    browser.close()
