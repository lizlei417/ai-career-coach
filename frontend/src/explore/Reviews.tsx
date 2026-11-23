import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ownerKey } from "../cloud";
import { registerResumeGuard } from "../lib/resume-navigation";
import { get, post, del } from "../lib/api";
import { useApp } from "../lib/store";
import { confirmAction } from "../ProductDialog";
import { useCopy, useAction } from "./shared";

import { InterviewQuestions, InterviewAnalysis } from "./InterviewReport";
import ReviewDate from "./ReviewDate";

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
export interface Review {
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
export interface Analysis {
  time: string;
  input: Review;
  result:
    | string
    | {
        items: (Record<string, string> & { grounded?: boolean })[];
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
// The account library is shared by all projects. Keep one snapshot per signed-in
// owner and reconcile writes that finish while a list request is in flight.
function reviewLibrary() {
  const key = ownerKey("review-library-v1");
  if (library?.key === key) return library;
  let rows: Entry[] | undefined;
  try {
    const stored = JSON.parse(sessionStorage.getItem(key) || "null");
    if (Array.isArray(stored)) rows = stored;
  } catch { /* Storage is optional. */ }
  let synced = 0;
  let pending: Promise<void> | undefined;
  const changes = new Map<string, Entry | null>();
  const listeners = new Set<() => void>();
  function publish(next: Entry[]) {
    if (library?.key !== key || ownerKey("review-library-v1") !== key) return;
    rows = next;
    try { sessionStorage.setItem(key, JSON.stringify(next)); }
    catch { try { sessionStorage.removeItem(key); } catch { /* Memory-only cache. */ } }
    listeners.forEach(listener => listener());
  }
  function update(id: string, entry: Entry | null) {
    if (pending) changes.set(id, entry);
    const other = (rows || []).filter(item => item.id !== id);
    publish(entry ? [entry, ...other] : other);
  }
  library = {
    key,
    snapshot: () => rows,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    update,
    read() {
      if (pending) return pending;
      if (Date.now() - synced < 30000) return Promise.resolve();
      pending = get<Entry[]>("/api/explore/review").then(fetched => {
        const merged = new Map(fetched.map(row => [row.id, row]));
        changes.forEach((entry, id) => { if (entry) merged.set(id, entry); else merged.delete(id); });
        publish(Array.from(merged.values()));
        synced = Date.now();
      }).finally(() => { changes.clear(); pending = undefined; });
      return pending;
    },
  };
  return library;
}
let library: {
  key: string;
  snapshot: () => Entry[] | undefined;
  subscribe: (listener: () => void) => () => void;
  update: (id: string, entry: Entry | null) => void;
  read: () => Promise<void>;
} | undefined;
export function clearReviewLibrary() {
  library = undefined;
  sessionStorage.removeItem(ownerKey("review-library-v1"));
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
  const cache = reviewLibrary();
  const entry = await post<Entry>("/api/explore/review/" + crypto.randomUUID(), {
    revision: 0,
    review: { ...fresh(), role, project, source: "mock", questions },
  });
  cache.update(entry.id, entry);
  return entry;
}
export default function Reviews() {
  const { l, error } = useCopy(),
    { s, project, setFeature } = useApp(),
    { busy, run, message } = useAction();
  const draftId = useRef("");
  const [action, setAction] = useState<"load" | "save" | "analyze" | "delete">(
    "load",
  );
  const cache = reviewLibrary();
  const snapshot = useSyncExternalStore(cache.subscribe, cache.snapshot);
  const entries = snapshot || [];
  const [selected, select] = useState(""),
    [form, edit] = useState<Review | null>(null),
    [notice, say] = useState("");
  const [filters, filter] = useState({
    company: "",
    role: "",
    round: "",
    date: "",
  });
  const [appliedFilters, applyFilters] = useState(filters);
  const visibleEntries = entries.filter(e => Object.entries(appliedFilters).every(([key, value]) =>
    String(e.review[key as keyof Review]).toLowerCase().includes(value.trim().toLowerCase())
  )).sort((a, b) => b.review.date.localeCompare(a.review.date));
  const current = entries.find((e) => e.id === selected);
  const loading = snapshot === undefined;
  const [loadError, setLoadError] = useState("");
  const [attempt, retry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoadError("");
    cache.read().catch(e => { if (active) setLoadError(error(e)); });
    return () => {
      active = false;
    };
  }, [cache, attempt]);
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
    cache.update(e.id, e);
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
      setAction("analyze");
      adopt(
        await post<Entry>(
          "/api/explore/review/" + current.id.slice(7) + "/analyze",
          {
            lang: s.lang,
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
              setAction("save");
              void run(async () => {
                adopt(
                  await post<Entry>(
                    "/api/explore/review/" +
                      (current ? current.id.slice(7) : draftId.current),
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
                  (k) =>
                    k === "date" ? (
                      <div key={k}>
                        {l(...formLabels.date)}
                        <ReviewDate
                          value={form.date}
                          change={(v) => replace("date", v)}
                        />
                      </div>
                    ) : (
                      <label key={k}>
                        {l(formLabels[k][0], formLabels[k][1])}
                        <input
                          required={k === "role"}
                          type="text"
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
              <small className="review-state">
                {current.review.questions.length} {l("道问题", "questions")} ·{" "}
                {busy && action === "analyze"
                  ? l("AI 正在分析中", "Analyzing")
                  : current.history.length
                    ? l("已分析", "Analyzed")
                    : l("待分析", "Awaiting analysis")}
              </small>
              <button onClick={() => edit(current.review)}>
                {l("编辑", "Edit")}
              </button>
              <button
                className="review-delete"
                onClick={() =>
                  run(async () => {
                    setAction("delete");
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
                      cache.update(current.id, null);
                    }
                  })
                }
              >
                {l("删除", "Delete")}
              </button>
              <button className="review-analyze" onClick={analyze}>
                {current.history.length
                  ? l("重新分析", "Analyze again")
                  : l("AI 复盘分析", "Analyze with AI")}
              </button>
            </article>
            {(!current.history[0]?.input ||
              !sameReview(current.history[0].input, current.review) ||
              typeof current.history[0].result === "string") && (
              <InterviewQuestions review={current.review} />
            )}
            {current.history.map((a, j) => (
              <details className="interview-report" open={j === 0} key={a.time}>
                <summary>
                  {l("复盘报告", "Review report")} ·{" "}
                  {new Date(a.time).toLocaleString(s.lang)}
                </summary>
                {a.input && !sameReview(a.input, current.review) && (
                  <p role="status">
                    {l(
                      "面经已修改，这份报告对应旧版本。",
                      "Record edited. This report covers an earlier version.",
                    )}
                  </p>
                )}
                <InterviewAnalysis report={a} />
              </details>
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
                draftId.current = crypto.randomUUID();
                edit(fresh());
                say("");
              }}
            >
              {l("＋ 新建面经", "＋ New interview record")}
            </button>
            <div className="review-filters">
              {(Object.keys(filters) as (keyof typeof filters)[]).map((k) =>
                k === "date" ? (
                  <div key={k}>
                    {l(...formLabels.date)}
                    <ReviewDate
                      clearable
                      value={filters.date}
                      change={(v) => filter({ ...filters, date: v })}
                    />
                  </div>
                ) : (
                  <label key={k}>
                    {l(formLabels[k][0], formLabels[k][1])}
                    <input
                      type="search"
                      value={filters[k]}
                      onChange={(e) =>
                        filter({ ...filters, [k]: e.target.value })
                      }
                    />
                  </label>
                ),
              )}
              <button type="button" className="review-query" onClick={() => applyFilters(filters)}>{l("查询", "Search")}</button>
            </div>
            {visibleEntries.map((e) => (
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
            {!!entries.length && !visibleEntries.length && <p role="status">{l("没有符合条件的面经","No matching records")}</p>}
            {loading && !loadError && (
              <p role="status">{l("正在读取面经", "Loading interviews")}…</p>
            )}
            {loadError && (
              <p role="alert">
                {loadError}{" "}
                <button onClick={() => retry((n) => n + 1)}>
                  {l("重试", "Retry")}
                </button>
              </p>
            )}
            {!entries.length && !loading && !loadError && !busy && (
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
        {busy ? (
          <>
            {action === "analyze"
              ? l("AI 正在分析中", "AI is analyzing your interview")
              : action === "save"
                ? l("正在保存草稿", "Saving draft")
                : action === "delete"
                  ? l("正在删除", "Deleting")
                  : l("正在读取面经", "Loading interviews")}
            <span className="working-dots" aria-hidden="true">
              ...
            </span>
          </>
        ) : (
          message || notice
        )}
      </p>
    </section>
  );
}
