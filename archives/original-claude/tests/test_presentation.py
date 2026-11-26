"""UI language and truthful request status contracts."""
from string import Formatter
from types import SimpleNamespace
import pytest
from coach.errors import CoachError
from coach.i18n import ERRORS,LANGUAGES,STRINGS,localize_error,tr
from coach.presentation import ObservedClient,connection_state


def test_all_locale_entries_have_equivalent_placeholders():
    for key,texts in STRINGS.items():
        assert len(texts)==3 and all(texts)
        fields=[{name for _,name,_,_ in Formatter().parse(text) if name} for text in texts]
        assert fields[0]==fields[1]==fields[2],key
    for original in ERRORS:
        for code in LANGUAGES:
            localized=localize_error(original,code)
            assert localized and localized != tr('error_generic',code)
            if code=='en': assert not any('\u4e00'<=c<='\u9fff' for c in localized)


def test_dynamic_input_pdf_and_guide_errors_are_localized():
    messages=['简历内容不足，请提供至少 30 个非空白字符的真实经历或岗位要求。',
              'JD超过 24,000 字符，请精简后重试；系统不会静默截断材料。',
              '无法读取知识文件：guide.pdf（请检查格式、编码或大小）。']
    for message in messages:
        assert localize_error(message,'en') != tr('error_generic','en')
        assert not any('\u4e00'<=c<='\u9fff' for c in localize_error(message,'en'))
        assert localize_error(message,'zh-TW') != message


def test_connection_status_never_infers_success_from_a_key():
    state={};config=SimpleNamespace(api_key='',model='test-model')
    assert connection_state(state,config)=='offline'
    config.api_key='synthetic-test-key'
    assert connection_state(state,config)=='unverified'
    class Stub:
        def generate(self,*args):return 'ok'
    assert ObservedClient(Stub(),state).generate(None,None,None)=='ok'
    assert connection_state(state,config)=='verified'
    config.model='changed-model'
    assert connection_state(state,config)=='unverified'
    class Failed:
        def generate(self,*args):raise CoachError('Synthetic error')
    with pytest.raises(CoachError):ObservedClient(Failed(),state).generate(None,None,None)
    assert connection_state(state,config)=='failed'
    config.api_key=''
    assert connection_state(state,config)=='offline'
