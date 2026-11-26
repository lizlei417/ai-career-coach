# IS5542 AI Career Coach — 统一项目

IS5542 课程 AI 职业辅导项目，保留 Codex 与 Claude 两条实现路线。统一仓库：https://github.com/lizlei417/ai-career-coach-codex 。当前主力是根目录 V4；`main` 目前仍是早期展示版，**尚未合并此次整合**。

整合分支：`codex/unified-repository-20261126`。请在此分支或其后续评审分支继续开发，正式合并、部署须经项目负责人决定。完整检查见 [版本验收报告](docs/UNIFICATION-AUDIT-20261126.md)。原 README 保存在 [历史说明](docs/README-before-unification.md)。

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

本次不创建服务、不改部署分支、不触发部署。根 `render.yaml` 是历史 V4 预览服务配置，**不要直接 Apply Blueprint**，以免建立额外服务；最终部署应在现有服务中，经批准选择整合 commit。先验证 Docker 构建，再核对现有环境、回滚 commit 和公开入口。Docker 引擎在本机不可用，因此本次不声称完成容器镜像测试。

## 功能与限制

V4 已有五模块导航、职业探索及岗位查看、八类测评结果与平衡结果、按得分分割的双色进度条、面试回顾、页面动画及减少动画设置、工作台/项目库、简历编辑/保存/PDF-DOCX 预览、中英文切换、Supabase 登录与持久化、DeepSeek 服务端接入。源码、构建和离线测试证据不等于所有生产业务流程已重新验收。

现有依赖审计告警、Docker/完整浏览器回归、真实 Supabase 双用户隔离与真实 DeepSeek 全流程复验仍需跟进；不要自动升级依赖或重跑生产数据迁移。原有详细功能文档在各版本 README 和 deploy 文档中，历史验收记录均须按记录日期理解。
