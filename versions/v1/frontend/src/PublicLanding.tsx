import { LandingPage } from "./views/LandingPage";
import { translate } from "./lib/i18n";
import type { Lang } from "./lib/types";
export default function PublicLanding({
  lang,
  setLang,
  begin,
}: {
  lang: Lang;
  setLang: (lang: Lang) => void;
  begin: () => void;
}) {
  return (
    <LandingPage
      t={(key) => translate(lang, key)}
      enter={begin}
      languageControl={
        <select
          aria-label="Language"
          value={lang}
          onChange={(e) => setLang(e.target.value as Lang)}
        >
          <option value="zh-CN">简体中文</option>
          <option value="zh-TW">繁體中文</option>
          <option value="en">English</option>
        </select>
      }
    />
  );
}
