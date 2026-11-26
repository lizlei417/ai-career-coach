import hashlib
import html
import json
import streamlit as st
from coach.config import ROOT, settings
from coach.errors import CoachError
from coach.i18n import AI_LANGUAGES, LANGUAGES, language_name, localize_error, tr
from coach.knowledge import KnowledgeBase
from coach.llm import AIClient
from coach.models import Turn
from coach.parsing import fingerprint, pdf_text, validate_text
from coach.presentation import ObservedClient, connection_state
from coach.service import CareerCoach
from coach.state import initialize, invalidate, new_interview
from coach.ui import (empty_state, evidence_panel, feedback_section, guide_panel, heading,
                      hero, icon, inject_styles, label, localize_native_controls, matching_table, quote_card, safe_text)

st.set_page_config(page_title="AI Career Coach", page_icon="✦", layout="wide", initial_sidebar_state="collapsed", menu_items={"Get Help":None,"Report a bug":None,"About":None})
S = st.session_state
initialize(S)
S.setdefault("ui_language", "en")
S.setdefault("selected", "Resume Optimization")
S.setdefault("result_languages", {})
S.setdefault("interview_languages", {})
S.setdefault("resume_draft", S.get("resume_text", ""))
S.setdefault("answer_drafts", {})
lang = S.ui_language
t = lambda key, **kwargs: tr(key, lang, **kwargs)
inject_styles(lang)
FEATURES = {"Resume Optimization":"resume_tab", "Job Matching":"matching_tab", "Mock Interview":"interview_tab"}

try:
    config = settings()
except CoachError as error:
    st.error(localize_error(str(error), lang))
    st.stop()
kb = KnowledgeBase(config.knowledge_dir)
status = connection_state(S, config)


def clear_session():
    for key in list(S):
        del S[key]


def service():
    return CareerCoach(ObservedClient(AIClient(config), S), kb, AI_LANGUAGES[lang])


def run_action(action, message="busy"):
    try:
        with st.spinner(t(message)):
            action()
        st.rerun()
    except CoachError as error:
        st.error(localize_error(str(error), lang))
    except Exception:
        st.error(t("error_generic"))


with st.container(key="top_nav"):
    brand, languages, connection, preferences = st.columns([6.6,1.65,1.65,.55],gap="small",vertical_alignment="center")
    with brand:
        st.markdown(f'<div class="brand"><span class="brand-mark">{icon("spark",26)}</span>AI Career Coach</div>',unsafe_allow_html=True)
    with languages:
        st.selectbox(t("language"),list(LANGUAGES),format_func=LANGUAGES.get,key="ui_language",label_visibility="collapsed")
    with connection:
        st.markdown(f'<div class="connection {status}" role="status"><span class="dot"></span>{html.escape(t(status))}</div>',unsafe_allow_html=True)
    with preferences:
        with st.popover("⚙",help=t("settings"),key="preferences"):
            st.markdown(f'**{t("settings")}**')
            st.caption(f'{t("model")}: {config.model}')
            st.caption(t("key_configured") if config.api_key else t("no_key"))
            st.caption(t("guides_count",n=len(kb.guides)))
            st.caption(t("retrieval"))
            if not kb.guides:
                st.caption(t("empty_guides"))
            for warning in kb.warnings:
                st.warning(localize_error(warning,lang))
            st.divider()
            st.caption(t("clear_help"))
            st.button(t("clear"),key="clear_session",on_click=clear_session,width="stretch")
hero(t("hero"))


def context(coach):
    if S.context is None:
        S.context = coach.prepare(resume,jd,fp)
    return S.context


def optimize():
    coach = service()
    result = coach.optimize(context(coach))
    S.optimization = result
    S.result_languages["optimization"] = lang
    S.accepted = {}
    for key in list(S):
        if str(key).startswith("accept_"):
            del S[key]


def match():
    coach = service()
    S.matching = coach.match(context(coach))
    S.result_languages["matching"] = lang


def ask(follow_up=None):
    interview = S.interview
    coach = service()
    question,guides = coach.question(context(coach),interview["turns"],follow_up)
    interview.update(question=question,guides=guides,feedback=None,question_number=interview["question_number"]+1,
                     attempt=1,draft_version=interview["draft_version"]+1)
    S.interview_languages["question"] = lang


def analyze():
    if S.selected == "Resume Optimization":
        optimize()
    elif S.selected == "Job Matching":
        match()
    elif S.interview["question"] is None and not S.interview["ended"]:
        ask()


