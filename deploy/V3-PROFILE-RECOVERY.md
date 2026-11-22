# V3 旧项目分析入口修复

用户截图中的现象来自前端：历史项目没有 languageConfirmed/userStage/jobGoal，新检查直接报 LANGUAGE_REQUIRED；当前语言在左下角显示已选，但侧栏滚动使新选择区不可见，缺少可发现的恢复入口。

修复：分析、改写、匹配及面试操作在缺选项时打开既有设计风格的 ProductDialog。沿用当前界面语言显示并由用户明确确认；身份、目标保留已有值，缺项由本人选择，不推断。确认后同步更新当前操作读取的状态并继续原请求，不需再点击一次；取消不调用模型。共享正在等待的确认，并在异步确认后再次检查请求锁，防止双击重复消费。侧栏固定标题增加“求职选项”入口，不再依赖滚动找表单。

不清理缓存、账户、材料或旧分析；不修改后端、正式 Prompt/RAG、API Key、额度、V1/V2 或数据库。

验证：

- profile_recovery_e2e：明确 Mock Auth/Storage/模型，真实浏览器、后端、隔离 DB。制造缺少所有新字段的旧存档、滚动侧栏；取消不丢材料不消费，确认后自动继续；双击只调用一次模型；刷新保存选择；两个项目隔离；Esc 关闭。通过。
- 既有简历审核/导出/项目/语言主流程 E2E 及两主题/追问面试 E2E 通过。
- 原有 50 项后端测试通过。TypeScript、Vite 构建通过。
- 证据：tests/evidence/profile-recovery.json、profile-recovery-modal.png、profile-recovery.png、profile-recovery-run.log、profile-full-regression.log、profile-build.log。

发布与线上验证另行追加。

线上首轮还复现了第二个前端问题：健康接口暂时不可读时 llm=null，旧 `!llm?.configured` 条件将其误报为“没配置模型”，没有发出模型请求（专用账户额度仍为 7）。修复为仅在后端明确报告 configured=false 时做本地拦截；状态未知允许后端判定，状态栏显示“状态暂未获取”。未放宽服务端认证、配置检查或额度限制。定向 E2E 现在故意让所有 /api/health 返回 503，完整验证取消、确认继续、去重、保存与刷新，依旧通过。


最终发布：Render `d10e834fa3d60126f8c7cfd3a3c47166cc3a51ac`，部署 `dep-dc1218ec6qcc73clsmig` 已 Live（构建/健康检查 1 分 25 秒）。

线上真实复测已通过：专用 QA 账号中新建独立虚构项目，构造没有语言确认、身份和目标字段的历史存档，滚动侧栏后从“生成改写建议”进入；取消不请求模型；确认自动调用真实 DeepSeek，HTTP 200、恰好 1 次调用（额度 7→8），简历和 JD 原文未变，选项和完整分析结果保存并在刷新后恢复。证据：tests/evidence/profile-live/result.json、modal.png、recovered.png，以及 profile-live-run.log。没有操作用户截图中的真实项目。

此前线上脚本第一次停在设置页（脚本已补充进入工作台），第二次复现健康状态未知被误拦截，两次均未调用模型、额度未变；没有将失败记录当成通过。修复后的通过记录和此前失败文件均保存在本地忽略目录。

后续仅提交测试脚本和报告，应用代码与 Render 的 d10e834 完全一致。无需依赖、环境变量或数据库迁移；未变更密钥、认证、10 次规则或其他版本。
