# V3 正式 M3 Prompt + RAG 集成验收

日期：2026-11-22（香港时间）。仅修改 auth-v3；未创建 V4。

## 1. 接手 Claude 遗留代码

入口工作目录的外层 Git 还是无提交的 main；实际应用仓库在 `auth-v3`，分支 `codex/v3-career-audit`，远程 `lizlei417/ai-career-coach-codex`。接手时 HEAD 为 `bbe78f0`。

开始时没有 reset、clean 或覆盖。先保存指定的非敏感工作区文件到 `../backups/claude-m3-before-integration-20261122.tar.gz`。没有打包 .env、账户凭据或私有配置。

|检查项|接手时实际状态|处理|
|---|---|---|
|正式材料复制|已完成且核对通过|Prompt、chunks、sources、README 与桌面 product 原文件逐字节一致，保留|
|rag.py 的 BM25、任务筛选、中文词扩展|部分完成|保留算法，接入三条业务链路并补测|
|SHA-256 校验|部分完成|原来只校验片段文字，未校验原始页面、完整数量或重复 ID；补齐并在不完整时停用索引|
|原始页面及 verify.py|尚未复制|从用户原压缩包补回，不重新抓取或编造内容|
|Prompt 接入、正式 JSON 适配、前置问题|尚未实现|补齐 M3 服务层及页面选择项|
|配置|存在错误|Claude 移除 KB_DIR，旧模块仍 import，启动发生 ImportError；恢复兼容配置|
|原 33 项测试|接手状态无法全部载入|恢复配置后先验证 33 项全部通过，再接入正式协议|
|状态显示|尚未接入正式索引|健康接口与界面改为真实索引、校验及连接状态|
|意外删除|kb/.gitkeep 被删除|已恢复；未发现原有业务文件被删除|

接手时属于本轮材料工作的新增文件为 rag.py、M3 Prompt、RAG README/chunks/sources；config.py 被修改。README、JD 审计报告、链接导入测试等是前一项 Codex 工作留下的未提交成果，已独立提交 `cd60018`，没有归为 Claude 新成果。Git 未提交文件本身不能证明作者身份。

没有发现所述 +18,106/-355 行对应的已提交改动。此轮应用提交实际 +4,520/-150 行，其中约 3,465 行为四份原始 HTML 证据快照，新增源码及材料合计约 198 KB，没有大模型、生成的巨型索引、node_modules、ZIP 重复件或真实密钥。`.gitattributes` 保留原快照换行与空白，避免破坏哈希。

正式材料来源：`/Users/zhouli/Desktop/IS5542 生成式商业AI/product/M3_Prompt_v1.md` 和 `product/RAG_v1/`；原始 HTML、verify.py 来自同目录 `CityUHK_RAG_v1.zip`。完整读取 Prompt、全部 18 段及来源清单，并按原 verify.py 逐份读取四个快照核验片段。

## 2. Prompt 集成

实际入口为 `backend/app/main.py` → `backend/app/m3.py` → 既有 `llm.complete_json` → DeepSeek。旧 coach.py 保留供历史适配辅助函数使用，当前 V3 的分析路由不再使用旧自定义模板。V1、V2、Claude 的 Docker 固定版本未改。

使用原 Markdown 的 `text` 围栏中的系统消息，正文 SHA-256 为 `85b8f6298336f9c24ecb4a578b68cb965ffc387992ffd8d4dec475d21eb10c9b`。没有改写原文件或其中的辅导规则；最终运行时在原系统消息后重申相同的 JSON 键名、枚举和字段类型，避免仅有 JSON 语法正确而外层协议不符。原 transport 的 JSON 输出指令仍保留。状态接口的哈希指原系统消息；完整运行时消息另有哈希。用户请求使用 task、ui_language、user_stage、job_goal、resume_format、resume_text、jd_text、rag_chunks 和面试字段。

|功能|按正式原文执行的要求|现有 UI 适配|
|---|---|---|
|简历优化|最多 3 条，original/jd_quote/rewrite/reason，questions_to_student；原句语言及事实范围不变|映射到原审核表，逐条确认、编辑、保留、撤销与导出仍可用；补充问题显示在结果中|
|岗位匹配|required/preferred/unspecified；direct/partial/not_evidenced；JD 和简历原句、原因、下一步|适配到现有证据表；未覆盖要求显示“未评估”，不会假装匹配通过|
|模拟面试|start/respond/finish，一次一问，默认两道主问题，每道最多一次追问；反馈仅依据实际回答|保存问题、回答、反馈及总结；可复用反馈携带的下一题，避免重复调用|
|评分|原文没有百分制评分或录用概率|没有新增评分规则或录用概率|
|前置选择|明确选择语言，再选身份和实习/正式工作|加入材料面板，随项目 JSON 保存；不替用户预选示例身份；缺项不调用模型|

