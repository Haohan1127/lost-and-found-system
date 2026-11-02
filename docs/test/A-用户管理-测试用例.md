# 成员 A：用户管理子系统测试用例

| 项目 | 内容 |
|---|---|
| 文档名称 | 成员 A 用户管理子系统测试用例 |
| 文档版本 | v1.2 |
| 编写日期 | 2026-11-02 |
| 作者 | 成员 A（用户管理） |
| 适用范围 | 注册登录、校园身份绑定、个人资料管理三个功能模块，及与 B/C 子系统的身份兼容回归 |
| 需求依据 | [需求规格说明书](../requirements/A-用户管理-需求规格说明书.md) 第 2 节需求编号与 FR/NFR；[共同字段与接口约定](../共同字段与接口约定.md) 第 2、3.2、3.3、4、8 节 |
| 配套文档 | [测试计划](A-用户管理-测试计划.md)、`docs/requirements/A-用户管理-需求规格说明书.md` |
| 结果记录 | 执行结果、缺陷与统计写入 `docs/test/A-用户管理-测试报告.md`，由验证角色在实现完成后填写 |

## 1. 使用说明

### 1.1 编号规则

- 用例编号 `TC-A-001`～`TC-A-078`，按功能域连续分组，编号不变更；新增用例追加在所属组末尾并登记变更记录。
- 每条用例标注对应需求编号（FR-A-xx / NFR-A-xx）。一个用例覆盖多条同类需求时列出主需求，其余在覆盖矩阵说明。
- `步骤` 均指对运行中的后端与前端执行的操作；接口路径省略公共前缀 `/api/v1`。
- 本文件**只定义用例、前置条件与预期结果**。不预填“实际结果/是否通过”，避免与后续独立执行结论混淆。

### 1.2 类型与优先级

| 类型 | 含义 | 执行方式 |
|---|---|---|
| 接口 | 直接调用 HTTP 接口，断言状态码、响应体与数据库 | Django `APITestCase` / 手工 HTTP |
| 集成 | 跨接口、跨模块或依赖事务、线程的验证 | Django `TransactionTestCase` + 独立连接 |
| 前端组件 | Vue 组件挂载、交互与路由 | Vitest + `@vue/test-utils`，mock HTTP |
| 浏览器 | 真实浏览器端到端 | Playwright + 隔离后端/前端 |
| 回归 | 既有交付物不被破坏 | 全量命令重跑 |
| 静态检查 | 配置、迁移、构建质量门禁 | 命令行 |

| 优先级 | 判定标准 |
|---|---|
| P0 | 主流程或安全边界，失败则本模块不可交付 |
| P1 | 重要分支、边界、异常与可用性，失败需在验收前修复 |
| P2 | 体验与文档一致性，可排期修复 |

### 1.3 测试数据约定

| 数据 | 值/来源 |
|---|---|
| 校区 | `campus_main`（主校区） |
| 预置测试身份 | 学号 `20260001`～`20260006`，校验码 6～64 位一次性绑定码，`sha256` 摘要入库 |
| e2e 固定绑定码 | `e2e-binding-0001`（环境变量 `DEMO_BINDING_CODE`，仅隔离测试库） |
| 演示账号 | `publisher`、`applicant`、`competitor`（演示认证）、`unverified`（未认证） |
| 新注册账号 | 用例内声明，统一含字母数字下划线、4～32 位 |
| 无数据环境 | 每个用例类使用独立测试数据库，由 Django 测试框架创建与销毁 |

## 2. 用例总览

| 用例组 | 覆盖需求 | 编号区间 | 数量 |
|---|---|---|---|
| G1 账号注册 | FR-A-01 | TC-A-001～007 | 7 |
| G2 登录 | FR-A-02、FR-A-08 | TC-A-008～013 | 6 |
| G3 令牌与登出 | FR-A-03、FR-A-08 | TC-A-014～020 | 7 |
| G4 个人资料 | FR-A-04、FR-A-05 | TC-A-021～028 | 8 |
| G5 校园身份绑定 | FR-A-06、FR-A-07、NFR-A-01 | TC-A-029～039 | 11 |
| G6 身份能力与权限 | FR-A-09、NFR-A-02 | TC-A-040～044 | 5 |
| G7 频率限制 | FR-A-10 | TC-A-045～048 | 4 |
| G8 并发与事务 | NFR-A-03 | TC-A-049～050 | 2 |
| G9 安全与隐私 | NFR-A-01、NFR-A-02 | TC-A-051～054 | 4 |
| G10 演示数据初始化 | FR-A-11、NFR-A-07 | TC-A-055～058 | 4 |
| G11 前端页面与路由 | FR-A-12、NFR-A-06 | TC-A-059～068 | 10 |
| G12 浏览器验收 | FR-A-12、NFR-A-06 | TC-A-069～071 | 3 |
| G13 兼容回归与工程检查 | NFR-A-05、NFR-A-07、NFR-A-04 | TC-A-072～078 | 7 |
| **合计** | FR-A-01～12、NFR-A-01～07 | TC-A-001～078 | **78** |