def old_language_note(feature, action):
    previous = S.result_languages.get(feature,lang)
    if previous != lang:
        st.caption(t("old_language",language=language_name(previous,lang),current=language_name(lang,lang)))
        if st.button(t("regenerate",language=language_name(lang,lang)),key=f"regenerate_{feature}",disabled=not can_call):
            run_action(action)


def render_optimization():
    if not S.optimization:
        empty_state(t("empty_optimization"),"document")
        return
    old_language_note("optimization",optimize)
    result,guides,blocked = S.optimization
    if blocked:
        st.warning(t("blocked",n=blocked))
    if not result.revisions:
        st.info(t("no_revisions"))
    for revision in result.revisions:
        with st.container(key=f"revision_{revision.id}"):
            st.markdown(f'<div class="revision-meta">{html.escape(revision.id)} · {html.escape(", ".join(revision.requirement_ids))}</div>',unsafe_allow_html=True)
            left,right = st.columns(2,gap="small")
            with left:
                quote_card(t("original"),"\n\n".join(e.quote for e in revision.evidence),", ".join(e.source_id for e in revision.evidence))
            with right:
                quote_card(t("optimized"),revision.optimized,refined=True)
            st.markdown(f'<div class="reason"><strong>{html.escape(t("why"))}</strong>{html.escape(revision.reason)}</div>',unsafe_allow_html=True)
            S.accepted[revision.id] = st.checkbox(t("adopt"),value=S.accepted.get(revision.id,False),key=f"accept_{revision.id}")
    if result.gaps:
        label(t("gaps"))
        lookup = {q.id:q for q in S.context.requirements}
        for gap in result.gaps:
            with st.expander(f'{gap.requirement_id} · {lookup[gap.requirement_id].quote}'):
                safe_text(gap.explanation)
                safe_text(gap.suggestion)
    selected = [r.optimized for r in result.revisions if S.accepted.get(r.id)]
    if selected:
        st.download_button(t("download_revisions"),"\n\n".join(selected),"selected-resume-revisions.txt",mime="text/plain")
        st.caption(t("download_note"))
    guide_panel(result.guide_ids,guides,lang)


def render_matching():
    if not S.matching:
        empty_state(t("empty_matching"),"target")
        return
    old_language_note("matching",match)
    result,guides = S.matching
    matching_table(S.context,result,lang)
    st.download_button(t("download_match"),result.model_dump_json(indent=2),"job-matching.json",mime="application/json")
    guide_panel(result.guide_ids,guides,lang)


