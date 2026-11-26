"""Opt-in real API smoke test, using clearly labelled synthetic inputs only.
Not a pytest test. Makes billable API calls only if a key is configured.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coach.config import settings
from coach.errors import CoachError
from coach.knowledge import KnowledgeBase
from coach.llm import AIClient
from coach.models import Turn
from coach.parsing import fingerprint
from coach.service import CareerCoach


def main():
    config = settings()
    if not config.api_key:
        print('SKIPPED: OPENAI_API_KEY 未配置；没有发起真实 API 请求。')
        return 2
    resume = (ROOT/'examples/demo_resume.txt').read_text()
    jd = (ROOT/'examples/demo_jd.txt').read_text()
    coach = CareerCoach(AIClient(config), KnowledgeBase(config.knowledge_dir))
    context = coach.prepare(resume, jd, fingerprint(resume,jd,config.model))
    print('PASS: 真实 API 资料解析与核验')
    result, _, blocked = coach.optimize(context)
    print(f'PASS: 真实 API 简历优化流程（保留 {len(result.revisions)} 条改写，拦截 {blocked} 项）')
    coach.match(context)
    print('PASS: 真实 API 岗位匹配与逐项来源核验')
    turns = []
    answers = [
        'In my coursework dashboard project I used pandas to check missing values. I documented cleaning decisions and asked a teammate to review them. I did not measure a quantitative outcome.',
        'For the dataset check, I would first count missing values per column, inspect unexpected types and keep a small test dataset including empty rows. I would record assumptions before changing values.',
    ]
    question, _ = coach.question(context, turns)
    for answer in answers:
        feedback, _ = coach.feedback(context, question, answer)
        turns.append(Turn(question=question,answer=answer,feedback=feedback,attempt=1))
        if len(turns) < len(answers):
            question, _ = coach.question(context, turns, feedback.follow_up)
    coach.summarize(context, turns)
    print('PASS: 真实 API 两轮面试、反馈与总结（回答为预先声明的合成测试输入）')
    print('这些检查验证可执行流程与结构校验，AI 语义质量仍需人工复核。')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except CoachError as error:
        print(f'FAILED: {error}')
        sys.exit(1)
