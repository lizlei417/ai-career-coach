import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ownerKey } from "../cloud";
import { flushSync } from "react-dom";
import { get, post } from "../lib/api";
import { useApp } from "../lib/store";
import { confirmAction, ProductDialog } from "../ProductDialog";
import { categories, useCopy, type QuizResult } from "./shared";

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
const pathTasks = new Map<string, Promise<Rec>>();
const pageSize = 3;
const searches = new Map<string, { time: number; data: Listing }>();
const historyReads = new Map<string, Promise<Rec | undefined>>();
const filterState = new Map<
  string,
  {
    path: string;
    keyword: string;
    page: number;
    kind: string;
    defaultKind: string;
  }
>();
function readHistory(key: string, project: string) {
  if (!historyReads.has(key)) {
    const read = get<Rec | undefined>("/api/explore/paths/" + project);
    historyReads.set(key, read);
    const forget = () => {
      if (historyReads.get(key) === read) historyReads.delete(key);
    };
    read.then(() => setTimeout(forget, 60000), forget);
  }
  return historyReads.get(key)!;
}
export default function Discovery() {
  const {
      s,
      project,
      setDraft,
      setInputs,
      generateMatch,
      flushSave,
      setFeature,
      busy,
    } = useApp(),
    { l, error } = useCopy();
  const taskKey = ownerKey("paths." + project.id);
  const defaultKind =
    s.inputs.jobGoal === "internship"
      ? "intern"
      : s.inputs.userStage === "recent_graduate"
        ? "graduate"
        : "";
  const [previous] = useState(() => filterState.get(taskKey));
  const [rec, setRec] = useState<Rec>(),
    [quiz, setQuiz] = useState<QuizResult>(),
    [combined, combine] = useState(s.drafts?.["career-assessment"] === "on");
  const [path, choose] = useState(previous?.path || ""),
    [region, place] = useState(s.drafts?.["career-region"] || ""),
    [keyword, search] = useState(previous?.keyword || ""),
    [kind, stage] = useState(
      previous?.defaultKind === defaultKind ? previous.kind : defaultKind,
    );
  const priorKind = useRef(defaultKind);
  useEffect(() => {
    if (defaultKind !== priorKind.current) {
      priorKind.current = defaultKind;
      stage(defaultKind);
      paginate(1);
    }
  }, [defaultKind]);
  const [page, paginate] = useState(
      previous?.defaultKind === defaultKind ? previous.page : 1,
    ),
    [refresh, reload] = useState(0),
    [listing, show] = useState<Listing>(),
    [detail, open] = useState<Job>(),
    [failure, fail] = useState(""),
    [loading, load] = useState(true),
    [ready, init] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [restoreError, setRestoreError] = useState(false);
  const [attempt, retry] = useState(0);
  const [matching, setMatching] = useState("");
  const mounted = useRef(false);
  const lastRefresh = useRef(0);
  useEffect(() => {
    filterState.set(taskKey, { path, keyword, page, kind, defaultKind });
  }, [taskKey, path, keyword, page, kind, defaultKind]);
  const pathTouched = useRef(false);
  const initialAssessment = useRef(s.drafts?.["career-assessment"]);
  const [focus] = useState(() => sessionStorage.getItem("v4-explore-focus"));
  const [requested] = useState(() =>
    sessionStorage.getItem("career-focus-path"),
  );
  useEffect(() => {
    let live = true;
    mounted.current = true;
    setRestoreError(false);
    const task = pathTasks.get(taskKey);
    setAnalyzing(!!task);
    const saved =
      task ||
      (project.id
        ? readHistory(taskKey, project.id)
        : Promise.resolve(undefined));
    saved
      .then((result) => {
        if (!live) return;
        setRec(result);
        if (initialAssessment.current === undefined)
          combine(!!result?.inputs.assessment);
        if (!focus && !previous && !pathTouched.current)
          choose(result?.paths[0]?.category || "");
      })
      .catch(() => {
        if (live) task ? setAnalysisError("failed") : setRestoreError(true);
      })
      .finally(() => {
        if (live) {
          init(true);
          setAnalyzing(false);
        }
      });
    return () => {
      live = false;
      mounted.current = false;
    };
  }, [taskKey, project.id, focus, attempt]);
  const [quizError, setQuizError] = useState(false);
  const [quizAttempt, retryQuiz] = useState(0);
  useEffect(() => {
    let live = true;
    setQuizError(false);
    get<QuizResult[]>("/api/explore/assessment")
      .then((qs) => {
        if (!live) return;
        const q = qs.find((x) => x.id === focus) || qs[0];
        setQuiz(q);
        if (focus && q) {
          choose(
            requested && q.paths.includes(requested) ? requested : q.paths[0],
          );
          sessionStorage.removeItem("career-focus-path");
          sessionStorage.removeItem("v4-explore-focus");
        }
      })
      .catch(() => {
        if (live) setQuizError(true);
      });
    return () => {
      live = false;
    };
  }, [focus, requested, quizAttempt]);
  useEffect(() => {
    let live = true;
    const query = new URLSearchParams({
      path,
      region,
      keyword,
      kind,
      all_results: "true",
    });
    const key = ownerKey(query.toString());
    const cached = searches.get(key);
    const force = refresh !== lastRefresh.current;
    if (!force && cached && Date.now() - cached.time < 60000) {
      show(cached.data);
      fail("");
      load(false);
      return;
    }
    load(true);
    fail("");
    query.set("refresh", String(force));
    const timer = setTimeout(() => {
      lastRefresh.current = refresh;
      get<Listing>(base + "?" + query)
        .then((data) => {
          if (live) {
            if (force) searches.clear();
            if (searches.size >= 4)
              searches.delete(searches.keys().next().value!);
            searches.set(key, { time: Date.now(), data });
            show(data);
            load(false);
          }
        })
        .catch(() => {
          if (live) {
            load(false);
            fail("source");
          }
        });
    }, 200);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [path, region, keyword, kind, refresh]);
  const pageCount = Math.max(
    1,
    Math.ceil((listing?.jobs.length || 0) / pageSize),
  );
  const currentPage = Math.min(page, pageCount);
  const offset = (currentPage - 1) * pageSize;
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
    if (fn === choose) pathTouched.current = true;
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
      if (mounted.current)
        fail(
          e instanceof Error && e.message === "CLOSED" ? "closed" : "source",
        );
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
  const disabledReason = !inputs.resume.trim()
    ? l("请先上传简历", "Please upload a resume")
    : !project.id
      ? l("请先创建项目", "Create a project first")
      : inputs.resume.length > 30000
        ? l("简历超过 30000 字", "Resume exceeds 30,000 characters")
        : "";
  async function analyze() {
    if (disabledReason || pathTasks.has(taskKey)) return;
    setAnalysisError("");
    setAnalyzing(true);
    const task = flushSave().then(() =>
      post<Rec>("/api/explore/paths/" + project.id, inputs),
    );
    pathTasks.set(taskKey, task);
    historyReads.delete(taskKey);
    try {
      const result = await task;
      if (mounted.current) {
        setRec(result);
        filter(choose, result.paths[0].category);
      }
    } catch (e) {
      if (mounted.current) setAnalysisError(error(e));
    } finally {
      pathTasks.delete(taskKey);
      if (mounted.current) setAnalyzing(false);
    }
  }
  return (
    <section className="explore discovery">
      <article>
        <h2>{l("适合你的岗位方向", "Recommended Career Paths")}</h2>
        <p className="muted">
          {l(
            "根据你的简历，分析适合发展的职业方向。",
            "Explore career paths based on your resume.",
          )}
        </p>
        {!inputs.resume.trim() && (
          <p>
            {l(
              "上传简历后，了解适合你的职业方向。",
              "Upload a resume to discover suitable career paths.",
            )}
          </p>
        )}
        {stale && (
          <small>
            {l(
              "资料已更新，可重新分析职业方向。",
              "Your inputs changed. You can refresh your recommendations.",
            )}
          </small>
        )}
        {rec && (
          <div className="xgrid recommended-paths">
            {rec.paths.map((p) => (
              <details key={p.name}>
                <summary>{p.name}</summary>
                <p>{p.reason}</p>
                <blockquote>{p.evidence}</blockquote>
                <p>
                  <strong>{l("可迁移能力", "Transferable strengths")}</strong> ·{" "}
                  {p.transfer}
                </p>
                <p>
                  <strong>{l("待补充能力", "Skills to develop")}</strong> ·{" "}
                  {p.gap}
                </p>
                <button
                  className="filter-chip"
                  aria-pressed={path === p.category}
                  onClick={() =>
                    filter(choose, path === p.category ? "" : p.category)
                  }
                >
                  {l("查看相关职位", "View related jobs")}
                </button>
              </details>
            ))}
          </div>
        )}
        <div className="path-actions">
          <button
            className={rec ? "secondary" : "primary"}
            disabled={!ready || analyzing || !!disabledReason || restoreError}
            onClick={analyze}
          >
            {analyzing ? (
              <>
                {l("正在分析", "Analyzing")}
                <span className="working-dots">…</span>
              </>
            ) : rec ? (
              l("重新分析", "Refresh paths")
            ) : (
              l("分析职业方向", "Analyze career paths")
            )}
          </button>
          <small role="status">
            {disabledReason ||
              (!ready && !analyzing
                ? l("正在读取历史结果…", "Loading saved results…")
                : "")}
          </small>
        </div>
        {restoreError && (
          <p role="alert">
            {l("历史结果读取失败", "Could not load saved recommendations")}{" "}
            <button
              onClick={() => {
                init(false);
                retry((n) => n + 1);
              }}
            >
              {l("重试", "Retry")}
            </button>
          </p>
        )}
        {analysisError && (
          <p role="alert">
            {l("分析失败，请重试", "Analysis failed. Please retry.")}{" "}
            {analysisError !== "failed" && analysisError}
          </p>
        )}
        <div className="quiz-option">
          <small>
            {l(
              "可选：结合职业测评结果，让推荐更贴近你的工作偏好。",
              "Optionally include your assessment to reflect your work preferences.",
            )}
          </small>
          {quiz ? (
            <label>
              <input
                type="checkbox"
                checked={combined}
                onChange={(e) => {
                  combine(e.target.checked);
                  setDraft(
                    "career-assessment",
                    e.target.checked ? "on" : "off",
                  );
                }}
              />
              {l("结合我的职业测评结果", "Include my career assessment")}
            </label>
          ) : quizError ? (
            <button
              className="text-link"
              onClick={() => retryQuiz((n) => n + 1)}
            >
              {l("重新读取测评", "Retry assessment lookup")}
            </button>
          ) : (
            <button
              className="text-link"
              onClick={() => setFeature("explorer")}
            >
              {l("前往职业测评", "Take the assessment")} →
            </button>
          )}
          {quiz && (combined || focus) && (
            <div>
              <small>{l("测评方向", "Preference-based paths")} </small>
              {quiz.paths
                .filter((p) => categories[p])
                .map((p) => (
                  <button
                    className="filter-chip"
                    key={p}
                    aria-pressed={p === path}
                    onClick={() => filter(choose, p === path ? "" : p)}
                  >
                    {l(...categories[p])}
                  </button>
                ))}
            </div>
          )}
        </div>
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
            maxLength={100}
            aria-label={l("搜索职位", "Search jobs")}
            type="search"
            placeholder={l("搜索职位或公司", "Search title or company")}
            value={keyword}
            onChange={(e) => filter(search, e.target.value)}
          />
          <button disabled={loading} aria-busy={loading} onClick={() => reload((v) => v + 1)}>
            <RefreshCw aria-hidden="true" size={14} className={"mr-1.5 inline-block align-[-2px] " + (loading ? "motion-safe:animate-spin" : "")} />
            {l("刷新职位", "Refresh jobs")}
          </button>
        </div>
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
                  <span className="muted">{l("暂无符合条件的职位", "No positions match these filters")}</span>{" "}
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
              {pageCount > 1 && (
                <nav
                  className="jobs-pagination"
                  aria-label={l("职位分页", "Job pages")}
                >
                  <button
                    aria-label={l("上一页", "Previous page")}
                    disabled={currentPage === 1}
                    onClick={() => paginate(currentPage - 1)}
                  >
                    ←
                  </button>
                  <span aria-live="polite">
                    {currentPage} / {pageCount}
                  </span>
                  <button
                    aria-label={l("下一页", "Next page")}
                    disabled={currentPage === pageCount}
                    onClick={() => paginate(currentPage + 1)}
                  >
                    →
                  </button>
                </nav>
              )}
              <div className="xgrid">
                {listing.jobs.slice(offset, offset + pageSize).map((j) => (
                  <div key={j.board + "/" + j.id} className="job">
                    <small>{j.company}</small>
                    <h3>{j.title}</h3>
                    <p>{[j.location, j.kind].filter(Boolean).join(" · ")}</p>
                    <small>
                      {!loading && !failure && path
                        ? l("符合所选方向", "Matches selected path") +
                          " · " +
                          l(...categories[path])
                        : l(
                            "来自企业官方招聘板",
                            "Published on the company job board",
                          )}
                    </small>
                    <footer>
                      {j.jd || !j.url ? (
                        <button
                          className="secondary"
                          disabled={!j.jd}
                          onClick={() => open(j)}
                        >
                          {l("查看岗位", "Details")}
                        </button>
                      ) : (
                        <a
                          className="secondary"
                          href={j.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {l("查看岗位", "Details")} ↗
                        </a>
                      )}
                      <button
                        className="match-action"
                        disabled={
                          !inputs.resume.trim() ||
                          !project.id ||
                          !!matching ||
                          busy.match ||
                          (j.jd !== undefined &&
                            (j.jd.trim().length < 100 || j.jd.length > 30000))
                        }
                        onClick={async () => {
                          setMatching(j.id);
                          try {
                            await match(j);
                          } finally {
                            if (mounted.current) setMatching("");
                          }
                        }}
                      >
                        {matching === j.id
                          ? l("正在匹配…", "Matching…")
                          : l("分析匹配", "Analyze match")}
                      </button>
                      {j.apply && (
                        <a
                          className="external"
                          href={j.apply}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {l("前往申请", "Apply")} ↗
                        </a>
                      )}
                    </footer>
                    {!inputs.resume.trim() && (
                      <small>
                        {l(
                          "上传或粘贴简历后可分析匹配",
                          "Add your resume to analyze this match",
                        )}
                      </small>
                    )}
                    {j.jd !== undefined &&
                      (j.jd.trim().length < 100 || j.jd.length > 30000) && (
                        <small>
                          {l(
                            "请从原文补充适合分析的 JD",
                            "Paste the relevant description from the source",
                          )}
                        </small>
                      )}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
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
