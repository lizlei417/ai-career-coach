# IS5542 AI Career Coach — 统一项目

IS5542 — AI Career Coach | Unified Repository (Codex & Claude)

IS5542 课程 AI 职业辅导项目，保留 Codex 与 Claude 两条实现路线。统一仓库：https://github.com/lizlei417/ai-career-coach 。当前主力是根目录 V4；正式统一代码源为 `main`，包含 V1/V2/V3/V4/Claude 完整源码及保留历史。

整合验收分支：`codex/unified-repository-20261126`。后续请从最新 `origin/main` 创建 `codex/` 功能分支，优先开发根目录 V4。完整检查见 [最终验收记录](docs/FINAL-ACCEPTANCE-20261126.md) 和 [初始盘点](docs/UNIFICATION-AUDIT-20261126.md)。原 README 保存在 [历史说明](docs/README-before-unification.md)。

## 版本与结构

| 版本 | 目录 | 技术栈与用途 | 入口 |
|---|---|---|---|
| V4（主力） | `frontend/`、`backend/` | React 18、TypeScript、Vite 5、FastAPI；职业探索、测评、简历、岗位匹配、模拟面试及回顾 | `/v4/` |
| V1 | `versions/v1/` | React 18、TypeScript、FastAPI；原始三功能云端版 | `/v1/` |
| V2 | `versions/v2/` | 同上；项目库、多项目切换、原 PDF 预览 | `/v2/` |
| V3（保留） | `versions/v3/` | 同上；M3/RAG、简历完整编辑及导出 | `/v3/` |
| Claude | `versions/claude/` | React 19、TypeScript、Vite 6；Python/FastAPI、原 Streamlit 入口和 coach 模块 | `/claude/` |
| 早期本地源码 | `archives/` | 未版本管理的历史源码存档，不参与部署 | 无 |

```text
frontend/ backend/          V4，原结构保留
deploy/                    共享网关、SQL、部署文档
versions/{v1,v2,v3,claude}/  独立版本，依赖和启动方式保留
versions/source-manifest.json  源 commit 与路径
versions/history-refs.json     原分支对应的保留标签
archives/                  早期源码；排除本地密钥、运行数据与截图
docs/                      验收和历史说明
Dockerfile                 一次 checkout 内构建所有版本，不再克隆其他仓库
AGENTS.md                  后续 Agent 的开发约束
```

## 本地运行

需要 Node 22+、Python 3.12。以下命令从统一仓库根目录执行：

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r deploy/requirements.txt
for pair in 'v1 versions/v1' 'v2 versions/v2' 'v3 versions/v3' 'v4 .' 'claude versions/claude'; do
  set -- $pair
  (cd "$2/frontend" && npm ci && npm run build -- --base=/$1/)
done
uvicorn local_gateway:app --app-dir deploy --host 127.0.0.1 --port 8114
```

循环示例使用 POSIX sh/bash。也可对表中任意目录单独运行 `npm ci && npm run build -- --base=/`，然后启动该版本：Codex 各版在其 `backend/` 执行 `uvicorn app.main:app --host 127.0.0.1 --port 8000`；Claude 在 `versions/claude/` 执行 `uvicorn server:app --host 127.0.0.1 --port 8765`。独立运行时前端必须使用 `/` base，避免误用共享网关路径。Claude 原 Streamlit 入口可在额外安装其 `requirements.txt` 后执行 `streamlit run app.py`；本次未验证 Streamlit 路径。

## 配置与数据

在本机未跟踪的 `~/.config/ai-career-coach/cloud.env` 或进程环境中设置：

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_KEY
SUPABASE_SECRET_KEY=YOUR_SERVER_ONLY_SECRET
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
DEEPSEEK_API_KEY=YOUR_SERVER_ONLY_API_KEY
ACCOUNT_DAILY_LIMIT=10
```

DeepSeek 和 Supabase secret/database 凭据只能放服务器。浏览器只接收 Supabase 公共配置。使用原 Supabase 项目、private schema、私有 Storage、owner/application RLS 和现有用户账户；不同版本的 application namespace 不得更改。`deploy/001_private.sql`、`002_storage.sql`、`003_account_quota.sql` 记录现有初始化方案，**整合不需要重新运行生产迁移**。保留邮箱确认、回调白名单、配额账本及管理员 app_metadata。不要导入、导出或提交真实用户资料。

