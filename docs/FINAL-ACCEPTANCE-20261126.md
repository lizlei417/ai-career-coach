# AI Career Coach 统一版本最终验收与发布记录

日期：2026-11-26，Asia/Hong_Kong。用户已确认 Render My Workspace，并明确授权关键验收通过后合并 main、更新现有 Render 服务；不改 UI、不新增功能、不归档或删除原 Claude 仓库。

本记录描述发布前验收证据。**实际发布 commit、Render deploy ID 与发布后检查结果记录在发布成功后创建的 Git annotated tag `release/unified-20261126` 中**，可用 `git show release/unified-20261126` 查看；没有该标签不应推断发布已经完成。初始阶段报告保留为时间点记录，不代表当前状态。

## Render 来源及回滚检查

- 已通过 Render MCP 核实 My Workspace（tea-dc0k7hu1egvs73876u00）。
- 原服务：ai-career-coach-three-versions，srv-dc0k9cm7bikc73b2iqug，Singapore，Docker Free，无新增服务。
- 原仓库：https://github.com/lizlei417/ai-career-coach-codex 。原部署分支 codex/v3-career-audit，实际 live commit `9bc2fcda32d830dde654969c1a590c7f9bcc6e31`，deploy ID `dep-dc2an1h7lnhs739qs8cg`。自动部署 Off，Dockerfile ./Dockerfile，context .，health /healthz。
- 正式来源为同一仓库的 main，保留手动部署和全部既有环境变量。域名仍为 https://ai-career-coach-three-versions.onrender.com 。入口 /v1/、/v2/、/v3/、/v4/、/claude/，根跳转 /v3/ 均保留。
- 回滚优先使用上述旧 live deploy 的保留 artifact；若超出 Render artifact 保留期，则从 `archive/codex/release/v4-on-existing-render-20261124` 的 9bc2fcd 重建。回滚不回滚数据库；本次无 schema、RLS、Storage namespace 或数据迁移，旧应用与现有数据兼容。确认 Auto-Deploy 仍 Off。
- 切换只改现有服务的 branch，不提交 environment 修改，不 Apply 旧 render.yaml，不改计划、域名或资源。部署失败时保留旧服务；发布后关键回归失败则回滚旧 artifact，并恢复分支。

