# GPT V3 全流程审计与修复报告

日期：2026-11-22（香港时间）。本轮遵循后续指示，将工作从 V2 移至独立 V3，未部署生产环境。

## 1 全流程测试结果

| 功能 | 测试结果 | 发现问题 | 修复情况 |
|---|---|---|---|
| 注册、登录、退出、刷新 | 本地模拟 Auth 的浏览器流程通过；正式邮件服务未重测 | 本轮未发现阻断性表单问题；退出原先只等待旧保存队列 | 退出等待项目写入；测试了非法邮箱、弱密码、密码不一致和登录错误 |
| 项目新建、重命名、删除 | 浏览器及真实 PostgreSQL 通过 | 无新阻断问题；保留既有自定义确认设计 | 反复切换两个项目、刷新后名称/JD 恢复；删除取消与确认通过 |
| 三页 PDF 上传与预览 | 实际后端提取和浏览器通过 | 扫描件曾被吞掉错误且页数返回 0；超长文件会静默截断 | 保留文件并返回无文本提示及真实页数；超限明确报错 |
| JD 粘贴、编辑和 URL | 浏览器通过；受控 HTML 导入成功；无效内网 URL 失败 | 重定向后目标未重新校验 | 每一跳校验公网地址并限制响应大小；真实 Jobsdb 页面未验证 |
| 岗位匹配 | 真实 DeepSeek 业务调用及 Mock 错误场景通过 | 材料变化后恢复入口受限；异步结果可能盖错快照 | 可重新解析当前材料再分析；结果固定关联请求时材料 |
| 简历优化及逐条审核 | 浏览器、针对性竞态测试通过 | JD 变化后审核和重新生成同时禁用；已决定项目不能直接继续修改；编辑草稿可能与新建议错位 | 过期原因与重生成入口；允许取消、撤销；已决定项目可重新编辑；按分析版本重置行状态 |
| 最终完整简历预览 | 浏览器及后端通过 | 原版本只有复制文字，缺少可靠完整简历产物 | 从完整原文定位并替换已确认源段落，保留所有未修改文本 |
| PDF 和 DOCX 导出 | 实际下载、重新打开、内容比较和版式渲染通过 | 原版本没有二进制文件导出 | 新增专业单栏模板和真正的 PDF/DOCX；无法安全定位则拒绝导出 |
| 审核保存、刷新和项目隔离 | 真实数据库与浏览器通过 | 导出若不等待保存可能读取旧决定；保存失败缺少恢复入口 | 导出等待写入；失败不显示已保存、不导出旧结果；支持重试 |
| 语言切换 | 简体、繁体、英文及刷新通过 | 工作台语言未同步到认证层的持久偏好 | 保留语言选择；切换不自动重跑 AI，不改变项目分析与审核 |
| 构建、启动与控制台 | TypeScript/Vite、独立 V3 和四版本网关通过 | 本地启动脚本沿用 V2 端口和根路由 | V3 使用 8113 和 /v3/，热更新 5174；无严重页面异常 |

“通过”范围为报告注明的测试环境，不代表线上 SMTP、线上 Storage 或 Render Docker 已经验收。

## 2 Bug 原因与修改文件

