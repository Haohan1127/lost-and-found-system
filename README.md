# 校园失物招领 · 成员 C

已实现成员 C 的三个功能模块：**认领流程、双方站内沟通、规则匹配**。技术栈为 Django 5.2 + DRF + Vue 3 + Vite，数据库为 SQLite。

包括认领提交、我的认领/收到的申请、同意/拒绝/取消、双方交接确认、私有消息和匹配页面。后端按既有 `/api/v1` 契约实现 10 个方法/路径组合。

仓库原先只有协作设计文档。本次补充的 `users`、`catalog`、`posts` 是供 C 独立运行的最小依赖；`demo` 提供演示登录、只读物品和撤回/恢复联调入口。**A 的完整注册/身份绑定/资料管理、B 的发布/搜索/编辑/图片功能仍由对应成员完成。**

## 启动

环境：Python 3.11+、Node.js 20.19+（或 22.12+）、npm；浏览器测试默认使用本机 Google Chrome。本次验证使用 Python 3.11、Node.js 24.15。

在项目根目录打开 PowerShell，首次执行：

```powershell
Set-Location 'D:\失物招领'
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

初始化会创建项目内 `.venv`、安装依赖、执行迁移并生成演示数据，终端输出演示密码。四个账号共用这次生成的演示密码：

| 账号 | 用途 | 身份 |
|---|---|---|
| `publisher` | 审核申请、与失主沟通、确认交接 | 演示认证 |
| `applicant` | 查找匹配、提交认领、沟通与确认 | 演示认证 |
| `competitor` | 竞争申请与非参与者权限验证 | 演示认证 |
| `unverified` | 验证未绑定身份不能申请 | 未认证 |

然后在两个终端分别运行：

```powershell
# 终端 1
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1

# 终端 2
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

打开 [演示工作台](http://127.0.0.1:5173)。前端开发服务器代理 `/api` 到 `127.0.0.1:8000`。两个不同浏览器窗口可分别登录失主和拾获者；同一窗口也可以退出后切换账号。令牌仅保存在内存中，刷新后需重新登录。

若忘记演示密码，在根目录执行：

```powershell
.\.venv\Scripts\python.exe backend\manage.py seed_demo --reset-passwords
```

该命令只重置四个演示账号的密码和会话，不删除申请、消息，也不重新开放已完成物品。重复初始化保留既有物品和申请状态。需要重新演示时可使用另外两件演示招领物品；终态认领记录保持只读。

## 验证

```powershell
# 后端、迁移一致性、前端单元测试和生产构建
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1

# 同时执行真实 Chrome 浏览器测试
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1 -Browser
```

浏览器验收启动专用的 `8001`/`5174` 服务，使用 `backend/e2e.sqlite3`，每次启动只清空这份隔离测试数据库。普通演示数据库 `backend/db.sqlite3` 保持不变。两个端口不能已有其他服务占用。

本次结果：后端 **52/52**，前端 **21/21**，浏览器 **4/4**，Vue 生产构建通过。场景和截图见[联调与验收](docs/联调与验收.md)。

## 文件入口

| 内容 | 路径 |
|---|---|
| C 的模型、接口、权限、消息、匹配 | `backend/claims/` |
| C 的跨模块事务与状态机 | `backend/workflows/claim_workflow.py` |
| B/C 撤回/恢复联调流程 | `backend/workflows/post_workflow.py` |
| C 的四个页面及复用组件 | `frontend/src/modules/claims/` |
| 真实浏览器验收 | `frontend/tests/e2e/claims.spec.js` |
| 需求、设计、数据模型和个人报告 | [C-失物认领](docs/reports/C-失物认领.md) |
| A/B 接入方法和实际验收记录 | [联调与验收](docs/联调与验收.md) |

## 实现边界

同意申请、关闭竞争申请、物品进入交接中，在一次事务内完成；双方都确认才完成申请和物品。数据库使用有效申请和交接对象的条件唯一约束。SQLite 使用 `IMMEDIATE` 写事务，避免将 `select_for_update()` 当作 SQLite 行锁；本次并发验收使用独立连接访问同一文件数据库。依据：[Django SQLite 事务说明](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes)、[锁定查询说明](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update)。

校园认证使用明确标识的演示数据。匹配分数仅为规则分，不验证失主身份。交接争议、确认撤销、管理员、真实学校认证不在三人第一版范围内。

环境变量示例见 `backend/.env.example` 和 `frontend/.env.example`；后端读取进程环境变量，不自动加载 `.env`。`DJANGO_DEBUG=0` 时演示路由关闭，并要求显式设置密钥；正式 A/B 接口尚需接入，因此当前交付以本地课程演示和联调为准。
