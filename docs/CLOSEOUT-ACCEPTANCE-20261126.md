# AI Career Coach 收尾验收报告

日期：2026-11-26，Asia/Hong_Kong。只读检查约 19:04–19:12；Render 控制台复核与旧仓库删除约 19:35–20:03。接手方为 Cursor。

本次没有改 UI、没有重新部署、没有调用 DeepSeek、没有登录业务测试账户、没有写入生产数据库、没有切换分支，也没有清理工作区。用户在控制台复核通过后，明确同意永久删除旧 Claude 独立仓库并接受旧演示站失效。删除已完成。

## 结论

统一仓库、五个线上入口和新的 GitHub Pages 演示站正常。正式部署仍是 `ec4fe4c`。公开站点的页面、静态资源和登录界面与更名前的验收产物一致。

`lizlei417/ai-career-coach-claude` 已于 2026-11-26 20:03 左右永久删除。删除后 API 与仓库页面返回 404，旧演示站 https://lizlei417.github.io/ai-career-coach-claude/ 也返回 404。Render 的 `/claude/` 仍返回 200，健康检查仍包含 `claude`。统一仓库 `lizlei417/ai-career-coach` 仍在。

## 版本对照

| 位置 | 结果 |
|---|---|
| 本地正式目录 | `/Users/zhouli/Documents/ChatGPT/IS5542/unified-career-coach` |
| 本地分支 | `codex/repository-rename-20261126`，与 `origin/main`、`origin/codex/repository-rename-20261126` 指向同一提交 |
| 本地与 GitHub `main` | `ec4fe4c8eb2ec208478fb11f581cfcf5d055ec85`，2026-11-26 17:58:40 +0800，`Rename canonical repository links and preserve Pages deployment paths` |
| 远端 | `https://github.com/lizlei417/ai-career-coach.git` |
| 仓库名与简介 | `lizlei417/ai-career-coach`；`IS5542 — AI Career Coach | Unified Repository (Codex & Claude)` |
| 仓库 ID | `1465800290`。旧地址 `ai-career-coach-codex` 返回 301，落到同一仓库，说明这是重命名而不是新建仓库 |
| 默认分支 | `main`，公开仓库，未归档 |
| 更名标签 | `maintenance/repository-rename-20261126`，对象 `b7c09ae`，指向 `ec4fe4c` |
| 统一发布标签 | `release/unified-20261126`，对象 `ae4d59f`，业务提交 `30e7ffb` |
| Render 控制台复核 | 2026-11-26 约 19:35，用户登录后直接查看。服务 `ai-career-coach-three-versions`，ID `srv-dc0k9cm7bikc73b2iqug`，Docker、Free、Singapore。来源 `lizlei417/ai-career-coach`，分支 `main`，Live commit `ec4fe4c`，deploy `dep-dc4065m1egvs73ev1p70`。Dockerfile `./Dockerfile`，context `.`，健康检查 `/healthz`，自动部署 Off，维护模式关闭。工作区只有这一个服务，没有 Blueprint 实例 |
| 本次公开探测 | `/healthz` 返回 `{"ok":true,"applications":["v1","v2","v3","v4","claude"]}`，响应来自 uvicorn |

另有一个旧工作树停在历史 `main`：`/Users/zhouli/Documents/ChatGPT/IS5542/github-pages-release/ai-career-coach-codex`，提交 `5494181`，相对当前 `origin/main` 落后。它不是正式开发目录，本次没有切换或更新它。

上一级 `/Users/zhouli/Documents/ChatGPT/IS5542` 的 Git 仍是没有提交的容器。没有在那里执行 `git add`。

## 本地状态与未重复的测试

开始检查时，正式目录工作区干净，没有未提交修改，也没有 stash。收尾提交只包含本报告、`AGENTS.md`、`README.md` 的状态说明，以及更名文档中的删除结果。没有业务代码改动。

没有重复以下已有且耗时的检查：127 项后端测试、Docker 双架构构建、真实 Supabase 双用户写入、DeepSeek 调用、重新部署。这些结果保留在 `docs/FINAL-ACCEPTANCE-20261126.md`、`release/unified-20261126` 和 `backups/final-acceptance-20261126/`。

