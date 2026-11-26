# 版本同步与仓库整合验收 — 2026-11-26（香港）

> 本文记录第一阶段检查时的状态。后续生产验收与发布以 [最终验收记录](FINAL-ACCEPTANCE-20261126.md) 为准。

## 结论与审批边界

统一工作树 `unified-career-coach`，独立分支 `codex/unified-repository-20261126`，基于 GitHub V4 发布分支 `release/v4-on-existing-render-20261124` 的 `9bc2fcd`。没有修改生产分支、服务、数据库或原工作树。GitHub main 是历史演示版，不是功能最完整版本。Claude 原仓库没有被删除或归档。

## 本地、GitHub、Render 对照

| 版本 | 本地原工作树/分支与 commit | GitHub 核验 | Render 核验 |
|---|---|---|---|
| V1 | auth-v1 / codex/v1-shared-quota-dialogs / 6c7d74a | fetch 后与远端一致；另有未提交测试 | /v1/ 200；JS/CSS 与 6c7d74a 构建逐字节一致 |
| V2 | auth-v2 / codex/v2-projects-shared-quota / b176ccc | 与远端一致；另有同一测试修改 | /v2/ 200；JS/CSS 与 b176ccc 构建逐字节一致 |
| V3 | auth-v3 / codex/v3-career-audit / 495acc9 | 远端已到 9bc2fcd，本地落后 13 提交；分支名已不能代表版本 | Dockerfile 固定 9d9bc24；线上后端 commit 未验证 |
| V4 旧工作树 | auth-v4 / wip/claude-v4-handoff / fda132d | 已推送，但不含后续所有 UI 修复 | 不能据此视作线上最新版 |
| V4 配色工作树 | preview-chatgpt-v4 / preview/v4-assessment-colors / e47ebad | 对应 origin/fix/v4-assessment-preference-colors；已推送 | 与发布版仅 Dockerfile 固定 V3 的差异 |
| V4 发布源 | origin/release/v4-on-existing-render-20261124 / 9bc2fcd | 已实际 fetch；包含 e47ebad 全部功能祖先 | /v4/ 200，JS/CSS 与此版本构建逐字节一致；后端 commit、当前部署分支未验证 |
| Claude | auth-claude / codex/claude-shared-quota-dialogs / 4ef8832 | fetch 后与远端一致、工作树干净 | /claude/ 200；JS/CSS 与此版本构建逐字节一致 |
| Codex main | github-pages-release/ai-career-coach-codex / main / 5494181 | 与 origin/main 一致，早期 Pages 展示版 | 不是当前完整云端代码源 |
| Claude main | github-pages-release/ai-career-coach-claude / main / f971cea | 与 origin/main 一致，早期版本 | 不是目前认证/配额版源 |

Render 已知公开域名为 https://ai-career-coach-three-versions.onrender.com ，历史文档服务 ID 为 `srv-dc0k9cm7bikc73b2iqug`。只读公开 HTTP 与静态产物对比已完成。Render MCP 列出唯一 My Workspace，但尚未获得工作区确认，因此没有读取控制面服务/部署详情；**不能把前端文件一致推断为后端 commit 已验证**。历史 CLOUD-STATUS 的分支记录不是当前部署证据。

## 其余本地分支与目录

