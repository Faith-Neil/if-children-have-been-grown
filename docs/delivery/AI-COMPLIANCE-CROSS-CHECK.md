# AI-COMPLIANCE-CROSS-CHECK 交付报告：AI 合规检查依据交叉核验与差距诊断

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-COMPLIANCE-CROSS-CHECK |
| 代码解释 | [docs/code/AI-COMPLIANCE-CROSS-CHECK.md](../code/AI-COMPLIANCE-CROSS-CHECK.md) |
| 验收 | 9 项专属后端自动化测试全绿；关联回归全部通过；工程治理检查通过 |
| 项目进度 | AI 核心推进，AI-COMPLIANCE-CROSS-CHECK 提交 in-review，关联 ISSUE-037、ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据 PRD v1.8 §5.8、§5.11.5、§5.11.6 与原交接规范：
- **目标**：实现正文承诺声明与知识库已核验证据、招标文件强制条款的交叉核验与量化差距诊断。
- **交付要点**：
  1. **声明与引用智能抽取**：精准提取正文段落中 SLA 指标（99.99%、响应时限等）、资质、人员与案例承诺，提取 `.cite` 引用；
  2. **依据交叉比对与差距诊断**：对标招标文件强制条款与 RAGFlow 资料，输出置信度得分（0.0~1.0）与改进建议；
  3. **负偏离合规强阻断**：承诺指标劣于招标强制要求或引用失效/缺协议证据时，评定置信度 0.0 并阻断（risk="block"）；
  4. **增量复查联动**：核验结果持久化至 `incremental_checks`，联动更新章节 `incremental_check_status`；
  5. **权限与涉密门禁**：涉密项目强校验本地离线模型（403）、跨租户 404、非项目成员 403；
  6. **契约保护**：路由挂载 `include_in_schema=False` 保护冻结 OpenAPI 契约。

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg_demo/compliance_cross_check.py`：核验服务类、抽取规则、置信度推导与差距诊断算法
- `backend/bid-core/icg_demo/workflow_schemas.py`：`ComplianceFinding`、`ComplianceCrossCheckRequest`、`ComplianceCrossCheckResponse` 数据模型
- `backend/bid-core/icg_demo/domain.py` / `workflow.py` / `workflow_routes.py`：业务与路由挂载

### 2.2 自动化测试
- `tests/backend/test_ai_compliance_cross_check.py`：9 项专属单元测试（全绿通过）
