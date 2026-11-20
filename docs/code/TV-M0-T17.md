# TV-M0-T17 代码说明

- `backend/bid-core/icg/domain/technical_model_extract.py`：三张清单提示词与摊平（`_payload_items`），`EXTRACT_CALL` 加大输出长度。
- `backend/bid-core/icg/domain/technical_clause_extract.py`：条款带 `extra`（评分项、分值、标准、★、废标类别）；废标写 `rejection_items`。
- `backend/bid-core/icg/domain/technical_digest.py`：三张清单编号与正文提示用的评分标准、废标清单。
- `backend/bid-core/icg/domain/technical_digest_outline.py`：清单拟目录、轻量校验、漏挂补入、回落规则目录。
- `technical_outline.py`、`tender_orchestrator.py`：改走 `plan_technical_outline`。
- `technical_volume.py`、`technical_rag.py`：正文提示与检索词。
- `tests/backend/test_technical_digest.py`：假模型用例。
