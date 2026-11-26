import { useRef, useState } from "react";
import {
  Check,
  ChevronRight,
  FileText,
  Link2,
  PanelLeftClose,
  Upload,
  Play,
  BriefcaseBusiness,
  Info,
} from "lucide-react";
import { api, ApiError } from "./api";
import type { Lang, Materials, Trans } from "./types";

export type DocumentKey = "resume" | "jd";
export function readable(text: string) {
  const count = text.replace(/\s/g, "").length;
  return (
    count >= 30 &&
    /\p{L}/u.test(text) &&
    (text.match(/\p{L}/gu) || []).length >= 12 &&
    new Set(text.trim().toLowerCase()).size >= 6
  );
}
type Props = {
  draft: Materials;
  t: Trans;
  lang: Lang;
  busy: boolean;
  setWorking: (key: string) => void;
  configured: boolean;
  onChange: (change: Partial<Materials>) => void;
  collapse: () => void;
  actionLabel: string;
  onRun: () => void;
  requirements: {
    id: string;
    source_id: string;
    category: string;
    quote: string;
  }[];
};
export function MaterialsPanel({
  draft,
  t,
  lang,
  busy,
  setWorking,
  configured,
  onChange,
  collapse,
  actionLabel,
  onRun,
  requirements,
}: Props) {
  const file = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState(draft.link),
    [linkOpen, setLinkOpen] = useState(false),
    [issue, setIssue] = useState<string | ApiError>("");
  const ready = readable(draft.resume) && readable(draft.jd);
  function change(p: Partial<Materials>) {
    setIssue("");
    onChange(p);
  }
  async function readDocument(key: DocumentKey, f?: File) {
    if (busy) return;
    const pdf = key === "resume";
    if (pdf && !f) return;
    if (f && (!f.name.toLowerCase().endsWith(".pdf") || f.size > 10485760)) {
      setIssue(f.size > 10485760 ? "pdfSize" : "pdfType");
      return;
    }
    setIssue("");
    setWorking(pdf ? "readPdf" : "loadingLink");
    try {
      const { text } = await api<{ text: string }>(
        pdf ? "pdf" : "import",
        "POST",
        pdf ? f : { url },
      );
      change(
        pdf ? { resume: text, filename: f!.name } : { jd: text, link: url },
      );
      if (!pdf) setLinkOpen(false);
    } catch (e) {
      setIssue(e instanceof ApiError ? e : "networkError");
    } finally {
      setWorking("");
    }
  }
  return (
    <section className="materials-panel" aria-labelledby="materials-title">
      <header className="panel-heading">
        <h2 id="materials-title">{t("materialsHeading")}</h2>
        <button
          className="icon-btn"
          aria-label={t("collapseMaterials")}
          title={t("collapseMaterials")}
          onClick={collapse}
        >
          <PanelLeftClose size={17} />
        </button>
      </header>
      <fieldset className="bare inputs" disabled={busy}>
        <div className="input-section">
          <div className="input-heading">
            <label htmlFor="work-resume">
              <FileText size={17} />
              {t("resume")}
            </label>
            <button className="text-btn" onClick={() => file.current?.click()}>
              <Upload size={14} />
              {t("pdf_mode")}
            </button>
          </div>
          <input
            hidden
            ref={file}
            type="file"
            accept=".pdf,application/pdf"
            aria-label={t("pdf_label")}
            onChange={(e) => {
              void readDocument("resume", e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <textarea
            id="work-resume"
            maxLength={24000}
            value={draft.resume}
            placeholder={t("resume_placeholder")}
            onChange={(e) => change({ resume: e.target.value, filename: "" })}
            onDragOver={(e) => {
              if (e.dataTransfer.types.includes("Files")) e.preventDefault();
            }}
            onDrop={(e) => {
              if (e.dataTransfer.files.length) {
                e.preventDefault();
                void readDocument("resume", e.dataTransfer.files[0]);
              }
            }}
          />
          <div className="input-meta">
            {draft.filename ? (
              <span title={draft.filename}>
                <Check size={12} />
                {draft.filename}
              </span>
            ) : (
              <span>{t("pdfLimit")}</span>
            )}
            <span>{t("characters", { n: draft.resume.length })}</span>
          </div>
        </div>
        <div className="input-section">
          <div className="input-heading">
            <label htmlFor="work-jd">
              <BriefcaseBusiness size={17} />
              {t("jd")}
            </label>
            <button
              className="text-btn"
              aria-expanded={linkOpen}
              onClick={() => {
                setLinkOpen(!linkOpen);
                setIssue("");
              }}
            >
              <Link2 size={14} />
              {t("linkMode")}
            </button>
          </div>
          {linkOpen && (
            <div className="link-import">
              <label htmlFor="job-link">{t("publicLink")}</label>
              <div>
                <input
                  autoFocus
                  id="job-link"
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://…"
                />
                <button
                  disabled={!url.trim()}
                  onClick={() => readDocument("jd")}
                >
                  {t("importShort")}
                </button>
              </div>
            </div>
          )}
          <textarea
            id="work-jd"
            maxLength={24000}
            value={draft.jd}
            placeholder={t("jd_placeholder")}
            onChange={(e) => change({ jd: e.target.value, link: "" })}
          />
          <div className="input-meta">
            <span title={draft.link}>{draft.link || t("jdTypes")}</span>
            <span>{t("characters", { n: draft.jd.length })}</span>
          </div>
        </div>
      </fieldset>
      {issue && (
        <p className="error" role="alert">
          {issue instanceof ApiError ? issue.messages[lang] : t(issue)}
        </p>
      )}
      <div className="material-action">
        <div className="readiness" role="status">
          <i className={ready ? "ready" : ""} />
          {t(
            ready
              ? "materials_ready"
              : draft.resume || draft.jd
                ? "incompleteMaterials"
                : "awaitingMaterials",
          )}
        </div>
        {!ready && (draft.resume.trim() || draft.jd.trim()) && (
          <p className="field-hint">{t("lengthHint")}</p>
        )}
        <button
          className="primary run-analysis"
          disabled={busy || !ready || !configured}
          onClick={onRun}
        >
          <Play size={15} />
          {actionLabel}
        </button>
        <p className="model-hint">
          <Info size={14} />
          {t(configured ? "privacyShort" : "modelNotice")}
        </p>
      </div>
      {requirements.length > 0 && (
        <details className="req-index">
          <summary>
            {t("source_context")}
            <ChevronRight size={15} />
          </summary>
          {requirements.map((q) => (
            <p key={q.id}>
              <small>
                {q.source_id} · {t(q.category)}
              </small>
              {q.quote}
            </p>
          ))}
        </details>
      )}
    </section>
  );
}
