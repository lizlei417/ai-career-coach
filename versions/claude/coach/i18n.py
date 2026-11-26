"""Presentation-only translations. Original documents and AI results are never rewritten."""
import re

LANGUAGES = {"en": "English", "zh-CN": "简体中文", "zh-TW": "繁體中文"}
AI_LANGUAGES = {"en": "English", "zh-CN": "简体中文", "zh-TW": "繁體中文"}

# One key, three complete UI strings. Product names, source IDs and file contents stay verbatim.
STRINGS = {
    "language": ("Language", "语言", "語言"),
    "settings": ("Settings", "设置", "設定"),
    "hero": ("Your next chapter starts here.", "开启职业生涯的下一章。", "開啟職業生涯的下一章。"),
    "materials": ("Your Materials", "求职材料", "求職材料"),
    "workspace": ("Career Workspace", "求职工作区", "求職工作區"),
    "resume": ("Resume", "简历", "履歷"),
    "jd": ("Job Description", "岗位描述", "職位描述"),
    "text_mode": ("Paste text", "粘贴文本", "貼上文字"),
    "pdf_mode": ("Upload PDF", "上传 PDF", "上傳 PDF"),
    "input_mode": ("Resume format", "简历输入方式", "履歷輸入方式"),
    "resume_text": ("Resume text", "简历正文", "履歷正文"),
    "resume_placeholder": ("Paste your education, experience, projects and skills…", "粘贴教育背景、经历、项目与技能…", "貼上教育背景、經歷、專案與技能…"),
    "jd_placeholder": ("Paste responsibilities, required and preferred qualifications…", "粘贴岗位职责、必备及优先条件…", "貼上職位職責、必要及優先條件…"),
    "pdf_label": ("Resume PDF", "简历 PDF", "履歷 PDF"),
    "pdf_help": ("Text-based PDF · Up to 10 MB / 20 pages", "含文字层的 PDF · 最多 10 MB／20 页", "含文字層的 PDF · 最多 10 MB／20 頁"),
    "drop": ("Drop your PDF here", "将 PDF 拖到这里", "將 PDF 拖到這裡"),
    "browse": ("Browse files", "选择文件", "選擇檔案"),
    "remove_file": ("Remove file", "移除文件", "移除檔案"),
    "extracted": ("Extracted text", "提取正文", "擷取文字"),
    "analyze": ("Analyze", "开始分析", "開始分析"),
    "reanalyze": ("Analyze again", "重新分析", "重新分析"),
    "resume_tab": ("Resume Optimization", "简历优化", "履歷優化"),
    "matching_tab": ("Job Matching", "岗位匹配", "職位配對"),
    "interview_tab": ("Mock Interview", "模拟面试", "模擬面試"),
    "materials_ready": ("Materials ready", "材料已就绪", "材料已就緒"),
    "materials_missing": ("Add your resume and job description.", "请提供简历和岗位描述。", "請提供履歷和職位描述。"),
    "invalidated": ("Materials changed. Previous results and interview were reset.", "材料已修改，旧结果及面试记录已清除。", "材料已修改，舊結果及面試紀錄已清除。"),
    "disclosure": ("Data & sources", "数据与来源", "資料與來源"),
    "privacy": ("AI actions send your materials, relevant guides and answers to DeepSeek. Personal data stays in this session and is not written to project files or logs.", "执行 AI 操作会将材料、相关指南及回答发送至 DeepSeek。个人数据仅保存在当前会话，不写入项目文件或日志。", "執行 AI 操作會將材料、相關指南及回答傳送至 DeepSeek。個人資料僅保存在目前工作階段，不寫入專案檔案或日誌。"),
    "limits": ("30–24,000 characters per document. Text-based PDF only; OCR and job-link import are not available.", "每份材料需 30–24,000 字符。PDF 须含文字层；暂不支持 OCR 和岗位链接导入。", "每份材料需 30–24,000 字元。PDF 須含文字層；暫不支援 OCR 和職位連結匯入。"),
    "offline": ("Not configured", "未配置", "未設定"),
    "unverified": ("Not verified", "连接待验证", "連線待驗證"),
    "verified": ("Last request OK", "上次请求成功", "上次請求成功"),
    "failed": ("Request failed", "请求失败", "請求失敗"),
    "no_key": ("AI is not connected. Set DEEPSEEK_API_KEY in .env to analyze.", "AI 尚未连接，请在 .env 中设置 DEEPSEEK_API_KEY。", "AI 尚未連線，請在 .env 中設定 DEEPSEEK_API_KEY。"),
    "key_configured": ("Key configured; connection is verified only by an actual model request.", "已配置密钥，连接状态仅通过实际模型请求验证。", "已設定金鑰，連線狀態僅透過實際模型請求驗證。"),
    "model": ("Model", "模型", "模型"),
    "guides_count": ("Local guide passages: {n}", "本地指南片段：{n}", "本機指南片段：{n}"),
    "retrieval": ("Local lexical retrieval", "本地词项检索", "本機詞項檢索"),
    "empty_guides": ("No guides loaded. Core features work without a knowledge base.", "尚无指南，基础功能无需知识库也可运行。", "尚無指南，基本功能無須知識庫亦可運作。"),
    "clear": ("Clear session", "清除会话", "清除工作階段"),
    "clear_help": ("Removes materials, results and interview history from this session.", "移除当前会话的材料、结果和面试记录。", "移除目前工作階段的材料、結果和面試紀錄。"),
    "busy": ("Analyzing and checking sources…", "正在分析并核对来源…", "正在分析並核對來源…"),
    "busy_question": ("Preparing your next question…", "正在准备下一道问题…", "正在準備下一道問題…"),
    "busy_feedback": ("Reviewing your answer…", "正在核对本轮回答…", "正在核對本輪回答…"),
    "busy_summary": ("Summarizing your practice…", "正在整理练习总结…", "正在整理練習總結…"),
    "error_generic": ("This action could not be completed. Please retry or check your configuration and materials.", "本次操作未完成，请重试或检查配置及材料。", "本次操作未完成，請重試或檢查設定及材料。"),
    "empty_optimization": ("Your original and refined resume content will appear here.", "简历原文与优化内容将在这里对照展示。", "履歷原文與優化內容將在這裡對照展示。"),
    "empty_matching": ("Compare each job requirement with evidence from your resume.", "逐项核对岗位要求与简历证据。", "逐項核對職位要求與履歷證據。"),
    "empty_interview": ("Practice one question at a time, with feedback on your actual answer.", "一次练习一个问题，反馈以你的实际回答为准。", "每次練習一個問題，回饋以你的實際回答為準。"),
    "start": ("Start interview", "开始面试", "開始面試"),
    "no_revisions": ("No verified revisions to display. Add evidence or analyze again.", "暂无通过核验的改写，可补充证据后重新分析。", "暫無通過核驗的改寫，可補充證據後重新分析。"),
    "blocked": ("{n} unsupported revisions or suggestions were withheld.", "已拦截 {n} 项缺乏依据的改写或建议。", "已攔截 {n} 項缺乏依據的改寫或建議。"),
    "original": ("Original", "原文", "原文"),
    "optimized": ("Optimized", "优化版本", "優化版本"),
    "why": ("Why this change", "修改理由", "修改理由"),
    "adopt": ("Use this revision", "采用此条改写", "採用此項改寫"),
    "gaps": ("Evidence to add", "待补充证据", "待補充證據"),
    "download_revisions": ("Download selected revisions", "下载已采用的改写", "下載已採用的改寫"),
    "download_note": ("Selected excerpts only. Review before adding them to your resume.", "仅包含已采用的片段，请核对后合并至完整简历。", "僅包含已採用的片段，請核對後合併至完整履歷。"),
    "guide_refs": ("Reference guides · {n}", "参考指南 · {n}", "參考指南 · {n}"),
    "no_refs": ("No local guides cited in this result.", "本次结果未引用本地指南。", "本次結果未引用本機指南。"),
    "direct": ("Direct evidence", "有直接证据", "有直接證據"),
    "partial": ("Partial evidence", "有部分证据", "有部分證據"),
    "none": ("No evidence found", "未见证据", "未見證據"),
    "matching_note": ("Evidence coverage is not a hiring probability. Missing evidence does not imply missing ability.", "证据状态不代表录用概率；未见证据不等于不具备能力。", "證據狀態不代表錄用機率；未見證據不等於不具備能力。"),
    "requirement": ("Job requirement", "岗位要求", "職位要求"),
    "evidence": ("Resume evidence", "简历证据", "履歷證據"),
    "assessment": ("Assessment", "匹配结论", "配對結論"),
    "suggestion": ("Next step", "改善建议", "改善建議"),
    "responsibility": ("Responsibilities", "岗位职责", "職位職責"),
    "required": ("Required qualifications", "必备条件", "必要條件"),
    "preferred": ("Preferred qualifications", "优先条件", "優先條件"),
    "high": ("Prioritize", "优先处理", "優先處理"),
    "medium": ("Refine next", "随后完善", "隨後完善"),
    "low": ("Build on this", "持续积累", "持續累積"),
    "no_evidence": ("Not evidenced in the supplied resume.", "本次简历中未见相应证据。", "本次履歷中未見相應證據。"),
    "clarify_existing": ("Clarify an existing experience.", "补充现有经历的细节。", "補充現有經歷的細節。"),
    "not_in_material": ("Add real evidence if available, or plan learning and practice.", "如有真实经历请补证，否则可安排学习与练习。", "如有真實經歷請補證，否則可安排學習與練習。"),
    "download_match": ("Download matching results", "下载匹配结果", "下載配對結果"),
    "question": ("Question {n}", "问题 {n}", "問題 {n}"),
    "attempt": ("Attempt {n}", "第 {n} 次作答", "第 {n} 次作答"),
    "behavioral": ("Behavioral", "行为题", "行為題"),
    "technical": ("Technical", "技术题", "技術題"),
    "situational": ("Situational", "情境题", "情境題"),
    "question_sources": ("Question sources", "问题依据", "問題依據"),
    "answer": ("Your answer", "你的回答", "你的回答"),
    "answer_placeholder": ("Explain what you did and why. For behavioral questions, use situation, task, action and result.", "说明你的做法及理由。行为题可按情境、任务、行动及结果组织。", "說明你的做法及理由。行為題可按情境、任務、行動及結果組織。"),
    "submit": ("Get feedback", "获取反馈", "取得回饋"),
    "feedback": ("Your feedback", "本轮反馈", "本輪回饋"),
    "strengths": ("What worked", "表现较好的内容", "表現較好的內容"),
    "missing": ("What to clarify", "待补充信息", "待補充資訊"),
    "action": ("One action to try", "一个可执行动作", "一個可執行動作"),
    "answer_sources": ("Quoted answer evidence", "回答引用原文", "回答引用原文"),
    "follow_up": ("Follow-up", "追问", "追問"),
    "retry": ("Try again", "重新回答", "重新回答"),
    "next": ("Next question", "下一题", "下一題"),
    "answer_followup": ("Answer follow-up", "回答追问", "回答追問"),
    "end": ("End & summarize", "结束并总结", "結束並總結"),
    "ended": ("Practice complete", "练习已结束", "練習已結束"),
    "summary": ("Practice summary", "练习总结", "練習總結"),
    "practice_priorities": ("Practice priorities", "优先练习项", "優先練習項"),
    "next_steps": ("Next steps", "下一步行动", "下一步行動"),
    "no_answers": ("No answers submitted; no performance summary was generated.", "尚未提交回答，未生成表现总结。", "尚未提交回答，未產生表現總結。"),
    "restart": ("New interview", "开始新面试", "開始新面試"),
    "history": ("Practice history · {n} answers", "练习记录 · {n} 次回答", "練習紀錄 · {n} 次回答"),
    "download_interview": ("Download practice", "下载练习记录", "下載練習紀錄"),
    "source_context": ("Shared source context", "共享资料来源", "共用資料來源"),
    "source_note": ("Check the extracted requirements against the original JD. Edit your materials to correct any omissions.", "请对照 JD 核查提取的要求；如有遗漏，可修改材料后重新分析。", "請對照職位描述核查擷取的要求；如有遺漏，可修改材料後重新分析。"),
    "manual_check": ("Review AI suggestions against your source materials before use.", "采用 AI 建议前，请自行核对原始材料。", "採用 AI 建議前，請自行核對原始材料。"),
    "old_language": ("Saved result: {language}. Regenerate to use {current}.", "已有结果语言：{language}。可重新生成{current}结果。", "已有結果語言：{language}。可重新產生{current}結果。"),
    "regenerate": ("Regenerate in {language}", "重新生成{language}结果", "重新產生{language}結果"),
    "interview_language": ("Saved interview content stays in its original language; new questions and feedback use {language}.", "已保存的面试内容保留原语言；新问题和反馈使用{language}。", "已儲存的面試內容保留原語言；新問題和回饋使用{language}。"),
    "retained": ("Saved content retained", "已保留原有内容", "已保留原有內容"),
    "question_limit": ("30 answers reached. End the interview to see your summary.", "已达 30 次回答上限，请结束并查看总结。", "已達 30 次回答上限，請結束並查看總結。"),
}