Render 当前部署、健康检查与回滚语义已对照 [Deploys](https://render.com/docs/deploys)、[Health checks](https://render.com/docs/health-checks)、[Rollbacks](https://render.com/docs/rollbacks)；artifact 不能当作数据库备份。

## Docker 与后端检查

- 本次新建隔离 Lima Linux 测试 VM，未触及生产主机；Docker 29.10.1、BuildKit。
- linux/arm64 Docker 构建、非 root coach 用户运行、五版首页/healthz 200、匿名 /api/workspaces 401，全部通过。
- linux/amd64 最终镜像构建和启动、同样五版路由及授权检查通过。首次跨架构仿真遇到 exec-format 与 esbuild Go lfstack 崩溃，属于测试工具架构问题；采用 Docker 官方 BUILDPLATFORM 原生构建前端、目标架构 Python 运行层后解决。没有升级 Vite/esbuild、没有改动 UI。
- Docker 前端构建循环改为 set -eu：任一版本失败即终止，防止循环掩盖早期失败。排除所有 tests/evidence，避免测试 trace 进入构建上下文。
- 根 Dockerfile 只 COPY 当前 checkout 的源码，无 git clone、submodule 或旧 Claude 远端依赖。旧版本的 Dockerfile/render.yaml 仅为历史快照，不是活动入口。
- 五版后端测试：V1 7、V2 7、V3 52、V4 58、Claude 3，共 127 项。独立 Python 环境及 Linux 容器内通过；不以编译成功代替运行验收。

复现：`docker build --platform linux/amd64 -t career-coach-unified .`，启动时保持原生产 env；无密钥的 smoke 只测首页/healthz/匿名拒绝。真实密钥不得放 Docker build ARG、镜像层或仓库。

## 浏览器回归检查

| 范围 | 内容 | 结果 |
|---|---|---|
| V4 深度 | e2e_races、api_integration、e2e_audit、m3_interview、profile_recovery、exploration、review_report、resume_documents、auth_verification | 9 组通过 |
| V3 深度 | races、API isolation/quota、主业务 E2E、M3 interview、profile recovery、resume documents | 6 组通过 |
| 五版真实 Auth | 两个新建专用测试账户之一登录；材料编辑/保存/刷新恢复；全部模块导航；简/繁/英切换；390px 与桌面渲染；JS page errors | 五版通过，无 page error |
| V4 真实 DeepSeek | prepare、match、optimize 三个业务 HTTP 请求；建议采用/保留；PDF/DOCX 全内容；刷新恢复 | 完整通过，实际 provider 次数由 quota ledger 单独记录 |

深度套件采用真实的一次性 UTF8 PostgreSQL、真实应用 API、合成 Auth/Storage 和确定性模型传输；不能把这些模拟组件描述为真实 Supabase。真实 Supabase 与真实模型验收另列如下。上述范围覆盖本次结构与部署变更的关键路径，不声称穷尽所有浏览器/输入组合。移动渲染测试没有重设计旧版本桌面布局。

本次修正了真实模型验收脚本中的旧假设：没有 grounded 建议时验证“保留原句”，不强行采用；先关闭格式预览对话框再下载；比较完整文字时忽略排版项目符号；分别记录业务 HTTP 请求与实际 provider attempts。并取消“打开预览必定新发 GET”的错误网络时序假设，验证无可展示建议时完整保留原文。业务实现未因此改变。

## 真实 Supabase 双用户隔离与持久化检查

- 通过现有 Supabase Admin API 新建两个 `is5542-unified-qa-...@example.test` 专用确认账户，不发送真实邮箱验证邮件，不使用已有用户的工作区进行写入。
- A/B 在同一版本使用同一测试项目 ID 保存不同标记，读回只得到自己的状态；五个 application namespace 互不串用。
- 各版上传新生成的虚构 PDF，经真实私有 Supabase Storage 写入后读取，字节完全一致；另一账户和其他四版读取均 404。仅删除本次新建的 PDF 对象以检查安全清理路径。
- 停止并重新启动本次本地统一网关，再次用真实 Supabase 验证五版原状态完整恢复。生产发布后重复相同验证，最终结果见 release tag receipt。
- 读写使用现有 owner/application RLS 和私有 Storage，没有执行任何生产迁移，没有重置配额，没有修改原有账户或项目。非测试账户的 projects/documents 内容摘要及 RLS 摘要在发布前后进行只读比较，摘要保存在仓库外私有验收目录。
- 测试账户与虚构项目保留供复验，凭据只在仓库外权限受限的验收目录，不提交。不存在覆盖 Claude 既有单一 workspace/draft 的风险，因为使用全新账户。

## DeepSeek 实际调用检查

- 五版 /api/settings/test 各一次真实请求成功；同一专用账户的 used 从 0 到 5，验证跨版本共享账本。
- V4 完整浏览器流程中的材料解析不必调用模型，不能把 3 个业务 HTTP 请求当成 3 次 provider 计费请求。最后一次干净流程的实际次数、结果和导出完整性见 final-acceptance-20261126/real-deepseek-workflow.json。
- 测试脚本修正过程中也发生了真实调用，所有请求都通过原有配额账本记录，没有为了通过测试重置或删除账本；没有业务代码自动重试或绕过配额。
- 发布后可用专用账户的剩余 5 次额度分别复验五版连接，不占用普通用户的账户额度。若 provider 失败，停止并诊断，不把 API 已接收请求当作成功。

## Vite/esbuild 安全告警的生产适用性

Codex 各版 audit 报告的高危/中危条目来自 Vite/esbuild 开发工具链。已核对 [esbuild 官方公告](https://github.com/evanw/esbuild/security/advisories/GHSA-67mh-4wv8-2f99) 和 [Vite 官方路径遍历公告](https://github.com/vitejs/vite/security/advisories/GHSA-4w7w-66w2-5vf9)：相关攻击需要运行开发服务器；其他 audit 子项涉及开发编辑器/Windows 等路径。

最终运行镜像只包含 Python 服务、业务源码和前端 dist，实查没有 node/npm、node_modules、Vite 或 esbuild。Render 运行 uvicorn 而非 Vite dev server，所以这些**已列出的开发服务器告警没有对应的生产运行路径**。这不是声称项目没有任何漏洞；本地开发服务器仍受影响，应保持 localhost、避免不可信网页和暴露开发端口，后续有独立任务再评估依赖升级。没有执行 npm audit fix --force，没有为本次整合跨大版本升级。

## Codex Project 与后续开发

现有 IS5542 Project 仍位于上层容器，根 AGENTS.md 强制默认进入 unified-career-coach；本次所有开发、构建、Git 操作都显式在统一目录执行。当前工具没有修改已有 Project 路径的接口，CUA 明确禁止操作 Codex 自身窗口，故没有改写应用内部状态文件来绕过限制。已请用户在同一个 Project 内修改目录或确认使用 AGENTS 导航；是否真正更新 Project 路径以实际 list_projects 核实为准。

后续从 origin/main 创建 codex/ 功能分支，默认改根 V4；只有明确请求才修改 versions/*。共享网关/Docker 变更必须复测五个入口。原始工作树、分支、备份均保留。

## Claude 独立仓库归档条件

主仓 main 包含完整 Claude 源码、合并父历史和 archive/claude/* 标签。活动的统一 Docker 构建/运行不访问原 Claude 仓库；旧文档和历史 Dockerfiles 中的 URL 是保留记录，不是当前依赖。

统一 main 在现有服务 live 且发布后五版验收通过后，原 Claude 独立仓库可以安全转为只读归档，历史链接仍可保留。本任务只报告是否具备条件，**不执行归档或删除**。最后确认结果记录在 release tag receipt 与本次任务最终答复中。

最终镜像候选的文件系统层和运行配置与已运行全部 amd64 测试的镜像完全相同，构建过程只有 provenance/attestation 元数据变化；详见 final-docker-runtime.json。五版构建 JS/CSS 均与切换前线上逐字节一致，详见 docker-versus-original-production-assets.json。
