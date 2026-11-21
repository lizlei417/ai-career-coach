import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { createRoot } from "react-dom/client";
import "./ProductDialog.css";

export function dialogWords() {
  const l = document.documentElement.lang;
  return l === "en"
    ? {
        cancel: "Cancel",
        ok: "Confirm",
        close: "Close",
        title: "Please confirm",
      }
    : l === "zh-TW"
      ? { cancel: "取消", ok: "確認", close: "關閉", title: "請確認" }
      : { cancel: "取消", ok: "确认", close: "关闭", title: "请确认" };
}
export function ProductDialog({
  title,
  children,
  onClose,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const focus = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    ref.current
      ?.querySelector<HTMLElement>("input,select,textarea,footer button")
      ?.focus();
    return () => {
      ref.current?.close();
      if (focus?.isConnected) focus.focus();
    };
  }, []);
  return createPortal(
    <dialog
      ref={ref}
      className="product-dialog"
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header>
        <h2 id={id}>{title}</h2>
        <button
          type="button"
          disabled={busy}
          aria-label={dialogWords().close}
          onClick={onClose}
        >
          ×
        </button>
      </header>
      {children}
    </dialog>,
    document.body,
  );
}
export function confirmAction(
  message: string,
  title = dialogWords().title,
): Promise<boolean> {
  return new Promise((resolve) => {
    const node = document.createElement("div");
    document.body.append(node);
    const root = createRoot(node);
    const finish = (value: boolean) => {
      root.unmount();
      node.remove();
      resolve(value);
    };
    root.render(
      <ProductDialog title={title} onClose={() => finish(false)}>
        <p>{message}</p>
        <footer>
          <button autoFocus onClick={() => finish(false)}>
            {dialogWords().cancel}
          </button>
          <button className="dialog-danger" onClick={() => finish(true)}>
            {dialogWords().ok}
          </button>
        </footer>
      </ProductDialog>,
    );
  });
}
export function showNotice(message: string): Promise<void> {
  return new Promise((resolve) => {
    const node = document.createElement("div");
    document.body.append(node);
    const root = createRoot(node);
    const finish = () => {
      root.unmount();
      node.remove();
      resolve();
    };
    root.render(
      <ProductDialog title="AI Career Coach" onClose={finish}>
        <p role="status">{message}</p>
        <footer>
          <button autoFocus className="dialog-primary" onClick={finish}>
            {dialogWords().ok}
          </button>
        </footer>
      </ProductDialog>,
    );
  });
}
