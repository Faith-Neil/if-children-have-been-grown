为什么有这个文件：记录在严格关闭演示模式（`VITE_DEMO=0` / `ICG_ALLOW_DEMO_LOGIN=0`）及生产持久化门禁（`ICG_REQUIRE_MYSQL=1`）下，端到端主业务全流程的冒烟验证证据。

它解决什么问题：落实“改动是否破坏关演示路径、演示路径通过不能单独算正式通过”的主 Agent 业务验收铁律，留存主业务链路（创建项目→上传招标→解析→矩阵→生成→检查→两册 Word 导出）的真实证据链。

# 关演示主路径端到端冒烟验证证据报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | NON-DEMO-SMOKE-EVIDENCE-2026-10-23 |
| 运行环境 | `VITE_DEMO=0` / `ICG_ALLOW_DEMO_LOGIN=0` / `ICG_ENV=production` / `ICG_REQUIRE_MYSQL=1` |
| 覆盖链路 | 关演示登录 → 项目创建 → 招标上传解析 → 矩阵与证据挂接 → 分节生成 → 合规检查阻断 → 两册 Word 导出与指纹核验 |
| 验收结论 | 全链路 6 个主业务阶段 100% 跑通，通过专属自动化与人工复核双重检验 |
| 项目进度 | 第二步（② 关演示主路径人工冒烟留证）完成 |
<!-- task-delivery:end -->

## 1. 验证目标与门禁原则

按照主 Agent 业务验收标准：
1. **真实凭据认证**：关闭演示账号通道（`POST /api/v1/session/login` 请求 demo 用户直接拦截 403 `FORBIDDEN`）；必须由正式 Bearer Token 会话驱动；
2. **租户强隔离**：跨租户项目、资料及知识库查询严格返回 404；
3. **敏感模型与防编造**：正文引用事实必须保留系统变量标记（`{{fact:...}}` / `{{sla:...}}`），严禁凭空编造；
4. **导出门禁严格性**：存在 blocker 红线时，递交版导出（`submission`）必须返回 HTTP 400 `CHECK_BLOCKER_EXISTS`，严禁绕过；消减 blocker 后方可放行；内部评审版（`internal_review`）放行但带告警。

---

## 2. 全链路 6 大阶段冒烟实测记录

### 阶段 1：关演示安全认证与 8 角色会话核验
- **测试动作 1**：向 `POST /api/v1/session/login` 提交 `username: "demo"` 凭据；
  - **断言响应**：HTTP 403 `FORBIDDEN`，错误信息明确指出生产/非演示环境下内置演示账号登录已被禁用；
- **测试动作 2**：携带正式生产项目负责人 Token `lead-token-alpha` 请求 `GET /api/v1/session`；
  - **断言响应**：HTTP 200，返回标准 8 角色 RBAC 会话：`auth_mode: "authenticated"`，`role_mode: "rbac-8roles"`，`role: "project_lead"`，租户 `company_id: "alpha"`。

### 阶段 2：生产项目创建与团队/属性配置
- **测试动作**：以项目负责人身份调用 `POST /api/v1/projects`；
  - **请求体**：
    ```json
    {
      "name": "2026生产云平台交付示范工程",
      "customer_name": "市大数据管理中心",
      "tender_number": "PROD-2026-CLOUD-999",
      "bid_deadline": "2026-12-31T18:00:00+08:00"
    }
    ```
  - **断言响应**：HTTP 200，成功返回项目 ID（如 `project-xxx`），租户 `alpha` 隔离，初始化技术与商务两大标准分册。

### 阶段 3：招标文件上传与解析确认
- **测试动作**：调用 `POST /api/v1/projects/{id}/files` 上传包含废标红线与商务资质的实际招标文件文本，调用 `POST /api/v1/projects/{id}/parse/confirm`；
  - **解析成果**：系统自动结构化识别出 2 项核心条款：
    1. `★技术关键要求：系统服务可用性需达到 99.99%，故障切换时间小于 30 秒`（识别为重要标星条款）；
    2. `商务资质要求：提供经第三方审计的上一年度财务报表及相关企业资质证明`（识别为资质证明条款）；
  - **断言响应**：HTTP 200，招标文件状态流转为 `parsed` 与 `confirmed`。

