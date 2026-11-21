import { Brand, Landing, Language, SiteFooter } from "./ui";
import { ui, index } from "./i18n";
import type { Lang, Trans } from "./types";
export default function PublicLanding({
  lang,
  setLang,
  begin,
}: {
  lang: Lang;
  setLang: (lang: Lang) => void;
  begin: () => void;
}) {
  const publicLabels: Record<string, string[]> = {
    resume_tab: ["Resume Optimization", "简历优化", "履歷優化"],
    matching_tab: ["Job Matching", "岗位匹配", "職位配對"],
    interview_tab: ["Mock Interview", "模拟面试", "模擬面試"],
    language: ["Language", "语言", "語言"],
  };
  const t: Trans = (key) =>
    (ui[key] || publicLabels[key])?.[index[lang]] || key;
  return (
    <div className="public welcome">
      <header className="public-header">
        <div className="header-inner">
          <Brand />
          <Language lang={lang} set={setLang} t={t} />
        </div>
      </header>
      <Landing t={t} begin={begin} />
      <SiteFooter t={t} />
    </div>
  );
}