INDEX = {"en": 0, "zh-CN": 1, "zh-TW": 2}


def tr(key: str, lang: str = "en", **values) -> str:
    return STRINGS[key][INDEX[lang]].format(**values)


def language_name(code: str, ui_language: str) -> str:
    names = {"en": ("English", "英文", "英文"), "zh-CN": ("Simplified Chinese", "简体中文", "簡體中文"), "zh-TW": ("Traditional Chinese", "繁体中文", "繁體中文")}
    return names[code][INDEX[ui_language]]


# Backend error contracts are adapted at the UI boundary; parsing, SDK and guard logic stay unchanged.
ERRORS = {
    "配置无效：超时须为 5–180 秒，输出 token 上限须为 1000–32000。": ("Invalid configuration: timeout must be 5–180 seconds and output tokens 1,000–32,000.", "設定無效：逾時須為 5–180 秒，輸出 token 上限須為 1,000–32,000。"),
    "AI 尚未连接。请在项目 .env 中设置 DEEPSEEK_API_KEY 后重试。": ("AI is not connected. Set DEEPSEEK_API_KEY in .env and retry.", "AI 尚未連線。請在專案 .env 中設定 DEEPSEEK_API_KEY 後重試。"),
    "模型未返回完整的结构化结果（可能拒答或达到输出上限）。请精简材料后重试。": ("The model did not return a complete structured result. It may have refused or reached its output limit. Shorten your materials and retry.", "模型未傳回完整結構化結果，可能拒答或達到輸出上限。請精簡材料後重試。"),
    "API 身份验证失败，请检查 .env 中的 API Key。": ("API authentication failed. Check the API key in .env.", "API 身分驗證失敗，請檢查 .env 中的金鑰。"),
    "API 配额不足或请求过于频繁，请检查账户额度或稍后重试。": ("API quota exceeded or rate limited. Check your account credit or retry later.", "API 額度不足或請求過於頻繁，請檢查帳戶額度或稍後重試。"),
    "AI 请求超时，当前操作尚未提交。请重试或缩短输入。": ("The AI request timed out. Your action was not committed. Retry or shorten the input.", "AI 請求逾時，本次操作尚未提交。請重試或縮短輸入。"),
    "无法连接 AI 服务，请检查网络连接后重试。": ("Could not reach the AI service. Check your network and retry.", "無法連接 AI 服務，請檢查網路後重試。"),
    "API 未接受请求，请检查模型名称及其 Structured Outputs 支持，或精简材料。": ("The API rejected this request. Check the model and its Structured Outputs support, or shorten the input.", "API 未接受請求，請檢查模型名稱及結構化輸出支援，或精簡材料。"),
    "模型输出格式未通过校验，结果未展示，请重新分析。": ("The model output failed format validation and was withheld. Analyze again.", "模型輸出格式未通過驗證，結果未顯示，請重新分析。"),
    "AI 服务暂时不可用，当前操作尚未提交，请稍后重试。": ("The AI service is temporarily unavailable. Your action was not committed. Retry later.", "AI 服務暫時無法使用，本次操作尚未提交，請稍後重試。"),
    "AI 响应无法处理，当前操作尚未提交，请重试。": ("The AI response could not be processed. Your action was not committed. Retry.", "AI 回應無法處理，本次操作尚未提交，請重試。"),
    "PDF 超过 10 MB，请压缩或粘贴简历正文。": ("PDF exceeds 10 MB. Compress it or paste the resume text.", "PDF 超過 10 MB，請壓縮或貼上履歷正文。"),
    "PDF 已加密，请上传未加密版本或粘贴文字。": ("This PDF is encrypted. Upload an unencrypted file or paste its text.", "PDF 已加密，請上傳未加密版本或貼上文字。"),
    "简历 PDF 最多支持 20 页，请精简材料。": ("Resume PDFs support up to 20 pages. Shorten the document.", "履歷 PDF 最多支援 20 頁，請精簡材料。"),
    "无法读取此 PDF。请检查文件是否损坏，或改用粘贴文字。": ("Could not read this PDF. Check for file corruption or paste its text.", "無法讀取此 PDF。請檢查檔案是否損壞，或改用貼上文字。"),
    "PDF 未提取到足够文字，可能是扫描件。此版本不含 OCR，请粘贴识别后的正文。": ("Not enough text could be extracted from this PDF. It may be scanned; OCR is not available. Paste recognized text instead.", "PDF 未擷取到足夠文字，可能為掃描件。此版本不含 OCR，請貼上辨識後的正文。"),
    "材料分段过多，请整理为较完整的经历段落或岗位条目后重试。": ("Too many source segments. Combine fragmented lines into complete experience or job requirement paragraphs.", "材料分段過多，請整理為較完整的經歷段落或職位條目後重試。"),
    "模型结果的来源核对未通过，结果已拦截。请重新分析。": ("Source verification failed. The result was withheld; analyze again.", "模型結果的來源核對未通過，結果已攔截。請重新分析。"),
    "未识别出可核对的岗位要求，请补充完整 JD。": ("No verifiable job requirements found. Add a complete job description.", "未辨識出可核對的職位要求，請補充完整職位描述。"),
    "模型没有逐项覆盖全部岗位要求，结果已拦截，请重新分析。": ("The model omitted job requirements. The result was withheld; analyze again.", "模型未逐項涵蓋全部職位要求，結果已攔截，請重新分析。"),
    "独立事实核查未完整返回结果，本次输出已拦截，请重试。": ("The independent fact check was incomplete. Output was withheld; retry.", "獨立事實核查未完整傳回結果，本次輸出已攔截，請重試。"),
    "独立事实核查未通过，本次结果未展示，请重试或补充材料。": ("The independent fact check failed. Results were withheld; retry or add supporting evidence.", "獨立事實核查未通過，本次結果未顯示，請重試或補充材料。"),
    "本次练习已达 30 次回答上限，请结束并生成总结。": ("This interview reached 30 answers. End it to generate a summary.", "本次練習已達 30 次回答上限，請結束並產生總結。"),
    "请先输入你的真实回答。": ("Enter your answer first.", "請先輸入你的真實回答。"),
    "单次回答最多 8,000 字符，请精简后提交。": ("Answers support up to 8,000 characters. Shorten it and submit again.", "單次回答最多 8,000 字元，請精簡後提交。"),
    "还没有完成的回答，请至少提交一次回答后生成总结。": ("Submit at least one answer before requesting a practice summary.", "尚無已完成的回答，請至少提交一次回答後產生總結。"),
    "知识库最多加载 100 个文件，其余文件未载入。": ("Up to 100 knowledge files can be loaded; additional files were skipped.", "知識庫最多載入 100 個檔案，其餘檔案未載入。"),
}