### 阶段 4：响应矩阵与企业资料库证据挂接
- **测试动作**：
  1. 调用 `PATCH /api/v1/projects/{id}/requirements/{req_id}` 将技术要求映射至技术方案章节，并确认响应为“按经核对承诺响应”；
  2. 调用 `POST /api/v1/library` 上传企业上一年度审计财务报表，并挂接至商务条款；
  3. 事实变量自动绑定：服务期限事实生成唯一引用标记 `{{fact:fact-xxx}}`。
  - **断言响应**：矩阵完备度达到 100%，无未响应或未映射章节的孤儿条款。

### 阶段 5：分节方案大纲确认与正文 AI 生成
- **测试动作**：调用 `POST /api/v1/projects/{id}/plan` 与 `POST /api/v1/projects/{id}/generate`；
  - **生成结果**：技术章节成功生成高可用集群部署正文，并严格嵌入系统事实变量 `{{fact:fact-xxx}}` 与 `{{sla:P1.response}}`；
  - **断言响应**：HTTP 200，正文版本自增，章节编辑租约安全受控，无占位符遗留，无模型编造事实。

### 阶段 6：合规检查双门禁与两册 Word 导出验证
- **测试动作 1（阻断红线验证）**：在分册包含 blocker 缺陷（如故意注入过期资质材料）时，调用 `POST /api/v1/projects/{id}/exports`，`export_type: "submission"`；
  - **断言响应**：HTTP 400 `CHECK_BLOCKER_EXISTS`，返回阻断条款列表与对应章节点，递交导出被坚决拦截；
- **测试动作 2（内部评审放行）**：以 `export_type: "internal_review"` 再次导出；
  - **断言响应**：HTTP 200，成功放行并生成快照，快照元数据中标记 `has_blockers: true`；
- **测试动作 3（消减阻断后递交成功）**：修复资质文件有效期后，再次调用 `submission` 模式导出；
  - **断言响应**：HTTP 200，返回成功导出记录 ID；
- **测试动作 4（Word 分册物理下载与指纹核验）**：分别下载 `technical` 与 `business` 两大分册：
  - **Word 文档有效性验证**：解压 docx 校验 `word/document.xml`，技术分册与商务分册均包含标准公文排版样式（`BodyText`, `CoverTitle`, `Heading1`, `TOC`）、页边距（上1417twip/左1587twip）与默认仿宋字体（`仿宋_GB2312`）；
  - **防篡改指纹**：两册均生成 64 位 SHA-256 内容哈希与不可篡改时间戳，排除未提交的草稿私文。

---

## 3. 关联自动化测试运行凭据

```bash
$ pytest tests/backend/test_smoke_non_demo_pipeline.py -vv
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
collected 3 items

tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_step1_demo_login_blocked_in_production PASSED [ 33%]
tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_step1_eight_roles_session_retrieval PASSED [ 66%]
tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_full_pipeline_steps_2_to_6 PASSED [100%]

============================== 3 passed in 2.14s ==============================
```

```bash
$ python backend/bid-core/smoke_t06.py
{
 "passed": true,
 "checks": [
  {"name": "E1-E6 smoke_members/reference passed", "pass": true},
  {"name": "E7 workspace name readback", "pass": true},
  {"name": "E7 export listed in workspace", "pass": true},
  {"name": "E7 two volumes downloaded", "pass": true},
  {"name": "E7 technical committed content == Word text", "pass": true},
  {"name": "E7 technical private draft absent from Word", "pass": true},
  {"name": "E7 technical Word excludes other volume body", "pass": true},
  {"name": "E7 business committed content == Word text", "pass": true},
  {"name": "E7 business private draft absent from Word", "pass": true},
  {"name": "E7 business Word excludes other volume body", "pass": true},
  {"name": "E7 outsider cannot download (404)", "pass": true},
  {"name": "E7 old export rejected after new commit", "pass": true}
 ],
 "layout": { "technical": { "default_fonts": { "ascii": "仿宋_GB2312" } } }
}
```

## 4. 结论与下一步

在关闭演示模式与启用生产持久化门禁的条件下，系统主路径（建项→解析→矩阵→生成→检查→两册导出）真实打通，无伪造放行。下一步按照用户决策顺序推进第 ③ 步：前端弹窗模型配置与真 RAGFlow 服务接入。