## 3. 用例明细

### G1 账号注册（FR-A-01）

前置：数据库无账号 `alice_01`，除非该用例另有说明。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-001 | FR-A-01 | 接口 | P0 | 账号 `alice_01` 不存在 | 1. POST `/auth/register`，body `{"username":"Alice_01","password":"Passw0rd!","nickname":" 小林 "}`；2. 查询数据库用户记录 | 1. 返回 201，`code=OK`；`data` 为 `UserSelf`，字段恰为 `id/username/nickname/bio/is_campus_verified/verification_mode/created_at/updated_at`；2. `username="alice_01"`（统一小写）、`nickname="小林"`（去首尾空白）、`bio=""`、`is_campus_verified=false`、`verification_mode=null`；3. 响应无 `access_token`、`token` 字段，不自动登录；4. 库中 `password` 为 Django 密码哈希，不等于明文 |
| TC-A-002 | FR-A-01 | 接口 | P0 | `alice_01` 已注册 | 分别以 `alice_01` 与 `Alice_01` 再次 POST `/auth/register` | 均返回 409 `DUPLICATE_RESOURCE`；`errors` 为对象；不新建用户；不返回令牌 |
| TC-A-003 | FR-A-01 | 接口 | P1 | 无 | 账号长度取 3、4、32、33；字符取 `ab-c`、`中文账号`、`ab cd`、空串；逐个注册 | 4 位与 32 位合法输入返回 201；3 位、33 位、含非法字符、含空格、空串均返回 400 `VALIDATION_ERROR` 且 `errors.username` 存在；失败请求不建用户 |
| TC-A-004 | FR-A-01 | 接口 | P1 | 无 | 密码长度取 7、8、64、65；另测首尾带空格的密码 | 8 位与 64 位成功；7 位与 65 位返回 400 且 `errors.password` 存在；密码不裁剪空白，按原值长度与内容校验 |
| TC-A-005 | FR-A-01 | 接口 | P1 | 无 | 昵称长度取 0、1、30、31 | 1 字与 30 字成功；0 字（空串/仅空白）与 31 字返回 400 且 `errors.nickname` 存在 |
| TC-A-006 | FR-A-01 | 接口 | P0 | 无 | 依次提交：含未知字段 `email`；含只读字段 `is_campus_verified`；含 `password_hash`；`username` 重复出现两次；body 为 JSON 数组；body 含 `id` | 全部返回 400 `VALIDATION_ERROR`；`errors` 指向对应字段；任一失败请求均不建用户 |
| TC-A-007 | FR-A-01 | 集成 | P0 | 无 | 两线程用屏障同时注册同一账号（一文大小写不同），各自独立数据库连接 | 恰一条返回 201、另一条返回 409；数据库中该账号只有一条记录；线程内无未捕获异常 |

### G2 登录（FR-A-02、FR-A-08）

前置：存在有效账号 `alice_01 / Passw0rd!`。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-008 | FR-A-02 | 接口 | P0 | 账号有效 | POST `/auth/login`，body `{"username":"alice_01","password":"Passw0rd!"}` | 1. 返回 200；`data.access_token` 非空；`token_type="Bearer"`；`expires_at` 为登录时刻加 24 小时的 UTC ISO8601；2. `data.user` 为完整 `UserSelf`，不含密码或哈希；3. 库中新增一条 `AuthSession`，`token_digest` 等于令牌的 SHA-256 十六进制 |
| TC-A-009 | FR-A-02 | 接口 | P1 | 账号有效 | 用 `ALICE_01` 与正确密码登录 | 返回 200，视同账号 `alice_01`；用户资料相同 |
| TC-A-010 | FR-A-02 | 接口 | P0 | 账号有效 | POST `/auth/login`，密码错误 | 返回 401 `UNAUTHENTICATED`；`message="账号或密码错误"`；`errors` 为空对象；不建立会话 |
| TC-A-011 | FR-A-02 | 接口 | P0 | 账号不存在 | POST `/auth/login`，使用不存在的账号 | 返回 401；`code` 与 `message` 与 TC-A-010 完全一致（不泄露账号是否存在）；不建立会话 |
| TC-A-012 | FR-A-02 | 接口 | P1 | 用户 `is_active=false`、密码正确 | POST `/auth/login` | 返回 401 `UNAUTHENTICATED`，错误文案与密码错误一致；不建立会话 |
| TC-A-013 | FR-A-08 | 接口 | P1 | 账号有效 | 同一账号连续登录两次；分别用两个令牌 GET `/users/me` | 两次 `access_token` 不同；`AuthSession` 为两条；两个令牌均能返回 200 与本人资料 |