## Render

继续使用现有服务 `ai-career-coach-three-versions`、原域名和环境变量。Dockerfile 从当前 checkout 的版本目录构建，URL、Python 模块和数据命名空间维持独立。网关根路径仍跳转 `/v3/`，避免此次整合改变既有入口。`COACH_V4_ROOT` 仅为本地共享网关提供源码根路径覆盖，容器默认不变。

2026-11-26 用户已授权在验收通过后合并 main 并部署现有服务。正式来源是 main，保留手动部署。根 `render.yaml` 是历史 V4 预览服务配置，**不要直接 Apply Blueprint**，以免建立额外服务；最终部署应在现有服务中，经批准选择整合 commit。先验证 Docker 构建，再核对现有环境、回滚 commit 和公开入口。已在独立 Lima Linux Docker 环境完成 arm64 与 amd64 镜像构建及运行验收。前端构建使用 BUILDPLATFORM，最终运行层使用目标架构，未将 Node 或开发服务器带入生产镜像。

## 功能与限制

V4 已有五模块导航、职业探索及岗位查看、八类测评结果与平衡结果、按得分分割的双色进度条、面试回顾、页面动画及减少动画设置、工作台/项目库、简历编辑/保存/PDF-DOCX 预览、中英文切换、Supabase 登录与持久化、DeepSeek 服务端接入。源码、构建和离线测试证据不等于所有生产业务流程已重新验收。

已执行 V4 九组、V3 六组浏览器回归，以及五版真实登录、材料持久化、导航及语言测试；已通过真实 Supabase 双用户/Storage 隔离和 DeepSeek 流程。Vite/esbuild 告警涉及开发服务器，生产 Python 镜像不包含这些工具；仍须谨慎使用本地开发服务器，不自动升级依赖或重跑生产迁移。原有详细功能文档在各版本 README 和 deploy 文档中，历史验收记录均须按记录日期理解。


## 验收复现与部署边界

完整命令、测试范围和回滚目标见最终验收记录。五版浏览器验收脚本：

```sh
QA_ACCOUNTS_FILE=/PRIVATE/PATH/dedicated-qa-accounts.json python tests/unified_browser.py http://127.0.0.1:8114
```

只接受本次格式的两个专用 `is5542-unified-qa-...@example.test` 测试账户，写入虚构材料，不调用模型。账户凭据、trace 和用户文件不得提交；证据在 gitignored tests/evidence/。真实模型脚本 tests/real_e2e.py 使用一次性本地数据库与模拟 Auth/Storage，明确调用真实 DeepSeek 三次，不自动重试。

**所有版本部署只使用仓库根 Dockerfile**。versions/v2、versions/v3 内原 Dockerfile/render.yaml 与旧 README 为原始提交历史快照，不是当前构建入口；其中外部 clone URL 不会被统一 Docker 构建执行。一次普通 git clone 即可获得所有源代码，构建与运行不再访问原 Claude 独立仓库。


## 仓库正式名称与删除旧仓库的边界

2026-11-26 统一仓库正式更名为 **lizlei417/ai-career-coach**。Render 服务和域名保持不变；本地唯一开发目录仍为 unified-career-coach，不更名、不迁移现有 IS5542 Project 或历史对话。

最新更名检查见 [仓库更名与旧仓库删除评估](docs/REPOSITORY-RENAME-20261126.md)。今后回滚/重建使用统一发布标签 `release/unified-20261126`（30e7ffb）或后续统一版本；这些版本的根 Dockerfile 不依赖原 Claude 仓库。早于整合的历史 Dockerfiles 仅作原样历史证据，不是当前部署入口或删除旧仓库后的重建方案。

旧 Claude 独立仓库已在 2026-11-26 控制台复核后永久删除。其旧演示站和旧仓库地址已失效。Claude 源码、提交历史与 Render 的 `/claude/` 保留在本仓库和现有服务中。完整记录见 [收尾验收报告](docs/CLOSEOUT-ACCEPTANCE-20261126.md)。
