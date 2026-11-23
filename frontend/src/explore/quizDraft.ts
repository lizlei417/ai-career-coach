import { useEffect, useSyncExternalStore } from "react";
import { apiFetch, ownerKey } from "../cloud";

type Draft = { answers: number[]; cursor: number; revision: number };
type Edit = {
  cursor: number;
  index?: number;
  value?: number;
  prefix?: number[];
  reset?: boolean;
};
const empty = (): Draft => ({ answers: [], cursor: 0, revision: 0 });

function apply(base: Draft, edits: Edit[]): Draft {
  let answers = [...base.answers],
    cursor = base.cursor;
  for (const edit of edits) {
    if (edit.reset) answers = [];
    if (edit.index !== undefined && edit.value !== undefined) {
      if (answers.length < edit.index)
        answers.push(...(edit.prefix || []).slice(answers.length, edit.index));
      while (answers.length < edit.index) answers.push(0);
      answers[edit.index] = edit.value;
    }
    cursor = edit.cursor;
  }
  return { ...base, answers, cursor: Math.min(cursor, answers.length, 11) };
}

function createDraft(key: string) {
  let base = empty(),
    edits: Edit[] = [];
  try {
    const cache = JSON.parse(sessionStorage.getItem(key) || "null");
    if (
      cache &&
      Array.isArray(cache.base?.answers) &&
      Array.isArray(cache.edits)
    ) {
      base = cache.base;
      edits = cache.edits;
    }
  } catch {
    /* Storage can be unavailable in private browsing. */
  }
  let loaded = false,
    syncing = false,
    failed = false;
  let timer: ReturnType<typeof setTimeout>;
  let view = {
    ...apply(base, edits),
    failed,
    loaded,
    pending: edits.length > 0,
  };
  const listeners = new Set<() => void>();
  function publish() {
    view = { ...apply(base, edits), failed, loaded, pending: edits.length > 0 };
    try {
      sessionStorage.setItem(key, JSON.stringify({ base, edits }));
    } catch {
      /* Still sync in memory. */
    }
    listeners.forEach((fn) => fn());
  }
  async function sync() {
    if (syncing || key !== ownerKey("quiz-draft-1")) return;
    syncing = true;
    try {
      for (let conflict = 0; conflict < 3;) {
        if (key !== ownerKey("quiz-draft-1")) return;
        const options = { signal: AbortSignal.timeout(10000) };
        if (!loaded) {
          const r = await apiFetch("/api/explore/draft", options);
          if (!r.ok) throw Error();
          base = (await r.json())[0] || empty();
          loaded = true;
          failed = false;
          publish();
        }
        if (!edits.length) break;
        if (key !== ownerKey("quiz-draft-1")) return;
        const count = edits.length,
          next = apply(base, edits);
        const r = await apiFetch("/api/explore/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(next),
          signal: AbortSignal.timeout(10000),
        });
        if (r.status === 409) {
          loaded = false;
          conflict++;
          continue;
        }
        if (!r.ok) throw Error();
        base = { ...next, revision: (await r.json()).revision };
        edits = edits.slice(count);
        failed = false;
        publish();
      }
      if (!loaded) throw Error();
    } catch {
      failed = true;
      loaded = false;
      publish();
    } finally {
      syncing = false;
    }
  }
  function edit(change: Edit) {
    edits.push(
      change.index === undefined
        ? change
        : { ...change, prefix: view.answers.slice(0, change.index) },
    );
    publish();
    clearTimeout(timer);
    timer = setTimeout(sync, 350);
  }
  return {
    read: () => view,
    edit,
    sync,
    subscribe(fn: () => void) {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    refresh() {
      if (!syncing) loaded = false;
      void sync();
    },
  };
}
let current: { key: string; store: ReturnType<typeof createDraft> } | undefined;
export function useQuizDraft() {
  const key = ownerKey("quiz-draft-1");
  if (current?.key !== key) current = { key, store: createDraft(key) };
  const { store } = current;
  const draft = useSyncExternalStore(store.subscribe, store.read);
  useEffect(() => {
    store.refresh();
    window.addEventListener("online", store.refresh);
    return () => window.removeEventListener("online", store.refresh);
  }, [store]);
  return { draft, store };
}
