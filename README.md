# 校园失物招领系统 · 成员 A（用户管理）

本仓库是软件工程课程项目「校园失物招领系统」的实现。本次交付完成**成员 A 负责的用户管理子系统**：账号注册登录、校园身份绑定（演示认证）、个人资料管理，以及个人中心入口框架；前端为登录、注册、个人资料、校园身份绑定四个页面。

仓库同时保留成员 C 已完成的**认领、双方沟通与规则匹配**模块（`backend/claims/`、`frontend/src/modules/claims/`）和 B/C 所需的最小 `catalog`、`posts` 适配骨架。三方共同遵守 [`docs/共同字段与接口约定.md`](docs/共同字段与接口约定.md)。

技术栈：Django 5.2.18 + Django REST framework 3.16.1 + SQLite；Vue 3 + Vite + Vitest + Playwright。

## 1. 功能范围

### 1.1 成员 A：用户管理（本次交付）

| 功能模块 | 能力 |
|---|---|
| 注册登录 | 账号注册（4～32 位字母/数字/下划线、唯一、统一小写）、登录（24 小时可撤销 Bearer 令牌）、退出登录（仅撤销当前会话） |
| 校园身份绑定 | 登录后使用预置“校区 + 学号 + 一次性绑定码”完成**演示认证**；未绑定返回 `null`，已绑定返回末 4 位脱敏学号；绑定后置认证标记，供 B/C 校验 |
| 个人资料管理 | 查看/修改本人昵称（1～30 字）与简介（0～200 字）；账号、认证标记等只读字段不可由客户端写入 |
| 个人中心框架 | `/me/profile`、`/me/campus-binding` 页面框架；登录守卫与回跳；B/C 的“我的发布/我的认领”由对应成员接入 |

后端接口（前缀 `/api/v1`，无结尾斜杠）：

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | 匿名 | 201 `UserSelf`，不自动登录 |
| POST | `/auth/login` | 匿名 | 200 `access_token`、`token_type`、`expires_at`、`user` |
| POST | `/auth/logout` | 登录 | 撤销当前令牌 |
| GET / PATCH | `/users/me` | 登录 | 查看 / 修改本人资料（`nickname`、`bio`） |
| GET / POST | `/users/me/campus-binding` | 登录 | 查询绑定（未绑定 `null`）/ 提交绑定 |

响应统一 `code/message/data`，错误另含 `errors` 对象；错误码与字段约束见共同契约第 2、3.2、3.3、4 节。

### 1.2 成员 C：认领、沟通与匹配（既有实现）

保留并回归通过：认领申请、发布者审核、双方确认交接、站内消息、规则匹配；前端页面位于 `/claims/*`、`/me/claims`、`/posts/:id/matches`。说明见 [`docs/reports/C-失物认领.md`](docs/reports/C-失物认领.md)。

## 2. 快速开始

环境：Windows + PowerShell、Python 3.11+、Node.js 20.19+（或 22.12+）、npm；浏览器验收使用本机 Google Chrome。

```powershell
Set-Location '<仓库根目录>'
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

初始化会：创建项目内 `.venv`、安装后端依赖（默认清华 PyPI 镜像，可用 `PIP_INDEX_URL` 覆盖）、`npm ci`、执行迁移、生成演示数据与演示校园身份。

随后在两个终端分别启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1   # http://127.0.0.1:8000
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1  # http://127.0.0.1:5173
```

打开 <http://127.0.0.1:5173>，未登录时进入登录页（`/login`），可注册新账号或使用演示账号。前端开发服务器把 `/api` 代理到 `127.0.0.1:8000`。

### 2.1 演示数据

`setup.ps1` 依次执行 `seed_demo` 与 `seed_demo_users`：

- 演示账号（密码由 `seed_demo` 输出，四个账号共用）：`publisher`、`applicant`、`competitor`（演示认证）、`unverified`（未认证）。
- 演示校园身份（`seed_demo_users` 输出一次性绑定码，明文只打印这一次）：
  - `20260001`～`20260003` 已自动绑定三个演示认证账号；
  - `20260004`～`20260006` 未使用，可在“校园身份绑定”页完成绑定演示。

忘记密码或绑定码：

```powershell
.\.venv\Scripts\python.exe backend\manage.py seed_demo --reset-passwords
.\.venv\Scripts\python.exe backend\manage.py seed_demo_users --reset-codes
```

两条命令都幂等：`--reset-codes` 只重置未使用身份的绑定码，不改动已绑定记录、申请与物品状态。

### 2.2 演示 A 模块流程

