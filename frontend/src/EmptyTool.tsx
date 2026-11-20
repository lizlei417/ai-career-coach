import { Check, ChevronRight, FileText, BriefcaseBusiness } from "lucide-react";
import type { Materials, Trans, View } from "./types";
import { toolList } from "./ui";
import { readable, type DocumentKey } from "./MaterialsPanel";
export default function EmptyTool({
  view,
  draft,
  t,
  focus,
  dirty,
}: {
  view: View;
  draft: Materials;
  t: Trans;
  focus: (k: DocumentKey) => void;
  dirty: boolean;
}) {
  const tool = toolList.find((x) => x.id === view)!;
  const title = {
    optimize: "optReady",
    match: "matchReady",
    interview: "ivReady",
  }[view];
  return (
    <section className="tool-blank">
      <div className="blank-lead">
        <div className="paper-symbol" aria-hidden="true">
          <div>
            <tool.icon size={30} strokeWidth={1.3} />
            <i />
            <i />
          </div>
        </div>
        <div className="blank-copy">
          <h1>{t(title)}</h1>
          <p>{t(tool.note)}</p>
        </div>
      </div>
      <div className="source-ledger">
        <h2>{t("sourceMaterials")}</h2>
        {(["resume", "jd"] as const).map((k) => {
          const Icon = k === "resume" ? FileText : BriefcaseBusiness;
          return (
            <button key={k} onClick={() => focus(k)}>
              <Icon size={19} />
              <div>
                <strong>{t(k)}</strong>
                <span>
                  {draft[k].trim()
                    ? draft[k].trim().slice(0, 125)
                    : t(k === "resume" ? "awaitResume" : "awaitJd")}
                </span>
              </div>
              {readable(draft[k]) && <Check size={15} />}
              <ChevronRight size={15} />
            </button>
          );
        })}
      </div>
      {dirty && <p className="notice">{t("materialsChanged")}</p>}
    </section>
  );
}