### G3 令牌与登出（FR-A-03、FR-A-08）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-014 | FR-A-03 | 接口 | P0 | 已登录 | 1. POST `/auth/logout`，body `{}`；2. 用原令牌 GET `/users/me` | 1. 登出返回 200，`data=null`；2. 对应 `AuthSession` 记录被删除；3. 旧令牌请求返回 401 `UNAUTHENTICATED` |
| TC-A-015 | FR-A-03 | 集成 | P1 | 同一账号两个令牌 | 登出其中一个令牌，再分别请求 `/users/me` | 被登出令牌返回 401；另一令牌仍返回 200；仅一条 `AuthSession` 被删除 |
| TC-A-016 | FR-A-03 | 接口 | P1 | 令牌已撤销 | 用已撤销令牌再次 POST `/auth/logout` | 返回 401 `UNAUTHENTICATED`；不删除其他会话；不返回 500 |
| TC-A-017 | FR-A-08 | 接口 | P0 | 无令牌 | 不带 `Authorization` 请求 GET `/users/me`、PATCH `/users/me`、POST `/auth/logout` | 均返回 401 `UNAUTHENTICATED`；响应头含 `WWW-Authenticate: Bearer`；响应体符合统一错误包装 |
| TC-A-018 | FR-A-08 | 接口 | P1 | 构造异常请求头 | 依次使用 `Authorization: Token abc`、`Basic eA==`、仅 `Bearer`、`Bearer a b` | 均返回 401，`code=UNAUTHENTICATED`；不出现 500 或未捕获异常 |
| TC-A-019 | FR-A-08 | 接口 | P1 | 存在 `expires_at` 已过期的会话 | 用该过期令牌 GET `/users/me` | 返回 401 `UNAUTHENTICATED`；不延长会话有效期 |
| TC-A-020 | FR-A-08 | 集成 | P1 | 公开接口可用；B 的 `/meta/campuses` 未接入时以 C 的公开详情为替代对象 | 携带随机无效 Bearer 令牌请求公开接口（B 未接入时用 C 的 `GET /posts/{id}` 公开详情；`/meta/campuses` 属 B 待实现接口），再移除令牌重试 | 携带无效令牌返回 401（共同契约 §2.2）；移除令牌后匿名访问返回 200，数据可见。**备注**：`/meta/campuses` 依赖成员 B 尚未实现的接口，B 未接入时该分支不可执行，A 侧以 C 的公开详情接口等价验证；B 接入后补执行 |

### G4 个人资料（FR-A-04、FR-A-05）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-021 | FR-A-04 | 接口 | P0 | 已登录 | GET `/users/me` | 200；`data` 字段集合恰为 `id/username/nickname/bio/is_campus_verified/verification_mode/created_at/updated_at`；`id` 为字符串；时间为 UTC ISO8601；响应中无 `password`、`password_hash`、令牌、学号 |
| TC-A-022 | FR-A-04 | 接口 | P1 | 未登录 | 不带令牌 GET 与 PATCH `/users/me` | 均返回 401 `UNAUTHENTICATED`；不修改任何数据 |
| TC-A-023 | FR-A-05 | 接口 | P0 | 已登录 | PATCH `/users/me`，body `{"nickname":"小周","bio":"软件工程 2024 级"}` | 200；返回完整 `UserSelf`；库中两字段更新；`updated_at` 大于修改前；`username`、`is_campus_verified` 不变 |
| TC-A-024 | FR-A-05 | 接口 | P1 | 已登录且 `bio` 非空 | PATCH `/users/me`，body `{"bio":""}` | 200；`bio` 变为空字符串；不触发“至少一个字段”或长度错误 |
| TC-A-025 | FR-A-05 | 接口 | P0 | 已登录 | PATCH `/users/me`，body `{}` | 400 `VALIDATION_ERROR`；`errors` 非空（字段错误或 `non_field_errors`）；资料不变 |
| TC-A-026 | FR-A-05 | 接口 | P0 | 已登录 | 分别提交 `{"username":"x"}`、`{"is_campus_verified":true}`、`{"verification_mode":"demo"}`、`{"password_hash":"x"}`、`{"password":"Passw0rd!"}`、`{"nickname":"ok","id":"1"}` | 全部 400 `VALIDATION_ERROR`，`errors` 指向未知/只读字段；账号、认证标记、密码均未被修改 |
| TC-A-027 | FR-A-05 | 接口 | P1 | 已登录 | `nickname` 取 1、30、31 字；`bio` 取 200、201 字 | 1/30/200 字成功；31/201 字返回 400，`errors` 归对应字段；失败时原值不变 |
| TC-A-028 | FR-A-05 | 接口 | P1 | 已登录 | PATCH `nickname=" 小林 "`、`bio="  简介  "`；随后 GET `/users/me` | 首尾空白被去除；GET 返回去除后的值；`updated_at` 单调增加且与数据库一致 |

