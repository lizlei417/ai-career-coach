# V3 正式文档预览与完整简历编辑验收

本轮只修改 V3 的文档预览、完整简历编辑和顶部功能导航。M3 Prompt、RAG、DeepSeek 分析规则、每账户 10 次额度规则和 V1/V2 固定版本均未修改。

## 实现

| 需求 | 实现 |
|---|---|
| 正式文件预览 | 原按钮打开自定义格式选择框。真实 PDF 在新标签页进入 Chrome 原生 PDF Viewer；真实 DOCX 在独立标签页通过 docx-preview 本机渲染，可下载同一个文件。 |
| 文档排版 | ReportLab PDF / python-docx Word，A4、姓名、联系信息、章节、经历条目、项目符号与分页；嵌入 OFL Noto 字体，支持简体、繁体和英文。Word 浏览器预览按实际段落高度分页。 |
| 完整简历编辑 | 原地只读文本切换为同尺寸 textarea；完成后通过现有项目 revision 校验写入服务器。保存失败不离开编辑状态，保留草稿，支持重试。 |
| 按钮 | 预览白底、深色文字、浅灰描边；编辑/完成为 #111827 黑底、白字、白色铅笔/勾选。编辑/完成固定宽 96px，右对齐，间隔 8px，保存显示 loading，防重复提交。 |
| 顶部导航 | 复用现有 setFeature 和路由，三个入口与左侧同步，固定统一位置，细下划线选中；保留保存状态和账户入口。 |

### 存储与保护

- 在现有项目 JSON 中增加 `finalResume`，包含完整文本、版本、保存时间和编辑前基准文本；`finalResumeHistory` 保留最近三个已保存旧版本。无需数据库迁移。
- 原始 `inputs.resumeText`、原 PDF 文件及分析时的 source snapshot 保留。
- 已保存完整简历优先用于预览和导出。后续审核决定与重新生成建议均不会清空或替换它，界面明确说明后续改动需在完整简历中编辑。
- 未保存编辑显示顶部“尚未保存”。项目切换、功能跳转、返回首页、退出登录和重新分析使用现有风格确认框；快速重复点击仅显示一个确认框。
- 草稿按账户和项目隔离存于本机，刷新或重新打开时恢复；“完成”成功后清除本机恢复草稿。已完成文本使用服务器项目存档，能够刷新、切换和重新登录恢复。
- 浏览器直接刷新、关闭标签页或关闭应用时，网页无法可靠展示自定义退出弹窗；此处以草稿恢复防止丢失，不假称能控制浏览器关闭行为。跨设备可恢复服务器已保存内容，本机未完成草稿不跨设备同步。
- 文档处理不调用 AI。DOCX 在本机浏览器渲染，不上传到 Office 在线或第三方文档转换服务。

## 主要文件

- `frontend/src/components/FinalResume.tsx`：原地编辑、保存反馈、草稿恢复、格式选择、真实文件预览和下载。
- `frontend/src/lib/document-preview.ts`：DOCX 文件渲染、A4 分页和文件下载。
- `frontend/src/lib/resume-navigation.ts`：统一未保存保护，避免重复确认框。
- `frontend/src/lib/store.tsx`：项目 JSON 版本存档、确认写入与失败重试。
- `frontend/src/App.tsx`、`components/Sidebar.tsx`：顶部功能导航及选中状态。
- `frontend/src/cloud.tsx`：退出前复用未保存保护。
- `backend/app/final_resume.py`：完整简历优先级、PDF/Word 模板、嵌入字体。
- `backend/app/main.py`：提供公开的开源字体资源，保留原有鉴权导出接口。
- `backend/data/fonts/`：开源字体及 OFL 许可证。约 10 MB 字体为刻意加入，非用户文件或临时产物。
- `frontend/package*.json`：新增 docx-preview，按需加载。
- `backend/tests/test_final_resume.py`、`tests/resume_documents_e2e.py`：内容保留、真实格式、编辑持久化与浏览器验收。
- 既有测试仅适配顶部重复入口、自动文本预览及新增排版；模拟模型加入明确标记的中文 fixture，正式分析模块没有改动。

