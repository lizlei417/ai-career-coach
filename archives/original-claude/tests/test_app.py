"""Streamlit interaction tests. FakeAI is explicitly injected only inside tests."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from coach.models import *

APP = Path(__file__).resolve().parents[1] / 'app.py'
RESUME = 'Built a Python dashboard for a university project.'
JD = 'Required: Python programming. Preferred: SQL analytics.'


class FakeAI:
    def __init__(self, config): pass
    def generate(self, schema, system, payload):
        if schema is Extraction:
            return Extraction(resume_is_valid=True,jd_is_valid=True,issues=[],requirements=[
                Requirement(id='Q001',source_id='J001',quote='Python programming',category='required'),
                Requirement(id='Q002',source_id='J001',quote='SQL analytics',category='preferred')])
        if schema is Audit:
            return Audit(items=[AuditItem(id=c['id'],supported=True,reason='Explicit UI test stub') for c in payload['candidate_items']])
        if schema is Optimization:
            return Optimization(revisions=[Revision(id='E001',requirement_ids=['Q001'],evidence=[Evidence(source_id='R001',quote=RESUME)],optimized='Developed a Python dashboard for a university project.',reason='Clarifies action')],gaps=[],guide_ids=[])
        if schema is Matching:
            return Matching(matches=[
                Match(requirement_id='Q001',status='direct',evidence=[Evidence(source_id='R001',quote=RESUME)],assessment='Python evidence',gap_type='sufficient',suggestion='Keep evidence',priority='low'),
                Match(requirement_id='Q002',status='none',evidence=[],assessment='Not in material',gap_type='not_in_material',suggestion='Practice SQL or add actual evidence',priority='medium')],guide_ids=[])
        if schema is Question:
            return Question(text=payload.get('requested_follow_up','How would you validate a Python dashboard?'),kind='technical',requirement_id='Q001',evidence=[],guide_ids=[])
        if schema is Feedback:
            return Feedback(strengths=['Mentions checking'],missing_information=['Edge cases'],action='Describe one edge case.',answer_quotes=[payload['current_answer']],follow_up='Which edge case would you test?',guide_ids=[])
        if schema is InterviewSummary:
            return InterviewSummary(strengths=['Validation'],practice_priorities=['Boundary cases'],next_steps=['Practice one test scenario.'],guide_ids=[])
        raise AssertionError(schema)


def select(app, feature):
    # AppTest does not expose tab click events; the browser test covers real clicks.
    from coach.i18n import tr
    keys={'Resume Optimization':'resume_tab','Job Matching':'matching_tab','Mock Interview':'interview_tab'}
    app.session_state['selected']=feature
    app.session_state['workspace_tab']=tr(keys[feature],app.session_state['ui_language'])
    app.run()
    assert not app.exception


def click(app, key):
    app.button(key=key).click().run()
    assert not app.exception


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-test-key')
    monkeypatch.setattr('coach.llm.AIClient',FakeAI)
    a = AppTest.from_file(str(APP),default_timeout=15).run()
    a.text_area(key='resume_text').input(RESUME)
    a.text_area(key='jd_text').input(JD).run()
    assert not a.exception
    return a


def test_missing_key_and_empty_materials(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','')
    a=AppTest.from_file(str(APP)).run()
    assert not a.exception
    assert a.selectbox(key='ui_language').value=='en'
    assert a.button(key='analyze').disabled
    assert a.session_state['connection_status']=='offline'
    for name in ['Job Matching','Mock Interview','Resume Optimization']: select(a,name)
    assert not a.session_state['context']


def test_all_features_shared_context_and_material_reset(app):
    click(app,'analyze')
    assert len(app.session_state['optimization'][0].revisions)==1
    app.checkbox(key='accept_E001').check().run()
    original=app.session_state['context'].fingerprint
    assert app.session_state['connection_status']=='verified'
    select(app,'Job Matching'); click(app,'analyze')
    assert app.session_state['matching']
    assert app.session_state['context'].fingerprint==original
    select(app,'Resume Optimization')
    assert app.checkbox(key='accept_E001').value
    select(app,'Mock Interview'); click(app,'start_interview')
    assert app.session_state['interview']['question']
    app.text_area(key='jd_text').input(JD+' Familiarity with reporting.').run()
    assert not app.exception
    assert app.session_state['context'] is None
    assert app.session_state['optimization'] is None
    assert app.session_state['matching'] is None
    assert app.session_state['interview']['question'] is None


def answer(app,text):
    area=next(t for t in app.text_area if t.key.startswith('answer_'))
    area.input(text).run()
    click(app,'submit_answer')


def test_interview_retry_followup_next_end_restart(app):
    select(app,'Mock Interview'); click(app,'start_interview')
    answer(app,'I would check row counts.')
    assert len(app.session_state['interview']['turns'])==1
    click(app,'retry_answer')
    assert app.session_state['interview']['attempt']==2
    answer(app,'I would check empty rows and data types.')
    assert len(app.session_state['interview']['turns'])==2
    click(app,'followup_question')
    assert app.session_state['interview']['question'].text=='Which edge case would you test?'
    answer(app,'I would use an empty dataset.')
    click(app,'next_question')
    assert app.session_state['interview']['question_number']==3
    click(app,'finish_interview')
    assert app.session_state['interview']['ended'] and app.session_state['interview']['summary']
    click(app,'restart_interview')
    assert not app.session_state['interview']['turns']
    assert not app.session_state['interview']['ended']


def test_end_without_answer_has_no_fake_summary(app):
    select(app,'Mock Interview'); click(app,'start_interview'); click(app,'finish_interview')
    assert app.session_state['interview']['ended']
    assert app.session_state['interview']['summary'] is None


def test_clear_session_removes_materials(app):
    click(app,'clear_session')
    assert app.text_area(key='resume_text').value==''
    assert app.text_area(key='jd_text').value==''
    assert app.session_state['context'] is None


def test_language_switch_preserves_results_sources_and_adoptions(app):
    click(app,'analyze')
    app.checkbox(key='accept_E001').check().run()
    original=app.session_state['optimization'][0].model_dump()
    original_fp=app.session_state['context'].fingerprint
    for code in ['zh-CN','zh-TW','en']:
        app.selectbox(key='ui_language').set_value(code).run()
        assert not app.exception
        assert app.text_area(key='resume_text').value==RESUME
        assert app.text_area(key='jd_text').value==JD
        assert app.session_state['optimization'][0].model_dump()==original
        assert app.session_state['context'].fingerprint==original_fp
        assert app.checkbox(key='accept_E001').value
    assert app.session_state['result_languages']['optimization']=='en'


def test_interview_draft_turns_and_feedback_survive_locale_and_tabs(app):
    select(app,'Mock Interview'); click(app,'start_interview')
    area=next(t for t in app.text_area if t.key.startswith('answer_'))
    area.input('Draft answer that must persist.').run()
    select(app,'Job Matching'); select(app,'Mock Interview')
    assert next(t for t in app.text_area if t.key.startswith('answer_')).value=='Draft answer that must persist.'
    app.selectbox(key='ui_language').set_value('zh-TW').run()
    assert not app.exception
    assert app.session_state['selected']=='Mock Interview'
    assert next(t for t in app.text_area if t.key.startswith('answer_')).value=='Draft answer that must persist.'
    click(app,'submit_answer')
    feedback=app.session_state['interview']['feedback'][0].model_dump()
    assert app.session_state['interview_languages']['feedback']=='zh-TW'
    app.selectbox(key='ui_language').set_value('en').run()
    assert app.session_state['interview']['feedback'][0].model_dump()==feedback
    assert len(app.session_state['interview']['turns'])==1


def test_paste_draft_survives_pdf_mode(app):
    app.radio(key='resume_mode').set_value('pdf').run()
    app.radio(key='resume_mode').set_value('text').run()
    assert app.text_area(key='resume_text').value==RESUME


def test_generated_language_tracks_selected_locale(app,monkeypatch):
    original=FakeAI.generate
    calls=[]
    def record(self,schema,system,payload):
        calls.append(payload['output_language'])
        return original(self,schema,system,payload)
    monkeypatch.setattr(FakeAI,'generate',record)
    app.selectbox(key='ui_language').set_value('zh-CN').run()
    click(app,'analyze')
    assert calls and set(calls)=={'简体中文'}
    assert app.session_state['result_languages']['optimization']=='zh-CN'
    app.selectbox(key='ui_language').set_value('en').run()
    assert app.button(key='regenerate_optimization')
    click(app,'regenerate_optimization')
    assert app.session_state['result_languages']['optimization']=='en'
    assert calls[-1]=='English'


@pytest.mark.parametrize('code,expected',[('en','authentication'),('zh-CN','身份验证'),('zh-TW','身分驗證')])
def test_backend_errors_localized_without_data_loss(app,monkeypatch,code,expected):
    from coach.errors import CoachError
    click(app,'analyze')
    previous=app.session_state['optimization'][0].model_dump()
    app.selectbox(key='ui_language').set_value(code).run()
    def fail(*args,**kwargs):
        raise CoachError('API 身份验证失败，请检查 .env 中的 API Key。')
    monkeypatch.setattr(FakeAI,'generate',fail)
    click(app,'analyze')
    assert any(expected in e.value for e in app.error)
    assert app.session_state['optimization'][0].model_dump()==previous
    assert app.session_state['connection_status']=='failed'


def test_summary_can_regenerate_language_without_losing_turns(app):
    select(app,'Mock Interview');click(app,'start_interview')
    answer(app,'I would verify missing values before applying transformations.')
    click(app,'finish_interview')
    turns=[t.model_dump() for t in app.session_state['interview']['turns']]
    original_summary=app.session_state['interview']['summary'][0].model_dump()
    app.selectbox(key='ui_language').set_value('zh-TW').run()
    assert app.session_state['interview']['summary'][0].model_dump()==original_summary
    assert app.session_state['interview']['ended']
    click(app,'regenerate_summary')
    assert app.session_state['interview_languages']['summary']=='zh-TW'
    assert [t.model_dump() for t in app.session_state['interview']['turns']]==turns


def test_material_consistent_v1_session_migrates_without_losing_results(app):
    import hashlib
    from coach.config import ROOT,settings
    from coach.parsing import fingerprint
    click(app,'analyze')
    original=app.session_state['optimization'][0].model_dump()
    prompt_hash=hashlib.sha256(''.join(p.read_text() for p in sorted((ROOT/'prompts').glob('*.md'))).encode()).hexdigest()
    legacy=fingerprint(RESUME,JD,settings().model+'English'+prompt_hash)
    app.session_state['ui_version']=1
    app.session_state['language']='English'
    app.session_state['input_fingerprint']=legacy
    app.session_state['context']=app.session_state['context'].model_copy(update={'fingerprint':legacy})
    app.run()
    assert not app.exception
    assert app.session_state['optimization'][0].model_dump()==original
    assert app.session_state['context'] is not None
    assert app.session_state['context'].fingerprint!=legacy
