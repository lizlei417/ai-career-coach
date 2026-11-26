# AI Career Coach for University Students

香港城市大学 IS5542 小组项目。从欢迎页直接进入一站式工作台，共用同一份简历、岗位描述和原文出处，随时进入简历优化、岗位匹配或模拟面试。默认 English，可切换简体中文与繁體中文。

## 在当前电脑启动

```bash
cd /Users/zhouli/Documents/ChatGPT/IS5542/career-coach-codex
./run.sh
```

打开 [本地工作台](http://127.0.0.1:8765/)。启动脚本使用项目的 Python 虚拟环境，由 FastAPI 同时提供网页与 API。仓库内已有构建好的前端，本机演示无需安装 Node。使用 Ctrl+C 停止服务。可用 `PORT=8766 ./run.sh` 更换端口。

## 在新环境安装

建议使用 Python 3.12。以下命令在项目目录执行。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

Windows 可使用 `.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8765 --no-access-log`。运行时保留一个 Uvicorn worker，使同一项目的后续请求能读取同一份内存状态。

## 启用真实 AI

在服务端环境设置 `OPENAI_API_KEY`，或复制 `.env.example` 为 `.env` 后填入密钥。已有 `.env` 时直接编辑即可。`OPENAI_MODEL` 默认使用 `gpt-4o-mini`，可替换为账户有权访问、支持 Responses API 及 Structured Outputs 的模型。环境变量优先于文件配置。

回到工作区设置点击“刷新状态”。配置密钥后，界面先显示“连接待验证”，实际模型请求成功后才显示“上次请求成功”。首次点击分析或开始面试时，服务才提取并核对共用资料。AI 操作会将相应的简历、岗位要求、指南和面试回答发送给 OpenAI，可能产生账户费用。

无密钥时可以直接进入工作台、导入 PDF 与公开 JD、检查原文、编辑材料和切换语言。此时只执行可读性、长度和分段检查。语义完整性检查在首次启用 AI 时完成，未通过时返回需要补充的材料。三个 AI 分析按钮会说明所缺配置。

## 演示流程

1. 在首页点击「开始使用」。工作台中间是共用材料编辑区，右侧是 AI 工作区。
2. 上传文字 PDF 或直接粘贴简历，再填写 JD 或点击「链接导入」读取公开岗位网页。PDF 上限为 10 MB、20 页。每份材料上限为 24,000 个字符，至少需要 30 个非空白字符的可读正文。
3. 选择右侧功能标签或侧栏入口，然后点击材料区中的分析按钮。分析采用当前已有的简历与 JD，结果直接显示在右侧。简历改写支持逐项采用、编辑和保留原句。岗位匹配可展开核对证据和建议。面试支持反馈、追问、重答、下一题与总结。
4. 阅读长结果时可收起材料区，随时展开继续编辑。材料一旦改动，工作台立即隐藏此前的结果；恢复原文可继续上次工作。以修改后的材料启动分析时，服务更新共用资料并重置基于旧材料的分析、改写选择和面试记录。
5. 标签切换会保留当前回答草稿。切换语言后，新生成的分析、问题和反馈使用新选语言，引用保留原文。已有结果可重新生成。

已提交的材料、结果和回答保存在服务内存中。刷新网页可恢复已提交内容。未提交的材料修改和回答草稿保留在当前页面，刷新后需重新输入。服务重启或闲置八小时后会话清空，也可以在「设置 → 清空工作台」中主动清除。浏览器存储语言、页面偏好与标签页的会话令牌。

## M3 指南与 Prompt

将取得授权的 PDF、UTF-8 TXT 或 Markdown 学校辅导资料放入 `knowledge/`，亦可通过 `KNOWLEDGE_DIR` 指定目录。设置页可查看载入文件、片段数和读取错误。分析按所选功能和岗位要求检索相关片段，结果只列出模型实际引用且已核对的文件名、片段 ID 和原文。当前交付未附学校指南。

提示词位于 `prompts/`。M3 的正式版本可替换相应文件，保留结构化输出、原文引用、事实核查与语言约定。当前版本已有可执行提示词。个人事实仅来自简历，岗位要求来自 JD，面试反馈以真实提交的本轮回答为依据。

## 开发与验收

`frontend/src/` 是 React、TypeScript 和 CSS 源码，`frontend/dist/` 是可直接运行的 Vite 构建产物。`server.py` 负责 HTTP 接口与项目会话，复用 `coach/` 内的解析、模型调用、检索、校验及面试编排。`assets/atrium.svg` 是本项目绘制的建筑图。旧版 Streamlit 入口保留在 `app.py`，用于历史回归。

前端开发使用 Node.js 22 与 npm，先运行 Python 服务，再在另一终端执行以下命令。Vite 开发代理默认连接本机 8765 端口。

```bash
cd frontend
npm ci
npm run dev
```

修改源码后在 `frontend/` 运行 `npm run build`，会先做 TypeScript 检查，再更新可交付文件。开发验收在项目根目录运行。

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
```

浏览器用例在临时端口启动独立测试服务，只替换模型传输层。测试数据不随生产网页载入。视觉检查截图保存在 `tmp/workbench/`。配置真实密钥后，可以用以下命令执行会产生 API 费用的合成材料冒烟测试。

```bash
.venv/bin/python tests/live_api_smoke.py
```

本轮验收范围与未验证项见 [测试记录](docs/TEST_REPORT.md)。重构前的源码、提示词、设置和资源备份在上级目录 `backups/`，压缩包不含可重建的虚拟环境与缓存。