def localize_error(message: str, lang: str) -> str:
    if lang == "zh-CN":
        return message
    idx = 0 if lang == "en" else 1
    if message in ERRORS:
        return ERRORS[message][idx]
    if message.startswith("材料未通过 AI 完整性检查："):
        issues = message.split("：", 1)[1]
        fallback = "请补充真实简历及完整岗位要求。"
        if fallback in issues:
            issues = "Add a real resume and complete job requirements." if lang == "en" else "請補充真實履歷及完整職位要求。"
        return ("Material validation failed: " if lang == "en" else "材料未通過 AI 完整性檢查：") + issues
    match = re.fullmatch(r"(.+)内容不足，请提供至少 30 个非空白字符的真实经历或岗位要求。", message)
    if match:
        field = tr("jd" if match[1] in {"JD", "岗位描述"} else "resume", lang)
        return f"{field}: provide at least 30 non-whitespace characters." if lang == "en" else f"{field}內容不足，請提供至少 30 個非空白字元。"
    match = re.fullmatch(r"(.+)超过 ([\d,]+) 字符，请精简后重试；系统不会静默截断材料。", message)
    if match:
        field = tr("jd" if match[1] == "JD" else "resume", lang)
        return f"{field} exceeds {match[2]} characters. Shorten it and retry." if lang == "en" else f"{field}超過 {match[2]} 字元，請精簡後重試。"
    match = re.fullmatch(r"无法读取知识文件：(.+)（请检查格式、编码或大小）。", message)
    if match:
        return f"Cannot read guide: {match[1]}. Check its format, encoding or size." if lang == "en" else f"無法讀取知識檔案：{match[1]}，請檢查格式、編碼或大小。"
    return tr("error_generic", lang)