### G5 校园身份绑定（FR-A-06、FR-A-07）

前置：`campus_main` 存在；存在可用预置身份（学号 `20260004` 及有效绑定码）；用户 `binder_01` 已登录且未绑定，除非另有说明。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-029 | FR-A-06 | 接口 | P0 | 用户未绑定 | GET `/users/me/campus-binding` | 200；`data=null`；`/users/me` 中 `is_campus_verified=false` |
| TC-A-030 | FR-A-07 | 接口 | P0 | 用户未绑定，身份有效 | POST `/users/me/campus-binding`，body `{"campus_id":"campus_main","student_no":"20260004","binding_code":"<有效码>"}` | 1. 返回 201；`data` 含 `campus_id`、`student_no_masked`、`verification_mode="demo"`、`verified_at`，不含 `student_no` 明文字段；2. 新建一条 `CampusBinding`，指向当前用户与 `campus_main`；3. `DemoIdentity.used_by` 为当前用户；4. `User.is_campus_verified=true`、`verification_mode="demo"` |
| TC-A-031 | FR-A-06 | 接口 | P1 | 分别准备 6 位与 20 位学号的有效身份 | 各自成功绑定后读取 `student_no_masked` | 6 位学号 `20260001` 返回 `****0001`；20 位学号仅保留末 4 位、其余替换为 `*`（共 16 个 `*`）；响应与日志中不出现完整学号 |
| TC-A-032 | FR-A-07 | 接口 | P0 | 用户已绑定 | 用另一个未使用的有效身份再次 POST `/users/me/campus-binding` | 409 `DUPLICATE_RESOURCE`；原绑定记录不变；用户认证标记不变；目标身份未被消耗（`used_by` 仍为 `null`） |
| TC-A-033 | FR-A-07 | 接口 | P0 | 身份 `20260002` 已被用户 U1 使用 | U2 用 `20260002` 及其原绑定码 POST 绑定 | 返回 409 `DUPLICATE_RESOURCE`（消息“该校园身份已被绑定”）；`data=null`、`errors` 为空对象；U2 仍为未绑定、未认证、无 `CampusBinding`；`DemoIdentity.used_by` 仍为 U1；U1 绑定不受影响；不产生第二条 `CampusBinding` |
| TC-A-034 | FR-A-07 | 接口 | P0 | 身份有效，用户未绑定 | POST 绑定，`binding_code` 为格式合法但错误的码 | 400 `VALIDATION_ERROR`；`errors` 归 `binding_code`；不消耗身份（`used_by` 仍 `null`）；用户未认证 |
| TC-A-035 | FR-A-07 | 接口 | P1 | 用户未绑定 | POST 绑定，`campus_id="campus_unknown"`，其余合法 | 400 `VALIDATION_ERROR`，`errors.campus_id` 存在；不创建绑定；身份未被消耗 |
| TC-A-036 | FR-A-07 | 接口 | P1 | 用户未绑定 | 学号依次取 `12345`、`abc-def`、`""`、21 位字符 | 均返回 400，`errors.student_no` 存在；身份不被消耗 |
| TC-A-037 | FR-A-07 | 接口 | P1 | 用户未绑定 | `binding_code` 取 5 位与 65 位 | 均返回 400，`errors.binding_code` 存在（长度要求 6～64）；身份不被消耗 |
| TC-A-038 | FR-A-07 | 集成 | P1 | 用户未绑定 | 1. 记录 `/users/me` 与 `/users/me/campus-binding`；2. 提交错误绑定码；3. 重新读取并检查数据库 | 两步读取仍为未认证、`data=null`；无 `CampusBinding` 记录；`DemoIdentity.used_by` 仍为 `null`；`User` 无变更 |
| TC-A-039 | FR-A-06 | 接口 | P1 | 用户已绑定 | GET `/users/me/campus-binding` | 200；返回脱敏学号、`campus_id`、`verification_mode`、`verified_at`；与绑定成功响应一致；不返回 `student_no` 明文 |

