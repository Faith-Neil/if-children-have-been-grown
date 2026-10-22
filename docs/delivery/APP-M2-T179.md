为什么有这个文件：记录 APP-M2-T179 自由问答（只“复制”与安全隔离）的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现智能助手自由提问场景下的四道安全门禁（禁止写入正文恒定 copy_only、知识库关闭零外呼与常驻提示、敏感项目强制本地模型隔离拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL、只读角色提问拦截 403 FORBIDDEN）、跨租户隔离、10 项专属自动化单测全过与后端全量回归证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T179：自由问答（只“复制”与安全隔离）交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T179 |
| 代码解释 | [docs/code/APP-M2-T179.md](../code/APP-M2-T179.md) |
| 验收 | 10 项专属自动化单测通过；智能助手系列 47 项测试全绿；全量后端单测通过；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T179 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T179](../tasks/APP-M2.md#app-m2-t179)
- 依赖任务：[APP-M2-T181](../tasks/APP-M2.md#app-m2-t181)、[APP-M2-T182](../tasks/APP-M2.md#app-m2-t182)、[APP-M2-T183](../tasks/APP-M2.md#app-m2-t183)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **智能助手自由提问核心逻辑与门禁流水线 (`backend/bid-core/icg_demo/answer_card.py`)**：
   - 实现 `AnswerCardService.general_chat`（别名 `ask_assistant`）；
   - **门禁 1（严格禁止写入正文）**：强制 `can_insert=False`、`action="copy_only"`、`insert_disabled_reason="自由问答仅供参考与复制，不可直接插入正文"`，绝不产生章节或版本历史写入；
   - **门禁 2（知识库关闭常驻说明）**：`knowledge_base_enabled=False` 时零外呼检索，并在回答尾部附带常驻说明“知识库已关闭，未查询公司资料库”，绝不编造虚假信息；
   - **门禁 3（敏感项目模型隔离）**：敏感项目强行核验是否绑定本地模型，企图使用云端大模型时拦截并抛出 `403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
   - **门禁 4（只读角色提问拦截）**：拦截集团管理员、审计员、只读成员、平台管理员及项目只读分工成员，抛出 `403 FORBIDDEN`。
2. **工作流门面委派 (`backend/bid-core/icg_demo/workflow.py`)**：
   - 在 `WorkflowService` 中暴露 `general_chat` 与 `ask_assistant` 统一接口，与既有工程协议完全兼容。
3. **自动化测试套件 (`tests/backend/test_general_chat_qa.py`)**：
   - 覆盖四道门禁正反例、跨租户隔离、模型 502 降级与门面委派共 10 项测试。

### 2. 变更文件清单
- `backend/bid-core/icg_demo/answer_card.py` (修改): 实现四道门禁流水线与自由问答核心逻辑
- `backend/bid-core/icg_demo/workflow.py` (修改): 暴露 WorkflowService 统一门面方法
- `tests/backend/test_general_chat_qa.py` (新增): 10 项自由问答与安全门禁单测
- `docs/code/APP-M2-T179.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T179.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单元测试（100% 通过）
运行命令：
```powershell
pytest tests/backend/test_general_chat_qa.py -v
```
实测输出：10 passed in 0.42s。
智能助手联合测试套件（test_answer_cards.py, test_direct_query_fallback.py, test_insert_answer_card.py, test_general_chat_qa.py）：**47 passed**。
后端全量回归套件：**532 passed, 37 skipped, 0 failed**。

### 2. 工程治理核查
```powershell
node scripts/check-project-governance.cjs
```
