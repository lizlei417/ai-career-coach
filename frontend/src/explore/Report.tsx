import { useEffect, useRef } from "react";
import { useCopy, categories, type QuizResult } from "./shared";
import { useApp } from "../lib/store";
const poles = [
  ["独立钻研", "Independent focus", "协作推进", "Collaboration"],
  ["创意尝试", "Creative experimentation", "结构化执行", "Structured delivery"],
  ["探索变化", "Exploration", "稳定规划", "Planning"],
  ["深度分析", "Deep analysis", "沟通表达", "Communication"],
];
const preferenceColors = [
  ["#CF7B84", "#55A9CC"], // independent focus / collaboration
  ["#E0AF4B", "#85B45F"], // creative experimentation / structured delivery
  ["#A28BCA", "#D78F61"], // exploration / stable planning
  ["#718FC6", "#C184A8"], // deep analysis / communication
] as const;
export const names = [
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
export const colors = [
  "#864350",
  "#786016",
  "#694677",
  "#236859",
  "#98512c",
  "#575c27",
  "#8a384c",
  "#634f86",
  "#5e5850",
];
export default function Report({
  result: r,
  retake,
  open,
}: {
  result: QuizResult;
  retake: () => void;
  open: (path: string) => void;
}) {
  const hero = useRef<HTMLElement>(null);
  useEffect(() => {
    hero.current?.closest("main")?.scrollTo(0, 0);
    if (window.innerWidth <= 800)
      hero.current?.scrollIntoView({ block: "start" });
  }, [r.id]);
  const { l } = useCopy(),
    { s } = useApp();
  const tr = (z: string, t: string, e: string) =>
    s.lang === "en" ? e : s.lang === "zh-TW" ? t : z;
  const directions = r.scores.map((v, i) =>
    v === 50
      ? tr("两端均衡", "兩端均衡", "Balanced")
      : v < 50
        ? l(poles[i][0], poles[i][1])
        : l(poles[i][2], poles[i][3]),
  );
  const ranked = r.scores
    .map((v, i) => ({ distance: Math.abs(v - 50), i }))
    .sort((a, b) => b.distance - a.distance);
  const tags = ranked
    .slice(0, 3)
    .map(({ i }) =>
      r.scores[i] === 50
        ? l(poles[i][0], poles[i][1]) + " ↔ " + l(poles[i][2], poles[i][3])
        : directions[i],
    );
  const insight = l(insights[r.profile][0], insights[r.profile][1]);
  const collab = r.scores[0];
  const strengthExample = tr(
    `回想最近一次涉及「${tags[0]}」的任务，看看在哪个环节你最愿意主动投入。这个例子能帮你辨认值得继续探索的职责。`,
    `回想最近一次涉及「${tags[0]}」的任務，看看在哪個環節你最願意主動投入。這個例子能幫你辨認值得繼續探索的職責。`,
    `Think of a recent task involving ${tags[0]}. Which part drew your attention first? Look for similar responsibilities in a role description.`,
  );
  const environmentExample =
    r.scores[2] > 50
      ? tr(
          "开始前约定交付节点，把需要确认的问题放到节点讨论，给其余时间留出稳定的节奏。",
          "開始前約定交付節點，把需要確認的問題放到節點討論，給其餘時間留出穩定的節奏。",
          "Agree on milestones first. Reserve decisions for check-ins so the rest of the week stays predictable.",
        )
      : tr(
          "把工作拆成短周期，每轮结束比较两种做法的效果，再决定下一轮怎样安排。",
          "把工作拆成短週期，每輪結束比較兩種做法的效果，再決定下一輪怎樣安排。",
          "Use short work cycles. Compare two approaches at each check-in before choosing the next step.",
        );
  return (
    <div className="career-report">
      <article ref={hero} className="profile-hero">
        <button onClick={retake}>{l("重新测试", "Retake")}</button>
        <small>
          {tr("你的职业画像", "你的職業畫像", "Your career profile")}
        </small>
        <h2>{l(names[r.profile][0], names[r.profile][1])}</h2>
        <p>
          {ranked[0].distance === 0
            ? tr(
                "你在四组工作情境中的选择都很均衡，可能会根据任务调整做法。比较两次具体经历，更容易发现哪些条件让你投入。",
                "你在四組工作情境中的選擇都很均衡，可能會根據任務調整做法。比較兩次具體經歷，更容易發現哪些條件讓你投入。",
                "Your choices balance both ends of all four dimensions. Compare two recent tasks to see which conditions helped you engage.",
              )
            : tr(
                `遇到新的工作任务时，你的选择最明显地偏向「${tags[0]}」。在另一组情境中，你的表现是「${tags[1]}」，可以结合这两点探索合适的岗位。`,
                `遇到新的工作任務時，你的選擇最明顯地偏向「${tags[0]}」。在另一組情境中，你的表現是「${tags[1]}」，可以結合這兩點探索合適的職位。`,
                `Your strongest preference is ${tags[0]}. Another pattern in your answers is ${tags[1]}. Look for roles where you can try both in everyday work.`,
              )}
        </p>
        <div>
          {tags.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </article>
      <section>
        <h2>{tr("推荐职业", "推薦職業", "Recommended careers")}</h2>
        <div className="career-cards">
          {r.paths.map((p) => (
            <article key={p}>
              <h3>{l(...categories[p])}</h3>
              <p>{l(...fit[p])}</p>
              <button data-path={p} onClick={() => open(p)}>
                {l("查看相关职位", "View related jobs")} →
              </button>
            </article>
          ))}
        </div>
      </section>
      <section>
        <h2>{tr("工作偏好", "工作偏好", "Work preferences")}</h2>
        <p>
          {tr(
            "位置表示回答更接近哪一端，50 为均衡。",
            "位置表示回答更接近哪一端，50 為均衡。",
            "The marker shows which preference your answers lean toward. 50 is balanced.",
          )}
        </p>
        <div className="preference-grid">
          {poles.map(([a, b, c, d], i) => {
            // The two colour lengths and the marker must share the same measured position.
            const score = Math.max(0, Math.min(100, r.scores[i] ?? 50));
            const [leftColor, rightColor] = preferenceColors[i];
            return (
              <article key={a}>
                <div className="pole-labels">
                  <span>{l(a, b)}</span>
                  <span>{l(c, d)}</span>
                </div>
                <div
                  className="preference-track"
                  style={{ background: `linear-gradient(to right, ${leftColor} 0%, ${leftColor} ${score}%, ${rightColor} ${score}%, ${rightColor} 100%)` }}
                  aria-label={`${l(a, b)} / ${l(c, d)}: ${score} / 100`}
                  role="img"
                >
                  <i style={{ left: score + "%" }} />
                </div>
                <small>
                  {r.scores[i]} / 100 ·{" "}
                  {r.scores[i] !== 50 &&
                    (Math.abs(r.scores[i] - 50) < 10
                      ? tr("略偏向", "略偏向", "Leans slightly toward ")
                      : tr("偏向", "偏向", "Leans toward "))}
                  {directions[i]}
                </small>
              </article>
            );
          })}
        </div>
      </section>
      <section>
        <h2>
          {tr("优势与成长建议", "優勢與成長建議", "Strengths and development")}
        </h2>
        <div className="career-cards">
          {[
            [
              tr("核心优势", "核心優勢", "Potential strength"),
              insight.split(/[。.]/)[0] + (s.lang === "en" ? "." : "。"),
              strengthExample,
            ],
            [
              tr("适合的工作方式", "適合的工作方式", "Working environment"),
              collab === 50
                ? tr(
                    "在独立思考和团队讨论之间留出切换空间。",
                    "在獨立思考和團隊討論之間留出切換空間。",
                    "Alternate focused work with team discussion.",
                  )
                : collab < 50
                  ? tr(
                      "先留一段独立工作时间，再和搭档核对想法。",
                      "先留一段獨立工作時間，再和搭檔核對想法。",
                      "Reserve individual focus time before a peer review.",
                    )
                  : tr(
                      "从小组讨论开始，让分工和下一步行动清晰可见。",
                      "從小組討論開始，讓分工和下一步行動清晰可見。",
                      "Start with a group discussion and agree on responsibilities.",
                    ),
              environmentExample,
            ],
            [
              tr("成长建议", "成長建議", "Growth suggestion"),
              insight.replace(/^[^。.]*[。.]\s*/, ""),
              l(...advice[r.paths[0]]),
            ],
          ].map(([title, copy, detail]) => (
            <article key={title}>
              <h3>{title}</h3>
              <p>
                {copy} {detail}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
