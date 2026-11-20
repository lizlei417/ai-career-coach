import {sample} from "./pages-demo";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  LayoutPanelLeft,
  Menu,
  PanelLeftOpen,
  RefreshCw,
  Settings,
  X,
} from "lucide-react";
import { api, ApiError } from "./api";
import { index, langs, ui } from "./i18n";
import { emptyMaterials } from "./types";
import type {
  Act,
  Lang,
  Materials,
  Project,
  Status,
  Strings,
  Trans,
  View,
} from "./types";
import {
  Brand,
  Landing,
  Language,
  ProgressNote,
  SiteFooter,
  toolList,
} from "./ui";
import { MaterialsPanel, readable, type DocumentKey } from "./MaterialsPanel";
import EmptyTool from "./EmptyTool";
import { Matching, Optimization } from "./Results";
import Interview from "./Interview";
import "./style.css";
import "./workbench.css";

type Bootstrap = { strings: Strings; status: Status };
const normalize = (s: string) =>
  s.replace(/\r\n/g, "\n").replace(/\0/g, "").trim();
function sameSources(a: Materials, b: Materials) {
  return (
    normalize(a.resume) === normalize(b.resume) &&
    normalize(a.jd) === normalize(b.jd)
  );
}
function App() {
  const [lang, setLang] = useState<Lang>(() => {
    const v = localStorage.getItem("career-language");
    return v && v in langs ? (v as Lang) : (import.meta.env.VITE_PAGES_DEMO === "1" ? "zh-CN" : "en");
  });
  const [strings, setStrings] = useState<Strings>(ui),
    [status, setStatus] = useState<Status | null>(null);
  const [entered, enter] = useState(false),
    [view, setView] = useState<View>("optimize");
  const [draft, setDraft] = useState<Materials>(emptyMaterials),
    [project, setProject] = useState<Project | null>(null);
  const [collapsed, collapse] = useState(false),
    [menu, setMenu] = useState(false),
    [settings, showSettings] = useState(false);
  const [working, setWorking] = useState(""),
    [err, setErr] = useState<unknown>(null),
    [revisionRun, setRevisionRun] = useState(0);
  const resultArea = useRef<HTMLElement>(null),
    settingToggle = useRef<HTMLButtonElement>(null);
  const [sessionEpoch, resetEditor] = useState(0);
  const busy = !!working;
  const t: Trans = (key, values = {}) =>
    (strings[key]?.[index[lang]] || key).replace(/\{(\w+)\}/g, (_, k) =>
      String(values[k] ?? ""),
    );
  const dirty = !!project && !sameSources(draft, project.materials);
  const demo = import.meta.env.VITE_PAGES_DEMO === "1";
  const ready = readable(draft.resume) && readable(draft.jd);
  const s = project?.status || status;
  const hasResult = {
    optimize: !!project?.optimization,
    match: !!project?.matching,
    interview: !!(project?.interview.question || project?.interview.ended),
  };
  const visibleResult = hasResult[view] && !dirty;
  const actionLabel = t(
    view === "interview"
      ? visibleResult
        ? "viewInterview"
        : "start"
      : visibleResult
        ? "reanalyze"
        : view === "match"
          ? "startMatch"
          : "startOpt",
  );
  const setLanguage = (v: Lang) => {
    setLang(v);
    localStorage.setItem("career-language", v);
  };
  function goWorkspace() {
    enter(true);
    sessionStorage.setItem("career-workspace", "1");
    window.scrollTo(0, 0);
  }
  function goHome() {
    enter(false);
    setMenu(false);
    showSettings(false);
    sessionStorage.setItem("career-workspace", "home");
    window.scrollTo(0, 0);
  }
  function restore(p: Project) {
    setProject(p);
    setDraft(p.materials);
  }
  async function load() {
    try {
      setErr(null);
      const boot = await api<Bootstrap>("bootstrap");
      setStrings({ ...boot.strings, ...ui, ...(demo ? {
        privacyShort: ["Scripted demo · materials stay in this tab.", "预设演示 · 材料仅保存在当前标签页。", "預設演示 · 材料僅保存在目前分頁。"],
        sessionPrivacy: ["Submitted sample materials and results stay in this browser tab.", "已提交的示例材料与结果仅保存在当前浏览器标签页。", "已提交的範例材料與結果僅保存在目前瀏覽器分頁。"],
      } : {}) });
      if (sessionStorage.getItem("career-project")) {
        try {
          restore(await api<Project>("project"));
        } catch (e) {
          if (e instanceof ApiError && e.status === 410)
            sessionStorage.removeItem("career-project");
          else throw e;
        }
      }
      const location = sessionStorage.getItem("career-workspace");
      enter(
        location === "1" ||
          (!location && !!sessionStorage.getItem("career-project")),
      );
      setStatus(boot.status);
    } catch (e) {
      setErr(e);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    function close(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenu(false);
        showSettings(false);
        if (settings) settingToggle.current?.focus();
      }
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [settings]);
  function focusSource(k: DocumentKey) {
    collapse(false);
    setMenu(false);
    requestAnimationFrame(() => document.getElementById("work-" + k)?.focus());
  }
  function select(v: View, fromRail = false) {
    setView(v);
    setMenu(false);
    if (fromRail)
      requestAnimationFrame(() =>
        resultArea.current?.scrollIntoView({ block: "start" }),
      );
  }
  function change(part: Partial<Materials>) {
    setErr(null);
    setDraft((m) => ({ ...m, ...part }));
  }
  async function ensureMaterials() {
    if (
      project &&
      !dirty &&
      draft.filename === project.materials.filename &&
      draft.link === project.materials.link
    )
      return project;
    // Keep the existing Python service contract. Only explicitly labelled titles
    // are extracted. The neutral JD label is internal and never becomes evidence.
    const title =
      draft.jd
        .match(
          /^(?:role|job title|position|岗位名称|职位名称|職位名稱)\s*[:：]\s*(.+)$/im,
        )?.[1]
        .trim()
        .slice(0, 120) || "JD";
    const m = {
      ...draft,
      role: title,
      name: project?.materials.name || title,
      language: lang,
    };
    let p: Project;
    if (project) {
      p = await api<Project>("project?version=" + project.version, "PUT", m);
    } else {
      const created = await api<{ project: Project; token: string }>(
        "project",
        "POST",
        m,
      );
      sessionStorage.setItem("career-project", created.token);
      p = created.project;
    }
    restore(p);
    return p;
  }
  async function reconcile(e: unknown) {
    if (e instanceof ApiError && e.status === 410) {
      sessionStorage.removeItem("career-project");
      setProject(null);
      setErr("expiredRetry");
      return;
    }
    setErr(e);
    if (sessionStorage.getItem("career-project")) {
      try {
        setProject(await api<Project>("project"));
      } catch {
        /* The editor retains the user's inputs until retry. */
      }
    }
  }
  const act: Act = async (kind, extra = {}) => {
    if (busy || !ready || (!s?.configured && kind !== "decision")) return false;
    setWorking(
      (
        {
          question: "busy_question",
          follow: "busy_question",
          answer: "busy_feedback",
          summary: "busy_summary",
          decision: "submitted",
        } as Record<string, string>
      )[kind] || "busy",
    );
    setErr(null);
    try {
      const p = await ensureMaterials();
      const next = await api<Project>("action", "POST", {
        kind,
        version: p.version,
        language: lang,
        ...extra,
      });
      setProject(next);
      if (kind === "optimize") setRevisionRun((n) => n + 1);
      return true;
    } catch (e) {
      await reconcile(e);
      return false;
    } finally {
      setWorking("");
    }
  };
  async function run() {
    if (view === "interview" && visibleResult) {
      resultArea.current?.scrollIntoView({ block: "start" });
      resultArea.current
        ?.querySelector<HTMLTextAreaElement>("textarea")
        ?.focus();
      return;
    }
    if (await act(view === "interview" ? "question" : view)) {
      if (window.matchMedia("(max-width:720px)").matches)
        resultArea.current?.scrollIntoView({ block: "start" });
    }
  }
  async function refresh() {
    setWorking("refresh");
    setErr(null);
    try {
      if (project) setProject(await api<Project>("project"));
      else setStatus((await api<Bootstrap>("bootstrap")).status);
    } catch (e) {
      await reconcile(e);
    } finally {
      setWorking("");
    }
  }
  async function clear() {
    if (!confirm(t("clearWorkspaceConfirm"))) return;
    setWorking("clear");
    try {
      if (project) await api("project", "DELETE");
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 410)) {
        setErr(e);
        return;
      }
    } finally {
      setWorking("");
    }
    sessionStorage.removeItem("career-project");
    setProject(null);
    setDraft({ ...emptyMaterials });
    resetEditor((n) => n + 1);
    setView("optimize");
    showSettings(false);
    collapse(false);
    setErr(null);
    goHome();
  }
  const errorText =
    err instanceof ApiError
      ? err.messages[lang]
      : typeof err === "string"
        ? t(err)
        : t("networkError");
  if (!s)
    return (
      <main className="loading">
        <Brand />
        {err ? (
          <>
            <p role="alert">{errorText}</p>
            <button onClick={load}>{t("retryLoad")}</button>
          </>
        ) : (
          <span className="spinner" />
        )}
      </main>
    );
  const language = (
    <Language lang={lang} set={setLanguage} t={t} disabled={busy} />
  );
  const resultProps = project ? { project, t, lang, act, busy } : null;
  return (
    <>
      {!entered && (
        <div className="public welcome">
          <header className="public-header">
            <div className="header-inner">
              <Brand />
              {language}
            </div>
          </header>
          <Landing t={t} begin={goWorkspace} />
          <SiteFooter t={t} />
        </div>
      )}
      <div hidden={!entered} className="shell bench">
        {menu && (
          <button
            className="scrim"
            aria-label={t("close")}
            onClick={() => setMenu(false)}
          />
        )}
        <aside
          className={"rail " + (menu ? "open" : "")}
          aria-label={t("navigation")}
        >
          <div className="rail-brand">
            <button
              className="brand-home"
              aria-label={t("home")}
              onClick={goHome}
            >
              <Brand />
            </button>
          </div>
          <nav>
            <button
              className="workspace-nav"
              onClick={() => {
                setMenu(false);
                collapse(false);
                window.scrollTo(0, 0);
              }}
            >
              <LayoutPanelLeft size={18} />
              {t("desk")}
            </button>
            <div className="rail-group">
              <small>{t("menuGroup")}</small>
              {toolList.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  aria-current={view === id ? "page" : undefined}
                  onClick={() => select(id, true)}
                >
                  <Icon size={17} />
                  {t(label)}
                </button>
              ))}
            </div>
          </nav>
          <div className="rail-foot">
            <button
              onClick={() => {
                setMenu(false);
                showSettings(!settings);
              }}
            >
              <Settings size={17} />
              {t("settings")}
            </button>
          </div>
        </aside>
        <div className="work">
          <header className="work-top">
            <div className="bench-title">
              <button
                className="icon-btn mobile-only"
                aria-label={t("openMenu")}
                onClick={() => setMenu(!menu)}
              >
                <Menu size={20} />
              </button>
              <LayoutPanelLeft size={20} />
              <strong>{t("desk")}</strong>
            </div>
            <div className="top-controls">
              <button
                ref={settingToggle}
                className="connection-button"
                aria-expanded={settings}
                onClick={() => showSettings(!settings)}
              >
                <i className={s.connection} />
                {t(s.connection)}
              </button>
              {language}
            </div>
          </header>
          {settings && (
            <section className="settings-strip" aria-label={t("settings")}>
              <div className="settings-head">
                <h2>{t("settings")}</h2>
                <button
                  className="icon-btn"
                  aria-label={t("close")}
                  onClick={() => showSettings(false)}
                >
                  <X size={16} />
                </button>
              </div>
              <div className="settings-grid">
                <div>
                  <h3>{t("configuration")}</h3>
                  <p>
                    {s.model} · {t(s.connection)}
                  </p>
                  <button disabled={busy} onClick={refresh}>
                    <RefreshCw size={14} />
                    {t("refresh")}
                  </button>
                </div>
                <div>
                  <h3>
                    <BookOpen size={14} />
                    {t("knowledge")}
                  </h3>
                  <p>
                    {s.guideCount
                      ? t("guides_count", { n: s.guideCount })
                      : t("empty_guides")}
                  </p>
                  {s.guideFiles.map((f) => (
                    <p key={f}>{f}</p>
                  ))}
                  {s.warnings.map((w, i) => (
                    <p key={i}>{w[lang]}</p>
                  ))}
                </div>
                <div>
                  <h3>{t("sessionHeading")}</h3>
                  <p>{t("sessionPrivacy")}</p>
                  <button disabled={busy} onClick={clear}>
                    {t("clearWorkspace")}
                  </button>
                </div>
              </div>
            </section>
          )}
          <main className={"bench-grid " + (collapsed ? "is-collapsed" : "")}>
            <div className="material-column" hidden={collapsed}>
              {demo && <div style={{padding:"12px 20px 0",fontSize:12,color:"#344d70"}}>
                <p>{lang==="en"?"Demo Mode · Scripted results in English.":lang==="zh-TW"?"演示模式 · 使用虛構材料體驗英文預設結果。":"演示模式 · 使用虚构材料体验英文预设结果。"}</p>
                <button onClick={() => change({...sample, filename:"",link:""})}>{lang==="en"?"Use fictional sample":lang==="zh-TW"?"填入虛構範例":"填入虚构示例"}</button>
              </div>}
              <MaterialsPanel
                key={sessionEpoch}
                draft={draft}
                t={t}
                lang={lang}
                busy={busy}
                setWorking={setWorking}
                configured={s.configured}
                onChange={change}
                collapse={() => collapse(true)}
                actionLabel={actionLabel}
                onRun={run}
                requirements={
                  !dirty ? project?.context?.requirements || [] : []
                }
              />
            </div>
            <section
              className="analysis-column"
              ref={resultArea}
              aria-label={t("aiWorkspace")}
            >
              <div className="analysis-bar">
                <div className="analysis-heading">
                  {collapsed && (
                    <button className="unfold" onClick={() => collapse(false)}>
                      <PanelLeftOpen size={16} />
                      {t("showMaterials")}
                    </button>
                  )}
                  <span>{t("aiWorkspace")}</span>
                </div>
                {collapsed && (!visibleResult || view !== "interview") && (
                  <button
                    className="primary compact"
                    disabled={busy || !ready || !s.configured}
                    onClick={run}
                  >
                    {actionLabel}
                  </button>
                )}
              </div>
              <div
                className="tool-tabs"
                role="tablist"
                aria-label={t("menuGroup")}
                onKeyDown={(event) => {
                  const i = toolList.findIndex((tool) => tool.id === view);
                  const positions: Record<string, number> = {
                    ArrowLeft: (i + 2) % 3,
                    ArrowRight: (i + 1) % 3,
                    Home: 0,
                    End: 2,
                  };
                  const position = positions[event.key];
                  if (position === undefined) return;
                  event.preventDefault();
                  const id = toolList[position].id;
                  select(id);
                  document.getElementById("tab-" + id)?.focus();
                }}
              >
                {toolList.map(({ id, label, icon: Icon }) => (
                  <button
                    role="tab"
                    id={"tab-" + id}
                    aria-controls="tool-panel"
                    aria-selected={view === id}
                    tabIndex={view === id ? 0 : -1}
                    key={id}
                    onClick={() => select(id)}
                  >
                    <Icon size={17} />
                    {t(label)}
                  </button>
                ))}
              </div>
              {!!err && (
                <p role="alert" className="error">
                  {errorText}
                </p>
              )}
              {busy && <ProgressNote text={t(working)} />}
              <div
                className="result-body"
                role="tabpanel"
                id="tool-panel"
                aria-labelledby={"tab-" + view}
              >
                {!visibleResult && (
                  <EmptyTool
                    view={view}
                    draft={draft}
                    t={t}
                    focus={focusSource}
                    dirty={dirty}
                  />
                )}
                {project && resultProps && (
                  <div
                    hidden={dirty}
                    key={project.context?.fingerprint || "pending"}
                  >
                    {project.optimization && (
                      <div hidden={view !== "optimize"}>
                        <Optimization key={revisionRun} {...resultProps} />
                      </div>
                    )}
                    {project.matching && (
                      <div hidden={view !== "match"}>
                        <Matching {...resultProps} />
                      </div>
                    )}
                    {(project.interview.question ||
                      project.interview.ended) && (
                      <div hidden={view !== "interview"}>
                        <Interview {...resultProps} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          </main>
        </div>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