def render_interview():
    interview = S.interview
    saved_languages = set(S.interview_languages.values())
    if saved_languages and saved_languages != {lang}:
        st.caption(t("interview_language",language=language_name(lang,lang)))
    if interview["ended"]:
        label(t("summary"))
        if interview["summary"]:
            summary,guides = interview["summary"]
            for title,items in [("strengths",summary.strengths),("practice_priorities",summary.practice_priorities),("next_steps",summary.next_steps)]:
                feedback_section(t(title),items,warm=title=="practice_priorities")
            guide_panel(summary.guide_ids,guides,lang)
            if S.interview_languages.get("summary",lang) != lang:
                def regenerate_summary():
                    interview["summary"] = service().summarize(S.context,interview["turns"])
                    S.interview_languages["summary"] = lang
                if st.button(t("regenerate",language=language_name(lang,lang)),key="regenerate_summary",disabled=not can_call):
                    run_action(regenerate_summary,"busy_summary")
        else:
            st.info(t("no_answers"))
        if st.button(t("restart"),key="restart_interview",type="primary",disabled=not can_call):
            S.interview = new_interview()
            S.interview_languages = {}
            S.answer_drafts = {}
            st.rerun()
    elif interview["question"] is None:
        empty_state(t("empty_interview"),"chat")
        if st.button(t("start"),key="start_interview",type="primary",disabled=not can_call,width="stretch"):
            run_action(ask,"busy_question")
    else:
        question = interview["question"]
        meta = f'{t("question",n=interview["question_number"])} · {t(question.kind)} · {question.requirement_id} · {t("attempt",n=interview["attempt"])}'
        st.markdown(f'<section class="question-card"><div class="question-meta">{html.escape(meta)}</div><div class="question-text">{html.escape(question.text)}</div></section>',unsafe_allow_html=True)
        with st.expander(t("question_sources")):
            requirement = next(q for q in S.context.requirements if q.id == question.requirement_id)
            safe_text(f"{requirement.id} · {requirement.quote}")
            evidence_panel(question.evidence)
            guide_panel(question.guide_ids,interview["guides"],lang)
        draft_key = f"answer_{fp[:10]}_{interview['draft_version']}"
        if draft_key not in S:
            S[draft_key] = S.answer_drafts.get(draft_key,"")
        def save_answer():
            S.answer_drafts[draft_key] = S.get(draft_key,"")
        answer = st.text_area(t("answer"),height=140,max_chars=8000,key=draft_key,
                              placeholder=t("answer_placeholder"),disabled=interview["feedback"] is not None,on_change=save_answer)
        at_limit = len(interview["turns"]) >= 30
        if at_limit:
            st.info(t("question_limit"))
        if interview["feedback"] is None:
            if st.button(t("submit"),key="submit_answer",type="primary",disabled=not can_call or at_limit):
                def submit():
                    feedback,guides = service().feedback(S.context,question,answer)
                    interview["turns"].append(Turn(question=question,answer=answer,feedback=feedback,attempt=interview["attempt"]))
                    interview["feedback"] = feedback,guides
                    S.interview_languages["feedback"] = lang
                    S.answer_drafts[draft_key] = answer
                run_action(submit,"busy_feedback")
        else:
            feedback,guides = interview["feedback"]
            feedback_section(t("strengths"),feedback.strengths)
            feedback_section(t("missing"),feedback.missing_information,warm=True)
            feedback_section(t("action"),[feedback.action])
            if feedback.follow_up:
                feedback_section(t("follow_up"),[feedback.follow_up])
            if feedback.answer_quotes:
                with st.expander(t("answer_sources")):
                    for quote in feedback.answer_quotes:
                        safe_text(quote)
            guide_panel(feedback.guide_ids,guides,lang)
            a,b,c = st.columns(3,gap="small")
            if a.button(t("retry"),key="retry_answer",disabled=not can_call or at_limit,width="stretch"):
                interview.update(feedback=None,attempt=interview["attempt"]+1,draft_version=interview["draft_version"]+1)
                st.rerun()
            if b.button(t("next"),key="next_question",disabled=not can_call or at_limit,width="stretch"):
                run_action(ask,"busy_question")
            if feedback.follow_up and c.button(t("answer_followup"),key="followup_question",disabled=not can_call or at_limit,width="stretch"):
                run_action(lambda:ask(feedback.follow_up),"busy_question")
        if st.button(t("end"),key="finish_interview",disabled=not can_call):
            def finish():
                if interview["turns"]:
                    interview["summary"] = service().summarize(S.context,interview["turns"])
                    S.interview_languages["summary"] = lang
                interview["ended"] = True
            run_action(finish,"busy_summary")
    if interview["turns"]:
        with st.expander(t("history",n=len(interview["turns"]))):
            for i,turn in enumerate(interview["turns"],1):
                st.caption(f'{i} · {t("attempt",n=turn.attempt)}')
                safe_text(turn.question.text)
                safe_text(turn.answer)
                safe_text(turn.feedback.action)
        export = {"turns":[turn.model_dump() for turn in interview["turns"]],"summary":interview["summary"][0].model_dump() if interview["summary"] else None}
        st.download_button(t("download_interview"),json.dumps(export,ensure_ascii=False,indent=2),"interview-practice.json",mime="application/json")


def on_tab_change():
    inverse = {tr(key,code):name for name,key in FEATURES.items() for code in LANGUAGES}
    S.selected = inverse.get(S.workspace_tab,"Resume Optimization")


def save_resume():
    S.resume_draft = S.get("resume_text","")