### G6 身份能力与权限（FR-A-09）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-040 | FR-A-09 | 集成 | P0 | 无令牌，存在可认领的 `found/open` 信息 | POST `/claims`，body 合法 | 401 `UNAUTHENTICATED`；不产生 `Claim`；不读取或写入申请数据 |
| TC-A-041 | FR-A-09 | 集成 | P0 | 已登录但未绑定 | POST `/claims`（合法 body）；`POST /posts`（合法 body）部分依赖 B | 均返回 403 `IDENTITY_REQUIRED`（`/claims` 可执行；B 未接入时 `POST /posts` 无路由返回 404，以 `/claims` 结果为准）；不产生 `Claim` 或 `Post`；错误文案提示需完成校园身份绑定。**备注**：`/posts` 部分待 B 接入后补执行 |
| TC-A-042 | FR-A-09 | 集成 | P1 | 已完成绑定，目标为他人 `found/open` 信息 | POST `/claims` | 201；`applicant` 为 `UserSummary`（仅 `id/nickname/is_campus_verified/verification_mode`）；服务端身份取令牌而非请求字段 |
| TC-A-043 | FR-A-09 | 接口 | P1 | 存在已认证发布者的公开信息 | GET 公开列表或详情，检查发布者摘要 | 摘要字段恰为 `id/nickname/is_campus_verified/verification_mode`；不含 `username`、`bio`、学号、联系方式 |
| TC-A-044 | FR-A-09 | 接口 | P1 | 已登录 | 在资料或认领请求中携带 `user_id`、`applicant_id`、`is_campus_verified`、`username` 等身份字段 | 返回 400 `VALIDATION_ERROR`（未知/只读字段）；身份仍由令牌决定；不越权修改 |

### G7 频率限制（FR-A-10）

前置：用例在 `override_settings(RATE_LIMIT_ENABLED=True)` 下执行，并在 `setUp` 清空缓存；默认测试运行时限流关闭，以免干扰其他用例。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-045 | FR-A-10 | 接口 | P0 | 限流开启，同一来源 IP | 连续发起 11 次登录请求（前 10 次密码错误） | 前 10 次返回 401；第 11 次返回 429 `RATE_LIMITED`；响应头含 `Retry-After`，值为正整数秒；第 11 次不建立会话 |
| TC-A-046 | FR-A-10 | 接口 | P0 | 限流开启，同一登录用户 | 1 分钟内连续发起 6 次绑定请求 | 第 6 次返回 429 `RATE_LIMITED` 且带 `Retry-After`；不创建绑定、不消耗身份；前 5 次按业务校验正常返回 |
| TC-A-047 | FR-A-10 | 接口 | P1 | 已触发限流 | 等待窗口结束（或推进固定窗口/清理缓存）后再次请求 | 恢复为正常业务响应（401 或 400），不再返回 429 |
| TC-A-048 | FR-A-10 | 接口 | P1 | 限流开启，两个来源 IP 与两个用户 | IP A 耗尽登录额度后由 IP B 登录；用户 U1 耗尽绑定额度后 U2 发起绑定 | 各自独立计数：IP B 登录正常；U2 绑定正常返回；不出现跨键误伤 |

### G8 并发与事务（NFR-A-03）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-049 | NFR-A-03 | 集成 | P0 | 两个未绑定用户 U1、U2；同一有效身份 `20260005` 与绑定码 | 两线程用屏障同时 POST 绑定，各自独立数据库连接 | 恰一个 201，败者统一返回 409 `DUPLICATE_RESOURCE`（`errors` 为空对象）；数据库中该身份只有一条 `CampusBinding`，`used_by` 只有一个用户；两用户最多一个 `is_campus_verified=true`；不出现 500 |
| TC-A-050 | NFR-A-03 | 集成 | P1 | 未绑定用户与有效身份 | 在“创建 `CampusBinding` 之后、置用户认证标记之前”注入异常，调用绑定服务 | 事务整体回滚：无 `CampusBinding` 记录；`DemoIdentity.used_by` 仍为 `null`；`User.is_campus_verified` 仍为 `false`；异常按统一错误处理返回，不写入半成品数据 |

### G9 安全与隐私（NFR-A-01、NFR-A-02）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-051 | NFR-A-01 | 接口 | P0 | 已注册用户 | 检查 `users_user.password` 与会话令牌；扫描注册、登录、资料、绑定响应体 | 密码以 Django 哈希格式存储（如 `pbkdf2_sha256$` 前缀），不等于明文；所有响应不含明文密码或哈希；`AuthSession` 仅存 64 位十六进制摘要，无明文令牌 |
| TC-A-052 | NFR-A-01 | 接口 | P0 | 已登录 | 对比登录返回的 `access_token` 与数据库 `AuthSession.token_digest`；检查库中是否存在明文令牌 | `token_digest = sha256(access_token)`，为 64 位小写十六进制；库中不存在明文令牌；令牌明文只在登录响应中出现一次 |
| TC-A-053 | NFR-A-01 | 接口 | P1 | 已有绑定成功的用户 | 对注册、登录、`/users/me`、绑定接口的响应做全文扫描 | 不出现 `student_no` 明文、`binding_code`、`password`、`password_hash`、`token_digest`、完整学号；错误消息与 `errors` 同样不含这些值 |
| TC-A-054 | NFR-A-01 | 接口 | P1 | 注入内部异常（如 monkeypatch 服务函数抛异常） | 请求任一接口触发 500 | 返回 500 `INTERNAL_ERROR`；响应体只有 `code/message/data/errors`；不含堆栈、SQL、文件路径或内部变量名 |

