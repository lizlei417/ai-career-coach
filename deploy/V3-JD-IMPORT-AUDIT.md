# V3 JD 链接导入排查与验收

2026-11-22，香港时间。本轮修复已发布到现有 Render 服务的 `/v3/`。上线源码为 `bbe78f0`，部署 ID `dep-dc0ul2qjnfac73f3vqu0`，Render 显示 Live，构建上线耗时 1 分 43 秒。测试使用独立 QA 账号和新建测试项目，没有修改用户截图中的项目、V1、V2 或 Claude 代码。

## 1 实际根因

前端调用地址是正确的：同源 `POST /v3/api/extract/url`，JSON 参数 `{url: 用户输入}`。浏览器网络记录验证了实际方法、路径和参数。原失败是后端返回 HTTP 422 的 `URL_FETCH_FAILED`，没有发现这两个案例由 CORS 或不存在的接口引起。

**后端重复解压 gzip 是已复现的直接根因。**旧实现用 `response.aiter_bytes()` 读取正文，这一步已经由 HTTPX 解压；随后却用原来的 `response.headers` 和解压后的正文重建 `httpx.Response`。原头部仍含 `Content-Encoding: gzip`，导致 HTTPX 再次解压普通 HTML，产生：

```text
DecodingError: Error -3 while decompressing data: incorrect header check
```

异常又被 `except httpx.HTTPError` 归并成没有 detail 的 `URL_FETCH_FAILED`，前端因此只能显示“无法访问这个链接”。实际牛客网页、用户的 Greenhouse 网页及该岗位的公开 API 均返回 HTTP 200/gzip。保存这三份真实响应后，旧式重建均可确定性复现同一个异常。

其次，旧 HTML 解析没有平台 API、JSON-LD 支持，且只遍历部分 HTML 标签。牛客的职责/要求实际放在 `.job-detail-infos` 内的 `div` 中，旧选择器不能可靠提取这些正文。普通网页第一处 h1 也可能是站点标题，而非岗位名。这些解析问题一并修复。

本机还有独立的测试网络差异：VPN 对部分域名返回 `198.18.0.0/15` 假 IP，必要的 SSRF 校验会拒绝它。没有为此放宽生产安全检查。本地真实联网测试通过 `tests/public_dns.py` 在测试进程中获取真实公网 DNS 记录并固定连接公网 IP；网页响应从未 Mock。Render 使用正常系统 DNS，不加载这个测试文件。

## 2 修改文件与实现

| 文件 | 修改及原因 |
|---|---|
| `backend/app/job_import.py` | 新的下载及解析模块。原始压缩字节只解压一次；区分 DNS、连接、上游 HTTP、解码、解析、超时和内部异常，记录 import_id、host、阶段、上游状态、错误类型及耗时 |
| `backend/app/materials.py` | 保持原公开导入函数和 FastAPI 接口兼容，转到新模块；简历 PDF 提取及段落分割不改 |
| `backend/requirements.txt`、`deploy/requirements.txt` | 显式声明已有 HTTPX 依赖链中的 `httpcore>=1,<2`，使用其公开网络后端接口固定安全 IP，保留原主机 TLS 验证 |
| `frontend/src/components/MaterialsPanel.tsx` | 加入导入中保护和重试；请求期间禁用 URL/JD/岗位名以避免异步覆盖；只在真实成功时回填；失败保留已有材料 |
| `frontend/src/lib/store.tsx` | 在原项目 JSON 中增加可选的 `jdSourceUrl`，成功导入来源与未成功的 URL 草稿分开，不改数据库结构 |
| `frontend/src/lib/api.ts` | 链接请求的浏览器超时映射为 URL_TIMEOUT，不误报 AI 超时 |
| `frontend/src/lib/i18n.ts` | 简体、繁体、英文分别提供格式错误、非公网地址、DNS、404/410、403、429、超时、压缩异常、内容过大、无岗位内容、内部异常等提示 |
| `backend/tests/test_materials_url.py` | 压缩、编码、错误分类、SSRF、DNS 固定、JSON-LD、ATS API、标题范围等回归测试 |
| `tests/jd_sources.json`、`jd_live_probe.py`、`jd_import_e2e.py` | 真实公开链接探测与本地/Render 浏览器 E2E，不预写 JD 或伪造成功响应 |
| `tests/public_dns.py` | 仅解决本机 VPN 的假 IP 测试问题，不在生产入口加载 |
| `tests/qa_server.py`、`run_audit.py`、`e2e_audit.py` | 保留原整体功能回归；明确区分真实外部抓取和已有 Mock 流程，并适配新的准确安全提示 |