materials,workspace = st.columns([.31,.69],gap="medium")
with materials, st.container(key="materials"):
    heading(t("materials"),"folder")
    label(t("resume"))
    # Locale-independent option values keep text/PDF selection stable across languages.
    legacy_modes = {"粘贴文本":"text", "上传 PDF":"pdf"}
    if S.get("resume_mode") in legacy_modes:
        S.resume_mode = legacy_modes[S.resume_mode]
    elif S.get("resume_mode") not in {"text","pdf"}:
        S.resume_mode = "text"
    mode = st.radio(t("input_mode"),["text","pdf"],format_func=lambda v:t("text_mode" if v=="text" else "pdf_mode"),horizontal=True,key="resume_mode",label_visibility="collapsed")
    resume = ""
    input_error = None
    if mode == "text":
        if "resume_text" not in S:
            S.resume_text = S.resume_draft
        resume = st.text_area(t("resume_text"),height=135,max_chars=24000,placeholder=t("resume_placeholder"),key="resume_text",label_visibility="collapsed",on_change=save_resume)
    else:
        upload = st.file_uploader(t("pdf_label"),type=["pdf"],key="resume_pdf",help=t("pdf_help"),label_visibility="collapsed")
        if upload is not None:
            data = upload.getvalue()
            digest = hashlib.sha256(data).hexdigest()
            if S.get("pdf_digest") != digest:
                S.update(pdf_digest=digest,pdf_content="",pdf_error=None)
                try:
                    S.pdf_content = pdf_text(data)
                except CoachError as error:
                    S.pdf_error = str(error)
            resume = S.get("pdf_content","")
            input_error = S.get("pdf_error")
            if input_error:
                st.error(localize_error(input_error,lang))
            else:
                with st.expander(t("extracted")):
                    safe_text(resume)
    label(t("jd"))
    jd = st.text_area(t("jd"),height=145,max_chars=24000,placeholder=t("jd_placeholder"),key="jd_text",label_visibility="collapsed")
    ready = True
    issues = []
    for text,name in [(resume,"简历"),(jd,"JD")]:
        try:
            validate_text(text,name)
        except CoachError as error:
            ready = False
            if text.strip():
                issues.append(localize_error(str(error),lang))
    prompt_hash = hashlib.sha256("".join(p.read_text() for p in sorted((ROOT/"prompts").glob("*.md"))).encode()).hexdigest()
    # Language is a presentation preference, never a material/version change.
    fp = fingerprint(resume,jd,config.model+prompt_hash)
    # Preserve material-consistent v1 sessions when installing the UI upgrade.
    if S.get("ui_version") != 2:
        for old_language in AI_LANGUAGES.values():
            if S.input_fingerprint == fingerprint(resume,jd,config.model+old_language+prompt_hash):
                S.input_fingerprint = fp
                if S.context:
                    S.context = S.context.model_copy(update={"fingerprint":fp})
                old_code = next((c for c,v in AI_LANGUAGES.items() if v==S.get("language")),"zh-CN")
                for feature in ("optimization","matching"):
                    if S.get(feature):
                        S.result_languages.setdefault(feature,old_code)
                break
        S.ui_version = 2
    changed = S.input_fingerprint != fp
    if invalidate(S,fp):
        st.toast(t("invalidated"))
    if changed:
        S.answer_drafts = {}
        S.result_languages = {}
        S.interview_languages = {}
    can_call = ready and bool(config.api_key) and not input_error
    active_interview = S.selected=="Mock Interview" and S.interview["question"] is not None
    has_result = S.optimization if S.selected=="Resume Optimization" else S.matching if S.selected=="Job Matching" else None
    if st.button(t("reanalyze" if has_result else "analyze"),key="analyze",type="primary",disabled=not can_call or active_interview,width="stretch",icon=":material/auto_awesome:"):
        run_action(analyze,"busy_question" if S.selected=="Mock Interview" else "busy")
    if issues:
        for issue in issues:
            st.warning(issue)
    elif ready:
        st.caption("✓ " + t("materials_ready"))
    with st.expander(t("disclosure")):
        st.caption(t("privacy"))
        st.caption(t("limits"))
        if not config.api_key:
            st.caption(t("no_key"))
        st.caption(t("manual_check"))

with workspace, st.container(key="career_workspace"):
    heading(t("workspace"),"layers")
    tab_labels = [t(k) for k in FEATURES.values()]
    # Remap only the tab label when changing locale; keep the selected feature.
    selected_label = t(FEATURES[S.selected])
    if S.get("workspace_tab") not in tab_labels or S.get("workspace_tab") != selected_label:
        S.workspace_tab = selected_label
    tabs = st.tabs(tab_labels,key="workspace_tab",on_change=on_tab_change)
    for tab,name in zip(tabs,FEATURES):
        if tab.open:
            with tab:
                # Keep long analyses/turn histories inside the workspace, not the entire page.
                with st.container(height=422,border=False,key="result_scroll"):
                    if name=="Resume Optimization":
                        render_optimization()
                    elif name=="Job Matching":
                        render_matching()
                    else:
                        render_interview()
    if S.context:
        with st.expander(t("source_context")):
            st.caption(t("source_note"))
            for requirement in S.context.requirements:
                safe_text(f"{requirement.id} [{t(requirement.category)}] ← {requirement.source_id} · {requirement.quote}")
            for name,items in [("resume",S.context.resume),("jd",S.context.jd)]:
                label(t(name))
                for item in items:
                    safe_text(f"{item.id} · {item.text}")

localize_native_controls(lang)