本机仍有更早留下的本地 uvicorn，端口 8114、8012、8111、8112、8775，分别位于临时目录和历史工作树。它们不是本次启动的，也没有被关闭。

## GitHub 与文档

使用已登录的 GitHub CLI（账户 `lizlei417`，命令在 `~/.local/bin/gh`）读取仓库。名称、简介、默认分支和 `main` 最新提交与上表一致。新仓库主页指向 `https://lizlei417.github.io/ai-career-coach/`。Pages 来源是 `main` 的 `/docs`，状态 `built`。最新 Pages 构建对应 `ec4fe4c`，结论为 success。

本地 `origin`、根目录 `README.md`、`AGENTS.md` 和更名文档中的正式地址已经是 `https://github.com/lizlei417/ai-career-coach`。活动根 `Dockerfile` 只复制当前 checkout 里的 `versions/claude`，没有 `git clone`。

## 五个线上版本

探测时间约 19:05–19:10。根路径 `/` 返回 200，并最终打开 `/v3/`，标题为 `AI Career Coach · GPT V3`。五个版本首页均为 200。未登录访问 `/api/workspaces` 均为 401。十个主 JS/CSS 文件的 SHA-256 与 `docs/final-acceptance-20261126/docker-versus-original-production-assets.json` 逐项相同，说明仓库重命名没有换成另一套前端产物。

| 入口 | 首页 | 标题 | 未登录 API | 浏览器登录页 |
|---|---|---|---|---|
| `/v1/` | 200 | AI Career Coach | 401 | 邮箱、密码、注册、忘记密码均在 |
| `/v2/` | 200 | AI Career Coach | 401 | 同上 |
| `/v3/` | 200 | AI Career Coach · GPT V3 | 401 | 同上 |
| `/v4/` | 200 | AI Career Coach · GPT V4 | 401 | 从「开始使用」进入 `/v4/login`，页面可见 |
| `/claude/` | 200 | AI Career Coach | 401 | 从「开始使用」进入 `/claude/login`，页面可见 |

静态资源均返回 200，包括 Claude 实际使用的 `/claude/mark.svg`。没有提交登录表单，因此这次没有创建会话，也没有改动账户数据。

持久化仍采用 18:04 的只读记录：`backups/repository-rename-20261126/production-readonly-verification.json` 和同目录 `production-readonly.log`。五个版本均记录为同一 UI 资源、Auth 身份和已保存的 owner/application 状态通过，并且明确没有模型请求、没有项目或文档写入。本次没有重做这组账户读取。

## GitHub Pages

新演示站 `https://lizlei417.github.io/ai-career-coach/` 返回 200。`index.html`、JS、CSS 和 favicon 与仓库 `docs/` 逐字节一致。浏览器可以进入演示工作台，状态为 Demo Mode、指南库未接入。填入虚构示例后，本地解析出预设面试题，没有调用 DeepSeek。

旧演示站 `https://lizlei417.github.io/ai-career-coach-claude/` 仍返回 200，首页标题和「开始使用」正常，页面标明演示模式。它的 Pages 来源仍是旧仓库 `main` 的 `/docs`，最近成功构建在 2026-11-20。

## 旧 Claude 仓库是否还被生产使用

删除前，旧仓库 `https://github.com/lizlei417/ai-career-coach-claude` 仍在，ID `1465800361`，公开、未归档。默认分支 `main` 最后推送时间为 2026-11-21。简介为 `AI Career Coach · claude edition`。没有 Issues、Pull Requests、Releases、星标、fork、webhook 或 deploy key。

四条远端分支与统一仓库标签的提交完全一致：

| 旧分支 | 提交 | 统一仓库标签 |
|---|---|---|
| `main` | `f971cea` | `archive/claude/main` |
| `feature/deepseek-api-integration` | `fdd1554` | `archive/claude/feature/deepseek-api-integration` |
| `feature/claude-auth-deploy` | `d99e2d6` | `archive/claude/feature/claude-auth-deploy` |
| `codex/claude-shared-quota-dialogs` | `4ef8832` | `archive/claude/codex/claude-shared-quota-dialogs` |

