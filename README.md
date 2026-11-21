# AI Career Coach GPT V3

V3 从 V2 提交 `b176cccb5121b783d7a163fafc9a7ae30218275c` 独立开发，分支为 `codex/v3-career-audit`。V2 代码已恢复并存档，V1 与 Claude 未修改。本版本尚未推送或部署到 Render。

本轮补齐了逐条审核到完整简历的确定性合成、在线全文预览、PDF/DOCX 导出，并修复过期结果恢复入口、分析快照、保存失败恢复及语言持久化。原始上传 PDF 和简历输入不会被优化流程覆盖。

- [完整审计报告](deploy/V3-AUDIT-REPORT.md)
- [测试方法和证据](tests/README.md)
- [V3 部署注意事项](deploy/V3-DEPLOYMENT.md)

需要 Node 22（含 npm）及 Python 3.11+。在本目录运行 `./start.sh`，本地入口为 `http://127.0.0.1:8113/v3/`，不占用 V2 默认端口。前端构建默认 base 为 `/v3/`。前端热更新服务端口为 5174，代理到 8113；需要先启动后端。

沿用已有私有 DeepSeek 与 Supabase 配置，不要把凭证写入仓库。V3 使用独立 `codex_v3` 数据命名空间和认证缓存；不会自动复制、修改或删除 V2 的项目。所有版本仍按同一账户共享每天 10 次模型调用额度。原有正式 Prompt/RAG 接入工作未在本轮进行。
