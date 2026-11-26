import { Folder, MoreHorizontal, Plus, Pencil, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useApp } from "../lib/store";
import { ProductDialog } from "../ProductDialog";
export default function ProjectList() {
  const {
    t,
    s,
    project,
    projects,
    busy,
    switching,
    pendingProject,
    changeProject,
    renameProject,
    deleteProject,
  } = useApp();
  const text =
    s.lang === "en"
      ? {
          rename: "Rename project",
          remove: "Delete project",
          title: "Delete this project?",
          description: (n: string) =>
            `Deleting “${n}” permanently removes its resume, job description, analyses, interview records and PDF files. This cannot be undone.`,
          save: "Save changes",
          confirm: "Delete project",
          error:
            "Could not complete the operation. Nothing has been hidden. Please retry.",
          name: "Project name",
          cancel: "Cancel",
        }
      : s.lang === "zh-TW"
        ? {
            rename: "修改專案名稱",
            remove: "刪除專案",
            title: "確認刪除專案？",
            description: (n: string) =>
              `刪除「${n}」後，該專案的履歷、職位描述、分析結果、模擬面試記錄及 PDF 將被刪除，且無法恢復。`,
            save: "儲存修改",
            confirm: "確認刪除",
            error: "未能完成操作，專案仍保留在清單中，請重試。",
            name: "專案名稱",
            cancel: "取消",
          }
        : {
            rename: "修改项目名称",
            remove: "删除项目",
            title: "确认删除项目？",
            description: (n: string) =>
              `删除「${n}」后，该项目的简历、岗位描述、分析结果、模拟面试记录及 PDF 将被删除，且无法恢复。`,
            save: "保存修改",
            confirm: "确认删除",
            error: "操作未能完成，项目仍保留在列表中，请重试。",
            name: "项目名称",
            cancel: "取消",
          };
  const [menu, setMenu] = useState<{ id: string; x: number; y: number }>(),
    [action, setAction] = useState<{
      kind: "rename" | "delete" | "create";
      id: string;
      name: string;
    }>(),
    [name, setName] = useState(""),
    [working, setWorking] = useState(false),
    [error, setError] = useState("");
  const menuRef = useRef<HTMLDivElement>(null),
    trigger = useRef<HTMLButtonElement | null>(null);
  const locked = switching || Object.values(busy).some(Boolean) || working;
  useEffect(() => {
    if (!menu) return;
    menuRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const close = (e: PointerEvent) => {
      if (
        !menuRef.current?.contains(e.target as Node) &&
        !trigger.current?.contains(e.target as Node)
      )
        setMenu(undefined);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [menu]);
  function closeDialog() {
    setAction(undefined);
    requestAnimationFrame(() => {
      if (trigger.current?.isConnected) trigger.current.focus();
    });
  }
  function choose(kind: "rename" | "delete") {
    const p = projects.find((p) => p.id === menu?.id);
    if (!p) return;
    setAction({ kind, ...p });
    setName(p.name);
    setError("");
    setMenu(undefined);
  }
  return (
    <section className="project-list mx-3 mt-4 min-h-0 border-b border-white/10 pb-3">
      <h2 className="px-2 pb-1 text-xs text-white/60">{t("project.list")}</h2>
      <div className="max-h-[23vh] overflow-y-auto">
        {projects.map((p) => (
          <div
            key={p.id}
            className={
              "flex w-full items-center rounded " +
              ((pendingProject || project.id) === p.id
                ? "bg-white/10 text-white"
                : "text-white/65")
            }
          >
            <button
              disabled={locked}
              aria-current={
                (pendingProject || project.id) === p.id ? "true" : undefined
              }
              onClick={() => {
                setMenu(undefined);
                if (p.id !== project.id)
                  void changeProject(p.id).catch(() => {});
              }}
              className="flex min-w-0 flex-1 items-center gap-2 px-2 py-1.5 text-left text-sm"
            >
              <Folder size={15} className="shrink-0" />
              <span className="truncate" title={p.name}>
                {p.name}
              </span>
            </button>
            <button
              disabled={locked}
              aria-label={`${p.name} · ${s.lang === "en" ? "Project menu" : s.lang === "zh-TW" ? "專案選單" : "项目菜单"}`}
              aria-haspopup="menu"
              aria-expanded={menu?.id === p.id}
              className="mr-1 shrink-0 rounded p-1 text-white/65 hover:bg-white/10 hover:text-white"
              onClick={(e) => {
                trigger.current = e.currentTarget;
                const rect = e.currentTarget.getBoundingClientRect();
                setMenu(
                  menu?.id === p.id
                    ? undefined
                    : {
                        id: p.id,
                        x: Math.min(rect.right, window.innerWidth - 180),
                        y: Math.min(rect.bottom + 4, window.innerHeight - 100),
                      },
                );
              }}
            >
              <MoreHorizontal size={17} />
            </button>
          </div>
        ))}
      </div>
      <button
        disabled={locked}
        className="flex items-center gap-2 px-2 pt-2 text-xs text-white/75"
        onClick={(e) => {
          trigger.current = e.currentTarget;
          setName("");
          setError("");
          setAction({ kind: "create", id: "", name: "" });
        }}
      >
        <Plus size={14} />
        {t("project.new")}
      </button>
      {menu &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            className="fixed z-50 min-w-[170px] rounded-lg border border-white/10 bg-[#172334] p-1.5 text-sm text-white shadow-xl"
            style={{ left: menu.x, top: menu.y }}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setMenu(undefined);
                trigger.current?.focus();
              }
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                const buttons = Array.from(
                  menuRef.current!.querySelectorAll("button"),
                );
                const idx = buttons.indexOf(
                  document.activeElement as HTMLButtonElement,
                );
                buttons[
                  (idx + (e.key === "ArrowUp" ? -1 : 1) + buttons.length) %
                    buttons.length
                ]?.focus();
              }
            }}
          >
            <button
              role="menuitem"
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left hover:bg-white/10"
              onClick={() => choose("rename")}
            >
              <Pencil size={14} />
              {text.rename}
            </button>
            <button
              role="menuitem"
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-red-200 hover:bg-white/10"
              onClick={() => choose("delete")}
            >
              <Trash2 size={14} />
              {text.remove}
            </button>
          </div>,
          document.body,
        )}
      {action && (
        <ProductDialog
          title={
            action.kind === "delete"
              ? text.title
              : action.kind === "rename"
                ? text.rename
                : t("project.new")
          }
          busy={working}
          onClose={() => {
            if (!working) closeDialog();
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (action.kind !== "delete" && !name.trim()) return;
              setWorking(true);
              setError("");
              try {
                if (action.kind === "rename")
                  await renameProject(action.id, name.trim());
                else if (action.kind === "delete")
                  await deleteProject(action.id);
                else await changeProject(name.trim(), true);
                closeDialog();
              } catch {
                setError(text.error);
              } finally {
                setWorking(false);
              }
            }}
          >
            {action.kind === "delete" ? (
              <p>{text.description(action.name)}</p>
            ) : (
              <label>
                {text.name}
                <input
                  autoFocus
                  required
                  maxLength={100}
                  value={name}
                  disabled={working}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
            )}
            {error && <p role="alert">{error}</p>}
            <footer>
              <button
                autoFocus={action.kind === "delete"}
                type="button"
                disabled={working}
                onClick={closeDialog}
              >
                {text.cancel}
              </button>
              <button
                type="submit"
                disabled={working || (action.kind !== "delete" && !name.trim())}
                className={
                  action.kind === "delete" ? "dialog-danger" : "dialog-primary"
                }
              >
                {working
                  ? "…"
                  : action.kind === "delete"
                    ? text.confirm
                    : action.kind === "rename"
                      ? text.save
                      : t("project.create")}
              </button>
            </footer>
          </form>
        </ProductDialog>
      )}
    </section>
  );
}
