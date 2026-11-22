# V3 注册验证邮件排查与恢复

2026-11-22 排查结果：真实邮件已经由 Supabase 经现有 Brevo SMTP 发出。请求者自己的 Gmail 中找到对应验证邮件，标签为 UNREAD、SPAM、CATEGORY_UPDATES；已仅将这一封邮件移回 INBOX，保留未读。没有打开验证链接或代替用户确认账户。

另一个接近时间的 Gmail 确认邮件在 Brevo 同样显示 Delivered，但不知道是否属于反馈同学，也无法检查其邮箱分类，不能声称他的具体问题已经得到验证或修复。

## 实际检查

- 自定义 SMTP 已启用，现有主机 smtp-relay.brevo.com:587；发件人名称 AI Career Coach；凭据未修改或输出。
- Brevo 最近相关邮件均为 Sent、Delivered，没有出现发送额度耗尽或该请求的退信记录。
- 认证数据库的 confirmation_sent_at 与投递记录对应，待确认账户尚未验证。
- 原邮件主题为 Confirm your email address。Delivered 表示接收邮件服务器接收，不保证主收件箱；请求者的 Gmail SPAM 标签是本次分类问题的直接证据。
- V3 验证和密码恢复回跳 URL 已在 Supabase 白名单中；未修改全局 Site URL、邮箱确认要求或旧版白名单。
- Gmail 原邮件已确认包含 INBOX、不再包含 SPAM，仍为 UNREAD。未创建全局过滤器，也未操作同学的邮箱。

## V3 代码修复

- 注册成功或登录提示未验证时，增加“重新发送验证邮件”入口。
- 使用现有 Supabase SDK auth.resend(type=signup)，正确传递当前 V3 auth/callback；不需要服务端密钥。
- 显示待验证邮箱、真实邮件主题、垃圾邮件/促销分类提示，以及使用最新链接的提醒。
- 初次成功请求及重发后显示 60 秒倒计时，防重复点击。保留服务端限流，没有放宽 SMTP 或认证安全限制。
- 503、网络故障和 429 显示发送失败/频率限制，允许恢复；不会保留错误的成功提示。
- 成功文案仅表示请求提交，并保留服务方防账号枚举语义，不声称已投递或已验证。
- 简体中文、繁体中文、英文全部支持。未修改 V1/V2、AI 调用规则、模型或 RAG。

文件：frontend/src/cloud.tsx、frontend/src/cloud.css、tests/auth_verification_e2e.py、tests/run_audit.py。

## 验证范围

- TypeScript、Vite 构建通过。
- 52 项后端测试通过。
- 原有浏览器完整回归通过。
- 新浏览器用例：注册后恢复入口、未验证登录恢复入口、SDK 参数和 V3 回跳、60 秒倒计时、快速双击仅一次请求、503 无假成功且可重试、429、修改邮箱取消旧恢复入口、三语言通过。
- 新增重发 UI 测试的 Supabase 响应明确 Mock，没有发送测试邮件。实际邮件投递和 Gmail 分类由原始真实注册邮件验证；为避免使用户当前验证链接失效，没有自动对真实账户再次重发或重置密码。

命令：

```sh
QA_DATABASE_URL=postgresql://postgres@127.0.0.1:28547/coachtest_v3_audit_utf8_20261122 python tests/run_audit.py auth_verification_e2e.py e2e_audit.py
QA_MAIL_HOSTED=1 python tests/auth_verification_e2e.py
```

参考：https://supabase.com/docs/reference/javascript/auth-resend

## 部署

本轮按现有 Render 服务发布；线上页面的浏览器重发交互使用明确拦截的模拟 Auth 响应验证，以免向真实用户重复发送邮件。实际部署提交与结果见 Git 和 Render 发布记录。

## 边界

此修复补齐恢复入口并纠正用户提示，不会控制 Gmail 或其他邮箱的垃圾邮件分类。用户仍应检查垃圾邮件并使用最新的验证链接。若要验证某位同学的确切投递问题，需要其具体注册记录；本次没有索取密码、验证码，也没有放弃或绕过邮箱验证。
