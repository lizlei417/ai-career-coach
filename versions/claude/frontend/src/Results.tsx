import { Fragment, useState } from "react";
import {
  ArrowRight,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Check,
  Download,
  FileText,
  ListChecks,
} from "lucide-react";
import type { Evidence, Project, TaskProps, Trans } from "./types";
import { Field, Guides, Title } from "./ui";
import { languageName } from "./i18n";

export function req(p: Project, id: string) {
  return p.context?.requirements.find((x) => x.id === id);
}
export function Citations({
  p,
  items,
  t,
}: {
  p: Project;
  items: Evidence[];
  t: Trans;
}) {
  return items.length > 0 ? (
    <details className="source">
      <summary>
        <FileText size={15} />
        {t("verifiedSource")}
        <ChevronDown size={14} />
      </summary>
      {[...new Set(items.map((e) => e.source_id))].map((id) => (
        <div key={id} className="source-body">
          <small>{id}</small>
          <p>{p.context?.resume.find((x) => x.id === id)?.text}</p>
        </div>
      ))}
    </details>
  ) : null;
}
export function download(name: string, content: string) {
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/plain;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function Optimization({ project: p, t, lang, act, busy }: TaskProps) {
  const [selected, select] = useState(0),
    [draft, setDraft] = useState(""),
    [editing, setEditing] = useState(false);
  const pack = p.optimization,
    items = pack?.data.revisions || [],
    idx = Math.min(selected, Math.max(0, items.length - 1)),
    r = items[idx];
  const choose = (i: number) => {
    select(i);
    setEditing(false);
  };
  const d = r && p.decisions[r.id],
    original = r?.evidence.map((e) => e.quote).join("\n");
  const selectedTexts = items.flatMap((x) => {
    const choice = p.decisions[x.id];
    return choice
      ? [
          choice.choice === "adopt"
            ? x.optimized
            : choice.choice === "edit"
              ? choice.edit
              : x.evidence.map((e) => e.quote).join("\n"),
        ]
      : [];
  });
  return (
    <>
      <Title title={t("resume_tab")} />
      {pack && (
        <>
          {pack.language !== lang && (
            <p className="notice">
              {t("reviewLang", { language: languageName(pack.language, lang) })}
            </p>
          )}
          {r ? (
            <div className="revision-layout">
              <aside className="item-list">
                <h3>
                  {t("reviewItems")}
                  <small>{items.length}</small>
                </h3>
                {items.map((x, i) => (
                  <button
                    key={x.id}
                    aria-pressed={i === idx}
                    onClick={() => choose(i)}
                  >
                    <i>{i + 1}</i>
                    <span>{x.title || x.evidence[0].quote}</span>
                    {p.decisions[x.id] && <Check size={14} />}
                  </button>
                ))}
              </aside>
              <article className="document">
                <div className="doc-heading">
                  <span className="num">{idx + 1}</span>
                  <h2>{r.title || t("revisions")}</h2>
                  {d && (
                    <span className="badge">
                      {t(
                        { adopt: "adopted", keep: "kept", edit: "edited" }[
                          d.choice
                        ] || "submitted",
                      )}
                    </span>
                  )}
                </div>
                <div className="compare">
                  <section>
                    <h3>{t("original")}</h3>
                    <p>{original}</p>
                  </section>
                  <ArrowRight size={19} />
                  <section className="refined">
                    <h3>{t("optimized")}</h3>
                    <p>{r.optimized}</p>
                  </section>
                </div>
                <div className="reason">
                  <h3>
                    <ListChecks size={18} />
                    {t("why")}
                  </h3>
                  <p>{r.reason}</p>
                  {r.requirement_ids.map((id) => (
                    <p className="quote" key={id}>
                      <small>
                        {t("requirement")} · {req(p, id)?.source_id}
                      </small>
                      {req(p, id)?.quote}
                    </p>
                  ))}
                </div>
                <Citations p={p} items={r.evidence} t={t} />
                {d?.choice === "edit" && !editing && (
                  <p className="quote">
                    <small>{t("editText")}</small>
                    {d.edit}
                  </p>
                )}
                {editing ? (
                  <div className="edit-box">
                    <Field label={t("editText")}>
                      <textarea
                        rows={4}
                        maxLength={24000}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                      />
                    </Field>
                    <div className="actions">
                      <button
                        disabled={!draft.trim() || busy}
                        className="primary"
                        onClick={async () => {
                          if (
                            await act("decision", {
                              id: r.id,
                              choice: "edit",
                              edit: draft,
                            })
                          )
                            setEditing(false);
                        }}
                      >
                        {t("save")}
                      </button>
                      <button onClick={() => setEditing(false)}>
                        {t("cancel")}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="actions">
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() =>
                        act("decision", { id: r.id, choice: "adopt" })
                      }
                    >
                      {t("adopt")}
                    </button>
                    <button
                      onClick={() => {
                        setDraft(d?.choice === "edit" ? d.edit : r.optimized);
                        setEditing(true);
                      }}
                    >
                      {t("edit")}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() =>
                        act("decision", { id: r.id, choice: "keep" })
                      }
                    >
                      {t("keep")}
                    </button>
                  </div>
                )}
                <div className="pager">
                  <button
                    aria-label={t("prevItem")}
                    disabled={idx === 0}
                    onClick={() => choose(idx - 1)}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span>
                    {idx + 1} / {items.length}
                  </span>
                  <button
                    aria-label={t("nextItem")}
                    disabled={idx === items.length - 1}
                    onClick={() => choose(idx + 1)}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </article>
            </div>
          ) : (
            <p className="notice">{t("no_revisions")}</p>
          )}
          {!!pack.blocked && (
            <p className="notice">{t("blocked", { n: pack.blocked })}</p>
          )}
          {pack.data.gaps.length > 0 && (
            <section className="subsection">
              <h2>{t("gaps")}</h2>
              {pack.data.gaps.map((g, i) => (
                <div className="list-row" key={i}>
                  <strong>{req(p, g.requirement_id)?.quote}</strong>
                  <p>{g.explanation}</p>
                  <p>{g.suggestion}</p>
                </div>
              ))}
            </section>
          )}
          <Guides guides={pack.guides} t={t} />
          {selectedTexts.length > 0 && (
            <button
              onClick={() =>
                download("revisions.txt", selectedTexts.join("\n\n"))
              }
            >
              <Download size={16} />
              {t("download_revisions")}
            </button>
          )}
        </>
      )}
    </>
  );
}
export function Matching({ project: p, t, lang, act, busy }: TaskProps) {
  const [expanded, set] = useState(""),
    pack = p.matching;
  const gaps = pack?.data.matches.filter((m) => m.status !== "direct") || [];
  const priority = ["high", "medium", "low"].find((v) =>
    gaps.some((m) => m.priority === v),
  );
  const priorities = gaps.filter((m) => m.priority === priority);
  return (
    <>
      <Title title={t("matching_tab")} />
      {pack && (
        <>
          {pack.language !== lang && (
            <p className="notice">
              {t("reviewLang", { language: languageName(pack.language, lang) })}
            </p>
          )}
          <section className="priority">
            <h2>{t("priorities")}</h2>
            {priorities.length ? (
              <ul>
                {priorities.map((m) => (
                  <li key={m.requirement_id}>
                    {req(p, m.requirement_id)?.quote}
                  </li>
                ))}
              </ul>
            ) : (
              <p>{t("noPriorities")}</p>
            )}
          </section>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {["requirement", "evidence", "assessment", "suggestion"].map(
                    (k) => (
                      <th key={k}>{t(k)}</th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {pack.data.matches.map((m) => {
                  const q = req(p, m.requirement_id)!,
                    open = expanded === q.id;
                  return (
                    <Fragment key={q.id}>
                      <tr>
                        <td>
                          <small>{t(q.category)}</small>
                          <button
                            className="table-toggle"
                            aria-expanded={open}
                            onClick={() => set(open ? "" : q.id)}
                          >
                            {q.quote}
                            <ChevronDown size={14} />
                          </button>
                        </td>
                        <td data-label={t("evidence")}>
                          {m.evidence.map((e, i) => (
                            <p key={i}>{e.quote}</p>
                          ))}
                          {!m.evidence.length && t("no_evidence")}
                        </td>
                        <td data-label={t("assessment")}>
                          <span className={"badge " + m.status}>
                            {t(m.status)}
                          </span>
                        </td>
                        <td data-label={t("suggestion")}>{m.suggestion}</td>
                      </tr>
                      {open && (
                        <tr>
                          <td colSpan={4}>
                            <div className="expanded">
                              <small>
                                {q.source_id} · {t("sourceJd")}
                              </small>
                              <p>
                                {
                                  p.context?.jd.find(
                                    (s) => s.id === q.source_id,
                                  )?.text
                                }
                              </p>
                              <b>{t(m.priority)}</b>
                              <p>{m.assessment}</p>
                              {m.gap_type !== "sufficient" && (
                                <p>{t(m.gap_type)}</p>
                              )}
                              <Citations p={p} items={m.evidence} t={t} />
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="meta">{t("matching_note")}</p>
          <Guides guides={pack.guides} t={t} />
          <button
            onClick={() =>
              download(
                "job-matching.txt",
                pack.data.matches
                  .map((m) =>
                    [
                      req(p, m.requirement_id)?.quote,
                      t(m.status),
                      ...m.evidence.map((e) => e.quote),
                      m.assessment,
                      m.suggestion,
                    ].join("\n"),
                  )
                  .join("\n\n"),
              )
            }
          >
            <Download size={16} />
            {t("download_match")}
          </button>
        </>
      )}
    </>
  );
}
