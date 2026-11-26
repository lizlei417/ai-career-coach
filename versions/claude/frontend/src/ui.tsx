import { cloneElement, useId } from "react";
import type { ReactNode, ReactElement } from "react";
import {
  BookOpen,
  ChevronDown,
  Globe2,
  Layers3,
  MessagesSquare,
  PencilLine,
  FolderOpen,
} from "lucide-react";
import { langs } from "./i18n";
import type { Guide, Lang, Trans } from "./types";

export const toolList = [
  { id: "optimize", label: "resume_tab", note: "optDesc", icon: PencilLine },
  { id: "match", label: "matching_tab", note: "matchDesc", icon: Layers3 },
  {
    id: "interview",
    label: "interview_tab",
    note: "ivDesc",
    icon: MessagesSquare,
  },
] as const;
export function Brand() {
  return (
    <span className="brand">
      <svg aria-hidden="true" viewBox="0 0 36 32">
        <path
          fill="currentColor"
          d="m2 26 12-22h6L8 26zm11 0 10-18h5L18 26zm9 0 6-11h5l-6 11z"
        />
      </svg>
      <b>AI Career Coach</b>
    </span>
  );
}
export function Language({
  lang,
  set,
  t,
  disabled = false,
}: {
  lang: Lang;
  set: (v: Lang) => void;
  t: Trans;
  disabled?: boolean;
}) {
  return (
    <label className="language">
      <Globe2 size={16} />
      <select
        aria-label={t("language")}
        value={lang}
        disabled={disabled}
        onChange={(e) => set(e.target.value as Lang)}
      >
        {Object.entries(langs).map(([code, name]) => (
          <option value={code} key={code}>
            {name}
          </option>
        ))}
      </select>
      <ChevronDown size={13} />
    </label>
  );
}
export function Landing({ t, begin }: { t: Trans; begin: () => void }) {
  return (
    <main className="landing">
      <section className="hero">
        <div className="hero-copy">
          <div className="kicker">
            <i />
            {t("forStudents")}
          </div>
          <h1>
            {t("headlineA")}
            <br />
            <em>{t("headlineB")}</em>
          </h1>
          <p>{t("intro")}</p>
          <button className="primary create" onClick={begin}>
            <FolderOpen size={18} />
            {t("getStarted")}
          </button>
        </div>
        <div className="hero-art" aria-hidden="true">
          <img src={import.meta.env.BASE_URL + "art/atrium.svg"} alt="" />
        </div>
      </section>
      <section className="features" aria-label={t("tools")}>
        <div className="section-line">
          <h2>{t("tools")}</h2>
          <span />
        </div>
        <div className="feature-grid">
          {toolList.map(({ id, label, note, icon: Icon }) => (
            <article key={id}>
              <Icon size={24} strokeWidth={1.55} />
              <div>
                <h3>{t(label)}</h3>
                <p>{t(note)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
export function SiteFooter({ t }: { t: Trans }) {
  return (
    <footer className="site-footer">
      <span>{t("university")}</span>
      <span>
        IS5542 <i /> AI Career Coach
      </span>
    </footer>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactElement<{ id?: string }>;
}) {
  const inputId = useId();
  return (
    <div className="field">
      <label htmlFor={inputId}>{label}</label>
      {cloneElement(children, { id: inputId })}
    </div>
  );
}
export function Guides({ guides, t }: { guides: Guide[]; t: Trans }) {
  return guides.length ? (
    <details className="source">
      <summary>
        <BookOpen size={16} />
        {t("guide_refs", { n: guides.length })}
        <ChevronDown size={14} />
      </summary>
      {guides.map((g) => (
        <div className="source-body" key={g.id}>
          <b>{g.filename}</b> <small>{g.id}</small>
          <p>{g.text}</p>
        </div>
      ))}
    </details>
  ) : (
    <p className="meta guide-note">
      <BookOpen size={14} />
      {t("no_refs")}
    </p>
  );
}
export function Title({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="view-title">
      <h1>{title}</h1>
      {children}
    </div>
  );
}
export function ProgressNote({ text }: { text: string }) {
  const id = useId();
  return (
    <div className="working" id={id} role="status">
      <i />
      {text}
    </div>
  );
}
