import { useEffect, useRef, useState } from "react";
import { get, post, del } from "../lib/api";
import { useQuizDraft } from "./quizDraft";
import { confirmAction } from "../ProductDialog";
import { useApp } from "../lib/store";
import { categories, useCopy, useAction, type QuizResult } from "./shared";

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
const poles = [
  ["独立钻研", "Independent focus", "协作推进", "Collaboration"],
  ["创意尝试", "Creative experimentation", "结构化执行", "Structured delivery"],
  ["探索变化", "Exploration", "稳定规划", "Planning"],
  ["深度分析", "Deep analysis", "沟通表达", "Communication"],
];
const names = [
  ["静思解题者", "Independent investigator"],
  ["团队联络人", "Team connector"],
  ["点子实验员", "Idea experimenter"],
  ["流程设计师", "Process designer"],
  ["机会探路者", "Opportunity scout"],
  ["节奏规划师", "Milestone planner"],
  ["证据侦探", "Evidence detective"],
  ["故事讲解员", "Story translator"],
  ["情境观察者", "Context observer"],
];
const insights = [
  [
    "你倾向先独立梳理线索。给自己留出思考时间，再邀请搭档挑战你的假设。",
    "You tend to sort out clues independently. Give yourself thinking time, then ask a partner to challenge your assumptions.",
  ],
  [
    "讨论能帮你理清分工。试着在一次小组会议后写下每个人负责的下一步。",
    "Discussion helps you organize responsibilities. After a meeting, write down one next step for each teammate.",
  ],
  [
    "你喜欢先产生多个可能的答案。选一个想法做低成本原型，看看谁真正需要它。",
    "You enjoy generating alternatives. Prototype one idea and see who actually needs it.",
  ],
  [
    "你习惯把散乱信息整理成步骤。选一个反复出错的交接环节，把它画成流程图。",
    "You turn scattered information into steps. Map a handoff that often goes wrong.",
  ],
  [
    "变化容易引起你的兴趣。给下一次小实验定一个截止时间，看看新方法是否值得保留。",
    "Change sparks your curiosity. Give your next experiment a deadline and decide what to keep.",
  ],
  [
    "清楚的节奏让你更容易投入。试着为下一个里程碑保留缓冲，并预想一个备选方案。",
    "A clear rhythm helps you engage. Add a buffer and a backup plan to the next milestone.",
  ],
  [
    "你喜欢追问证据从哪里来。找一个与你直觉相反的例子，写下它会怎样改变你的判断。",
    "You enjoy tracing evidence. Find a counterexample and describe how it would change your conclusion.",
  ],
  [
    "你偏好把想法讲出来。用两分钟向陌生听众解释一个复杂问题，再请对方复述重点。",
    "You prefer thinking aloud. Explain a complex problem in two minutes and ask someone to summarize it.",
  ],
  [
    "你的回答随情境变化。挑两个相反的工作方式各试一次，记录哪种条件下更投入。",
    "Your preferences vary with the situation. Try opposite approaches and note the conditions that help you engage.",
  ],
];
const fit: Record<string, [string, string]> = {
  product: [
    "适合在用户需求和团队协作之间切换。",
    "Explore this if you enjoy balancing user needs and teamwork.",
  ],
  operations: [
    "适合喜欢协调资源、帮助团队落地计划的人。",
    "Explore this if you enjoy coordinating people and delivering plans.",
  ],
  analytics: [
    "适合喜欢独立核对线索、追问原因的人。",
    "Explore this if you enjoy checking evidence and investigating causes.",
  ],
  design: [
    "适合喜欢把新点子做成可见原型的人。",
    "Explore this if you enjoy making ideas tangible.",
  ],
  engineering: [
    "适合喜欢分解问题、设计可复用方法的人。",
    "Explore this if you enjoy breaking down problems and building reusable solutions.",
  ],
  marketing: [
    "适合喜欢尝试不同方案、观察市场反应的人。",
    "Explore this if you enjoy experiments and observing audience reactions.",
  ],
  finance: [
    "适合喜欢预估风险、用计划减少意外的人。",
    "Explore this if you enjoy assessing risks and planning for uncertainty.",
  ],
  people: [
    "适合喜欢用对话理解他人需求的人。",
    "Explore this if conversations help you understand what others need.",
  ],
};
const advice: Record<string, [string, string]> = {
  product: [
    "把一个用户痛点写成需求草图，再问两个人是否遇到过。挑战是从多个合理需求中做取舍。",
    "Sketch a user problem and interview two people. Practise making trade-offs between competing needs.",
  ],
  operations: [
    "把一次活动拆成任务、负责人和时间表。挑战是协调进度变化。",
    "Plan an event with owners and dates. Practise adjusting dependencies when plans change.",
  ],
  analytics: [
    "挑一组公开数据，写下一条可检验的假设。挑战是解释数据的局限。",
    "Test a hypothesis with public data and explain the limits of your evidence.",
  ],
  design: [
    "为同一问题画两个原型并收集反馈。挑战是接受与直觉不同的意见。",
    "Prototype two solutions and invite feedback that challenges your intuition.",
  ],
  engineering: [
    "把重复任务拆成步骤并实现一个小工具。挑战是排查边界情况。",
    "Build a tool for a repeated task and investigate edge cases.",
  ],
  marketing: [
    "为同一活动写两个版本的邀请，比较反馈。挑战是区分偶然反应和趋势。",
    "Try two campaign messages and separate noisy responses from a trend.",
  ],
  finance: [
    "给一个预算方案列出风险与控制条件。挑战是应对不完整的信息。",
    "List risks and controls for a budget while working with incomplete information.",
  ],
  people: [
    "设计一组访谈问题并试着追问实例。挑战是减少自己的判断偏差。",
    "Design an interview guide and follow up on examples while checking your assumptions.",
  ],
};
export default function Explorer() {
  const { l } = useCopy(),
    { setFeature } = useApp(),
    { busy, message, run } = useAction();
  const [history, setHistory] = useState<QuizResult[]>([]),
    [selected, select] = useState<string | null>(null),
    [historyFailed, setHistoryFailed] = useState(false);
  const { draft, store } = useQuizDraft();
  const { answers, cursor } = draft;
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
          <article>
            <h2>{l(names[current.profile][0], names[current.profile][1])}</h2>
            {poles.map(([a, b, c, d], i) => (
              <label key={a}>
                {l(a, b)} ↔ {l(c, d)} · {current.scores[i]}%
                <progress value={current.scores[i]} max={100} />
              </label>
            ))}
            <p>
              {l(insights[current.profile][0], insights[current.profile][1])}{" "}
              {l(
                "这些偏好来自你在十二个情境中的选择。先回想一次做起来很投入的任务，把最享受的环节写下来，再比较下面的岗位练习。选一项用半天做一个小作品，请同学或同事观察你在哪一步最主动、哪一步最费力。下一次看职位描述时，标出对应的日常任务，问清它们各占多少时间。把这次结果当作可以检验的工作假设；实际体验和你的履历可以帮助你修正方向。",
                "Recall a task that held your attention and identify the part you most enjoyed. Pick one experiment below, spend half a day on it, and ask a colleague which steps energized you. Compare those steps with daily duties in a vacancy. Treat these preferences as hypotheses to test against experience.",
              )}
            </p>
            {current.paths.map((p) => (
              <p key={p}>
                <strong>{l(...categories[p])}</strong> · {l(...fit[p])}{" "}
                {l(...advice[p])}
              </p>
            ))}
            <button
              onClick={() => {
                sessionStorage.setItem("v4-explore-focus", current.id);
                setFeature("match");
              }}
            >
              {l("查看适合我的岗位", "View suitable positions")}
            </button>
            <button
              onClick={() => {
                store.edit({ reset: true, cursor: 0 });
                select("");
              }}
            >
              {l("重新测试", "Retake")}
            </button>
          </article>
        ) : (
          <article>
            <small>{cursor + 1} / 12</small>
            <h2>{l(questions[cursor][0], questions[cursor][1])}</h2>
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
            {cursor > 0 && (
              <button onClick={() => store.edit({ cursor: cursor - 1 })}>
                {l("上一题", "Previous")}
              </button>
            )}
            {answers.length === 12 && (
              <button
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
            )}
          </article>
        )}
        {history.length > 0 && (
          <article>
            <h2>{l("测评历史", "Assessment history")}</h2>
            {history.map((h) => (
              <div key={h.id}>
                <button onClick={() => select(h.id)}>
                  {new Date(h.updated).toLocaleString()} ·{" "}
                  {l(names[h.profile][0], names[h.profile][1])}
                </button>
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
              </div>
            ))}
          </article>
        )}
      </fieldset>
      {busy && <p role="status">{l("正在处理…", "Working…")}</p>}
    </section>
  );
}