1. **过期审核无法恢复**：ResumeView 把 stale 直接用于审核和重新生成的 disabled；ResultBanners 的 stale 分支没有操作入口。修改 `frontend/src/views/ResumeView.tsx`、`views/MatchView.tsx`、`components/ui.tsx`、`lib/store.tsx` 和 `lib/i18n.ts`。重新生成会按需解析最新材料；有已确认决定时先显示站内确认，成功才替换旧结果。取消编辑与撤销可用于过期结果，采纳/保存继续受明确的过期保护。旧 V2 在独立浏览器构建中实际复现，V3 回归通过。
2. **异步快照与当前材料混用**：prepare 原先使用请求时文本，却用完成时 inputs 计算 inputsKey；优化/匹配又把旧输出标在完成时的 fingerprint 上。修改 `lib/store.tsx`：输入键、fingerprint、补充材料和原始源快照均取自请求快照。针对“请求发出后修改 JD”的浏览器测试分别覆盖 prepare 和 optimize。
3. **编辑状态不能可靠复用**：已确认行只有撤销入口，行键仅按 O1 等编号，重新分析后可能复用旧草稿。修改 `views/ResumeView.tsx`：已确认行提供修改；键包含分析指纹与改写文本；取消回到最近保存值，保存与取消含义明确。
4. **没有完整可投递文件**：原“导出”只调用 clipboard。新增 `backend/app/final_resume.py` 与 `frontend/src/components/FinalResume.tsx`，在 `backend/app/main.py` 增加当前账户/项目范围的 final 和 export 接口。完整原文作为底稿，采用源编号与顺序映射定位，反向替换精确文本范围；重复段落不做全局替换，不能定位或有重复源建议时明确失败。未决定/保留使用原文，不自动添加 missing 建议；导出完全不调用模型。
5. **保存失败与导出状态不一致**：新增保存刷新等待和重试，见 `lib/store.tsx`、`App.tsx`、`lib/projects.ts`、`cloud.tsx`、`components/FinalResume.tsx`。失败保持明确提示，阻止服务器导出旧审核状态；恢复后移除未保存离开保护。浏览器注入一次 503 写入失败，验证重试与立即刷新均恢复，无原生弹窗。
6. **扫描件无提示、长文件截断**：修改 `backend/app/main.py`、`materials.py` 和 `components/MaterialsPanel.tsx`。扫描件返回 PDF_NO_TEXT 警告但可预览原件；不得把空文本当成功分析。超出文本上限明确拒绝，避免输出残缺履历。
7. **URL 重定向缺少目标校验**：修改 `backend/app/materials.py`。逐跳校验公网主机，限制跳转次数和读取体积；单元测试覆盖受控 HTML、空内容、跳转内网。浏览器覆盖成功导入和明确失败。
8. **语言刷新回退与请求状态**：修改 `cloud.tsx`、`lib/store.tsx`、`lib/api.ts`。同步语言偏好；模型操作用同步 guard 防止同一种请求重复触发，finally 释放状态；浏览器请求设超时并映射为可理解的错误。后端不会自动重试收费调用。
9. **V3 本地入口与 V2 冲突**：新增 `backend/dev_app.py`，修改 `start.sh`、`frontend/vite.config.ts` 和 `index.html`。V3 保持 /v3/ base 和独立端口；Docker/gateway 中另挂 V3，并固定旧 V2 提交。
10. **DOCX 默认标题蓝线**：文件渲染检查发现 python-docx 的默认 Title 样式带蓝色段落边框，已在生成器中移除并重新渲染验证。

`backend/tests/test_deepseek.py` 的已有本地改动由 V2 继承保留，不作为本轮新增 Bug 修复声称。V1、Claude 的源码无本轮改动。

## 3 简历生成能力

| 能力 | 结果 |
|---|---|
| 根据确认决定生成完整新简历 | 支持，确定性合成；不再调用 AI |
| 采纳优化文本、使用保存的手动文本 | 支持 |
| 拒绝全部或仅采纳部分 | 支持；全部拒绝时提取原文完全相等 |
| 未涉及修改的内容 | 保留完整输入，包括姓名、联系信息、教育和技能 |
| 重复段落、换行段落 | 单元测试覆盖，按源位置替换而非全局替换 |
| 在线完整预览 | 支持全文预览；投递版使用统一单栏模板 |
| PDF | 支持，实际二进制下载、文本完整性与页面渲染验证 |
| DOCX | 支持，实际 OOXML 打开、段落比对与页面渲染验证 |
| 项目关联、重开后再导出 | 支持，使用当前账户项目状态和保存的审核决定重建 |
| 原始简历 | 优化/导出不修改 inputs.resumeText 或原始 PDF；用户主动清空/删除属于独立操作 |
| 扫描件 OCR | 不支持；原件可预览，需要用户粘贴可提取文本 |

