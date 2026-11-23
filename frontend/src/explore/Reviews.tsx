import { useEffect, useState } from "react";
import { registerResumeGuard } from "../lib/resume-navigation";
import { get, post, del } from "../lib/api";
import { useApp } from "../lib/store";
import { confirmAction } from "../ProductDialog";
import { useCopy, useAction } from "./shared";

const fields = {
  question: ["面试官的问题", "Question"],
  answer: ["当时的回答", "Your answer"],
  reflection: ["想改进的地方", "Your reflection"],
  feedback: ["面试官反馈", "Interviewer feedback"],
} as const;
type Question = Record<keyof typeof fields, string>;
const blank = (): Question => ({
  question: "",
  answer: "",
  reflection: "",
  feedback: "",
});
interface Review {
  date: string;
  company: string;
  role: string;
  round: string;
  format: string;
  project: string;
  source: string;
  notes: string;
  questions: Question[];
}
const formats: Record<string, [string, string]> = {
  online: ["线上", "Online"],
  onsite: ["线下", "On site"],
  phone: ["电话", "Phone"],
  other: ["其他", "Other"],
};
interface Analysis {
  time: string;
  input: Review;
  result: {
    items: Record<string, string>[];
    strengths: string;
    priorities: string;
    practice: string;
    checklist: string;
  };
}
interface Entry {
  id: string;
  revision: number;
  updated: string;
  review: Review;
  history: Analysis[];
}
function sameReview(a: Review, b: Review) {
  return Object.keys(a).every((k) =>
    k === "questions"
      ? a.questions.length === b.questions.length &&
        a.questions.every((q, i) =>
          Object.keys(fields).every(
            (f) =>
              q[f as keyof Question] === b.questions[i][f as keyof Question],
          ),
        )
      : a[k as keyof Review] === b[k as keyof Review],
  );
}
function fresh(): Review {
  const local = new Date();
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return {
    date: local.toISOString().slice(0, 10),
    company: "",
    role: "",
    round: "",
    format: "online",
    source: "real",
    project: "",
    notes: "",
    questions: [blank()],
  };
}
export async function importMock(
  role: string,
  project: string,
  questions: Question[],
) {
  return post<Entry>("/api/explore/review/" + crypto.randomUUID(), {
    revision: 0,
    review: { ...fresh(), role, project, source: "mock", questions },
  });
}
export default function Reviews() {
  const { l } = useCopy(),
    { s, project, projects, setFeature } = useApp(),
    { busy, run, message } = useAction();
  const [entries, list] = useState<Entry[]>([]),
    [selected, select] = useState(""),
    [form, edit] = useState<Review | null>(null),
    [useResume, include] = useState(false),
    [notice, say] = useState("");
  const [filters, filter] = useState({
    company: "",
    role: "",
    round: "",
    date: "",
  });
  const current = entries.find((e) => e.id === selected);
  async function load() {
    list(await get<Entry[]>("/api/explore/review"));
  }
  useEffect(() => {
    void run(load);
  }, []);
  useEffect(() => {
    if (!form) return;
    const unload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", unload);
    const unregister = registerResumeGuard(() =>
      confirmAction(l("放弃未保存的修改？", "Discard unsaved changes?")),
    );
    return () => {
      unregister();
      window.removeEventListener("beforeunload", unload);
    };
  }, [!!form, s.lang]);
  function adopt(e: Entry) {
    list((rows) => [e, ...rows.filter((x) => x.id !== e.id)]);
    select(e.id);
    edit(null);
  }
  function replace(key: keyof Review, value: unknown) {
    say("");
    if (form) edit({ ...form, [key]: value });
  }
  const formLabels = {
    company: ["公司", "Company"],
    role: ["应聘岗位", "Role"],
    round: ["轮次", "Round"],
    date: ["面试日期", "Interview date"],
  } as const;
  const analyze = () =>
    run(async () => {
      if (!current) return;
      adopt(
        await post<Entry>(
          "/api/explore/review/" + current.id.slice(7) + "/analyze",
          {
            lang: s.lang,
            resume: useResume ? s.inputs.resumeText.slice(0, 12000) : "",
            revision: current.revision,
          },
        ),
      );
      say(l("分析已保存", "Analysis saved"));
    });
  return (
    <section className="explore">
      <h1>{l("面经复盘", "Interview Review")}</h1>
      <fieldset disabled={busy}>
        {form ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                adopt(
                  await post<Entry>(
                    "/api/explore/review/" +
                      (current ? current.id.slice(7) : crypto.randomUUID()),
                    { review: form, revision: current?.revision || 0 },
                  ),
                );
                say(l("草稿已保存", "Draft saved"));
              });
            }}
          >
            <article>
              <div className="xgrid">
                {(Object.keys(formLabels) as (keyof typeof formLabels)[]).map(
                  (k) => (
                    <label key={k}>
                      {l(formLabels[k][0], formLabels[k][1])}
                      <input
                        required={k === "date" || k === "role"}
                        type={k === "date" ? "date" : "text"}
                        maxLength={k === "round" ? 80 : 160}
                        value={form[k]}
                        onChange={(e) => replace(k, e.target.value)}
                      />
                    </label>
                  ),
                )}
                <label>
                  {l("面试形式", "Format")}
                  <select
                    value={form.format}
                    onChange={(e) => replace("format", e.target.value)}
                  >
                    {Object.entries(formats).map(([k, v]) => (
                      <option key={k} value={k}>
                        {l(...v)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {l("关联项目", "Linked project")}
                  <select
                    value={form.project}
                    onChange={(e) => replace("project", e.target.value)}
                  >
                    <option value="">—</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label>
                {l("备注", "Notes")}
                <textarea
                  maxLength={1800}
                  value={form.notes}
                  onChange={(e) => replace("notes", e.target.value)}
                />
              </label>
            </article>
            {form.questions.map((q, i) => (
              <article key={i}>
                <h2>
                  {l("问题", "Question")} {i + 1}
                </h2>
                {(Object.keys(fields) as (keyof Question)[]).map((k) => (
                  <label key={k}>
                    {l(fields[k][0], fields[k][1])}
                    <textarea
                      aria-label={l(fields[k][0], fields[k][1])}
                      required={k === "question"}
                      maxLength={
                        k === "question" ? 1200 : k === "answer" ? 1800 : 800
                      }
                      value={q[k]}
                      onChange={(e) =>
                        replace(
                          "questions",
                          form.questions.map((v, j) =>
                            j === i ? { ...v, [k]: e.target.value } : v,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
                {[-1, 1].map((d) => (
                  <button
                    key={d}
                    type="button"
                    disabled={!form.questions[i + d]}
                    onClick={() => {
                      const a = [...form.questions];
                      [a[i], a[i + d]] = [a[i + d], a[i]];
                      replace("questions", a);
                    }}
                  >
                    {d < 0 ? l("上移", "Move up") : l("下移", "Move down")}
                  </button>
                ))}
                <button
                  type="button"
                  disabled={form.questions.length < 2}
                  onClick={() =>
                    replace(
                      "questions",
                      form.questions.filter((_, j) => i !== j),
                    )
                  }
                >
                  {l("移除问题", "Remove question")}
                </button>
              </article>
            ))}
            <button
              type="button"
              disabled={form.questions.length >= 12}
              onClick={() => replace("questions", [...form.questions, blank()])}
            >
              {l("添加问题", "Add question")}
            </button>
            <button>{l("保存草稿", "Save draft")}</button>
            <button
              type="button"
              onClick={async () => {
                if (
                  await confirmAction(
                    l("放弃未保存的修改？", "Discard unsaved changes?"),
                  )
                )
                  edit(null);
              }}
            >
              {l("取消", "Cancel")}
            </button>
          </form>
        ) : current ? (
          <>
            <article>
              <button
                onClick={() => {
                  select("");
                  say("");
                }}
              >
                {l("返回列表", "Back to records")}
              </button>
              <h2>
                {current.review.company} · {current.review.role}
              </h2>
              <small>
                {current.review.date} · {current.review.round} ·{" "}
                {l(...formats[current.review.format])} ·{" "}
                {current.review.source === "mock"
                  ? l("模拟面试", "Mock interview")
                  : l("真实面试", "Real interview")}
              </small>
              <p>{current.review.notes}</p>
              {current.review.questions.map((q, i) => (
                <details key={i} open>
                  <summary>
                    {i + 1}. {q.question}
                  </summary>
                  <p>
                    {q.answer || l("未提供当时的回答", "No answer recorded")}
                  </p>
                  <p>{q.reflection}</p>
                  <p>{q.feedback}</p>
                </details>
              ))}
              <button onClick={() => edit(current.review)}>
                {l("编辑", "Edit")}
              </button>
              <button
                onClick={() =>
                  run(async () => {
                    if (
                      await confirmAction(
                        l(
                          "删除这份面经及复盘历史？",
                          "Delete this record and its analyses?",
                        ),
                      )
                    ) {
                      await del(
                        "/api/explore/review/" +
                          current.id +
                          "?revision=" +
                          current.revision,
                      );
                      select("");
                      await load();
                    }
                  })
                }
              >
                {l("删除", "Delete")}
              </button>
              {s.inputs.resumeText && (
                <label>
                  <input
                    type="checkbox"
                    checked={useResume}
                    onChange={(e) => include(e.target.checked)}
                  />
                  {l("参考当前项目简历", "Include current project resume")} ·{" "}
                  {project.name}
                </label>
              )}
              <button onClick={analyze}>
                {current.history.length
                  ? l("重新分析", "Analyze again")
                  : l("AI 复盘分析", "Analyze with AI")}
              </button>
            </article>
            {current.history.map((a, j) => (
              <article key={a.time}>
                <h2>
                  {l("复盘报告", "Review report")} ·{" "}
                  {new Date(a.time).toLocaleString()}
                </h2>
                {!sameReview(a.input, current.review) && (
                  <p role="status">
                    {l(
                      "面经已修改，这份报告对应旧版本。",
                      "Record edited. This report covers an earlier version.",
                    )}
                  </p>
                )}
                <details open={!j}>
                  <summary>{l("查看分析", "View analysis")}</summary>
                  {a.result.items.map((v, i) => (
                    <div key={i}>
                      <h3>{a.input.questions[i].question}</h3>
                      {[
                        ["intent", "考察点", "Interviewer intent"],
                        ["evaluation", "回答评价", "Answer feedback"],
                        ["improve", "改进建议", "Improvements"],
                        ["example", "参考回答", "Example answer"],
                      ].map(([k, z, e]) => (
                        <p key={k}>
                          <strong>{l(z, e)}</strong> ·{" "}
                          {v[k] || l("未提供当时的回答", "No answer recorded")}
                        </p>
                      ))}
                    </div>
                  ))}
                  {(
                    [
                      "strengths",
                      "priorities",
                      "practice",
                      "checklist",
                    ] as const
                  ).map((k, i) => (
                    <p key={k}>
                      <strong>
                        {l(
                          ["主要优点", "改进重点", "练习题型", "准备清单"][i],
                          ["Strengths", "Priorities", "Practice", "Checklist"][
                            i
                          ],
                        )}
                      </strong>{" "}
                      · {a.result[k]}
                    </p>
                  ))}
                </details>
              </article>
            ))}
            {project.id === current.review.project && (
              <button onClick={() => setFeature("interview")}>
                {l("继续模拟面试", "Continue mock interview")}
              </button>
            )}
          </>
        ) : (
          <>
            <button
              onClick={() => {
                edit(fresh());
                say("");
              }}
            >
              {l("＋ 新建面经", "＋ New interview record")}
            </button>
            <div className="xgrid">
              {(Object.keys(filters) as (keyof typeof filters)[]).map((k) => (
                <label key={k}>
                  {l(formLabels[k][0], formLabels[k][1])}
                  <input
                    type={k === "date" ? "date" : "search"}
                    value={filters[k]}
                    onChange={(e) =>
                      filter({ ...filters, [k]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
            {entries
              .filter((e) =>
                Object.entries(filters).every(([k, v]) =>
                  String(e.review[k as keyof Review])
                    .toLowerCase()
                    .includes(v.toLowerCase()),
                ),
              )
              .sort((a, b) => b.review.date.localeCompare(a.review.date))
              .map((e) => (
                <article key={e.id}>
                  <small>
                    {e.review.date} · {e.review.round} ·{" "}
                    {l(...formats[e.review.format])}
                  </small>
                  <h2>
                    {e.review.company} · {e.review.role}
                  </h2>
                  <p>
                    {e.review.questions.length} {l("道问题", "questions")} ·{" "}
                    {l("更新于", "Updated")}{" "}
                    {new Date(e.updated).toLocaleString()}
                  </p>
                  <button
                    onClick={() => {
                      select(e.id);
                      say("");
                    }}
                  >
                    {l("查看详情", "View details")}
                  </button>
                </article>
              ))}
            {!entries.length && !busy && (
              <p>
                {l(
                  "记录一次面试中的问题，之后可以回来补写回答。",
                  "Record a question from an interview and come back later to add your answer.",
                )}
              </p>
            )}
          </>
        )}
      </fieldset>
      <p role="status">
        {busy
          ? l("正在处理，请稍候…", "Working, please wait…")
          : message || notice}
      </p>
    </section>
  );
}
