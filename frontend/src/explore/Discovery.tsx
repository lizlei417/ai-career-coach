import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { get, post } from "../lib/api";
import { useApp } from "../lib/store";
import { confirmAction, ProductDialog } from "../ProductDialog";
import { categories, useAction, useCopy, type QuizResult } from "./shared";

interface Path {
  name: string;
  category: string;
  reason: string;
  evidence: string;
  transfer: string;
  gap: string;
}
interface Rec {
  id: string;
  inputs: Record<string, string>;
  paths: Path[];
}
interface Job {
  id: string;
  board: string;
  company: string;
  title: string;
  location: string;
  kind: string;
  url: string;
  apply: string;
  jd: string;
}
interface Listing {
  jobs: Job[];
  total: number;
  failed: string[];
  synced: string;
}
const base = "/api/positions";
export default function Discovery() {
  const {
      s,
      project,
      setDraft,
      setInputs,
      generateMatch,
      flushSave,
      setFeature,
    } = useApp(),
    { l } = useCopy(),
    { busy, message, run } = useAction();
  const [rec, setRec] = useState<Rec>(),
    [quiz, setQuiz] = useState<QuizResult>(),
    [combined, combine] = useState(true);
  const [path, choose] = useState(""),
    [region, place] = useState(s.drafts?.["career-region"] || ""),
    [keyword, search] = useState(""),
    [kind, stage] = useState(
      s.inputs.jobGoal === "internship"
        ? "intern"
        : s.inputs.userStage === "recent_graduate"
          ? "graduate"
          : "",
    );
  useEffect(() => {
    stage(
      s.inputs.jobGoal === "internship"
        ? "intern"
        : s.inputs.userStage === "recent_graduate"
          ? "graduate"
          : "",
    );
    paginate(1);
  }, [s.inputs.jobGoal, s.inputs.userStage]);
  const [page, paginate] = useState(1),
    [refresh, reload] = useState(0),
    [listing, show] = useState<Listing>(),
    [detail, open] = useState<Job>(),
    [failure, fail] = useState(""),
    [loading, load] = useState(true),
    [ready, init] = useState(false);
  const mounted = useRef(true),
    lastRefresh = useRef(0);
  useEffect(() => {
    mounted.current = true;
    void run(async () => {
      const [saved, qs] = await Promise.all([
        project.id
          ? get<Rec | undefined>("/api/explore/paths/" + project.id)
          : Promise.resolve(undefined),
        get<QuizResult[]>("/api/explore/assessment"),
      ]);
      if (!mounted.current) return;
      const focus = sessionStorage.getItem("v4-explore-focus"),
        q = qs.find((x) => x.id === focus) || qs[0];
      sessionStorage.removeItem("v4-explore-focus");
      setRec(saved);
      setQuiz(q);
      combine(focus ? true : saved ? !!saved.inputs.assessment : true);
      choose(
        (focus ? q?.paths[0] : saved?.paths[0]?.category || q?.paths[0]) || "",
      );
      init(true);
    });
    return () => {
      mounted.current = false;
    };
  }, [project.id]);
  useEffect(() => {
    let live = true;
    load(true);
    fail("");
    const query = new URLSearchParams({
      path,
      region,
      keyword,
      kind,
      page: String(page),
      refresh: String(refresh !== lastRefresh.current),
    });
    const timer = setTimeout(() => {
      lastRefresh.current = refresh;
      get<Listing>(base + "?" + query)
        .then((data) => {
          if (live) {
            show(data);
            load(false);
          }
        })
        .catch(() => {
          if (live) {
            show(undefined);
            load(false);
            fail("source");
          }
        });
    }, 200);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [path, region, keyword, kind, page, refresh]);
  const inputs = {
    resume: s.inputs.resumeText,
    target: s.inputs.jobTitle,
    stage: s.inputs.userStage || "",
    goal: s.inputs.jobGoal || "",
    lang: s.lang,
    assessment: combined && quiz ? quiz.id : "",
  };
  const stale =
    rec && Object.entries(inputs).some(([k, v]) => rec.inputs[k] !== v);
  function filter(fn: (v: string) => void, v: string) {
    fn(v);
    paginate(1);
  }
  const latestInputs = useRef(s.inputs);
  latestInputs.current = s.inputs;
  async function inspect(j: Job) {
    fail("");
    try {
      return await get<Job>(base + "/" + j.board + "/" + j.id);
    } catch (e) {
      fail(e instanceof Error && e.message === "CLOSED" ? "closed" : "source");
      return null;
    }
  }
  async function match(j: Job) {
    if (!project.id) {
      fail("project");
      return;
    }
    const live = await inspect(j);
    if (!live || !mounted.current) return;
    if (live.jd.trim().length < 100 || live.jd.length > 30000) {
      open(live);
      fail("jd");
      return;
    }
    if (
      latestInputs.current.jdText.trim() &&
      !(await confirmAction(
        l(
          "用这个职位替换当前 JD 并分析匹配？",
          "Replace the current JD and analyze this position?",
        ),
      ))
    )
      return;
    if (!mounted.current) return;
    flushSync(() =>
      setInputs({
        jobTitle: live.title,
        jdText: live.jd,
        jdFromUrl: true,
        jdSourceUrl: live.url,
        jdUrl: live.url,
      }),
    );
    open(undefined);
    if (latestInputs.current.resumeText.trim()) await generateMatch();
  }
  return (
    <section className="explore discovery">
      <article>
        <h2>{l("适合你的岗位方向", "Recommended Career Paths")}</h2>
        {quiz && (
          <label>
            <input
              type="checkbox"
              checked={combined}
              onChange={(e) => combine(e.target.checked)}
            />
            {l("结合职业测评", "Include career preferences")}
          </label>
        )}
        {stale && (
          <small>
            {l(
              "输入已变化，可重新分析。",
              "Inputs changed. Refresh your recommendations.",
            )}
          </small>
        )}
        {rec && (
          <div className="xgrid">
            {rec.paths.map((p) => (
              <details key={p.name}>
                <summary>{p.name}</summary>
                <p>{p.reason}</p>
                <blockquote>{p.evidence}</blockquote>
                <p>
                  {l("可迁移能力", "Transferable strengths")} · {p.transfer}
                </p>
                <p>
                  {l("待补充能力", "Skills to develop")} · {p.gap}
                </p>
                <button onClick={() => filter(choose, p.category)}>
                  {l("查看相关职位", "View related jobs")}
                </button>
              </details>
            ))}
          </div>
        )}
        {!s.inputs.resumeText.trim() && (
          <p>
            {l(
              "添加简历即可生成有原文依据的推荐，也可以先做职业测评。",
              "Add a resume for evidence-based paths, or explore your preferences first.",
            )}{" "}
            <button onClick={() => setFeature("explorer")}>
              {l("职业测评", "Career Explorer")}
            </button>
          </p>
        )}
        {quiz && combined && (
          <p>
            {l("测评方向", "Preference-based paths")} ·{" "}
            {quiz.paths.map((p) => (
              <button key={p} onClick={() => filter(choose, p)}>
                {l(...categories[p])}
              </button>
            ))}
          </p>
        )}
        <button
          disabled={busy || !ready || !s.inputs.resumeText.trim()}
          onClick={() =>
            run(async () => {
              await flushSave();
              const result = await post<Rec>(
                "/api/explore/paths/" + project.id,
                inputs,
              );
              if (mounted.current) {
                setRec(result);
                filter(choose, result.paths[0].category);
              }
            })
          }
        >
          {busy
            ? l("正在处理…", "Working…")
            : rec
              ? l("重新分析方向", "Refresh paths")
              : l("分析职业方向", "Analyze career paths")}
        </button>
        {message && <p role="alert">{message}</p>}
      </article>
      <article>
        <h2>{l("正在招聘的相关职位", "Open Positions for You")}</h2>
        <div className="filters">
          <select
            aria-label={l("岗位方向", "Career path")}
            value={path}
            onChange={(e) => filter(choose, e.target.value)}
          >
            <option value="">{l("全部方向", "All paths")}</option>
            {Object.entries(categories).map(([k, v]) => (
              <option key={k} value={k}>
                {l(...v)}
              </option>
            ))}
          </select>
          <select
            aria-label={l("地点", "Location")}
            value={region}
            onChange={(e) => {
              filter(place, e.target.value);
              if (project.id) setDraft("career-region", e.target.value);
            }}
          >
            {[
              ["", "全部地点", "All locations"],
              ["hk", "香港", "Hong Kong"],
              ["cn", "中国内地", "Mainland China"],
              ["other", "其他地区", "Other regions"],
            ].map(([v, z, e]) => (
              <option value={v} key={v}>
                {l(z, e)}
              </option>
            ))}
          </select>
          <select
            aria-label={l("岗位类型", "Job type")}
            value={kind}
            onChange={(e) => filter(stage, e.target.value)}
          >
            {[
              ["", "全部类型", "All types"],
              ["intern", "实习", "Internship"],
              ["graduate", "校招", "Graduate"],
              ["full", "全职", "Full-time"],
            ].map(([v, z, e]) => (
              <option key={v} value={v}>
                {l(z, e)}
              </option>
            ))}
          </select>
          <input
            aria-label={l("搜索职位", "Search jobs")}
            type="search"
            placeholder={l("搜索职位或公司", "Search title or company")}
            value={keyword}
            onChange={(e) => filter(search, e.target.value)}
          />
          <button onClick={() => reload((v) => v + 1)}>
            {l("刷新职位", "Refresh jobs")}
          </button>
        </div>
        {loading ? (
          <p role="status">{l("正在查询招聘来源…", "Checking job boards…")}</p>
        ) : (
          <>
            {failure && (
              <p role="alert">
                {failure === "project"
                  ? l(
                      "请先新建项目，以便保存职位和匹配结果。",
                      "Create a project first to save this position and its match report.",
                    )
                  : failure === "jd"
                    ? l(
                        "此 JD 长度不适合直接分析，请查看原文并粘贴相关部分。",
                        "Open the source and paste the relevant JD text.",
                      )
                    : failure === "closed"
                      ? l(
                          "该职位已关闭，请刷新职位。",
                          "This position has closed. Refresh the list.",
                        )
                      : l(
                          "招聘来源暂时不可用，请重试。",
                          "Job board unavailable. Try refreshing.",
                        )}
              </p>
            )}
            {!!listing?.failed.length && (
              <p>
                {l("部分招聘来源暂时不可用", "Some boards are unavailable")} ·{" "}
                {listing.failed.join(", ")}
              </p>
            )}
            {listing && (
              <>
                <small>
                  Lever · {l("同步于", "Synced")}{" "}
                  {new Date(listing.synced).toLocaleString()}
                </small>
                {!listing.total && (
                  <p>
                    {l(
                      "暂无符合条件的职位",
                      "No positions match these filters",
                    )}{" "}
                    <button
                      onClick={() => {
                        place("");
                        stage("");
                        choose("");
                        search("");
                        paginate(1);
                      }}
                    >
                      {l("清除筛选", "Clear filters")}
                    </button>{" "}
                    <a
                      href="https://hk.jobsdb.com/"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {l("搜索更多职位", "Search more jobs")}
                    </a>
                  </p>
                )}
                <div className="xgrid">
                  {listing.jobs.map((j) => (
                    <div key={j.id} className="job">
                      <small>{j.company}</small>
                      <h3>{j.title}</h3>
                      <p>{[j.location, j.kind].filter(Boolean).join(" · ")}</p>
                      <small>
                        {path
                          ? l("符合所选方向", "Matches selected path") +
                            " · " +
                            l(...categories[path])
                          : l(
                              "来自企业官方招聘板",
                              "Published on the company job board",
                            )}
                      </small>
                      <footer>
                        <button
                          disabled={busy}
                          onClick={() =>
                            run(async () => {
                              const v = await inspect(j);
                              if (v) open(v);
                            })
                          }
                        >
                          {l("查看岗位", "Details")}
                        </button>
                        <button
                          disabled={busy}
                          onClick={() => run(() => match(j))}
                        >
                          {l("分析匹配", "Analyze match")}
                        </button>
                        <a href={j.apply} target="_blank" rel="noreferrer">
                          {l("前往申请", "Apply")} ↗
                        </a>
                      </footer>
                    </div>
                  ))}
                </div>
                {listing.total > 3 && (
                  <div>
                    <button
                      disabled={page === 1}
                      onClick={() => paginate(page - 1)}
                    >
                      ←
                    </button>{" "}
                    {page} / {Math.ceil(listing.total / 3)}{" "}
                    <button
                      disabled={page * 3 >= listing.total}
                      onClick={() => paginate(page + 1)}
                    >
                      →
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </article>
      {detail && (
        <ProductDialog title={detail.title} onClose={() => open(undefined)}>
          <small>
            {detail.company} · {detail.location} · Lever
          </small>
          <p
            style={{
              whiteSpace: "pre-line",
              maxHeight: "55vh",
              overflow: "auto",
            }}
          >
            {detail.jd ||
              l(
                "请在招聘页面查看原文。",
                "Read the description on the official posting.",
              )}
          </p>
          <a href={detail.url} target="_blank" rel="noreferrer">
            {l("官方职位页面", "Official posting")} ↗
          </a>
        </ProductDialog>
      )}
    </section>
  );
}
