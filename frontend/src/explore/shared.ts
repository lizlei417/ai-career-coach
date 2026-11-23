import { useState } from "react";
import { useApp } from "../lib/store";
import { errorKey } from "../lib/i18n";
import traditional from "./traditional.json";

export function useCopy() {
  const { s, t } = useApp();
  const l = (zh: string, en: string) =>
    s.lang === "en"
      ? en
      : s.lang === "zh-TW"
        ? (traditional as Record<string, string>)[zh] || zh
        : zh;
  return {
    l,
    error: (e: unknown) =>
      t(errorKey(e instanceof Error ? e.message : "SERVER")),
  };
}
export function useAction() {
  const { error } = useCopy();
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setMessage(error(e));
    } finally {
      setBusy(false);
    }
  }
  return { busy, message, run };
}
export const categories: Record<string, [string, string]> = {
  product: ["产品管理", "Product management"],
  operations: ["运营协调", "Operations"],
  analytics: ["数据与研究", "Analytics and research"],
  marketing: ["市场增长", "Marketing and growth"],
  engineering: ["软件工程", "Engineering"],
  design: ["创意设计", "Design"],
  finance: ["金融与风控", "Finance and risk"],
  people: ["人才发展", "People and talent"],
  other: ["更多方向", "Other paths"],
};
export interface QuizResult {
  id: string;
  revision: number;
  updated: string;
  profile: number;
  paths: string[];
  scores: number[];
  answers: number[];
}
