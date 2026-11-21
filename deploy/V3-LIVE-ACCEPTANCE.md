# V3 Render 人工验收入口

最新增量：JD 链接导入修复 `bbe78f0` 已上线，详见 [修复与线上验收](V3-JD-IMPORT-AUDIT.md)。以下保留最初 V3 发布记录。

用户于 2026-11-22 明确授权部署后，V3 已发布到现有 Render 服务，在原站点新增独立 `/v3/` 入口。

- 验收地址：https://ai-career-coach-three-versions.onrender.com/v3/
- Render 服务：`srv-dc0k9cm7bikc73b2iqug`
- 部署：`dep-dc0u1hl9el5s73f7l6m0`
- 已部署源码：`f21d062f8e6c05c851403c142970b9e3ca74d935`
- 分支：`codex/v3-career-audit`
- Render 显示 Live，构建与上线耗时 1 分 40 秒，上线时间为香港时间 2026-11-22 02:21:30。

本次采用现有服务新增版本的方式，没有创建新付费资源，没有应用 `render.yaml` 中的独立 preview Blueprint。既有自动部署仍关闭。V1/Claude 保留原 Docker 源码固定提交，V2 固定在存档提交 b176ccc。发布前后 V1、V2、Claude 的 HTML、JS/CSS 资源名称逐一相同；未登录接口仍返回 401。

Supabase 保留原 Site URL 和原有三个版本的重定向配置，仅新增两个同源精确回调：`/v3/auth/callback` 与 `/v3/auth/callback?mode=recovery`。没有更改密码、API Key、数据库结构或每日 10 次模型调用规则。

已完成线上检查：

1. 四版本 health、HTML、JS/CSS 与未登录访问保护。
2. 独立既有 QA 邮箱账号真实登录，V3 工作台和项目恢复。
3. 真实私有 Storage 上传三页虚构简历，下载字节与原文件一致。
4. 将此前实际 DeepSeek 测试的真实输出复制到该 QA 账号的独立验收项目，不使用模拟 AI 建议，也不额外消耗模型调用。完整简历预览和两种二进制导出均通过。
5. 浏览器实际点击 PDF/DOCX 下载；本地下载文件均存在，PDF 包含末尾原文标记，DOCX 全文与导出 API 一致。
6. 发布前后该 QA 账号其他三个版本的项目目录保持不变。用户的真实项目未作测试写入。
7. 测试账号已退出，验收页停留在 V3 首页。用户可以使用原邮箱登录；V3 项目库独立，V2 原项目仍在 `/v2/`。

本次没有重测真实注册验证邮件或密码重置邮件的投递，也没有在 Render 上重复调用 DeepSeek；其现有配置已确认存在。原审计报告中的“未部署”描述属于部署前记录，以本文件为最新部署状态。

本地证据在 `tests/evidence/hosted-deployment-smoke.json`、`hosted-auth-storage-export.json`、`hosted-browser-downloads.json`、`hosted-v3-preview.jpg` 和 `hosted-v3-home.jpg`；这些文件不推送到公开仓库。
