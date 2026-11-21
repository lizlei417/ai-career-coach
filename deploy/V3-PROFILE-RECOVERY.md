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
