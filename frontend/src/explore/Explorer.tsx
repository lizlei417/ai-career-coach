import { useEffect, useRef, useState } from "react";
import { get, post, del } from "../lib/api";
import { useQuizDraft } from "./quizDraft";
import { confirmAction } from "../ProductDialog";
import { useApp } from "../lib/store";
import Report, { names, colors } from "./Report";
import { useCopy, useAction, type QuizResult } from "./shared";

const questions = [
  [
    "新项目启动时，我想先和搭档一起画出问题地图。",
    "At kickoff I want to map the problem with a teammate.",
  ],
  [
    "面对零散的交接材料，我喜欢先整理出一份步骤清单。",
    "I like turning messy handover notes into a checklist.",
  ],
  [
    "排下周的工作时，我会预先给重要任务留出固定时段。",
    "I reserve fixed time blocks for important tasks next week.",
  ],
  [
    "报告出现意外数字时，我喜欢找人当面讲一遍我的理解。",
    "When a report surprises me, I like talking someone through my interpretation.",
  ],
  [
    "一个难题摆在桌上，我愿意先关掉群聊独自推演。",
    "For a tricky problem I mute the chat and work it out alone first.",
  ],
  [
    "设计展位时，我想先试试几个大胆的概念。",
    "When designing a booth I want to try several bold concepts first.",
  ],
  [
    "临时出现一个有意思的小实验，我愿意调整原计划参与。",
    "I would rearrange my plan to join an interesting last-minute experiment.",
  ],
  [
    "比较两个方案时，我最享受安静核对数据的过程。",
    "When comparing proposals I enjoy quietly checking the numbers.",
  ],
  [
    "活动卡住时，我喜欢拉上不同分工的人一起拆解问题。",
    "When an event stalls I bring people from different teams together.",
  ],
  [
    "重复出现的客户请求让我想做一套可复用的处理流程。",
    "Repeated customer requests make me want to build a repeatable process.",
  ],
  [
    "临近交付时，我更喜欢提前排好里程碑再逐项推进。",
    "Near delivery I like setting milestones and working through them.",
  ],
  [
    "介绍新工具时，我愿意站到台前演示并回答问题。",
    "When introducing a tool I enjoy demonstrating it and taking questions.",
  ],
] as const;
export default function Explorer() {
  const { l } = useCopy(),
    { setFeature } = useApp(),
    { busy, message, run } = useAction();
  const [history, setHistory] = useState<QuizResult[]>([]),
    [selected, select] = useState<string | null>(null),
    [historyFailed, setHistoryFailed] = useState(false);
  const { draft, store } = useQuizDraft();
  const { answers } = draft;
  const answered = answers.filter((v) => v >= 1 && v <= 5).length;
  const historyVersion = useRef(0);
  async function load() {
    const version = ++historyVersion.current;
    try {
      const results = await get<QuizResult[]>("/api/explore/assessment");
      if (version !== historyVersion.current) return;
      setHistory(results);
      setHistoryFailed(false);
    } catch {
      if (version === historyVersion.current) setHistoryFailed(true);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const submitId = useRef(crypto.randomUUID());
  const defaultId =
    draft.loaded && !answers.length && !draft.pending
      ? history[0]?.id
      : undefined;
  const [manage, setManage] = useState(false);
  const current = history.find((x) => x.id === (selected ?? defaultId));
  return (
    <section className="explore">
      <h1>{l("职业测评", "Career Explorer")}</h1>
      {message && <p role="alert">{message}</p>}
      {(draft.failed || historyFailed) && (
        <p role="status">
          {draft.failed
            ? l(
                "草稿尚未同步，可以继续答题。",
                "Draft sync is pending. You can keep answering.",
              )
            : l(
                "测评历史暂未载入。",
                "Assessment history is unavailable.",
              )}{" "}
          <button
            onClick={() => {
              void store.sync();
              void load();
            }}
          >
            {l("重试", "Retry")}
          </button>
        </p>
      )}
      <fieldset disabled={busy}>
        {current ? (
          <Report
            result={current}
            retake={() => {
              store.edit({ reset: true, cursor: 0 });
              select("");
            }}
            open={(path) => {
              sessionStorage.setItem("v4-explore-focus", current.id);
              sessionStorage.setItem("career-focus-path", path);
              setFeature("match");
            }}
          />
        ) : (
          <>
            {questions.map((question, cursor) => (
              <article className="quiz-question" key={question[1]}>
                <small>{cursor + 1} / 12</small>
                <h2>{l(question[0], question[1])}</h2>
                <div className="choices">
                  {[
                    ["很不同意", "Strongly disagree"],
                    ["较不同意", "Disagree"],
                    ["视情况而定", "It depends"],
                    ["较同意", "Agree"],
                    ["很同意", "Strongly agree"],
                  ].map(([a, b], i) => (
                    <button
                      aria-pressed={answers[cursor] === i + 1}
                      key={b}
                      onClick={() => {
                        select("");
                        store.edit({
                          index: cursor,
                          value: i + 1,
                          cursor: Math.min(cursor + 1, 11),
                        });
                      }}
                    >
                      {l(a, b)}
                    </button>
                  ))}
                </div>
              </article>
            ))}
            <div className="quiz-footer">
              <span>{answered} / 12</span>
              <button
                className="quiz-submit"
                disabled={answered !== questions.length}
                onClick={() =>
                  run(async () => {
                    const r = await post<QuizResult>(
                      "/api/explore/assessment/" + submitId.current,
                      { answers },
                    );
                    store.edit({ reset: true, cursor: 0 });
                    submitId.current = crypto.randomUUID();
                    historyVersion.current++;
                    setHistoryFailed(false);
                    setHistory((rows) => [
                      r,
                      ...rows.filter((x) => x.id !== r.id),
                    ]);
                    select(r.id);
                  })
                }
              >
                {l("查看结果", "Finish and view report")}
              </button>
            </div>
          </>
        )}
        {history.length > 0 && (
          <details className="report-history">
            <summary>{l("测评历史", "Assessment history")}</summary>
            <button aria-pressed={manage} onClick={() => setManage(!manage)}>
              {l("管理", "Manage")}
            </button>
            {history.map((h) => (
              <div className="history-entry" key={h.id}>
                <button onClick={() => select(h.id)}>
                  {new Date(h.updated).toLocaleDateString(
                    document.documentElement.lang,
                  )}{" "}
                  ·{" "}
                  <strong style={{ color: colors[h.profile] }}>
                    {l(names[h.profile][0], names[h.profile][1])}
                  </strong>
                </button>
                {manage && (
                  <button
                    onClick={() =>
                      run(async () => {
                        if (
                          await confirmAction(
                            l("删除这份测评结果？", "Delete this assessment?"),
                          )
                        ) {
                          await del(
                            "/api/explore/assessment/" +
                              h.id +
                              "?revision=" +
                              h.revision,
                          );
                          select(null);
                          await load();
                        }
                      })
                    }
                  >
                    {l("删除", "Delete")}
                  </button>
                )}
              </div>
            ))}
          </details>
        )}
      </fieldset>
      {busy && <p role="status">{l("正在更新测评记录", "Updating assessment records")}<span className="working-dots" aria-hidden="true">...</span></p>}
    </section>
  );
}