### G10 演示数据初始化（FR-A-11、NFR-A-07）

前置：`DEMO_MODE=True`；隔离测试数据库；命令行在仓库根目录执行。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-055 | FR-A-11 | 集成 | P0 | 空库，`DEMO_MODE=True` | 连续执行两次 `manage.py seed_demo_users` | 两次均以 0 退出且无未捕获异常；`campus_main` 唯一；`DemoIdentity` 仍为 6 条、不重复；已存在的绑定与 `used_by` 不重复创建；输出中给出“已有身份 N 个可用”类提示 |
| TC-A-056 | FR-A-11 | 集成 | P1 | `DJANGO_DEBUG=0`（`DEMO_MODE=False`） | 执行 `manage.py seed_demo_users` | 抛出 `CommandError`，命令以非 0 退出；不写校区、身份、绑定或用户数据 |
| TC-A-057 | FR-A-11 | 集成 | P1 | 已执行初始化，部分身份已使用 | 执行 `manage.py seed_demo_users --reset-codes` | 仅为 `used_by is None` 的身份重新生成绑定码并打印；已使用身份的码不变；已有 `CampusBinding` 与用户认证标记不受影响；重复执行结果稳定 |
| TC-A-058 | FR-A-11 | 集成 | P1 | 存在已认证（`is_campus_verified=true`）的演示账号 `publisher/applicant/competitor` 且无绑定，`unverified` 未认证 | 执行初始化命令 | 三个演示账号分别建立 `CampusBinding`（学号 20260001～20260003）并置 `used_by`；不打印这些已使用身份的码；`unverified` 与普通注册用户仍为未认证；不产生重复绑定 |

### G11 前端页面与路由（FR-A-12、NFR-A-06）

前置：Vitest + `@vue/test-utils`，mock `shared/http.js` 或 `modules/users/api.js`，路由使用 `createMemoryHistory`，不发起真实网络请求。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-059 | FR-A-12 | 前端组件 | P1 | 挂载 `LoginPage` | 1. 检查初始渲染；2. 空表单提交；3. 输入错误账号提交（mock 401）；4. mock 成功登录 | 1. 渲染账号、密码输入与提交按钮，页脚含“注册新账号”“演示工作台”入口；2. 前端校验提示出现且不调用接口；3. 展示后端错误文案；4. 调用 `setSession` 并以 `data.user` 更新会话，跳转目标页 |
| TC-A-060 | FR-A-12 | 前端组件 | P1 | 挂载 `LoginPage`，路由带查询参数 | 分别访问 `?next=/me/profile`、`?next=//evil.com`、`?next=https://example.com` 后登录成功 | `next=/me/profile` 时回跳该路径；`//` 开头或绝对 URL 被拒绝，改跳 `/demo`；不发生外部跳转 |
| TC-A-061 | FR-A-12 | 前端组件 | P1 | 挂载 `RegisterPage` | 依次提交：账号 3 位、密码 7 位、昵称空、两次密码不一致、全部合法 | 前四种显示对应字段错误且不调用注册接口；合法提交调用 `register`，成功后不写入会话，跳转 `/login?registered=1&username=...` |
| TC-A-062 | FR-A-12 | 前端组件 | P1 | 挂载 `RegisterPage`，mock 服务端 400/409 | 提交表单，mock 返回字段错误；再观察请求期间按钮状态 | 字段错误按字段展示；请求未完成时提交按钮为禁用状态，重复点击不发出第二次请求；失败后按钮恢复 |
| TC-A-063 | FR-A-12 | 前端组件 | P1 | 已登录会话，挂载 `ProfilePage` | 1. 进入页面；2. 修改昵称并保存；3. mock 保存失败 | 1. 调用 `me()` 并展示账号（只读）、注册时间、认证状态、昵称、简介；2. 调用 `updateMe` 并同步 `session.user`，显示成功提示；3. 显示错误提示，已填内容不被清空 |
| TC-A-064 | FR-A-12 | 前端组件 | P1 | 挂载 `CampusBindingPage` | 1. mock 未绑定；2. mock 已绑定 | 1. 展示校区选择、学号、绑定码表单及“第一版为演示认证”说明；2. 展示校区、脱敏学号、“演示认证”、绑定时间，不渲染表单 |
| TC-A-065 | FR-A-12 | 前端组件 | P1 | 校区字典接口不可用 | mock `/meta/campuses` 返回 404 或网络错误后进入绑定页 | 降级为文本输入（默认 `campus_main`）并显示已知限制说明；表单仍可提交并调用 `bindCampus`；页面不报未捕获错误 |
| TC-A-066 | FR-A-12 | 前端组件 | P1 | 挂载绑定页，mock 409 与 400 | 1. mock 409；2. mock 400 且 `errors.binding_code`；3. mock 成功 | 1. 显示“已绑定/重复”类提示；2. 错误展示在绑定码输入框下；3. 成功后重新调用 `getBinding()` 与 `me()` 刷新页面与会话 |
| TC-A-067 | FR-A-12 | 前端组件 | P1 | 未登录会话，存在 `meta.requiresAuth` 路由 | 访问受保护页面；再模拟登录成功 | 跳转 `/login?next=<原路径>`；登录后回跳原路径，而非固定首页 |
| TC-A-068 | FR-A-12 | 前端组件 | P1 | 挂载 `App.vue`，切换登录状态 | 1. 未登录检查导航；2. 已登录检查导航；3. 点击退出登录 | 1. 显示“登录”“注册”；2. 显示“个人中心”并保留演示工作台、我的认领、收到的申请入口与认证徽标；3. 清理会话并跳转 `/demo`（保持成员 C 的既有行为） |