合成器不会主动创造经历或数字。AI 建议仍需人工核对事实；规则式 grounding 并不等于对所有语义事实的形式证明。系统不会自动采纳待审核建议，也不会把“缺失经历”直接写进简历。

V3 使用独立 `codex_v3` 应用命名空间，不会自动搬迁 V2 项目。可选 source 快照存入现有 JSON 字段；无 source 的旧格式已有兼容测试，不需要新数据库列。

## 4 测试证据

- 后端测试：18 项全部通过，含原有认证/模型错误测试、合成与二进制文件测试、URL 测试。证据：`tests/evidence/unit-tests.log`。
- 主浏览器流程：14 组全部通过。Chrome 实际上传、表单填写、点击、刷新、切换、下载；无 pageerror 和原生弹窗。证据：`e2e-results.json`、`e2e_audit.log` 与 `e2e-trace.zip`。
- 针对性竞态：prepare 与 optimize 请求中修改 JD、503 失败后重试均通过。证据：`race-results.json`、`e2e_races.log`。
- 数据库集成：账户/项目 RLS、409 修订冲突、导出不增加调用次数、10 次上限、第 11 次拒绝、删除项目后额度不重置均通过。证据：`api-integration.json`、`api_integration.log`。
- 真实 DeepSeek：成功流程 3 次调用（prepare、match、optimize），解析 6 项要求、生成 3 条建议，采纳 1 条并保留其余，刷新后仍能生成相同完整简历。另 1 次先前解析因测试断言仅匹配英文而停止；补充中文断言后完成流程。总共 4 次真实调用、6,243 tokens；没有自动模型重试。证据：`real-deepseek-results.json`、`real-deepseek-usage.json`、`real-deepseek-run.log`。
- 真实调用仍使用合成 Auth/Storage 和独立本地数据库，不能据此声称 hosted Supabase/SMTP 通过。
- 完整 Mock 流程重新统一运行成功：`tests/evidence/final-audit-run.log`。
- TypeScript 与 Vite 构建通过；Vite 有单包约 530 KB 的非阻断告警，尚未做拆包优化。证据：`frontend-build.log`。
- 独立 V3 入口与四版本网关的页面、JS/CSS、health 和未登录 API 401 通过。证据：`standalone-smoke.json`、`gateway-smoke.json`。未运行 Docker 镜像构建。
- V2 存档后逐文件校验：92 个跟踪文件完全一致，保留本来就有的测试文件修改。证据：`v2-archive-verification.json`；存档位于仓库同级 `backups/auth-v2-before-v3-20261122.tar.gz` 及其 manifest。

关键截图（位于 `tests/evidence/`）：

| 文件 | 内容 |
|---|---|
| `00-baseline-disabled.png` | 旧 V2 实际复现：JD 改变后审核/重新生成禁用 |
| `01-original-preview.png` | 三页原始 PDF 预览，读取字节与上传文件相等 |
| `01-original-preview-page2.png`、`01-original-preview-page3.png` | 实际操作浏览器内置 PDF 页码控件后显示第 2、3 页，已逐页视觉检查 |
| `02-ai-review.png` | Mock 建议审核界面 |
| `03-final-resume.png` | Mock 混合审核后的完整简历及导出入口 |
| `04-stale-recovery.png` | V3 过期提示与可恢复操作 |
| `05-delete-confirmation.png` | 项目删除的自定义确认弹窗 |
| `06-real-deepseek-match.png` | 真实 DeepSeek 岗位匹配结果 |
| `07-real-deepseek-final.png` | 真实 DeepSeek 建议人工确认后的完整预览 |
| `08-race-recovered.png` | 异步竞态与失败重试后审核恢复 |

实际文件：`real-deepseek-final.pdf` 和 `real-deepseek-final.docx`。pypdf 与 python-docx 已重新打开并比对完整文本；PDF 经 Poppler 渲染，DOCX 经 render_docx.py 渲染，逐页视觉检查未发现截断、重叠或缺字。Mock 最终文件也经过相同验证。长履历单元测试覆盖多页输出及每一行文本的保留。