## 本地测试

| 测试 | 结果 |
|---|---|
| 后端单元/接口测试 | 52 项通过，包括原有 50 项与新增完整简历保护和嵌入字体内容验证。 |
| 旧浏览器 E2E | 注册登录退出、多项目隔离/重命名/删除、原始多页 PDF 上传/预览、扫描件提示、JD 输入/受控导入、人工审核、保存失败/重试、匹配结果、三语言通过。模型/Auth/Storage 使用明确 Mock，数据库和后端真实运行。 |
| AI 请求竞争条件 | 材料变更、过期标记、重新生成及服务失败重试通过。 |
| 面试回归 | 两个主问题、一次追问、缓存下一题、结束总结、刷新和顶部切换保留面试进度通过；切换没有新增模型调用。Mock 模型。 |
| 历史项目恢复 | 缺少旧资料选项、取消和确认后继续、无重复调用、刷新恢复通过。Mock 模型。 |
| 本轮中文流程 Mock | 使用正式林知夏 PDF 与模拟 AI 产品运营 JD。分析→采纳→两个真实文件预览/下载→编辑→保存失败→重试→保存→刷新→项目切换→退出重新登录通过。 |
| 真实 DeepSeek | 本地已实际生成林知夏改写结果并采纳，文件预览、编辑保存和重新登录流程通过；后续调试复用真实结果，记录明确标注复用，避免重复调用。 |
| 文档视觉检查 | 下载文件通过 pypdf/python-docx 重新打开；PDF 由 Poppler 渲染、DOCX 由捆绑 LibreOffice 渲染，逐页检查中文、标题、符号和分页；浏览器 DOCX/PDF 截图检查通过。 |
| 构建 | TypeScript 和 Vite 通过；现有动态导入和包大小提示不影响构建。 |
| V2 存档 | 92 个文件 SHA-256 对照全部未变；Docker 的 V1/V2/Claude 固定提交未变。 |

执行命令（示例为隔离的本地测试库）：

```sh
cd frontend
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build --base=/v3/
cd ..
QA_DATABASE_URL=postgresql://postgres@127.0.0.1:28547/coachtest_v3_audit_utf8_20261122 python tests/run_audit.py e2e_races.py api_integration.py e2e_audit.py m3_interview_e2e.py profile_recovery_e2e.py
QA_DOCUMENTS_MOCK=1 QA_DATABASE_URL=postgresql://postgres@127.0.0.1:28547/coachtest_v3_audit_utf8_20261122 python tests/run_audit.py resume_documents_e2e.py
```

真实模式需启用既有私有 DeepSeek 配置的隔离服务；`tests/resume_documents_e2e.py` 默认测试本地真实模式，`QA_DOCUMENTS_HOSTED=1` 测试 Render 的专用测试账号。`QA_DOCUMENTS_REUSE=1` 明确复用该测试账号此前实际生成的结果。测试证据在被 Git 忽略的 `tests/evidence/`；凭据和恢复会话缓存不提交。

## 部署与线上验收

待本轮 Render 发布和线上浏览器验收后补充实际部署提交、状态、配额及文档检查结果。

依赖变化：新增 npm `docx-preview`；已有 ReportLab、python-docx 不变，未新增运行时 Python 包；字体包含在镜像。无需数据库迁移或新环境变量。未修改 API Key、额度配置或生产用户数据。

## 边界

DOCX 浏览器渲染和 Microsoft Word 的最终行距/分页可能略有差异；下载内容是真正 DOCX，不是 HTML 或建议 TXT。正式文件采用统一模板，不复刻上传 PDF 的像素排版。完整简历历史版本暂不提供独立历史管理界面。浏览器关闭场景的草稿恢复限制见上文。