1. 打开 `/register` 注册新账号（注册成功不自动登录，回到 `/login`）。
2. 用新账号登录 → 顶部出现“个人中心”；认证状态为“未认证”。
3. `/me/campus-binding` 输入校区 `campus_main`、学号 `20260004`、初始化输出的绑定码 → 提交成功，显示 `****0004` 与“演示认证”。
4. `/me/profile` 修改昵称/简介 → 保存后顶部昵称与认证状态同步更新。
5. 退出登录后回到演示工作台；重新登录可看到资料与认证状态已在服务端保存。
6. 绑定身份后可进入 C 的认领流程（`/demo` 演示工作台 → 申请认领）。

## 3. 验证

```powershell
# 后端检查、迁移一致性、后端测试（含 C 的 52 项回归）、前端单测与生产构建
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1

# 追加真实 Chrome 浏览器验收（隔离数据库 8001/5174）
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1 -Browser
```

本次交付的实际结果（详见[测试报告](docs/test/A-用户管理-测试报告.md)与[完整性验证报告](docs/verify/A-用户管理-完整性验证报告.md)）：

| 检查 | 结果 |
|---|---|
| Django `check` | 0 issues |
| 迁移一致性 | No changes detected |
| 后端自动测试 | **105/105 通过**（成员 A 新增 53 + 成员 C 基线 52） |
| 前端单元测试 | **47/47 通过**（既有 21 + 成员 A 新增 26） |
| Vite 生产构建 | 通过 |
| Chrome 浏览器验收 | **5/5 通过**（成员 C 认领 4 + 成员 A 用户流程 1） |

浏览器验收使用隔离数据库与固定绑定码，并在该隔离环境关闭限流，避免多账号用例在一分钟窗口内累计触发 429；限流行为由后端测试单独覆盖。正常演示与默认配置仍开启限流（登录 10 次/分钟/IP、绑定 5 次/分钟/用户）。

## 4. 文件入口

| 内容 | 路径 |
|---|---|
| A 的后端接口、校验、服务、限流 | `backend/users/` |
| A 的模型与迁移 | `backend/users/models.py`、`backend/users/migrations/0002_*.py` |
| 演示校园身份初始化 | `backend/users/management/commands/seed_demo_users.py` |
| A 的后端测试 | `backend/users/tests/`、`backend/tests/test_identity_integration.py` |
| A 的前端页面与接口 | `frontend/src/modules/users/` |
| A 的浏览器验收 | `frontend/tests/e2e/users.spec.js` |
| C 的认领、沟通与匹配（既有） | `backend/claims/`、`frontend/src/modules/claims/` |
| 公共契约 | [`docs/共同字段与接口约定.md`](docs/共同字段与接口约定.md) |

## 5. 文档

| 文档 | 说明 |
|---|---|
| [需求规格说明书](docs/requirements/A-用户管理-需求规格说明书.md) | 角色与用例、业务规则、FR-A-01～12、NFR-A-01～07、验收标准与追踪 |
| [概要设计](docs/design/A-用户管理-概要设计.md) / [详细设计](docs/design/A-用户管理-详细设计.md) | 架构与分层、接口规格、事务与并发、限流与脱敏、前端设计、追踪矩阵 |
| [数据库设计](docs/数据库设计.md) | 全库 ER、A 的 4 张表、约束与索引、迁移与初始化 |
| [测试计划](docs/test/A-用户管理-测试计划.md) / [测试用例](docs/test/A-用户管理-测试用例.md) / [测试报告](docs/test/A-用户管理-测试报告.md) | 分层策略、TC-A-001～078、实际执行结果与缺陷记录 |
| [完整性验证报告](docs/verify/A-用户管理-完整性验证报告.md) | 交付物清单、需求追踪、接口逐项核对、验收清单与未覆盖项 |
| [软件工程过程说明](docs/process/A-软件工程过程说明.md) | 过程模型、阶段产物、评审与质量门禁、度量、风险与变更控制 |
| [个人报告](docs/reports/A-用户管理.md) | 课程个人成果与贡献边界 |
| [项目文件结构说明](docs/项目文件结构说明.md) | 目录职责与 A/B/C 文件归属 |

## 6. 已知限制

- **演示认证**：未接入真实学校认证服务，校园身份为预置测试数据，页面与接口均明确标识“演示认证”。
- **依赖 B/C**：`/meta/campuses` 等字典接口与完整物品发布/图片接口由成员 B 负责，当前仓库未接入；绑定页在该接口不可用时降级为文本输入（默认 `campus_main`）并给出说明。
- **会话保持**：令牌仅保存在前端内存中，刷新页面需重新登录（与共同契约一致）。
- **限流实现**：基于 Django LocMemCache 的单进程固定窗口，多进程/多实例部署不共享计数；生产部署需替换为共享缓存或网关限流。
- **数据库**：SQLite 为本地课程演示用，写事务串行；生产需评估 PostgreSQL/MySQL 的事务与并发方案。
- **范围外**：管理员审核、争议裁决、备份管理（第四子系统）、真实校园卡照片认证、解绑/换绑、任意用户私聊等不在第一版范围。
