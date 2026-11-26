"""Visual components only; all generated text is escaped before rendering."""
import base64
import html
from pathlib import Path
import streamlit as st
from coach.i18n import tr

ICONS = {
    "spark": '<path d="m12 2 2.8 7.2L22 12l-7.2 2.8L12 22l-2.8-7.2L2 12l7.2-2.8Z"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9H3Z"/>',
    "layers": '<path d="m12 3 10 6-10 6L2 9Z"/><path d="m3 14 9 5 9-5"/>',
    "edit": '<path d="m15 5 4 4M4 20l4-1L21 6l-4-4L4 15Z"/><path d="M12 21h9"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="m12 12 9-9M17 3h4v4"/>',
    "chat": '<path d="M21 11a9 9 0 0 1-9 9H4l-3 2 2-6a9 9 0 1 1 18-5Z"/><path d="M8 10h8M8 14h5"/>',
    "document": '<path d="M14 2H5v20h14V7Z"/><path d="M14 2v6h5M8 12h8M8 16h6"/>',
}


def icon(name, size=22):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'


CSS = """
<style>
:root {--ink:#142b35;--teal:#087e7b;--mint:#dff2eb;--line:#e0e7e3;--muted:#6e7e80;}
html,.stApp {font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink);}
.stApp {background:radial-gradient(ellipse at 78% 20%,#e8f5ed85,transparent 42%),#faf8f4;}
.stApp p,.stApp button,.stApp label,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3 {font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
[data-testid="stHeader"],#MainMenu,[data-testid="stToolbar"],footer,[data-testid="stStatusWidget"] {display:none!important;}
.block-container,[data-testid="stMainBlockContainer"] {max-width:1680px;padding:22px 38px 28px!important;}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"] {gap:15px;}
.st-key-top_nav {align-items:center;min-height:52px;margin-bottom:2px;}
.brand {display:flex;align-items:center;gap:12px;font-size:23px;font-weight:760;letter-spacing:-.65px;white-space:nowrap;height:46px;}
.brand-mark {display:grid;place-items:center;flex:none;color:white;width:43px;height:43px;border-radius:14px;background:linear-gradient(135deg,#67c7b8,#04827f 70%);box-shadow:0 5px 12px #07827c16;}
.connection {display:flex;justify-content:center;align-items:center;gap:7px;min-height:42px;border-radius:24px;padding:8px 12px;font-size:12px;font-weight:600;white-space:nowrap;margin-top:2px;}
.connection .dot {height:7px;width:7px;border-radius:50%;background:currentColor;flex:none;}
.connection.offline {background:#eff0ec;color:#6a7776;}.connection.unverified {background:#fff0d9;color:#906120;}.connection.verified {background:#dcf2e6;color:#257457;}.connection.failed {background:#fce8e5;color:#aa493b;}
.st-key-top_nav [data-testid="stSelectbox"]>div>div {border-radius:24px;background:#fffdf9;min-height:43px;border-color:#d8dfd9;}
.st-key-top_nav [data-testid="stPopover"] button {border-radius:50%;width:43px;min-height:43px;padding:8px;background:#fffdf9;}
.hero {position:relative;isolation:isolate;overflow:hidden;height:166px;border-radius:22px;background:linear-gradient(105deg,#edf7ee 0%,#d4efea 60%,#def3ec 100%);border:1px solid #d4e8df;}
.hero:before,.hero:after {content:'';position:absolute;inset:0;pointer-events:none;z-index:-1;}
.hero:before {width:90%;height:240px;left:-14%;top:30px;transform:rotate(-11deg);border-radius:50%;background:linear-gradient(110deg,#fffdf4b0,#b6e4dd66);}
.hero:after {width:65%;height:230px;left:35%;top:108px;border-radius:50%;background:#f8fcf4aa;transform:rotate(-10deg);}
.hero h1 {position:absolute;left:32px;top:50%;transform:translateY(-50%);margin:0!important;padding:0!important;font-size:clamp(25px,2.9vw,43px)!important;line-height:1.17!important;max-width:57%;letter-spacing:-1.4px;font-weight:760;color:#103a41;z-index:2;}
.hero img {position:absolute;right:18px;top:-42px;width:clamp(300px,36vw,520px);height:246px;object-fit:contain;filter:drop-shadow(0 7px 8px #246d6410);}
.st-key-materials,.st-key-career_workspace {background:rgba(255,255,255,.94);border:1px solid #e3e8e1;border-radius:24px;box-shadow:0 8px 32px #243c3510;padding:23px 22px 20px;}
.panel-heading {display:flex;align-items:center;gap:12px;margin-bottom:4px;}
.panel-icon {display:grid;place-items:center;width:45px;height:45px;flex:none;border-radius:15px;background:linear-gradient(135deg,#e7f5f0,#cfebe4);color:#126965;}
.panel-heading h2 {font-size:23px!important;line-height:1.2;margin:0!important;padding:0!important;letter-spacing:-.65px;font-weight:740;}
.st-key-materials [data-testid="stVerticalBlock"],.st-key-career_workspace>[data-testid="stVerticalBlock"] {gap:12px;}
.stTextArea textarea {font-size:13px;line-height:1.55;border-radius:12px;resize:vertical;background:linear-gradient(135deg,#fbfcfc,#f7faf9);color:var(--ink);}
[data-baseweb="textarea"],[data-baseweb="base-input"] {border-radius:13px!important;border-color:#d9e3de!important;}
[data-testid="stWidgetLabel"] p {font-size:13px;font-weight:650;letter-spacing:.05px;}
[data-testid="stCaptionContainer"] p {font-size:11.5px;line-height:1.55;color:var(--muted);}
.stButton button,.stDownloadButton button,[data-testid="stFormSubmitButton"] button {border-radius:11px;min-height:40px;border-color:#dbe5df;font-weight:650;font-size:13px;box-shadow:0 2px 3px #234e3d06;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:linear-gradient(115deg,#15968a,#037976);border:1px solid #087a74;box-shadow:0 4px 10px #007a6c15;color:white;}
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover {background:linear-gradient(115deg,#0e8c80,#006b69);border-color:#006b69;color:white;}
button:disabled {opacity:.65;}
button[kind="primary"]:disabled {background:#e2efe9;border-color:#d2e5db;color:#557b69;opacity:1;box-shadow:none;}
.st-key-analyze button {min-height:47px;font-size:15px;}
[data-testid="stRadio"] [role="radiogroup"] {gap:15px;}
[data-testid="stRadio"] p {font-size:12px;font-weight:500;}
[data-testid="stFileUploaderDropzone"] {background:#f2f8f6;border:1px dashed #bad7cb;border-radius:14px;padding:12px;}
[data-testid="stFileUploaderDropzoneInstructions"]>div>span {font-size:0;}
[data-testid="stFileUploaderDropzoneInstructions"] small {display:none;}
[data-testid="stFileUploaderDropzone"] button p {display:none;}
[data-testid="InputInstructions"] {display:none;}
.stTabs [role="tablist"] {gap:8px;margin-bottom:14px;background:none;border:0;}
.stTabs [role="tab"] {flex:1;justify-content:center;height:47px;min-height:47px;padding:8px 10px;background:linear-gradient(135deg,#faf9f5,#f2f0eb);border:1px solid #e3e1da;border-radius:13px;color:#253c40;box-shadow:0 2px 2px #302c2310;}
.stTabs [role="tab"] p {font-size:13px;font-weight:700;white-space:nowrap;}
.stTabs [role="tab"][aria-selected="true"] {background:linear-gradient(120deg,#1b9b90,#007875);color:white;border-color:#0a8b81;box-shadow:0 3px 8px #006d6420;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"] {display:none;}
.stTabs [role="tabpanel"] {padding:0!important;}
.st-key-result_scroll {border:0!important;padding:1px 3px 6px!important;scrollbar-width:thin;scrollbar-color:#c4dcd3 transparent;}
.empty-state {display:flex;min-height:330px;align-items:center;justify-content:center;flex-direction:column;text-align:center;padding:30px;border:1px solid #e4ece6;border-radius:18px;background:radial-gradient(ellipse at top,#edf8f3,#fff 75%);}
.empty-icon {height:72px;width:72px;border-radius:24px;background:linear-gradient(135deg,#e1f4eb,#f2f7ec);display:grid;place-items:center;color:#4a9c89;margin-bottom:20px;box-shadow:0 4px 15px #24866309;}
.empty-state p {max-width:340px;font-size:14px;line-height:1.7;color:#7b8d86;margin:0;}
.revision-meta {font-size:10px;letter-spacing:.06em;color:#789087;margin-bottom:8px;}
[class*="st-key-revision_"] {border:1px solid #e0e8e1;border-radius:17px;padding:15px;background:#fff;box-shadow:0 2px 7px #153e3005;}
.quote-card {padding:14px 15px;border-radius:13px;min-height:108px;background:#f5f6f8;border:1px solid #e6e8eb;height:100%;}
.quote-card.refined {background:linear-gradient(135deg,#eef9f4,#f2faf7);border-color:#d0e9de;}
.chip {display:inline-block;font-size:10px;font-weight:700;line-height:1.5;border-radius:20px;padding:3px 10px;color:#5a6971;background:#e8ecf0;margin-bottom:9px;}
.refined .chip {background:#d8f0e5;color:#176e5b;}
.quote-text {font-size:13px;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere;color:#253b40;}
.source-id {display:inline-block;font-size:10px;color:#7c8d89;margin:6px 0 0;}
.reason {background:#fff8e9;border:1px solid #f3ead8;border-radius:11px;padding:11px 13px;font-size:12px;line-height:1.6;color:#655d49;margin:10px 0 0;overflow-wrap:anywhere;}
.reason strong {color:#26796b;margin-right:8px;}
.small-label {font-size:11px;font-weight:700;color:#4e7469;margin:9px 0 5px;}
.evidence-explanation {padding:11px 14px;border-radius:12px;background:#f0f7f3;color:#527063;font-size:11px;line-height:1.6;margin-bottom:12px;}
.match-table {width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;border:1px solid #e0e9e3;border-radius:14px;overflow:hidden;margin-bottom:16px;font-size:12px;}
.match-table th {background:#edf6f0;color:#416556;padding:11px;text-align:left;font-size:10px;letter-spacing:.02em;font-weight:750;}
.match-table td {padding:13px 11px;border-top:1px solid #e5ece6;vertical-align:top;line-height:1.6;overflow-wrap:anywhere;color:#354c46;}
.match-table tr:nth-child(even) td {background:#fcfdfb;}
.match-table th:nth-child(1){width:26%;}.match-table th:nth-child(2){width:29%;}.match-table th:nth-child(3){width:45%;}
.match-table .source-id {display:block;}.table-note {display:block;font-size:10px;color:#83908a;margin:5px 0;}
.badge {display:inline-block;border-radius:20px;padding:3px 8px;font-size:10px;font-weight:650;margin:0 0 7px;}
.badge.direct {background:#def3e6;color:#297452;}.badge.partial {background:#fcf0d9;color:#9c7426;}.badge.none {background:#edf0f0;color:#71827c;}
.counts {display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap;}.count {padding:5px 9px;border:1px solid #e0e9e2;border-radius:9px;font-size:10px;color:#60796c;}.count strong {font-size:15px;color:#296e56;margin-right:5px;}
.section-title {font-weight:700;font-size:13px;margin:12px 0 8px;color:#375e50;}
.question-card {border:1px solid #cce5d8;background:linear-gradient(120deg,#edf8f0,#f6fbf7);padding:18px 20px;border-radius:16px;}
.question-meta {font-size:10px;color:#6a8a7a;margin-bottom:10px;}.question-text {font-size:16px;font-weight:620;line-height:1.65;color:#21463c;white-space:pre-wrap;overflow-wrap:anywhere;}
.feedback-section {padding:13px 16px;background:#f5f9f5;border:1px solid #e3ece3;border-radius:13px;margin:10px 0;font-size:12px;line-height:1.65;overflow-wrap:anywhere;}
.feedback-section.warm {background:#fffaee;border-color:#f3e9d3;}.feedback-section h4 {font-size:12px;margin:0 0 7px;font-weight:700;color:#477559;}.feedback-section p {margin:4px 0;white-space:pre-wrap;}
.stText [data-testid="stText"] {font-size:12px;}
[data-testid="stExpander"] {border:1px solid #e3eae3;border-radius:12px;box-shadow:none;}
[data-testid="stExpander"] summary p {font-size:11px;font-weight:550;}
[data-testid="stAlert"] {border-radius:12px;font-size:12px;}
[data-testid="stAlert"] p {font-size:12px;line-height:1.55;}
[data-testid="stForm"] {border:0;padding:0;}
[data-testid="stCheckbox"] p {font-size:12px;}
.muted-footnote {font-size:10px;color:#8b9a91;line-height:1.6;}
@media(min-width:1050px){.st-key-career_workspace{min-height:630px;}.st-key-materials{min-height:630px;}}
@media(max-width:1100px){.block-container,[data-testid="stMainBlockContainer"]{padding:18px 22px!important;}.panel-heading h2{font-size:20px!important;}.stTabs [role="tab"] p{font-size:11px;}.st-key-materials,.st-key-career_workspace{padding:18px 16px;}}
@media(max-width:800px){.brand{font-size:18px;gap:8px;}.brand-mark{width:35px;height:35px;border-radius:11px;}.connection{font-size:10px;padding:5px 8px;}.hero{height:155px;}.hero h1{font-size:29px!important;left:22px;max-width:55%;}.hero img{right:-25px;width:300px;height:215px;top:-27px;}.st-key-top_nav [data-testid="stSelectbox"]{font-size:12px;}}
@media(max-width:640px){.block-container,[data-testid="stMainBlockContainer"]{padding:14px 14px 24px!important;}.st-key-top_nav>[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:8px;}.st-key-top_nav [data-testid="stColumn"]:first-child{flex-basis:100%!important;width:100%!important;}.st-key-top_nav [data-testid="stColumn"]:not(:first-child){flex:1!important;min-width:0!important;}.hero{height:148px;border-radius:18px;}.hero h1{font-size:25px!important;left:19px;max-width:55%;letter-spacing:-.8px;}.hero img{width:225px;right:-46px;top:-2px;height:165px;}.panel-heading h2{font-size:21px!important;}.stTabs [role="tablist"]{gap:5px;}.stTabs [role="tab"]{padding:7px 5px;min-width:0!important;height:52px;}.stTabs [role="tab"] p{font-size:10px!important;white-space:normal;text-align:center;line-height:1.25;}.match-table th,.match-table td{padding:8px;font-size:10px;}.st-key-result_scroll{max-height:520px!important;}.empty-state{min-height:245px;}}
</style>
"""