### G12 浏览器验收（FR-A-12）

前置：Playwright 使用隔离后端（`8001`）与隔离前端（`5174`）、`backend/e2e.sqlite3`；`DEMO_BINDING_CODE=e2e-binding-0001`；独立浏览器上下文。

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-069 | FR-A-12 | 浏览器 | P0 | 隔离环境已初始化演示校区与身份 | 1. 注册新账号；2. 登录；3. 用 `campus_main`、`20260004`、`e2e-binding-0001` 绑定；4. 修改昵称/简介；5. 退出；6. 重新登录并查看资料 | 全流程无失败请求导致的中断；绑定成功显示脱敏学号与“演示认证”；退出后再登录资料仍为修改后的值；认证标记保持 |
| TC-A-070 | FR-A-12 | 浏览器 | P1 | 已完成绑定 | 查看绑定页与个人资料页文案 | 出现“演示认证”，并出现“第一版为演示认证，不是真实学校认证”类说明；不出现“真实认证”“已通过学校认证”等不实表述 |
| TC-A-071 | NFR-A-06 | 浏览器 | P1 | 390×844 视口 | 依次打开登录、注册、资料、绑定页并操作表单 | 页面无横向溢出（`scrollWidth <= clientWidth`）；输入框与按钮可点按；表单可完成提交；错误提示在可视区域内 |

### G13 兼容回归与工程检查（NFR-A-05、NFR-A-07、NFR-A-04）

| 编号 | 需求 | 类型 | 优先级 | 前置条件 | 步骤 | 预期结果 |
|---|---|---|---|---|---|---|
| TC-A-072 | NFR-A-05 | 回归 | P0 | 实现完成 | 在仓库根目录执行 `manage.py test tests users.tests --noinput` | 既有 `tests` 52 项全部通过；`users.tests` 新增用例全部通过；退出码 0；无接口路径或响应结构回归 |
| TC-A-073 | NFR-A-05 | 回归 | P0 | 实现完成 | 在 `frontend` 执行 `npm.cmd test` | 既有 21 项前端测试全部通过；新增用户模块测试全部通过；无未处理 Promise 或控制台错误断言失败 |
| TC-A-074 | NFR-A-05 | 回归 | P1 | 已登录并登出 | 用旧令牌访问 C 的 `/claims`；在请求中伪造 `user_id`、`applicant_id`、`is_campus_verified` | 旧令牌返回 401；伪造身份字段返回 400 或不影响服务端身份判定；不产生越权业务数据（共同验收 T13 的 A 侧部分） |
| TC-A-075 | NFR-A-05 | 回归 | P1 | 未登录用户与已登录未认证用户；B 的 `POST /posts` 未接入时以 `/claims` 替代 | 未登录与已登录未认证分别 POST `/claims`（合法 body）；若 B 已接入则再 POST `/posts`（合法 body）；检查数据库 | 未登录 401；已登录未认证 403 `IDENTITY_REQUIRED`；均不产生 `Claim`（B 接入后同样不产生 `Post`）（共同验收 T01 的 A 侧部分）。**备注**：`POST /posts` 依赖 B 未实现接口，B 未接入时不可执行，A 侧以认领接口验证 401/403；B 接入后补执行 |
| TC-A-076 | NFR-A-05 | 集成 | P1 | 演示路由已按契约移除登录/登出/本人资料入口 | 检查 `/api/v1/auth/login`、`/auth/logout`、`/users/me` 由 `users` 正式路由提供且无重复；访问 C 的 `/claims`、`/posts/{id}/matches` 与前端 C 页面 | 路径唯一、方法正确；C 接口与页面在新认证/守卫下工作正常；不出现 404/405 回归 |
| TC-A-077 | NFR-A-04 | 静态检查 | P0 | 实现完成 | 执行 `manage.py check`、`manage.py makemigrations --check --dry-run`、`npm.cmd run build` | `check` 0 issues；无待生成迁移（`No changes detected`）；生产构建成功；无因分层或严格校验引入的配置错误 |
| TC-A-078 | NFR-A-07 | 集成 | P1 | 普通演示库 `backend/db.sqlite3` 已存在且有数据 | 1. 运行 `manage.py test tests users.tests`；2. 运行浏览器验收；3. 对比普通库文件与内容 | 测试使用独立测试库，结束后自动销毁；`backend/db.sqlite3` 的时间戳与数据内容不变；`e2e.sqlite3` 仅被隔离环境重建；初始化命令可重复执行不产生重复数据 |

