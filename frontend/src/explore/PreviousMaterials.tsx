import { useState } from "react";
import { get } from "../lib/api";
import { useApp } from "../lib/store";
import { useAction, useCopy } from "./shared";
import { ProductDialog, confirmAction } from "../ProductDialog";

export default function PreviousMaterials() {
  const { s, project, setInputs } = useApp(),
    { l } = useCopy(),
    { run, busy, message } = useAction();
  const [rows, list] = useState<{ id: string; name: string }[] | null>(null);
  if (!project.id) return null;
  return (
    <div>
      <button
        disabled={busy}
        onClick={() =>
          run(async () => list(await get("/api/previous-materials")))
        }
      >
        {l("从 V3 复制求职材料", "Copy materials from V3")}
      </button>
      {message && <p role="alert">{message}</p>}
      {rows && (
        <ProductDialog
          title={l("选择 V3 项目", "Choose a V3 project")}
          busy={busy}
          onClose={() => list(null)}
        >
          <p>
            {l(
              "复制简历文本、目标岗位和 JD 到当前 V4 项目。原始文件和历史报告保留在 V3。",
              "Copy resume text, role and JD into the current V4 project. Original files and historical reports stay in V3.",
            )}
          </p>
          {!rows.length && (
            <p>
              {l(
                "这个账户还没有 V3 项目。",
                "This account has no V3 projects.",
              )}
            </p>
          )}
          {rows.map((row) => (
            <button
              className="field my-1"
              key={row.id}
              disabled={busy}
              onClick={() =>
                run(async () => {
                  if (
                    (s.inputs.resumeText ||
                      s.inputs.jdText ||
                      s.inputs.jobTitle) &&
                    !(await confirmAction(
                      l(
                        "替换当前项目的简历文本、目标岗位和 JD？",
                        "Replace the resume text, role and JD of this project?",
                      ),
                    ))
                  )
                    return;
                  const m = await get<{
                    resumeText: string;
                    jdText: string;
                    jobTitle: string;
                  }>("/api/previous-materials/" + row.id);
                  setInputs({
                    ...m,
                    resumeFile: null,
                    jdUrl: "",
                    jdFromUrl: false,
                    jdSourceUrl: "",
                  });
                  list(null);
                })
              }
            >
              {row.name}
            </button>
          ))}
        </ProductDialog>
      )}
    </div>
  );
}
