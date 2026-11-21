import type { Lang, Strings } from "./types";
export const langs: Record<Lang, string> = {
  en: "English",
  "zh-CN": "简体中文",
  "zh-TW": "繁體中文",
};
export const index = { en: 0, "zh-CN": 1, "zh-TW": 2 };
export function languageName(saved: Lang, current: Lang) {
  const names = {
    en: ["English", "英文", "英文"],
    "zh-CN": ["Simplified Chinese", "简体中文", "簡體中文"],
    "zh-TW": ["Traditional Chinese", "繁体中文", "繁體中文"],
  };
  return names[saved][index[current]];
}
const entries = `
university|City University of Hong Kong|香港城市大学|香港城市大學
forStudents|For university students|大学生求职工作台|大學生求職工作台
headlineA|Your AI|你的 AI|你的 AI
headlineB|career coach.|求职教练。|求職教練。
intro|Turn your resume and a target role into a focused plan for your next application.|从一份简历和一个目标岗位出发，为下一次求职做好准备。|從一份履歷和一個目標職位出發，為下一次求職做好準備。
getStarted|Get started|开始使用|開始使用
desk|Career workspace|求职工作台|求職工作台
materialsHeading|Your materials|求职材料|求職資料
sourceMaterials|Source documents|分析材料|分析資料
aiWorkspace|AI workspace|AI 工作区|AI 工作區
collapseMaterials|Collapse materials|收起材料区|收合資料區
showMaterials|Show materials|展开材料区|展開資料區
pdfLimit|PDF · 10 MB max|PDF · 最大 10 MB|PDF · 上限 10 MB
jdTypes|Responsibilities & qualifications|职责与任职条件|職責與任職條件
importShort|Import|导入|匯入
incompleteMaterials|More material needed|材料待补充|資料待補充
awaitingMaterials|Awaiting materials|等待输入材料|等待輸入資料
lengthHint|Each document needs at least 30 non-space characters of readable text.|每份材料至少需要 30 个非空白字符的可读正文。|每份資料至少需要 30 個非空白字元的可讀正文。
awaitResume|Add your experience and skills|添加你的经历与技能|加入你的經歷與技能
awaitJd|Add the responsibilities and qualifications|添加岗位职责与任职条件|加入職位職責與任職條件
materialsChanged|Materials have changed. Analyze again to update your results and start a fresh interview.|材料已修改。重新分析后将更新结果并重置面试记录。|資料已修改。重新分析後將更新結果並重設面試記錄。
viewInterview|View interview|查看本次面试|查看本次面試
sessionHeading|Current session|当前会话|目前工作階段
sessionPrivacy|Materials and results are saved to your private Claude workspace.|材料和结果保存在你的 Claude 私人工作区。|資料與結果儲存在你的 Claude 私人工作區。
clearWorkspace|Clear workspace|清空工作台|清空工作台
clearWorkspaceConfirm|Clear all materials, results and interview answers from this session?|清除本次会话的所有材料、分析结果和面试回答？|清除本次工作階段的所有資料、分析結果及面試回答？
expiredRetry|The session expired. Your inputs are still here. Run the analysis again.|会话已过期，输入的材料仍在。请重新分析。|工作階段已過期，輸入的資料仍在。請重新分析。
project|Career project|求职项目|求職專案
tools|Inside your workspace|工作区功能|工作區功能
optDesc|Refine your writing with side-by-side revisions grounded in your experience.|逐条对照原文，写清真实经历。|逐項對照原文，寫清真實經歷。
matchDesc|See which role requirements your resume supports and where to add evidence.|逐项核对岗位要求，找出可补充的证据。|逐項核對職位要求，找出可補充的證據。
ivDesc|Practise role-specific questions with feedback on your own answers.|围绕目标岗位练习，根据实际回答获得反馈。|圍繞目標職位練習，根據實際回答取得回饋。
home|Home|首页|首頁
cancel|Cancel|取消|取消
save|Save changes|保存修改|儲存變更
pdfDone|Text extracted|已提取正文|已擷取正文
linkMode|Import a link|链接导入|連結匯入
publicLink|Public job posting URL|公开岗位链接|公開職位連結
import|Import posting|提取岗位描述|擷取職位描述
imported|Imported from|内容来源|內容來源
minChars|Include at least 30 non-whitespace characters of readable material.|请提供至少 30 个非空白字符的可读材料。|請提供至少 30 個非空白字元的可讀資料。
readable|Readable material required.|请提供可读的正文。|請提供可讀的正文。
characters|{n} characters|{n} 个字符|{n} 個字元
checking|Checking materials…|正在核对材料…|正在核對資料…
readPdf|Reading PDF…|正在读取 PDF…|正在讀取 PDF…
loadingLink|Reading job posting…|正在提取网页…|正在擷取網頁…
pdfSize|Choose a PDF of 10 MB or less.|请选择不超过 10 MB 的 PDF。|請選擇不超過 10 MB 的 PDF。
pdfType|Choose a PDF file or paste your resume text.|请选择 PDF 文件或粘贴简历。|請選擇 PDF 檔案或貼上履歷。
overview|Workspace|工作空间|工作空間
navigation|Navigation|导航|導覽
openMenu|Open navigation|打开导航栏|開啟導覽列
close|Close|关闭|關閉
originals|Source documents|原始资料|原始資料
sourceResume|Original resume|简历原文|履歷原文
sourceJd|Original job description|岗位描述原文|職位描述原文
revisions|Revisions|改写建议|改寫建議
verifiedMaterials|Sources verified|已核对来源|已核對來源
startOpt|Analyze resume|分析简历|分析履歷
startMatch|Compare requirements|分析岗位要求|分析職位要求
optReady|Review your resume against this role|对照目标岗位审阅简历|對照目標職位審閱履歷
matchReady|Find evidence for each requirement|逐项查找岗位证据|逐項尋找職位證據
ivReady|Prepare for your interview|准备岗位面试|準備職位面試
runOptNote|Compare the original wording with a suggested revision, then choose what to keep.|对照原文与改写建议，逐条决定是否采用。|對照原文與改寫建議，逐項決定是否採用。
runMatchNote|Compare responsibilities and qualifications with specific passages in your resume.|将岗位职责与任职条件逐条对应到简历原文。|將職位職責與任職條件逐項對應至履歷原文。
runIvNote|Answer one question at a time and practise a more specific response with follow-up feedback.|一次练习一道岗位问题，根据反馈和追问完善回答。|每次練習一道職位問題，根據回饋及追問完善回答。
keep|Keep original|保留原句|保留原句
edit|Edit revision|编辑改写|編輯改寫
adopted|Adopted|已采用|已採用
kept|Original kept|已保留原句|已保留原句
edited|Edited by you|已手动修改|已手動修改
editText|Your revision|你修改的版本|你修改的版本
verifiedSource|View source passages|查看原文出处|查看原文出處
priorities|Priority requirements|优先处理的要求|優先處理的要求
noPriorities|All listed requirements have direct evidence.|所列要求均有直接证据。|所列要求均有直接證據。
originalAnswer|Submitted answer|已提交的回答|已提交的回答
configuration|Model connection|模型连接|模型連線
knowledge|School guides|学校辅导指南|學校輔導指南
refresh|Refresh status|刷新状态|重新整理狀態
comingNext|Next question and feedback will use the selected language.|后续提问与反馈将使用当前语言。|後續提問與回饋將使用目前語言。
retryLoad|Retry|重试|重試
modelNotice|Configure DEEPSEEK_API_KEY in the server’s .env to enable analysis.|请在服务端 .env 配置 DEEPSEEK_API_KEY 以启用分析。|請於伺服器 .env 設定 DEEPSEEK_API_KEY 以啟用分析。
privacyShort|AI actions send the project materials and relevant answers to DeepSeek.|AI 操作会将项目材料和相关回答发送至 DeepSeek。|AI 操作會將專案資料及相關回答傳送至 DeepSeek。
read|Read|已读取|已讀取
uploaded|Uploaded PDF|已上传的 PDF|已上傳的 PDF
pasted|Pasted text|粘贴的文本|貼上的文字
allSources|Source passages|原文片段|原文片段
reviewItems|Review items|优化项目列表|優化項目清單
prevItem|Previous item|上一项|上一項
nextItem|Next item|下一项|下一項
notAnalyzed|Ready for analysis|待分析|待分析
scaffold|University career workspace|大学生求职工作台|大學生求職工作台
notStarted|Ready to practise|待练习|待練習
complete|Results available|已有结果|已有結果
inProgress|In progress|进行中|進行中
submitted|Saved|已保存|已儲存
reviewLang|Saved in {language}. Analyze again to generate in the selected language.|已保存{language}结果。可重新分析以使用当前语言。|已儲存{language}結果。可重新分析以使用目前語言。
openResult|Open|打开|開啟
menuGroup|Coaching tools|辅导工具|輔導工具
checkFields|Check your inputs.|请检查输入。|請檢查輸入。
networkError|Could not reach the local server. Restart it and retry.|无法连接本地服务，请重新启动后重试。|無法連接本機服務，請重新啟動後重試。
`
  .trim()
  .split("\n");
export const ui: Strings = Object.fromEntries(
  entries.map((row) => {
    const [k, ...v] = row.split("|");
    return [k, v];
  }),
);