## 4. 需求覆盖矩阵

| 需求 | 覆盖用例 |
|---|---|
| FR-A-01 | TC-A-001～007 |
| FR-A-02 | TC-A-008～013 |
| FR-A-03 | TC-A-014～016 |
| FR-A-04 | TC-A-021、022、053 |
| FR-A-05 | TC-A-023～028（含 022 未登录） |
| FR-A-06 | TC-A-029、031、039、053 |
| FR-A-07 | TC-A-030、032～038 |
| FR-A-08 | TC-A-008、014、017～020、045、047 |
| FR-A-09 | TC-A-040～044 |
| FR-A-10 | TC-A-045～048 |
| FR-A-11 | TC-A-055～058 |
| FR-A-12 | TC-A-059～071 |
| NFR-A-01 | TC-A-030、051～054 |
| NFR-A-02 | TC-A-043、053、070 |
| NFR-A-03 | TC-A-033、038、049、050 |
| NFR-A-04 | TC-A-006、026、044、077 |
| NFR-A-05 | TC-A-072～076 |
| NFR-A-06 | TC-A-059～071（尤其 062、066、071） |
| NFR-A-07 | TC-A-055、072、078 |

## 5. 用例与测试数据映射

| 用例组 | 主要账号/身份 | 说明 |
|---|---|---|
| G1～G4 | 用例内新建账号 | 每个用例类独立注册，避免相互污染 |
| G5 | `binder_01` + 20260004；占用场景需 U1/U2 + 20260002 | 绑定码由初始化命令写入隔离库，测试通过 fixture 直接构造哈希摘要 |
| G6～G9 | 已绑定用户 + C 模块演示数据 | 依赖 `tests.helpers` 的模型工厂构造公开信息与认领数据 |
| G10 | 隔离测试库 | 命令执行后检查 `Campus`、`DemoIdentity`、`CampusBinding` 计数 |
| G11 | mock 数据 | 断言组件行为，不依赖真实后端 |
| G12 | 新注册账号 + `campus_main` + 20260004 + `e2e-binding-0001` | Playwright 独立上下文，固定码由 `DEMO_BINDING_CODE` 提供 |
| G13 | 全量 | 命令与回归，不新增业务数据 |

## 6. 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|---|---|---|---|
| v1.0 | 2026-11-02 | 首次编写，覆盖 FR-A-01～12 与 NFR-A-01～07，共 78 条；按契约第 2 节需求编号与第 5 节文档要求组织 | 成员 A（用户管理） |
| v1.1 | 2026-11-02 | 按 CR-A-08 与后端定稿对齐：TC-A-033 改为确定性 409 `DUPLICATE_RESOURCE`（errors 空对象、无副作用）；TC-A-049 并发败者统一按 409 断言；编号基线不变 | 成员 A（用户管理） |
| v1.2 | 2026-11-02 | 按 verifier 文档偏差 DV-A-05 标注 B 依赖：TC-A-020（`/meta/campuses`）与 TC-A-075（`POST /posts`）注明“B 未接入时不可执行、A 侧以 C 公开详情/认领接口替代验证，B 接入后补执行”；TC-A-041 的 `/posts` 部分同步标注；编号不变 | 成员 A（用户管理） |