可复现命令：

```sh
cd auth-v3/frontend
npm ci
npm run build -- --base=/v3/
cd ..
python -m pip install -r tests/requirements.txt
QA_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/coachtest_v3_audit_NAME python tests/run_audit.py
cd backend
python -m unittest discover -s tests -v
```

需要事先准备 UTF8 的独立本地 PostgreSQL 数据库，以及 Chrome；测试脚本只接受 `coachtest_v3_audit*` 数据库。详细运行方法见 `tests/README.md`。真实 API 测试脚本 `real_e2e.py` 不被默认运行器调用，避免重复收费。

## 5 场景覆盖与尚未验证事项

| 场景 | 结果/范围 |
|---|---|
| A 正常完整闭环 | 真实 AI + 本地真实后端/DB/文件通过；Mock 全流程亦通过 |
| B 无简历 | 浏览器明确报错 |
| C 无 JD | 浏览器明确报错 |
| D AI 请求失败 | Mock 504 超时与 503 失败，提示/恢复/手动重试通过 |
| E 分析后改 JD | 过期标记、重生成恢复、后端拒绝旧导出通过 |
| F 审核后刷新 | 决策恢复、完整简历一致通过 |
| G 两项目反复切换 | 数据隔离与恢复通过；工作台保持挂载与加载状态，不切成整页空白 |
| H 全部拒绝 | 最终文本与提取原文完全相同 |
| I 部分采纳 | 仅对应已确认源段落替换 |
| J 手动修改再撤销 | 回到待处理和原文，重改保存通过 |
| K 导出文件打开 | PDF/DOCX 实际下载、解析、全文比对、渲染通过 |
| L 中英文切换 | 保留语言与数据，不多调用模型 |
| M 多页/段落/扫描件 | 三页上传、换行段落、重复段落、多页导出；无文本 PDF 提示与预览通过 |

未解决或未验证：

1. 本轮没有重测真实邮箱的收信、验证链接、密码重置邮件、hosted Supabase token 长时刷新及真实私有 Storage。本地替代服务不是其验收证明。
2. 本机没有 Docker，未执行 Docker 镜像构建或 Render 预发布/生产测试。不能宣称已满足全部线上发布条件。
3. URL 导入不是 Jobsdb 全站检索/API 接入。受控 HTML 正常链路和失败链路已验证；真实 Jobsdb、登录墙、JS 动态招聘网站仍可能无法读取，应回退粘贴文本。
4. 没有 OCR，也不保证任意复杂双栏 PDF 的提取阅读顺序。用户需核对提取文本；本轮验证的是三页英文简历与确定的段落结构。
5. 当前界面提供全文内容预览，PDF 与 DOCX 使用统一模板；不还原上传文件的图形设计，也不承诺任意字体/emoji 的排版效果。
6. 未接入正式 Prompt/RAG，保持现有测试模板；没有进行正式知识库质量验收。
7. V1/Claude 仅做本地入口/资源/未登录保护的兼容性冒烟检查，没有完整重跑它们的业务 E2E，且源码未改。

## 6 部署说明

当前可以进入 V3 预发布验收，未部署、未推送。最终生产发布仍须验证实际 Docker/Render 构建、V3 Supabase callback allowlist、真实邮件及私有 Storage，完成后再决定发布。

新增运行依赖为 ReportLab 与 python-docx，已加入 backend 和 deploy requirements；无新增前端运行依赖、无新必需环境变量、无新增数据库结构迁移。现有账户每天 10 次模型调用规则及密钥配置均未修改。

`render.yaml` 改为独立 V3 preview 服务且关闭自动部署，Docker 中固定旧 V2 源码，同时挂载 `/v3/`。完整配置说明见 `deploy/V3-DEPLOYMENT.md`。不要直接把当前项目当作已经部署成功，也不要以本轮本地测试替代线上服务验收。
