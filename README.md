# AI Career Coach V4

V4 从 V3 提交 `495acc91f884d4ca971d350c63f8dfd13aa62eef` 独立开发。进入工作台可以选择职业测评、岗位匹配或面经复盘。岗位匹配页先展示职业方向与企业招聘板职位，再展示原有 JD 匹配报告。

| 本地入口 | 路径 |
|---|---|
| 工作台 | `/v4/workspace/overview` |
| 测评 | `/v4/workspace/explorer` |
| 岗位方向、招聘与匹配 | `/v4/workspace/match` |
| 面经复盘 | `/v4/workspace/reviews` |

在本目录运行 `./start.sh`，打开 [本地 V4](http://127.0.0.1:8114/v4/) 。首次构建需要 Node 22、npm 和 Python 3.11+。使用 V3 原有的 Supabase、PostgreSQL 与 DeepSeek 服务端配置。Lever 招聘板无需新增密钥。登录后可在当前项目中编辑求职材料。

V4 普通项目使用 `codex_v4`，账户测评、复盘和推荐使用 `codex_v4_exploration`。模型限额仍按同一账户、香港日期跨版本计数。已有 V3 数据库无需迁移。Render 配置以独立预览服务为目标，默认关闭自动部署。

[完整中文交付与测试记录](deploy/V4-DELIVERY.md) · [V3 历史上线记录](deploy/V3-LIVE-ACCEPTANCE.md)
