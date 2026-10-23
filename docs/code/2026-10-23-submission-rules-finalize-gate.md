# 代码解释：规则最小可递交集与分册定稿闸门端到端闭环

## 1. 业务逻辑与时序链路

落实 PRD §5.8.5 分册定稿与整本递交导出的安全状态机：

```mermaid
sequenceDiagram
    participant Lead as 项目负责人 / 管理员
    participant Gate as 分册定稿门禁 (VolumeFinalizeMixin)
    participant Export as 导出服务 (ExportService)
    participant Writer as 普通编写人

    Note over Lead,Export: 阶段一：前置检查与定稿锁定
    Lead->>Gate: POST /volumes/technical/finalize
    Gate->>Gate: 检查章节正文非空、无排他锁、无 blocker
    Gate-->>Lead: 200 OK (is_finalized=True)
    
    Lead->>Export: POST /exports (kind="submission", volume="all")
    Export->>Export: 检查商务分册尚未定稿
    Export-->>Lead: 409 RULES_INCOMPLETE ("商务分册尚未完成责任人定稿锁定")

    Lead->>Gate: POST /volumes/business/finalize
    Gate-->>Lead: 200 OK (is_finalized=True)

    Note over Lead,Export: 阶段二：定稿通过，生成正式递交版
    Lead->>Export: POST /exports (kind="submission", volume="all")
    Export->>Export: 校验两册均已定稿 + 最新检查无 blocker
    Export-->>Lead: 200 OK (生成 Word 正式递交版, is_submission=True, compliance_notice=None)

    Note over Lead,Export: 阶段三：分级下载安全保护
    Writer->>Export: GET /exports/{id}/technical
    Export-->>Writer: 403 SUBMISSION_FORBIDDEN (仅项目经理可下载)

    Lead->>Export: GET /exports/{id}/technical
    Export-->>Lead: 200 OK (返回注入 SHA-256 指纹的标准 Word 文档)
```

## 2. 关键代码变更点

### 2.1 动态定稿状态校验 (`backend/bid-core/icg/domain/export_service.py`)
```python
            if payload.get("kind") == "submission":
                # 分册定稿闸门（PRD §5.8.5）：所选分册必须全部经负责人或管理员定稿锁定
                volumes_state = workflow.get("volumes", {})
                unfinalized = [
                    vol for vol in sorted(required_volumes)
                    if not volumes_state.get(vol, {}).get("is_finalized")
                ]
                if unfinalized:
                    unfinalized_names = "、".join("技术分册" if v == "technical" else "商务分册" for v in unfinalized)
                    raise DomainError(
                        409,
                        "RULES_INCOMPLETE",
                        f"完整合规规则与分册定稿未完成：{unfinalized_names}尚未完成责任人定稿锁定，不能把本地内部稿冒充递交版。"
                    )
```

### 2.2 契约模式对齐 (`backend/bid-core/icg_demo/workflow_schemas.py`)
在 `ProjectExport` 响应体中明确定义 `is_submission: bool = False`，确保在导出正式递交版时，序列化输出准确反映正式版标志，且契约与 OpenAPI demo-v1.json 保持 100% 一致。
