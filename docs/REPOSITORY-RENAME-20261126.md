# 统一仓库正式更名与 Claude 永久删除评估

日期：2026-11-26，Asia/Hong_Kong。用户授权重命名、同步地址及验证，不授权删除原 Claude 仓库。本次不改变现有 IS5542 Project、历史对话、业务功能、UI、Supabase 或线上域名。

## 正式身份与地址

- 新地址：https://github.com/lizlei417/ai-career-coach
- 简介：IS5542 — AI Career Coach | Unified Repository (Codex & Claude)
- GitHub repository ID 仍为 **1465800290**，与更名前一致；这是原仓库重命名，没有另建仓库、重建历史或修改可见性。
- 正式分支仍是 main；本地唯一路径仍为 unified-career-coach。其 Git common-dir 的 origin 已改为 https://github.com/lizlei417/ai-career-coach.git，关联的 Codex 工作树共同使用该新 remote。
- 备份中的旧 remote 和不可变发布标签/凭证保留原状，历史工作树路径不重命名。旧 Claude 工作树仍指向原仓库，作为历史资料，不是正式开发入口。
- 顶层与统一仓库的 AGENTS.md、README、维护文档和部署示例中的正式链接更新；archives/、旧构建产物和原发布凭证保留为原始证据。

## Render 与数据边界

现有服务 srv-dc0k9cm7bikc73b2iqug，域名 https://ai-career-coach-three-versions.onrender.com ，继续使用 main、根 Dockerfile、Docker runtime、原环境变量与手动部署。仅更新来源为新仓库 URL，不新建服务、不更换域名、不重置用户数据。

控制台的 Update Source 流程会用 Deploy 保存来源变更，因此在文档和路径检查完成后，对同一服务部署同一份业务代码。最终来源、commit、deploy ID 与发布后结果在完成后创建的 annotated tag `maintenance/repository-rename-20261126` 中记录。没有该凭证，不应把来源修改意图视为成功。

回滚/重建基线改用独立于旧 Claude 仓库的统一标签 `release/unified-20261126` / commit 30e7ffb。更早的 9bc2fcd 及嵌套旧 Dockerfiles 只是历史记录，不是删除旧 Claude 仓库后的独立重建方案。

重命名前后对比现有项目、文档与 RLS 的只读内容摘要；以两个专用 QA 账户读取持久化数据并验证跨用户/版本边界，不编辑真实用户资料、不发模型请求、不执行生产 SQL 迁移。五个入口和已部署 JS/CSS 必须与原验收摘要一致。

## GitHub Pages 的路径调整

主仓库原来启用 main:/docs 的旧离线演示站。GitHub 仓库重命名不会自动保留原项目站路径，因此同步调整为 https://lizlei417.github.io/ai-career-coach/ 。这不改变 Render 域名。

使用 archive/codex/main 的同一源码、锁文件、Node 22 和 VITE_PAGES_DEMO=1 重建。旧 base 构建逐文件完全复现现有 docs 发布文件；新 base 构建的 JavaScript 把新路径还原后与旧文件逐字节一致，CSS、hero 和 favicon 不变。只改变 URL base，没有改变 UI 或业务逻辑。旧 assets 不删除，本地备份不覆盖。已验证新路径的资源加载、进入演示、填入示例及离线材料分析，无页面或 HTTP 错误。

## Claude 源码与历史完整性

对原 Claude 仓库实际 fetch 后的所有远端 refs 核对：

| 原分支 | 原 commit | 统一仓库保留引用 |
|---|---|---|
| main | f971cea | archive/claude/main |
| feature/deepseek-api-integration | fdd1554 | archive/claude/feature/deepseek-api-integration |
| feature/claude-auth-deploy | d99e2d6 | archive/claude/feature/claude-auth-deploy |
| codex/claude-shared-quota-dialogs | 4ef8832 | archive/claude/codex/claude-shared-quota-dialogs |

原仓库没有其他公开 advertised refs。独立从重命名后的 GitHub 地址普通 clone，核验原 Claude 全部 **175 个可达 commit/tree/blob 对象**均可从统一仓库 refs 访问，缺失对象为 0；四条分支的保留标签 SHA 完全一致。versions/claude 与原 4ef8832 tracked 源文件逐文件字节一致。原提交还通过统一合并的父节点保留，不依赖本机对象缓存或仅存本地的引用。

迁移前和本次更名前均已在仓库外保存 Git bundle。可用 git show archive/claude/main:README.md 或 git log archive/claude/codex/claude-shared-quota-dialogs 访问原历史。对象和 refs 结果见 repository-rename-20261126/claude-preservation.json。

## 当前部署依赖与永久删除影响

活动的根 Dockerfile、网关及五版生产业务源码没有对原 Claude 独立仓库的 clone、submodule、下载或启动依赖。Render 工作区列出的服务没有以原 Claude 仓库为源的服务；只有现有统一服务。versions/claude 是普通完整目录，一次 clone 即可获取。

保留的旧 Dockerfiles/README/历史标签会出现原 Claude URL，它们是历史记录，不是当前构建或回滚入口。永久删除后不要拿这些旧 clone-based Dockerfiles 重建；使用统一发布标签即可。

**删除评估：从统一源码、Git 历史、当前 Render 五版运行/部署与统一回滚来源看，已具备删除原仓库的条件。但以下原 GitHub 托管内容会消失，必须由用户最终确认接受：**

- 原 Claude 独立 Pages 站 https://lizlei417.github.io/ai-career-coach-claude/ 仍在线；删除仓库会使该旧演示入口失效。Render 的 /claude/ 不受影响。
- GitHub 自动 pages-build-deployment workflow 及其运行历史/托管设置没有迁移为统一仓库的运行历史；Git 对象备份不是这些托管元数据的完整备份。
- API 检查未发现 Issues（含关闭）、PR（含关闭）、Releases 或 release assets。Wiki clone 返回 404，未发现可克隆 Wiki，不能声称备份了不可访问的 Wiki 内容。
- 原仓库 URL、星标及其他站点级元数据不属于代码/提交对象；删除不是改名重定向，也不应依赖恢复窗口来保证可逆。

本次评估当时不归档、不删除，等待用户最终确认。用户随后在 Render 控制台复核通过后明确同意。`ai-career-coach-claude` 已于 2026-11-26 约 20:03 永久删除，旧仓库与旧 Pages 地址返回 404。Render `/claude/`、统一仓库中的 Claude 源码和 `archive/claude/*` 历史均保留。结果见 [收尾验收报告](CLOSEOUT-ACCEPTANCE-20261126.md)。现有本地备份、Project 和历史对话全部保留。