- codex-v2：feature/pdf-preview-project-management / aa88262；deepseek-v1：feature/deepseek-v1 / 4c6a2a2；deepseek-v2：feature/deepseek-v2 / 2272a26，均干净且与 fetch 后远端一致。
- deepseek-claude：feature/deepseek-api-integration / fdd1554，干净且与远端一致，是 Claude 认证版的历史路线。
- 其他无工作树分支和 commit 的完整保留清单在 versions/history-refs.json；两仓原提交对象通过 merge parent 与 archive/* 标签保留，不使用 submodule。
- 工作区顶层 .git 无提交，只是容器，不应把所有本地目录一起 git add。
- ai-career-coach 与 career-coach-codex 没有 .git。逐文件 Git blob 对比发现分别 13/32 个未匹配文件（包括文档、生成信息或图片），所以额外保留代码/文档快照到 archives/，原图和运行数据留在原处，不推送。它们不是已证实更完整的新版。
- Desktop/昼里/港城/Codebanana/ai-career-coach 的业务源文件与 ai-career-coach 相同；README.md、start.sh 不同，另存 archives/desktop-original/。backend/.env 存在差异但未读取内容或提交，不重复迁移业务源码。主目录按名称搜索到的其他 .config/ai-career-coach 是私密配置，不迁移。
- 搜索范围：/Users/zhouli 深度 5 的 career 名称目录，加上当前项目所有 worktree；无权限或更深层、其他磁盘/主机不能声称完全覆盖。

## 备份与迁移

迁移前在仓库外 backups/integration-20261126 保存两仓 `--all` bundle、V1/V2 二进制 patch、工作树状态清单。目录权限 700；不提交备份和本机环境。未清理或改动任何原目录。

整合前：Codex 各版在分支/工作树；Claude 在另一仓库；Dockerfile 构建时分别联网 clone 两仓。整合后：

```text
统一仓库根 frontend/ backend/   V4（保留原布局）
versions/v1/                   6c7d74a 快照 + 原未提交配额测试
versions/v2/                   b176ccc 快照 + 原未提交配额测试
versions/v3/                   9d9bc24（原 Docker 固定版本）
versions/claude/               4ef8832 完整 tracked 源码
archives/original-codex/       早期无 Git 源码存档
archives/original-claude/      早期无 Git 源码存档
deploy/                       网关、SQL、独立本地入口
```

主仓库没有既存 Claude 完整源码树，仅 Dockerfile 外部 clone；因此新增一次完整目录。迁移用 git archive，保留 tracked 源文件，不搬 node_modules、.env、真实数据。V1/V2 的测试差异覆盖未发送调用退款和预检不计费，已通过测试；没有业务实现差异。Docker 改用 COPY versions/*，一次 clone 后不依赖 Claude 远端。网关命名空间、根跳转、URL、Storage 与 RLS 都保留。

## V4 功能核验

| 项目 | 源码/提交证据 | 本次验证范围 |
|---|---|---|
| 五模块、顶部导航、工作台/项目库 | App.tsx、components/ProjectHost.tsx；8c35d29、878f030、18141d3、7899e98 | TypeScript/生产构建通过；未全量交互回归 |
| 职业测评八类配色 | explore/shared.ts、Report.tsx、explore.css；bbf7ffe、e47ebad | 源码包含八类及平衡结果，测评后端测试通过 |
| 偏好双色条 | Report.tsx 以 score 分割 linear-gradient，非固定 50% | 源码、构建；未逐一截图验收 |
| 面试回顾 | explore/Reviews.tsx、InterviewReport.tsx、后端探索接口 | 源码与离线后端测试 |
| 岗位匹配/查看 | explore/Discovery.tsx、views/MatchView.tsx、exploration.py | 去重、安全链接等测试；外部招聘站实时可用性不保证 |
| 页面动画 | 7af3d50、46cec53；App.tsx、index.css | 源码包含 reduced-motion；构建通过 |
| 简历编辑/保存/预览 | FinalResume.tsx、document-preview.ts、后端 final_resume | 编辑与文档后端测试；真实用户保存未执行 |
| 中英文 | lib/i18n.ts、useCopy、3f6cd20 | 源码与构建；不是所有文字人工复核 |
| Supabase 登录、隔离、持久化 | cloud.tsx、backend/app/cloud.py、deploy/001–003 | 认证边界单元测试、匿名 API 401；未重新跑真实云端双用户/RLS E2E |
| DeepSeek | backend/app/llm.py 和各版服务端模块 | 离线 transport mocks、错误及配额测试；本次无真实模型调用 |

上述 V4 提交是 9bc2fcd 的祖先，已在 GitHub；未发现这两处 V1/V2 测试以外的工作树未提交修改。最新日期/commit 不是唯一判断依据，已额外比较源码、祖先关系、测试和线上产物。

## 构建与运行测试

环境：独立 Node 22.16.0、Python 3.12 venv。首次使用应用内置 Node 因 macOS Team ID 原生模块限制失败；改用官方独立 Node 后全部通过，无项目依赖改动。最初测试启动目录不正确，调整为各 backend 后通过。

| 版本 | npm ci + TypeScript/Vite build | 后端 unittest | 共享网关首页/healthz | 未登录 /api/projects |
|---|---|---|---|---|
| V1 | 通过 /v1/ | 7/7 | 200/200 | 401 |
| V2 | 通过 /v2/ | 7/7 | 200/200 | 401 |
| V3 | 通过 /v3/ | 52/52 | 200/200 | 401 |
| V4 | 通过 /v4/ | 58/58 | 200/200 | 401 |
| Claude | 通过 /claude/ | 3/3 | 200/200 | 401 |

共 127 项后端测试。网关测试使用隔离 HOME，未加载现有云端密钥。V4 首轮网关测试发生在构建未结束时返回 404，全部构建结束后复验五版均通过。

公开 HTTP 五个入口（含 healthz）200；V1/V2/V4/Claude 共八个线上 JS/CSS 逐字节与本地构建相同。机器可读结果在 docs/audit-20261126/。

未验证：完整浏览器交互/视觉回归、Docker/Linux 镜像、Streamlit、生产 Supabase 双账户持久化与 Storage 删除、真实 DeepSeek 全业务流程、SMTP 回调及生产后端 commit。没有 Docker 引擎；不要把源码构建和 TestClient 测试描述为容器部署通过。

## 安全检查

- 939 个原历史对象经高置信模式扫描，未发现 DeepSeek sk-、长 Supabase secret、带密码 PostgreSQL URL 或私钥命中；迁移源码再次扫描无命中。扫描不是完整人工安全审计，不能保证不存在其他形式的敏感信息。
- 发现的 sb_secret_offline、offline-test-only 是测试占位值。现有真实 .config 密钥未打印、读取内容、复制或提交；未包含用户数据库/PDF/trace。
- 各 Codex 版本 npm audit：Vite/esbuild 共 1 high、1 moderate；Claude 前端 0。整合没有强制升级，需后续独立修复并回归。Python 依赖没有完成漏洞数据库审计。
- 历史文档曾要求轮换聊天中披露的 DeepSeek 凭据；其当前轮换状态无法验证。本次不修改任何生产密钥。

## 后续与 Claude 归档判断

源码和历史整合可以送审；生产合并与部署尚未进行。原 Claude 仓库**目前不建议立即归档**：旧生产 Dockerfile 仍引用它，且当前 Render 部署分支/commit 未确认。只有统一分支通过评审、现有服务按新 Dockerfile 部署、云端回归及历史标签远端核验完成后，才可归档为只读；无需删除，也不需要长期双仓维护。统一仓库默认 main 要在批准合并后才真正成为完整默认 clone 入口；在此之前请显式 clone 整合分支。

Codex 目前已有一个 IS5542 Project，路径是上层无提交容器；此次未创建第二个项目。建议后续将统一工作树设为该项目工作目录；现有工具未提供修改已有 Project 路径的能力。本地顶层导航 AGENTS 将指向统一工作树，避免后续 Agent 误改历史工作树。

差异格式检查发现历史快照中 6 个末尾空行和字体 OFL 许可证 1 处尾随空格；为保留原文件字节不清理，非新业务代码问题。

## 远端交付复核

整合提交 `616cc623f40c95aeb3f1ed5fca27fafbbce049df` 已推送到统一仓库的 `codex/unified-repository-20261126`，其父节点分别是 Codex `9bc2fcd` 和 Claude `4ef8832`。19 个 archive/* 标签已推送。重新从 GitHub 一次 clone 整合分支成功，git fsck --full 通过，Claude 历史祖先关系成立。逐文件比对：Claude、V3 与原 commit 全部 tracked 文件字节一致；V1/V2 只有已备份并测试通过的 backend/tests/test_deepseek.py 差异。

GitHub main 仍是 `5494181`，生产候选发布分支仍是 `9bc2fcd`。此后的文档补充提交不改变应用源码。

```sh
git clone --branch codex/unified-repository-20261126 https://github.com/lizlei417/ai-career-coach.git
```
