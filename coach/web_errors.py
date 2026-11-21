from coach.i18n import ERRORS, LANGUAGES, localize_error
from coach.job_links import INVALID, UNREADABLE, UNSUPPORTED, TOO_LARGE

MESSAGES = {
    "余额不足，请充值后重启服务。": ("Insufficient balance. Top up and restart the service.", "餘額不足，請充值後重啟服務。"),
    "输入过长，请精简材料或面试记录。": ("Shorten the materials or interview history.", "輸入過長，請精簡材料或面試記錄。"),
    INVALID: ("Enter a public HTTP or HTTPS job posting URL.", "請輸入可公開存取的 HTTP 或 HTTPS 職位連結。"),
    UNREADABLE: ("Could not read this posting. Check the URL or paste the job description.", "無法讀取職位網頁。請檢查連結，或貼上職位描述。"),
    UNSUPPORTED: ("No readable job description found. Paste the responsibilities and qualifications.", "未找到可讀取的職位說明。請貼上職責與任職要求。"),
    TOO_LARGE: ("This page is too large. Paste the job description instead.", "職位網頁過大，請直接貼上職位描述。"),
    "请填写目标岗位名称。": ("Enter a target role.", "請填寫目標職位名稱。"),
    "请提供可读的经历和岗位要求。": ("Provide readable experience and job requirements.", "請提供可讀的經歷與職位要求。"),
    "项目已过期，请重新创建。": ("Your project session expired. Create a new project.", "專案已過期，請重新建立。"),
    "请刷新页面以加载最新状态。": ("Refresh to load the current project state.", "請重新整理頁面以載入最新狀態。"),
    "当前面试阶段无法执行此操作。": ("This action is unavailable at this interview stage.", "目前面試階段無法執行此操作。"),
    "请检查输入内容及长度。": ("Check the input and its length.", "請檢查輸入內容及長度。"),
    "当前项目数量已满，请稍后重试。": ("The local server is at capacity. Try again later.", "目前專案數量已滿，請稍後重試。"),
}
ERRORS.update(MESSAGES)


def translations(message):
    return {lang: localize_error(message, lang) for lang in LANGUAGES}

