import { useEffect, useState } from "react";
import { cloudJson } from "./cloud";
export default function PersonalQuota({ lang }: { lang: string }) {
  const [q, setQ] = useState<{
    remaining: number;
    limit: number;
    blocked: boolean;
  }>();
  useEffect(() => {
    let active = true;
    const update = () => {
      cloudJson("/api/quota")
        .then((v) => {
          if (active) setQ(v);
        })
        .catch(() => {
          if (active) setQ(undefined);
        });
    };
    update();
    window.addEventListener("quota-update", update);
    window.addEventListener("focus", update);
    return () => {
      active = false;
      window.removeEventListener("quota-update", update);
      window.removeEventListener("focus", update);
    };
  }, []);
  const text =
    lang === "en"
      ? [
          "Daily AI calls remaining",
          "Today’s free calls are used up. Please come back tomorrow.",
          "AI requests paused",
        ]
      : lang === "zh-TW"
        ? [
            "今日剩餘 AI 次數",
            "今日免費次數已用完，明天可以繼續使用。",
            "AI 請求已暫停",
          ]
        : [
            "今日剩余 AI 次数",
            "今日免费次数已用完，明天可以继续使用。",
            "AI 请求已暂停",
          ];
  return (
    <div aria-live="polite" style={{ fontSize: 14, padding: "18px 0" }}>
      <strong>{text[0]}</strong>
      <span style={{ marginLeft: 24 }}>
        {q ? `${q.remaining} / ${q.limit}` : "—"}
      </span>
      {q?.blocked ? (
        <p>{text[2]}</p>
      ) : q?.remaining === 0 ? (
        <p>{text[1]}</p>
      ) : null}
    </div>
  );
}
