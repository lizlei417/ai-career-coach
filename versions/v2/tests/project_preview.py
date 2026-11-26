"""Run against an isolated local V2 instance: python tests/project_preview.py URL."""
import hashlib
import sys
from playwright.sync_api import sync_playwright


def exercise(browser, url):
    context = browser.new_context()
    p = context.new_page()
    errors = []
    p.on("pageerror", lambda error: errors.append(str(error)))
    documents = {}
    for name in ["Campus", "Museum"]:
        pages = [f"<section style='break-after:page'>{name} page {n}. Fictional candidate collected visitor feedback for the design team.</section>" for n in range(1, 4)]
        p.set_content("".join(pages))
        documents[name] = p.pdf()
    p.goto(url)
    p.get_by_role("button", name="开始使用", exact=True).click()
    preview = p.get_by_role("button", name="预览", exact=True)
    assert preview.is_disabled()

    def upload(name):
        p.locator('input[type=file]').first.set_input_files({
            "name": name + ".pdf", "mimeType": "application/pdf", "buffer": documents[name]
        })
        p.wait_for_function("document.querySelector('#resume').value.includes('"+name+" page 3')")
        p.locator("#jd").fill(name + " job")

    def verify(name):
        preview.click()
        frame = p.locator("dialog[open] iframe")
        frame.wait_for()
        digest = frame.evaluate("""async el => {
          const data = await (await fetch(el.src)).arrayBuffer()
          return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2,'0')).join('')
        }""")
        assert digest == hashlib.sha256(documents[name]).hexdigest()
        assert frame.bounding_box()["width"] > p.viewport_size["width"] * .9
        p.get_by_role("button", name="关闭", exact=True).click()
        assert p.locator("#jd").input_value() == name + " job"

    upload("Campus")
    verify("Campus")
    p.get_by_role("button", name="新建项目", exact=True).click()
    p.get_by_label("项目名称").fill("Museum portfolio")
    p.get_by_role("button", name="创建", exact=True).click()
    p.locator("main header").filter(has_text="Museum portfolio").wait_for()
    assert p.locator("#resume").input_value() == "" and preview.is_disabled()
    upload("Museum")
    verify("Museum")
    p.locator("[data-saved=true]").wait_for()
    p.reload()
    verify("Museum")
    p.get_by_role("button", name="我的第一个项目").click()
    p.locator("main header").filter(has_text="我的第一个项目").wait_for()
    verify("Campus")
    assert not errors, errors
    return context, p, verify

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        exercise(browser, sys.argv[1])
        print("PASS: two three-page originals, project isolation, reload, input preservation")
