import { useRef, useState } from "react";
import { useApp } from "../lib/store";
import { useCopy } from "./shared";

export default function ReviewDate({
  value,
  change,
  clearable = false,
}: {
  value: string;
  change: (date: string) => void;
  clearable?: boolean;
}) {
  const { s } = useApp();
  const { l } = useCopy();
  const panel = useRef<HTMLDetailsElement>(null);
  const [month, setMonth] = useState(new Date());
  const year = month.getFullYear(),
    m = month.getMonth();
  const offset = new Date(year, m, 1).getDay();
  const days = new Date(year, m + 1, 0).getDate();
  function choose(day: string) {
    change(day);
    if (panel.current) {
      panel.current.open = false;
      panel.current.querySelector("summary")?.focus();
    }
  }
  return (
    <details
      className="review-date"
      ref={panel}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget))
          e.currentTarget.open = false;
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.currentTarget.open = false;
          e.currentTarget.querySelector("summary")?.focus();
        }
      }}
      onToggle={(e) => {
        if (e.currentTarget.open)
          setMonth(value ? new Date(value + "T12:00:00") : new Date());
      }}
    >
      <summary>{value || l("选择日期", "Choose date")}</summary>
      <div className="calendar-panel">
        <header>
          {[-1, 1].map((step) => (
            <button
              type="button"
              key={step}
              aria-label={
                step < 0
                  ? l("上个月", "Previous month")
                  : l("下个月", "Next month")
              }
              onClick={() => setMonth(new Date(year, m + step, 1))}
            >
              {step < 0 ? "‹" : "›"}
            </button>
          ))}
          <strong>
            {month.toLocaleDateString(s.lang, {
              year: "numeric",
              month: "long",
            })}
          </strong>
        </header>
        <div className="calendar-grid">
          {Array.from({ length: 7 }, (_, i) => (
            <small key={i}>
              {new Date(2024, 8, 1 + i).toLocaleDateString(s.lang, {
                weekday: "narrow",
              })}
            </small>
          ))}
          {Array.from({ length: days }, (_, i) => {
            const iso = [
              year,
              String(m + 1).padStart(2, "0"),
              String(i + 1).padStart(2, "0"),
            ].join("-");
            return (
              <button
                type="button"
                key={iso}
                aria-label={iso}
                aria-pressed={value === iso}
                style={i === 0 ? { gridColumnStart: offset + 1 } : undefined}
                onClick={() => choose(iso)}
              >
                {i + 1}
              </button>
            );
          })}
        </div>
        {clearable && (
          <button type="button" onClick={() => choose("")}>
            {l("清除", "Clear")}
          </button>
        )}
      </div>
    </details>
  );
}