Greenhouse 使用官方 [Job Board API](https://docs.greenhouse.io/job-board.html)；Lever 使用官方 [Postings API](https://github.com/lever/postings-api)。仅使用公开 GET 接口，不提交申请，不使用账户 Cookie，不绕过登录、验证码或访问限制。

普通网页优先读取 JSON-LD JobPosting，包括 @graph；否则选取岗位正文容器或 article/main，并排除表单、导航、侧栏和推荐信息。HTML 实体、UTF-8/HTTP 指定字符集、gzip、zlib/raw deflate 均有测试。提取岗位名、公司及地点时使用实际页面/公开 API 字段，不编造缺失信息。

## 3 四个真实链接的实际结果

以下每个来源都完成了：粘贴 URL → 点击导入 → 真实请求 → 回填 JD → 人工编辑 → 已保存 → 切换到空白项目 → 切回恢复 → 刷新恢复。本地和 Render 浏览器都验证，且检查了实际 POST 参数及保存结果。

| 来源与链接 | 实际岗位 | Render 结果 | 导入方式与长度 |
|---|---|---|---|
| [用户牛客链接](https://www.nowcoder.com/jobs/detail/315366) | AI产品运营实习生，慧搭信息 | HTTP 200，完整链路通过 | `nowcoder_html`，347 字符；职责、要求、地点；排除导航及安全提示 |
| [用户 Greenhouse 链接](https://job-boards.greenhouse.io/globalizationpartners/jobs/8207500003?gh_src=remoteitjobs.app&utm_source=chatgpt.com) | Product Management Intern – AI & Analytics，G-P，India (Remote-First) | HTTP 200，完整链路通过 | `greenhouse_api`，7,276 字符 |
| [Spotify Lever 岗位](https://jobs.lever.co/spotify/2a55d6c9-c564-443a-be3e-a3851db5a93b) | Account Executive - Commercial, Spotify Technology，New York | HTTP 200，完整链路通过 | `lever_api`，4,613 字符；正文及 requirements 列表保留 |
| [Python.org 普通 HTML 岗位](https://www.python.org/jobs/8219/) | Senior Image Analysis Software Engineer，Nick Gilbert Neurofibromatosis Research Institute | HTTP 200，完整链路通过 | `html`，4,835 字符；正确区分站点标题与岗位标题，不混入推荐岗位 |

字符数为返回 JSON 的 text 长度，不是 UI 去空格后的计数。牛客页面现在明确显示“已结束”，导入时保留了这个状态；不把它说成正在招聘。

Render 实际应用日志已核对，例如：

```text
id=b11c57ab2469 stage=http host=www.nowcoder.com status=200 encoding=gzip
id=b11c57ab2469 stage=done host=www.nowcoder.com status=200 source=nowcoder_html chars=347
id=1a7ea49752e4 stage=http host=boards-api.greenhouse.io status=200 encoding=gzip
id=1a7ea49752e4 stage=done host=job-boards.greenhouse.io status=200 source=greenhouse_api chars=7276
id=b8caf2ce11f5 stage=done host=jobs.lever.co status=200 source=lever_api chars=4613
id=f9a39d4f49d9 stage=done host=www.python.org status=200 source=html chars=4835
```

这是 Render 中的真实出站请求，未使用本机 DNS 测试辅助文件或模拟 JD 响应，也没有新增抓取代理、付费服务或 API Key。

## 4 失败、重试和安全验收

| 场景 | 实际上游/阶段 | 结果 |
|---|---|---|
| `not a URL` | validate；未发出网页请求 | URL_INVALID，表单可恢复 |
| Greenhouse 不存在 ID `99999999999999999` | 实际 API HTTP 404 | URL_NOT_FOUND，已有材料不变 |
| `https://httpbingo.org/status/403` | 实际 HTTP 403 | URL_ACCESS_DENIED，已有材料不变 |
| 本地 `https://httpbingo.org/delay/15` | 真实 read 阶段 ReadTimeout，未收到 HTTP 状态 | URL_TIMEOUT，Loading 恢复、可重试；额外有确定性 timeout 单元测试 |
| Render 同一 delay/15 探针 | 上游实际 HTTP 400，响应说明 15 秒超过服务的 10 秒上限 | 正确返回 URL_HTTP_ERROR；**未把该请求记作线上超时验证通过** |
| `https://www.python.org/about/` | HTTP 200，parse 阶段未找到岗位内容 | URL_NO_CONTENT，不伪造成功 |
| `http://127.0.0.1/private` | dns/validate，阻止连接 | URL_UNSAFE，已有材料不变 |
| 修改错误 URL 后点击“重试” | 使用真实 Greenhouse API，HTTP 200 | 本地和 Render 均恢复正常回填与保存 |

Render 的人工延迟探针未成功产生超时，是测试服务参数限制，不是将上游 400 误判为超时。线上强制超时未额外验证；本地实际网络 ReadTimeout、端到端提示/恢复，以及后端确定性超时测试都已通过。这个边界保留在 `hosted-e2e.json` 的 timeout_not_observed 字段中。

一次本地额外牛客重试曾收到 HTTP 200 但没有找到岗位正文容器，返回 URL_NO_CONTENT 并保留旧 JD；随后实际页面探测和 Render 完整流程均成功。未取得该次页面变体的完整正文，不能据此宣称反爬，也没有自动切 IP 或绕过验证。失败分类和回退粘贴机制仍保留。

SSRF 与资源保护：

- 仅允许 HTTP/HTTPS、公网目标和 80/443 端口；拒绝 URL 中的账户凭证。
- 拒绝 localhost、私网、链路本地、云元数据地址、CGNAT/基准测试地址、IPv4 映射 IPv6 及其他非公网目标。
- DNS 返回混合公网/私网也拒绝；校验的公网 IP 固定用于实际 TCP 连接，TLS 主机名仍为原域名，防止校验后重解析的 DNS rebinding。
- 每个重定向都重新验证，最多 5 次跳转。
- 总预算 28 秒，DNS 5 秒、连接 5 秒、读操作 10 秒；不采用无限重试。
- 原始响应和解压后正文分别不超过 2 MiB，最终 JD 不超过原有 30,000 字符上限。
- 不转发用户 Cookie/认证头，不执行网页脚本，不访问 JSON-LD 引用的额外资源。

## 5 测试、证据和发布状态

后端现有与新增测试合计 **33 项通过**。原全流程 `run_audit.py` 再次通过项目、简历、PDF 预览、Mock AI、审核、最终导出、保存失败恢复和语言切换回归。真实来源 E2E 与这些 Mock AI 测试分开记录，不把 Mock 当成真实抓取。

本轮没有调用 DeepSeek；仅 JD 获取和解析。V1、V2、Claude 线上 HTML 与静态资源逐项和发布前一致。V2 的 92 个存档文件仍完全一致。无数据库结构迁移，无密钥或额度修改。

本地证据位于 `tests/evidence/jd-import/`（不推送到公开仓库）：

- `before.json`、`reproduction-decode.json`、`double-decode-evidence.json`：原失败与重复解压证据。
- `all-unit.log`：33 项后端测试。
- `local-e2e.json`、`hosted-e2e.json`：真实成功/失败流程、保存恢复、重试和范围标记。
- `local-e2e.log`、`hosted-e2e.log`、`app-local.log`：浏览器与后端实际记录。
- `render-log-excerpt.txt`：Render 可见应用日志。
- `hosted-nowcoder.png`、`hosted-greenhouse.png`、`hosted-lever.png`、`hosted-html.png`：线上真实 JD 已回填并保存的界面。
- `render-live.jpg`、`versions-preserved.json`：发布与旧版本保留证据。
- `frontend-build.log`、`full-regression.log`：构建和原功能回归。

可复现：

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
# 准备好 tests/README.md 的独立本地 Auth/PostgreSQL 服务后：
QA_REAL_JD_IMPORT=1 QA_PUBLIC_DNS=1 ... python tests/qa_server.py app
python tests/jd_live_probe.py
python tests/jd_import_e2e.py
# 使用现有独立 hosted QA 账号，真实访问 Render：
python tests/jd_import_e2e.py --hosted
```

公开职位以后可能下架，真实链接测试届时应报告 404/410，而非改用预写内容。只依赖浏览器运行脚本或登录后才显示正文的其他网站仍可能无法导入，系统会明确提示，并允许粘贴原文。本轮四个实际招聘来源均已成功。

**当前可以刷新 V3 再试原链接。**发布不是待操作项；已部署并完成线上核心验收。唯一没有额外完成的线上强制场景是被上游 400 拒绝的延迟探针，已按上述边界如实标记。
