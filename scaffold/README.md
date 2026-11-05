# 成员 A 脚手架（feat/member-a-own 分支）

这份脚手架把「用户管理」子系统的**骨架、路由、模型、页面壳、测试模板**摆好，业务逻辑留 TODO 给你写。
每个 TODO 都带步骤号（如 `[D1-03]`），与 [`docs/process/A-3天实施计划.md`](../../docs/process/A-3天实施计划.md) 的表格一一对应。

## 1. 已给定 vs 自己写

| 类别 | 内容 | 说明 |
|---|---|---|
| 已给定 | 目录结构、`users/urls.py`、`config/urls.py` 挂载、`permissions.py` | 路由与权限壳，不用改 |
| 已给定 | `User` / `AuthSession` 既有模型 + 新增 `CampusBinding` / `DemoIdentity` 与迁移 0002 | 结构照契约给好，你要能讲清字段与约束 |
| 已给定 | 入参 Serializer 的字段声明（长度、正则、未知字段拦截） | 字段照契约抄，别改长度 |
| 已给定 | `frontend/src/modules/users/api.js`、`routes.js`、路由接入、App.vue 导航 | 前端接线 |
| **自己写** | `services.py` 的 5 个业务函数（注册/登录/登出/资料/绑定） | 核心逻辑 |
| **自己写** | `views.py` 的 6 个方法（视图只做校验+调用+包装） | 对应 5 个接口 |
| **自己写** | `serializers.py` 的 `mask_student_no` / `user_self` / `binding_view` / `UpdateProfileInput.validate` | 出参与脱敏 |
| **自己写** | `selectors.py` 的 4 个查询函数 | 只读查询 |
| **自己写** | `throttles.py` 的 `_fixed_window` | 限流 |
| **自己写** | `management/commands/seed_demo_users.py` 的 handle | 演示身份初始化 |
| **自己写** | 4 个前端页面的 script 逻辑（模板已给） | 登录/注册/资料/绑定 |
| **自己写** | 测试用例（用下面模板起步）与全部文档 | 交付必需 |

## 2. 测试模板怎么用（先红后绿）

模板放在 `scaffold/tests/`、`scaffold/frontend-tests/`，**不参与自动发现**；复制到正式目录后生效：

```powershell
# 后端：某一步做完就复制对应模板，跑测试看红/绿
Copy-Item scaffold\tests\test_auth.py           backend\users\tests\test_auth.py
Copy-Item scaffold\tests\test_campus_binding.py backend\users\tests\test_campus_binding.py
Copy-Item scaffold\tests\test_profile.py        backend\users\tests\test_profile.py
.\.venv\Scripts\python.exe backend\manage.py test users.tests -v 2

# 前端
Copy-Item scaffold\frontend-tests\login.spec.js          frontend\src\modules\users\tests\login.spec.js
Copy-Item scaffold\frontend-tests\campus-binding.spec.js frontend\src\modules\users\tests\campus-binding.spec.js
cd frontend; npm.cmd test

# 浏览器验收（需要后端 8001 + 前端 5174，见 D3-02）
Copy-Item scaffold\e2e\users.spec.js frontend\tests\e2e\users.spec.js
cd frontend; npm.cmd run test:e2e
```

模板是**验收基线**：允许你补充用例、调整措辞，但不要为了“变绿”删掉断言；每删一条，就等于丢一条验收证据。

## 3. 参考实现

同仓库 `feat/member-a-user-management` 分支是这一模块的完成版（AI 辅助产出），**只用于对照思路**：

```powershell
git show feat/member-a-user-management:backend/users/services.py
git show feat/member-a-user-management:docs/requirements/A-用户管理-需求规格说明书.md
```

不要直接 `git merge` 或整文件抄；课程要求自己写，且抄来的代码答辩时讲不清会扣分。
