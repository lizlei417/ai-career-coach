import { useState } from "react";
import { Mic, ChevronDown } from "lucide-react";
import type { TaskProps } from "./types";
import { Citations, req, download } from "./Results";
import { languageName } from "./i18n";
import { Field, Guides, Title } from "./ui";
function List({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="feedback-section">
      <h3>{title}</h3>
      <ul>
        {items.map((v, i) => (
          <li key={i}>{v}</li>
        ))}
      </ul>
    </section>
  );
}
export default function Interview({
  project: p,
  t,
  lang,
  act,
  busy,
}: TaskProps) {
  const [answer, setAnswer] = useState(""),
    iv = p.interview,
    q = iv.question,
    f = iv.feedback,
    disabled = busy || !p.status.configured;
  const action = async (kind: string, extra?: Record<string, string>) => {
    if (await act(kind, extra)) setAnswer("");
  };
  const turns = iv.turns,
    latest = turns.at(-1);
  return (
    <>
      <Title title={t("interview_tab")}>
        {q && !iv.ended && (
          <button disabled={disabled} onClick={() => action("summary")}>
            {t("end")}
          </button>
        )}
      </Title>
      {(q || iv.ended) && (
        <>
          {!iv.ended &&
            (iv.questionLanguage !== lang ||
              (iv.feedbackLanguage && iv.feedbackLanguage !== lang)) && (
              <p className="notice">{t("comingNext")}</p>
            )}
          {iv.ended ? (
            <article className="interview-sheet">
              <div className="kicker">
                <Mic size={16} />
                {t("ended")}
              </div>
              <h2>{t("summary")}</h2>
              {iv.summary && iv.summary.language !== lang && (
                <button disabled={disabled} onClick={() => action("summary")}>
                  {t("regenerate", { language: languageName(lang, lang) })}
                </button>
              )}
              {iv.summary ? (
                <>
                  <List
                    title={t("strengths")}
                    items={iv.summary.data.strengths}
                  />
                  <List
                    title={t("practice_priorities")}
                    items={iv.summary.data.practice_priorities}
                  />
                  <List
                    title={t("next_steps")}
                    items={iv.summary.data.next_steps}
                  />
                  <Guides guides={iv.summary.guides} t={t} />
                </>
              ) : (
                <p>{t("no_answers")}</p>
              )}
              <button
                className="primary"
                disabled={disabled}
                onClick={() => action("restart")}
              >
                {t("restart")}
              </button>
            </article>
          ) : (
            q && (
              <article className="interview-sheet">
                <div className="kicker">
                  <Mic size={16} />
                  {t("question", { n: iv.question_number })}
                  <span> / </span>
                  {t(q.kind)}
                </div>
                <h2>{q.text}</h2>
                <details className="source">
                  <summary>
                    {t("question_sources")}
                    <ChevronDown size={14} />
                  </summary>
                  <div className="source-body">
                    <small>
                      {t("requirement")} · {req(p, q.requirement_id)?.source_id}
                    </small>
                    <p>{req(p, q.requirement_id)?.quote}</p>
                    {q.evidence.map((e, i) => (
                      <p className="quote" key={i}>
                        <small>{e.source_id}</small>
                        {e.quote}
                      </p>
                    ))}
                    <Citations p={p} items={q.evidence} t={t} />
                    <Guides guides={iv.guides} t={t} />
                  </div>
                </details>
                {!f ? (
                  <>
                    <div className="answer-box">
                      <Field
                        label={
                          t("answer") + " · " + t("attempt", { n: iv.attempt })
                        }
                      >
                        <textarea
                          maxLength={8000}
                          rows={6}
                          disabled={busy}
                          value={answer}
                          placeholder={t("answer_placeholder")}
                          onChange={(e) => setAnswer(e.target.value)}
                        />
                      </Field>
                    </div>
                    <button
                      disabled={disabled || !answer.trim()}
                      className="primary"
                      onClick={() => action("answer", { answer })}
                    >
                      {t("submit")}
                    </button>
                  </>
                ) : (
                  <>
                    <div className="quote">
                      <small>
                        {t("originalAnswer")} ·{" "}
                        {t("attempt", { n: iv.attempt })}
                      </small>
                      {latest?.answer}
                    </div>
                    <h2 className="subhead">{t("feedback")}</h2>
                    <List title={t("strengths")} items={f.strengths} />
                    {f.answer_quotes.length > 0 && (
                      <List
                        title={t("answer_sources")}
                        items={f.answer_quotes}
                      />
                    )}
                    <List title={t("missing")} items={f.missing_information} />
                    <div className="action-tip">
                      <h3>{t("action")}</h3>
                      <p>{f.action}</p>
                    </div>
                    {f.follow_up && (
                      <p className="quote">
                        <small>{t("follow_up")}</small>
                        {f.follow_up}
                      </p>
                    )}
                    <Guides guides={iv.feedbackGuides || []} t={t} />
                    {turns.length >= 30 ? (
                      <p>{t("question_limit")}</p>
                    ) : (
                      <div className="actions">
                        <button
                          className="primary"
                          disabled={disabled}
                          onClick={() => action("question")}
                        >
                          {t("next")}
                        </button>
                        {f.follow_up && (
                          <button
                            disabled={disabled}
                            onClick={() => action("follow")}
                          >
                            {t("answer_followup")}
                          </button>
                        )}
                        <button
                          disabled={disabled}
                          onClick={async () => {
                            if (await act("retry"))
                              setAnswer(latest?.answer || "");
                          }}
                        >
                          {t("retry")}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </article>
            )
          )}
          {turns.length > 0 && (
            <>
              <button
                className="export-interview"
                onClick={() =>
                  download(
                    "interview.txt",
                    turns
                      .map((v) =>
                        [
                          v.question.text,
                          v.answer,
                          ...v.feedback.strengths,
                          ...v.feedback.missing_information,
                          v.feedback.action,
                        ].join("\n"),
                      )
                      .concat(
                        iv.summary
                          ? [
                              ...iv.summary.data.strengths,
                              ...iv.summary.data.practice_priorities,
                              ...iv.summary.data.next_steps,
                            ].join("\n")
                          : [],
                      )
                      .join("\n\n"),
                  )
                }
              >
                {t("download_interview")}
              </button>
              <details className="source history">
                <summary>
                  {t("history", { n: turns.length })}
                  <ChevronDown size={14} />
                </summary>
                {turns.map((v, i) => (
                  <div className="source-body" key={i}>
                    <small>{t("attempt", { n: v.attempt })}</small>
                    <h3>{v.question.text}</h3>
                    <p>{v.answer}</p>
                    <List title={t("strengths")} items={v.feedback.strengths} />
                    <List
                      title={t("missing")}
                      items={v.feedback.missing_information}
                    />
                    <p>{v.feedback.action}</p>
                    <Guides
                      t={t}
                      guides={Object.values(iv.sourceArchive || {}).filter(
                        (g) =>
                          v.question.guide_ids.includes(g.id) ||
                          v.feedback.guide_ids.includes(g.id),
                      )}
                    />
                  </div>
                ))}
              </details>
            </>
          )}
        </>
      )}
    </>
  );
}