材料分段和 JD 引文整理使用本地确定性处理，不再为准备材料额外调用模型。只有实际 AI 分析/面试操作记入原有每账户每日 10 次账本；规则及密钥配置未改。

原文为经历唯一依据；JD 和 RAG 不写成用户技能。后端核对改写引用的原句及 JD 引句，保留局部改写之外的文字，隐藏无法唯一定位的改写。新增数字、工具、协助/参与范围变化或否定条件丢失会进入人工核实流程。匹配中的虚构证据被移除并降级。只接受当前检索命中的 citation ID，链接来自版本内来源清单。

身份/目标变化也会使结果过期；历史无这些字段的存档仍兼容，不迁移、不删除。无简历、无 JD、缺语言或选项均明确提示，保持既有要求提供 JD 的工作流；目前没有启用“无 JD 的通用优化”。

## 3. RAG 集成

沿用 Claude 的纯本地 BM25、英文分词、中文二元词及简繁词扩展，不增加向量库或付费服务。先按任务筛选，再以任务意图、JD、部分简历与当轮问题检索最多 3 段。模型不参与检索，不消耗 AI 额度。

|官方知识页面|片段数|证据边界|
|---|---:|---|
|图书馆 Resume & CV writing|5|只证明列出了履历资源|
|图书馆 Career Exploration|7|职业探索导览及资源目录|
|图书馆 Interviewing & Presentations|4|面试/展示资源目录和导览|
|电子工程学系 2019 年工作坊报道|2|仅支持那次历史活动的描述|
|合计|18|4 份来源快照|

启动核对：原始页面 SHA-256、片段 SHA-256、官方来源域名、锚点原文、来源片段数量、重复 ID 和三个任务覆盖。损坏、缺失或重复时整库停用并返回真实错误状态，分析可使用空 rag_chunks 继续，不虚构引用。加载后运行三个实际检索自检；不硬编码“已接入”。

检索用例：personal statement/sample resumes → resume-03；900 occupations/O*NET → career-03；STAR/peers feedback → workshop-01。均通过，并验证简体、繁体扩展及无命中返回空数组。

正式请求中的 RAG 已在 Mock HTTP 请求和真实 DeepSeek 请求两级验证。`tests/evidence/m3/local-results.json` 保留六次成功请求的系统消息哈希、task、语言、真实 chunk_id 和不同项目简历哈希；不记录密钥。指南来源与模型实际引用分别显示，没有将“被检索”当成“已引用”。

## 4. 测试及回归证据

|层级|结果|证据|
|---|---|---|
|接手后原始基线|33 项通过|tests/evidence/m3-baseline.log|
|新增单元/接口测试|50 项通过|tests/evidence/m3-unit.log、unit-tests.log|
|前端|TypeScript、Vite 构建通过|tests/evidence/m3-build.log；仅原有 bundle 大小提示|
|完整 Mock 回归|竞态、API/RLS/10 次额度、浏览器主流程通过|tests/evidence/m3-release-final.log；e2e-results.json、race-results.json、api-integration.json|
|真实 DeepSeek 本地|优化、匹配、提问、反馈、总结、第二项目匹配六次成功|tests/evidence/m3/local-results.json、raw-*.json、m3-real-app.log|
|真实多项目|两份虚构简历、不同 JD 分别分析，保存、切换两轮、刷新恢复|同上，两个简历 SHA 不同，档案隔离|
|完整导出|PDF 和 DOCX 可重新打开，包含与预览一致的完整正文|tests/evidence/m3/local-final.pdf、local-final.docx、local-final.png|

本地 Auth/Storage 为明确的模拟服务，数据库为隔离 PostgreSQL，模型调用是真实 DeepSeek。模型格式失败、超时、HTTP 503、额度耗尽等故障由明确 Mock 测试验证，不能视为真实故障注入。真实六次业务调用没有使用硬编码响应。

真实调用过程中另一次岗位匹配收到 HTTP 200，但外层不符合 M3 协议，后端返回 AI_FORMAT/m3_envelope；没有保存为成功结果。一次后续真实重试成功。首次原始 JSON 未保留，因此不能确定缺少哪一个外层字段，不能把它说成认证失败。相关观测在 observed-format-failure.json。测试脚本的选择器及 PDF 空白比对问题已修正；为节约额度，途中复用同一测试账户中已保存的真实结果继续核验，不伪装成额外模型调用。

回归覆盖：注册表单和模拟邮件确认、登录/退出/恢复、项目新增/重命名/删除自定义确认、切换和隔离、三页 PDF 提取及预览、扫描件提示、JD 编辑、人工审核全部决定、撤销、保存失败恢复、过期拦截、中英繁切换、浏览器返回、PDF/DOCX 完整性；浏览器无严重 JS 错误或原生弹窗。真实邮箱投递链路本轮未重测。

复现命令（PY 指安装了 tests/requirements 的现有测试解释器）：