从这四条历史可达的 Git 对象为 175 个，与更名记录一致。`4ef8832` 的 72 个已跟踪文件与 `versions/claude/` 逐字节相同，没有缺失或差异。

活动生产路径不克隆旧仓库。根 `Dockerfile` 从当前目录复制 Claude 源码。Render 的当前正式入口是这个根 Dockerfile。`versions/v2/Dockerfile` 和 `versions/v3/Dockerfile` 里仍有旧的 `git clone https://github.com/lizlei417/ai-career-coach-claude.git`，它们是历史快照，不是现在的构建入口。删除旧仓库后，不能再用这两个旧 Dockerfile 重建。

2026-11-26 约 19:35 已重新打开 Render 工作区。Production 环境只有 `ai-career-coach-three-versions` 一个服务，状态为 Deployed；没有 Blueprint 实例，来源也不是旧 Claude 仓库。

## 永久删除

用户于 2026-11-26 明确同意永久删除，并接受旧演示站和旧仓库链接失效。删除前再次确认：Claude 源码 72 个文件无差异，175 个历史对象仍在，`/healthz` 与 `/claude/` 均为 200。Render 控制台确认来源不是旧仓库。随后使用仓库所有者账号删除。

删除后立即复核：

- 旧仓库 API 与 https://github.com/lizlei417/ai-career-coach-claude 返回 404。
- 旧演示站 https://lizlei417.github.io/ai-career-coach-claude/ 返回 404。
- 新演示站 https://lizlei417.github.io/ai-career-coach/ 返回 200。
- Render `/claude/` 返回 200，`/healthz` 仍列出五个应用。
- 统一仓库 `lizlei417/ai-career-coach` 仍可访问，默认分支仍是 `main`。

已经消失、且不能从统一仓库恢复的内容：

- 旧演示站地址和旧仓库地址。删除不是改名，不会像 `ai-career-coach-codex` 那样自动跳转。
- 三份 GitHub Actions `pages build and deployment` 运行记录，以及旧仓库的 Pages 设置。
- 旧仓库页面上的简介和主页链接。删除前星标、fork、Issue、PR、Release 都是 0。
- Wiki 开关当时显示开启，但克隆返回不存在，没有可迁移内容。

`versions/v2/Dockerfile` 与 `versions/v3/Dockerfile` 仍含旧克隆地址。它们不是当前部署入口。以后重建使用根 `Dockerfile`，来源为统一仓库 `main` 或 `release/unified-20261126`（`30e7ffb`）。本地备份、`archive/claude/*` 标签、现有工作树、IS5542 Project 和历史对话都保留。

## Codex 遗留任务

| 任务 | 状态 |
|---|---|
| 五版本整合、历史保留、127 项测试、Docker、Supabase、DeepSeek、合并和部署 | 已有证据，本次未重跑 |
| 仓库重命名、远端和文档地址 | 已核实 |
| Render 改到新仓库并部署 `ec4fe4c` | 控制台已复核：来源、分支、commit、deploy ID 与 Live 状态一致 |
| 五个线上入口和资源 | 本轮重新检查通过；删除后 `/claude/` 再次返回 200 |
| 新 GitHub Pages | 本轮重新检查通过；删除后仍返回 200 |
| Claude 源码与历史进入统一仓库 | 删除前再次核对通过 |
| 最终完整报告 | 由本文补齐 |
| 永久删除旧 Claude 仓库 | 已于 2026-11-26 约 20:03 完成 |

## 交给后续 Codex 的状态

正式开发目录仍是 `unified-career-coach`，远端仍是 `https://github.com/lizlei417/ai-career-coach.git`。从最新 `origin/main` 创建新的 `codex/` 分支，默认修改根目录 V4。不要恢复或重新克隆已删除的 `ai-career-coach-claude`。不要运行 `versions/v2` 或 `versions/v3` 里的旧 Dockerfile，也不要重新部署当前正常运行的 Render 服务。旧演示站地址已经失效。
