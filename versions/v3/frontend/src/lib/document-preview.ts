
/** Render the actual exported DOCX locally; no third-party document service. */
export async function renderWordPreview(win: Window, blob: Blob, name: string, lang: string) {
  const en = lang === 'en', tw = lang === 'zh-TW'
  const doc = win.document
  doc.documentElement.lang = lang
  doc.title = `${name} · Word`
  doc.head.innerHTML = `<meta charset="utf-8"><style>
    @font-face{font-family:'Noto Sans SC';src:url('${new URL(import.meta.env.BASE_URL + 'resume-font.ttf', location.origin)}')}
    *{box-sizing:border-box}body{margin:0;background:#e9edf1;font-family:'Noto Sans SC',Arial,sans-serif;color:#111827}
    header{position:sticky;top:0;z-index:2;background:white;border-bottom:1px solid #ddd;padding:12px 24px;display:flex;justify-content:space-between;align-items:center;gap:16px}
    a{background:#111827;color:white;border-radius:6px;padding:9px 16px;text-decoration:none;font-size:14px}
    .docx-wrapper{background:transparent!important;padding:24px!important;overflow:auto}
    section.docx{box-shadow:0 2px 14px #0002;margin:0 auto 24px!important;position:relative}
    section.docx article{overflow-wrap:anywhere}section.docx p{white-space:pre-wrap;color:#172333!important}
    @media print{header{display:none}.docx-wrapper{padding:0!important}section.docx{margin:0!important;box-shadow:none;break-after:page}}
  </style>`
  doc.body.replaceChildren()
  const toolbar = doc.createElement('header'), label = doc.createElement('span'), download = doc.createElement('a')
  label.textContent = `${name} · Word (DOCX)`
  const url = URL.createObjectURL(blob)
  download.href = url; download.download = `${name}.docx`
  download.textContent = en ? 'Download DOCX' : tw ? '下載 DOCX' : '下载 DOCX'
  toolbar.append(label, download);doc.body.append(toolbar)
  const container = doc.createElement('div');doc.body.append(container)
  const { renderAsync } = await import('docx-preview')
  await renderAsync(blob, container, undefined, { ignoreLastRenderedPageBreak: false, renderAltChunks: false, breakPages: true })
  await doc.fonts.load('14px "Noto Sans SC"')
  await doc.fonts.ready
  // docx-preview honours explicit breaks but does not calculate Word pagination.
  // Paginate our simple paragraph template by its real rendered A4 content height.
  for (const section of Array.from(container.querySelectorAll<HTMLElement>('section.docx'))) {
    const article = section.querySelector<HTMLElement>('article')
    if (!article) continue
    const style = win.getComputedStyle(section)
    const height = parseFloat(style.minHeight || style.height) || 1122.5
    const limit = height - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom) - 28
    const nodes = Array.from(article.children) as HTMLElement[]
    article.replaceChildren()
    let page = section, body = article
    const nextPage = () => {
      const next = section.cloneNode(true) as HTMLElement
      const nextBody = next.querySelector<HTMLElement>('article')!
      nextBody.replaceChildren();page.after(next);page = next;body = nextBody
    }
    for (const node of nodes) {
      body.append(node)
      if (body.scrollHeight > limit && body.children.length > 1) {
        node.remove()
        // Keep section headings with the following paragraph where possible.
        const previous = body.lastElementChild as HTMLElement | null
        const keep = previous && /heading/i.test(previous.className) ? previous : null
        if (keep) keep.remove()
        nextPage();if (keep) body.append(keep);body.append(node)
      }
      // Very long user paragraphs are split into continuations without losing text.
      while (body.scrollHeight > limit && node.textContent && node.textContent.length > 100) {
        const text = node.textContent;let lo = 1, hi = text.length
        while (lo < hi) {
          const mid = Math.ceil((lo + hi) / 2);node.textContent = text.slice(0, mid)
          if (body.scrollHeight <= limit) lo = mid;else hi = mid - 1
        }
        node.textContent = text.slice(0, lo)
        const rest = node.cloneNode(false) as HTMLElement;rest.textContent = text.slice(lo)
        nextPage();body.append(rest)
        // Remaining overflow is rare in resume paragraphs; process recursively below.
        if (body.scrollHeight > limit) {
          const remaining = rest.textContent!;rest.remove()
          for (let i = 0; i < remaining.length; i += 700) {
            const part = rest.cloneNode(false) as HTMLElement;part.textContent = remaining.slice(i, i + 700);body.append(part)
            if (body.scrollHeight > limit) { part.remove();nextPage();body.append(part) }
          }
        }
        break
      }
    }
  }
  win.addEventListener('pagehide', () => URL.revokeObjectURL(url), { once: true })
}
