"""Synthetic materials and explicit test doubles; no real API calls or demo results."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import httpx
import openai
import pytest
from pypdf import PdfWriter
from coach.config import Settings
from coach.errors import CoachError
from coach.knowledge import KnowledgeBase
from coach.llm import AIClient
from coach.models import *
from coach.parsing import fingerprint, pdf_text, sources, validate_text
from coach.service import CareerCoach
from coach.state import initialize, invalidate
from coach.validation import check_matching


@pytest.fixture
def context():
    return Context(fingerprint="test", resume=[Source(id="R001", text="Built a Python dashboard for a university project.")],
                   jd=[Source(id="J001", text="Required: Python. Preferred: SQL.")],
                   requirements=[Requirement(id="Q001", source_id="J001", quote="Python", category="required"),
                                 Requirement(id="Q002", source_id="J001", quote="SQL", category="preferred")])


class FakeAI:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def generate(self, schema, system, payload):
        self.calls.append((schema, system, payload))
        value = self.responses.pop(0)
        assert isinstance(value, schema)
        return value


def coach(tmp_path, *responses):
    return CareerCoach(FakeAI(*responses), KnowledgeBase(tmp_path))


def verdict(*pairs):
    return Audit(items=[AuditItem(id=k, supported=v, reason="Synthetic test verdict") for k, v in pairs])


def question():
    return Question(text="How would you validate a Python data pipeline?", kind="technical", requirement_id="Q001", evidence=[], guide_ids=[])


def feedback(answer="I would validate row counts."):
    return Feedback(strengths=["Mentions validation"], missing_information=["Edge cases"], action="Add one edge case.", answer_quotes=[answer], follow_up="Which edge case would you test?", guide_ids=[])


@pytest.mark.parametrize("text", ["", " \n", "short", "x"*24001])
def test_rejects_bad_text(text):
    with pytest.raises(CoachError): validate_text(text, "Resume")


def test_source_ids_and_fingerprint():
    assert [s.id for s in sources("First\n\nSecond", "R")] == ["R001", "R002"]
    assert fingerprint("a", "b") != fingerprint("b", "a")
    assert fingerprint("a", "b", "English") != fingerprint("a", "b", "中文")


def test_pdf_corrupt_scanned_and_encrypted():
    with pytest.raises(CoachError, match="无法读取"): pdf_text(b"not a PDF")
    writer = PdfWriter(); writer.add_blank_page(400, 500)
    buf = BytesIO(); writer.write(buf)
    with pytest.raises(CoachError, match="扫描件"): pdf_text(buf.getvalue())
    writer.encrypt("secret"); buf = BytesIO(); writer.write(buf)
    with pytest.raises(CoachError, match="加密"): pdf_text(buf.getvalue())


def test_text_pdf_is_readable():
    # Small portable PDF fixture using built-in Helvetica, no extra dependency.
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter(); page = writer.add_blank_page(600, 800)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 30 750 Td (Built a Python dashboard for a university project.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    buf = BytesIO(); writer.write(buf)
    assert "Python dashboard" in pdf_text(buf.getvalue())


def test_state_invalidation_clears_all_derived_data():
    state = {}; initialize(state)
    state.update(input_fingerprint="old", context="old", optimization="old", matching="old", accepted={"E001":True})
    state["interview"]["turns"] = ["old"]
    state["answer_old"] = "private answer"; state["accept_E001"] = True
    assert invalidate(state, "new")
    assert state["context"] is None and state["optimization"] is None and state["matching"] is None
    assert not state["interview"]["turns"] and not state["accepted"]
    assert "answer_old" not in state and "accept_E001" not in state
    assert not invalidate(state, "new")


def test_retrieval_uses_real_content_only(tmp_path):
    assert KnowledgeBase(tmp_path).retrieve("Python") == []
    (tmp_path / "README.md").write_text("Python should not be loaded")
    (tmp_path / "interview.md").write_text("Python technical interviews: explain validation, methods and reasoning.")
    (tmp_path / "中文.txt").write_text("面试回答请说明具体行动和结果，展示推理过程。")
    kb = KnowledgeBase(tmp_path)
    assert len(kb.retrieve("Python reasoning")) == 1
    assert kb.retrieve("行动结果")[0].filename == "中文.txt"
    assert kb.retrieve("zebraquux") == []
    assert all(g.filename != "README.md" for g in kb.guides)


def test_bad_guide_shows_warning(tmp_path):
    (tmp_path / "bad.pdf").write_bytes(b"bad")
    assert KnowledgeBase(tmp_path).warnings


def test_hallucinated_quote_is_blocked(context, tmp_path):
    result = Optimization(revisions=[Revision(id="E001", requirement_ids=["Q001"], evidence=[Evidence(source_id="R001", quote="Invented internship")], optimized="Invented", reason="Test")], gaps=[], guide_ids=[])
    with pytest.raises(CoachError): coach(tmp_path, result).optimize(context)


def test_unsupported_rewrite_hidden(context, tmp_path):
    result = Optimization(revisions=[Revision(id="E001", requirement_ids=["Q001"], evidence=[Evidence(source_id="R001", quote="Built a Python dashboard")], optimized="Led 20 engineers and increased revenue 50%.", reason="Test")], gaps=[], guide_ids=[])
    safe, guides, blocked = coach(tmp_path, result, verdict(("E001", False))).optimize(context)
    assert not safe.revisions and blocked == 1 and not guides


def test_auditor_omission_fails_closed(context, tmp_path):
    c = coach(tmp_path, Audit(items=[]))
    with pytest.raises(CoachError): c.audit([{"id":"E001"}], {})


def test_matching_coverage_and_no_evidence(context):
    m = Match(requirement_id="Q001", status="none", evidence=[], assessment="Not in provided resume", gap_type="not_in_material", suggestion="Add actual evidence", priority="high")
    with pytest.raises(CoachError, match="全部岗位要求"): check_matching(Matching(matches=[m], guide_ids=[]), context)
    second = m.model_copy(update={"requirement_id":"Q002"})
    check_matching(Matching(matches=[m, second], guide_ids=[]), context)
    wrong = m.model_copy(update={"status":"direct", "gap_type":"sufficient"})
    with pytest.raises(CoachError): check_matching(Matching(matches=[wrong, second], guide_ids=[]), context)


def test_unknown_guide_is_blocked(context, tmp_path):
    q = question().model_copy(update={"guide_ids":["G-invented"]})
    with pytest.raises(CoachError): coach(tmp_path, q).question(context, [])


def test_real_multiturn_orchestration_with_test_double(context, tmp_path):
    answer = "I would validate row counts."
    summary = InterviewSummary(strengths=["Validation"], practice_priorities=["Edge cases"], next_steps=["Practice boundary tests"], guide_ids=[])
    c = coach(tmp_path, question(), verdict(("result",True)), feedback(), verdict(("result",True)),
              question().model_copy(update={"text":"Which edge case would you test?"}), verdict(("result",True)), summary, verdict(("result",True)))
    q, _ = c.question(context, [])
    f, _ = c.feedback(context, q, answer)
    turns = [Turn(question=q, answer=answer, feedback=f, attempt=1)]
    q2, _ = c.question(context, turns, f.follow_up)
    assert q2.text == f.follow_up
    s, _ = c.summarize(context, turns)
    assert s.next_steps and len(c.client.calls) == 8
    assert c.client.calls[2][2]["current_answer"] == answer
    assert c.client.calls[4][2]["history"][0]["answer"] == answer


def test_feedback_cannot_quote_unsubmitted_answer(context, tmp_path):
    with pytest.raises(CoachError): coach(tmp_path, feedback("Invented answer")).feedback(context, question(), "Actual answer")


def test_feedback_and_summary_semantic_failures_blocked(context, tmp_path):
    with pytest.raises(CoachError, match="独立事实核查"):
        coach(tmp_path, feedback(), verdict(("result",False))).feedback(context, question(), "I would validate row counts.")
    with pytest.raises(CoachError): coach(tmp_path).summarize(context, [])


def test_ai_without_key_never_calls_api(tmp_path):
    with pytest.raises(CoachError, match="尚未连接"):
        AIClient(Settings("", "gpt-4o-mini", 60, 8000, tmp_path))


@pytest.mark.parametrize("error,expected", [
    (openai.APITimeoutError(request=httpx.Request("POST","https://api.openai.com")), "超时"),
    (openai.APIConnectionError(request=httpx.Request("POST","https://api.openai.com")), "无法连接"),
    (openai.AuthenticationError("private raw details", response=httpx.Response(401,request=httpx.Request("POST","https://api.openai.com")), body=None), "身份验证"),
    (openai.RateLimitError("private raw details", response=httpx.Response(429,request=httpx.Request("POST","https://api.openai.com")), body=None), "配额"),
    (ValueError("private resume content"), "格式"),
])
def test_api_errors_are_sanitized(tmp_path, error, expected):
    c = AIClient(Settings("synthetic-test-key", "gpt-4o-mini", 5, 1000, tmp_path))
    def fail(**kwargs): raise error
    c.client = SimpleNamespace(responses=SimpleNamespace(parse=fail))
    with pytest.raises(CoachError, match=expected) as exc:
        c.generate(Question, "system", {})
    assert "private" not in str(exc.value)


def test_sdk_receives_structured_schema_and_no_storage(tmp_path):
    c = AIClient(Settings("synthetic-test-key", "gpt-4o-mini", 5, 1000, tmp_path))
    args = {}
    def parse(**kwargs):
        args.update(kwargs)
        return SimpleNamespace(status="completed", output_parsed=question())
    c.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    assert c.generate(Question, "system", {"resume":"synthetic"}) == question()
    assert args["store"] is False and args["text_format"] is Question


def test_new_metric_blocked_even_if_model_audit_misses_it(context, tmp_path):
    result = Optimization(revisions=[Revision(id="E001", requirement_ids=["Q001"], evidence=[Evidence(source_id="R001", quote="Built a Python dashboard")], optimized="Built a Python dashboard with 50% faster reporting.", reason="Test")], gaps=[], guide_ids=[])
    safe, _, blocked = coach(tmp_path, result, verdict(("E001",True))).optimize(context)
    assert not safe.revisions and blocked == 1


def test_guide_is_passed_separately_from_resume(context, tmp_path):
    (tmp_path/'guide.md').write_text('Python interview: describe methods and verify assumptions.')
    q = question()
    c = coach(tmp_path, q, verdict(("result",True)))
    _, guides = c.question(context, [])
    payload = c.client.calls[0][2]
    assert guides and payload['guides'][0]['filename'] == 'guide.md'
    assert payload['resume'][0]['text'] == context.resume[0].text
    assert 'methods and verify' not in payload['resume'][0]['text']


def test_invented_jd_extraction_is_rejected(tmp_path):
    extraction = Extraction(resume_is_valid=True,jd_is_valid=True,issues=[], requirements=[Requirement(id='Q001', source_id='J001', quote='Invented C++', category='required')])
    with pytest.raises(CoachError):
        coach(tmp_path, extraction).prepare('Built a Python dashboard for a university project.', 'Required: Python programming for data analysis.', 'fp')