def inject_styles(lang):
    st.html(CSS)
    drop, browse = (html.escape(tr(k, lang), quote=True) for k in ("drop", "browse"))
    # Keep the real Streamlit file input and button; localize its native visual labels.
    st.html(f'''<style>
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span:after {{content:"{drop}";font-size:12px;}}
    [data-testid="stFileUploaderDropzone"] button[aria-label="{browse}"]:after {{content:"{browse}";font-size:11px;}}
    [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"]) button:after {{display:none;}}
    </style>''')


def hero(title):
    image_path = Path(__file__).resolve().parents[1] / "assets/career-hero.png"
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    st.markdown(f'<section class="hero"><h1>{html.escape(title)}</h1><img src="data:image/png;base64,{encoded}" alt="" aria-hidden="true"></section>', unsafe_allow_html=True)


def heading(title, name):
    st.markdown(f'<div class="panel-heading"><span class="panel-icon">{icon(name)}</span><h2>{html.escape(title)}</h2></div>', unsafe_allow_html=True)


def safe_text(text):
    st.text(text)


def label(text):
    st.markdown(f'<div class="small-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def empty_state(text, name):
    st.markdown(f'<div class="empty-state"><div class="empty-icon">{icon(name,32)}</div><p>{html.escape(text)}</p></div>', unsafe_allow_html=True)


def guide_panel(ids, guides, lang="en"):
    used = [g for g in guides if g.id in ids]
    with st.expander(tr("guide_refs", lang, n=len(used))):
        if not used:
            st.caption(tr("no_refs", lang))
        for g in used:
            st.caption(f"{g.id} · {g.filename}")
            safe_text(g.text)


def evidence_panel(items):
    for e in items:
        st.caption(e.source_id)
        safe_text(e.quote)


def quote_card(title, text, sources="", refined=False):
    st.markdown(f'<div class="quote-card {"refined" if refined else ""}"><span class="chip">{html.escape(title)}</span><div class="quote-text">{html.escape(text)}</div><span class="source-id">{html.escape(sources)}</span></div>', unsafe_allow_html=True)


def feedback_section(title, items, warm=False):
    content = "".join(f'<p>{html.escape(item)}</p>' for item in items)
    st.markdown(f'<section class="feedback-section {"warm" if warm else ""}"><h4>{html.escape(title)}</h4>{content}</section>', unsafe_allow_html=True)


def matching_table(context, result, lang):
    lookup = {m.requirement_id: m for m in result.matches}
    counts = ''.join(f'<span class="count"><strong>{sum(m.status == key for m in result.matches)}</strong>{html.escape(tr(key,lang))}</span>' for key in ("direct","partial","none"))
    st.markdown(f'<div class="counts">{counts}</div><div class="evidence-explanation">{html.escape(tr("matching_note",lang))}</div>', unsafe_allow_html=True)
    for category in ("responsibility", "required", "preferred"):
        requirements = [q for q in context.requirements if q.category == category]
        if not requirements:
            continue
        rows = []
        for q in requirements:
            match = lookup[q.id]
            evidence = '<br>'.join(f'{html.escape(e.quote)}<span class="source-id">{html.escape(e.source_id)}</span>' for e in match.evidence) or html.escape(tr("no_evidence",lang))
            gap = f'<span class="table-note">{html.escape(tr(match.gap_type,lang))}</span>' if match.gap_type != 'sufficient' else ''
            rows.append(f'''<tr><td>{html.escape(q.quote)}<span class="source-id">{html.escape(q.id)} ← {html.escape(q.source_id)}</span><span class="table-note">{html.escape(tr(match.priority,lang))}</span></td><td><span class="badge {match.status}">{html.escape(tr(match.status,lang))}</span><br>{evidence}<span class="table-note">{html.escape(match.assessment)}</span></td><td>{html.escape(match.suggestion)}{gap}</td></tr>''')
        headers = ''.join(f'<th>{html.escape(tr(k,lang))}</th>' for k in ('requirement','evidence','suggestion'))
        st.markdown(f'<div class="section-title">{html.escape(tr(category,lang))}</div><table class="match-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table>', unsafe_allow_html=True)


def localize_native_controls(lang):
    """Localize only Streamlit-owned upload controls, never source or AI text.

    Streamlit has no uploader locale argument. CSS supplies visible labels; this
    narrow DOM adapter supplies equivalent accessible names and native file errors.
    It never reads file bytes, inputs, answers, credentials or network responses.
    """
    import json
    payload = json.dumps({
        "lang": lang,
        "upload": tr("browse",lang),
        "drop": tr("drop",lang),
        "file": tr("pdf_label",lang),
        "remove": tr("remove_file",lang),
        "limit": {"en":"Upload a PDF no larger than 10 MB.","zh-CN":"请上传不超过 10 MB 的 PDF。","zh-TW":"請上傳不超過 10 MB 的 PDF。"}[lang],
    },ensure_ascii=False)
    st.html('''<script>
    (() => {
      const words = ''' + payload + ''';
      document.documentElement.lang = words.lang;
      if (window.__careerLocaleObserver) window.__careerLocaleObserver.disconnect();
      const set = (el, attr, value) => {if(el && el.getAttribute(attr)!==value) el.setAttribute(attr,value);};
      const apply = () => {
        document.querySelectorAll('[data-testid="stFileUploader"]').forEach(root => {
          set(root.querySelector('input[type="file"]'),'aria-label',words.file);
          root.querySelectorAll('[data-testid="stFileUploaderDropzone"] button').forEach(el => {
            const isDelete = !!el.closest('[data-testid="stFileChipDeleteBtn"]');
            set(el,'aria-label',isDelete ? words.remove : words.upload);
            if(isDelete) set(el,'title',words.remove);
          });
          root.querySelectorAll('[role="alert"]').forEach(el => {
            const text=el.textContent.trim();
            if (text===words.limit || !/file|size|large|type|exceed|请上传不超过|請上傳不超過/i.test(text)) return;
            const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
            let node, first=true;
            while((node=walker.nextNode())) {
              if (!node.nodeValue.trim()) continue;
              node.nodeValue=first ? words.limit : '';
              first=false;
            }
          });
        });
      };
      apply();
      window.__careerLocaleObserver = new MutationObserver(apply);
      window.__careerLocaleObserver.observe(document.body,{childList:true,subtree:true,characterData:true});
    })();
    </script>''',unsafe_allow_javascript=True)
