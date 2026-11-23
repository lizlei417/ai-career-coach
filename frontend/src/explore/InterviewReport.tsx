import { useState } from "react";
import { useCopy } from "./shared";
import type { Analysis, Review } from "./Reviews";

function SuggestedAnswer({
  text,
  framework,
}: {
  text: string;
  framework: boolean;
}) {
  const { l } = useCopy();
  const [feedback, setFeedback] = useState("");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setFeedback(l("已复制", "Copied"));
    } catch {
      setFeedback(l("请选中回答后复制", "Select the answer to copy it."));
    }
  }
  return (
    <section className="suggested-answer">
      <h4>{l("参考回答", "Suggested Answer")}</h4>
      <small>
        {framework
          ? l(
              "示范框架，请补充真实经历。",
              "Answer framework. Fill in your own experience.",
            )
          : l(
              "本回答参考了已上传的简历。",
              "This answer draws on your resume.",
            )}
      </small>
      <p>{text}</p>
      <button type="button" onClick={copy}>
        {l("复制回答", "Copy answer")}
      </button>{" "}
      <span role="status">{feedback}</span>
    </section>
  );
}

export function InterviewQuestions({
  review,
  analysis,
}: {
  review: Review;
  analysis?: Analysis["result"];
}) {
  const { l } = useCopy();
  const result =
    typeof analysis === "object" && Array.isArray(analysis?.items)
      ? analysis
      : undefined;
  return (
    <div className="interview-questions">
      {review.questions.map((q, i) => {
        const item = result?.items[i];
        return (
          <details key={i} open={i === 0} className="interview-question">
            <summary>
              <small>
                {l("面试官的问题", "Interviewer question")} {i + 1}
                {item?.question_type && " · " + item.question_type}
              </small>
              <strong>{q.question}</strong>
            </summary>
            <div className="question-body">
              <div className="actual-answer">
                <h4>{l("我的实际回答", "My recorded answer")}</h4>
                <p>
                  {q.answer || l("尚未记录当时的回答", "No answer recorded")}
                </p>
              </div>
              {q.reflection && (
                <p>
                  <b>{l("想改进的地方", "Your reflection")}</b> · {q.reflection}
                </p>
              )}
              {q.feedback && (
                <p>
                  <b>{l("面试官反馈", "Interviewer feedback")}</b> ·{" "}
                  {q.feedback}
                </p>
              )}
              {item && (
                <>
                  <section>
                    <h4>
                      {l(
                        "面试官想考察什么？",
                        "What is the interviewer assessing?",
                      )}
                    </h4>
                    <p>{item.intent}</p>
                  </section>
                  {q.answer && (
                    <section>
                      <h4>
                        {l("你的回答表现如何？", "What does your answer show?")}
                      </h4>
                      <p>{item.evaluation}</p>
                    </section>
                  )}
                  <section className="next-answer">
                    <h4>{l("下次应该怎么改进？", "What to do next time")}</h4>
                    <p>{item.improve}</p>
                  </section>
                  <SuggestedAnswer
                    text={item.example}
                    framework={!item.grounded || /［|\[/.test(item.example)}
                  />
                </>
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}

export function InterviewAnalysis({ report }: { report: Analysis }) {
  const { l } = useCopy();
  const r = report.result;
  if (
    !report.input?.questions ||
    !r ||
    typeof r !== "object" ||
    !Array.isArray(r.items) ||
    r.items.length !== report.input.questions.length ||
    r.items.some((item) => !item || typeof item.example !== "string")
  ) {
    return (
      <section>
        <h3>{l("旧版分析", "Earlier analysis")}</h3>
        <p>
          {typeof r === "string"
            ? r
            : typeof report === "string"
              ? report
              : JSON.stringify(r ?? report, null, 2)}
        </p>
      </section>
    );
  }
  return (
    <>
      <InterviewQuestions review={report.input} analysis={r} />
      <section className="interview-summary">
        <h3>{l("本次面试总结", "Interview summary")}</h3>
        <div>
          {(
            [
              ["strengths", "已有的积极表现", "Observed strengths"],
              ["priorities", "最需要改进的地方", "Improvement priorities"],
              ["practice", "建议重点练习的问题", "Questions to practise"],
              ["checklist", "下次面试准备清单", "Preparation checklist"],
            ] as const
          ).map(([key, zh, en]) => {
            const points = String(r[key] || "")
              .split(/\n+|(?:^|[；;。]\s*)\d+[.、]\s*/)
              .map((v) => v.trim())
              .filter(Boolean);
            return (
              <section key={key}>
                <h4>{l(zh, en)}</h4>
                {points.length > 1 ? (
                  <ul>
                    {[...new Set(points)].map((v) => (
                      <li key={v}>{v}</li>
                    ))}
                  </ul>
                ) : (
                  <p>{points[0]}</p>
                )}
              </section>
            );
          })}
        </div>
      </section>
    </>
  );
}