```sh
PYTHONPATH=backend "$PY" -m unittest discover -s backend/tests -v
"$PY" backend/data/rag_v1/verify.py
QA_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/coachtest_v3_audit_NAME "$PY" tests/run_audit.py
# 配置隔离 QA 服务为 QA_REAL_MODEL=1 后（使用既有私有配置，不在命令行传密钥）：
"$PY" tests/m3_real_e2e.py
# 部署后，使用现有私有配置中的专用测试账户：
M3_HOSTED=1 "$PY" tests/m3_real_e2e.py
```

## 5. 部署状态

实现提交 `38fd606`；原始快照保护 `f604163`。首次构建在发布前主动取消，以补齐“默认界面语言不等于用户明确选择”的门槛。最终提交、部署及线上验收结果在文末追加，不将构建中或本地通过视为线上通过。

无需新增依赖、数据库迁移、环境变量或付费服务；Docker 已复制整个 V3 backend，因此 Prompt、语料、来源清单、原始快照都在镜像中，启动从文件重新加载。没有访问/修改真实用户档案或重置额度。自动部署仍关闭；手动部署现有服务，不创建额外 Render 服务。

## 6. 遗留事项和边界

- 原 RAG 本身缺少详细的改写手册、能力矩阵和评分表，不能把目录或 2019 年活动说成学校当前标准。
- 文本事实核对与范围提示是保守启发式，不能数学证明模型的所有语义判断正确；投递前仍须人工核实。模型偶发非协议输出会明确报错，手动重试；服务端不自动重复消耗额度。
- Word 上传与扫描件 OCR 沿用当前未实现状态；PDF/文字和扫描件预览保留，没有做假按钮。
- 补充笔记保留，但依正式 Prompt，经历证据只取 resume_text；需参与分析的已核实信息应写入正文，界面已说明。
- 语言与前置选项随项目存档；旧项目不补写虚构身份。重新生成时需提供缺少的选择。
- JD 导入不属于本轮主线：修复版 `bbe78f0` 的 job_import.py 未修改，17 项相关回归仍通过。此前 Nowcoder、Greenhouse、Lever、Python.org 的真实线上导入已通过；Nowcoder 职位已结束，原样保留状态。登录、验证码、拒绝自动访问的网站仍明确失败，不绕过访问限制；详见 V3-JD-IMPORT-AUDIT.md。本轮新部署后的抽检结果另行记录。

## 后续线上发现与修复记录

初次线上发布 f1be781 后，实际发现：

1. 认证中间件一次返回 HTTP 503 Authentication unavailable，尚未进入 DeepSeek，额度保持 0；随后 me/quota/health 均恢复 200。没有误报为 DeepSeek 或 Claude Credentials rejected。认证仍失败关闭，没有放宽权限或更换配置。
2. JD 中“一行两句要求”未在原 PDF 分段的 260 字阈值以下拆开，且结果以 requirement_id 覆盖写入，导致后一个评估覆盖前一个。现在逐句建立要求、跳过标题前言，并保留同一句内多个模型评估及各自证据与下一步。针对性测试验证不会覆盖。
3. 线上总结两次被严格外层校验拒绝，均显示 AI_FORMAT/m3_envelope，未保存假总结。用相同测试材料与已发生问答在本地直接调用真实 DeepSeek，得到合法完整原始对象，说明并非确定性的材料或认证错误。原线上两次响应正文未记录，不能猜测具体缺失字段；新版错误返回安全的字段类型诊断，并在系统消息中重申正式原文的机器协议，不自动重复调用模型、不猜补分析结果。新约束本地真实总结调用为 HTTP 200，原始对象保留在 raw-mock_interview.json。最终线上结果以最终验收追加为准。

新解析器有版本标记。旧项目仍可查看和导出原有结果；下一次主动生成会先刷新材料，防止用旧的要求编号解释新结果。新增浏览器用例验证旧存档缺少版本字段时保留结果，并在用户重新生成时刷新材料。原语料 workshop-01 与 workshop-02 有原始内容重叠，保留提供方片段；所有 chunk_id 唯一，每个只索引一次。

匹配界面按正式返回的 required/preferred/unspecified 分组，明确必备条件先于优先条件；不再用准备阶段的粗分类覆盖模型优先级。历史结果没有 priority_code 时继续使用原来的分类显示。

最终完整线上流程在 215e5bc 上通过（见 hosted-results.json）：6 次成功分析及一次被拒绝的格式响应，测试账户额度 0→7，原始 PDF 预览字节一致、双项目、三语言、导出和检索均通过。首次匹配错误的安全诊断明确为 status=ok、result=dict、citations=None；不推断早先两次总结具有相同原因。针对这一已证实的问题，最后补丁将 null/缺失 citations 仅归一为 []，记录 protocol_warnings=citations_missing，所有来源 used=false；不编造引用、不补写分析内容，也不额外调用模型。非数组引用或不合法正文仍拒绝。针对性测试证明只调用一次模型，最终补丁部署与真实抽检另见末尾。
