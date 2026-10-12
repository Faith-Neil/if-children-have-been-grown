为什么有这个文件：记录QA对ISSUE-028配置驱动对话模型设计（Provider侧）的复核。

它解决什么问题：确认设计只覆盖 Provider 侧、与冻结错误码和现有适配器一致、不改契约与依赖，并找出与 ISSUE-024 的分工缺口。

# ISSUE-028 配置驱动对话模型设计 QA 签署

日期 2026-10-12（UTC+8）。签署卡 REV-M0-T17，归入 ISSUE-013。分支 `codex/repository-foundation`，被验提交 `29694e0`（首版）与 `ca05676`（范围收窄），核对到 `2fe6198`。范围只看 Provider/模型服务配置侧；设计 `docs/architecture/model-config-provider.md`，决定记录 `docs/testing/2026-10-12-issue-010-decisions.md`。本卡为设计复核，没有运行时可测。

## 结论

**通过，附 1 项 P2（实现前须消除）和 2 项 P3。** AC-01～AC-03 满足。ISSUE-028 保持 in-review，done 由项目经理设置。

## 逐条核对

| 编号 | 结果 | 证据 |
|---|---|---|
| AC-01 | 通过 | 设计逐节写明读取配置、启动快照、local/cloud 路由、敏感约束、流式默认与 JSON 模式、错误映射、`job.model_call`（provider、model 加现有 is_real_model、is_local、duration_ms、error_code）；字段表与 API 已删去，注明以 ISSUE-024 为准 |
| AC-02 | 通过 | “CI”一节：假 OpenAI 兼容服务记录请求头与 base_url；真实连接显式打开、默认跳过 |
| AC-03 | 通过 | `git show --stat 29694e0 ca05676 -- spec backend frontend requirements* package.json` 为空：未改 OpenAPI、后台代码与依赖；设计只沿用已有 `httpx==0.28.1`（`backend/bid-core/requirements.txt` 第16行） |
| 与代码一致 | 通过 | `openai_model.py` 用 httpx 调 `{base_url}/v1/chat/completions`，`is_real_model=True`，失败映射 502 `MODEL_UNAVAILABLE`（`errors.py` 第85行冻结表）；`domain.py` 现为 409 `LOCAL_MODEL_REQUIRED`，设计如实写明“实现时再改映射” |
| 错误码 | 通过 | 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 与 ISSUE-024 冻结错误码表、`spec/openapi/demo-v1.json` startGeneration 草案说明一致，均只引用、未写入运行时枚举 |
| 密钥 | 通过 | 现有适配器只经 `ICG_MODEL_API_KEY_ENV` 指向的环境变量取密钥；配置页密钥按用户决定由 ISSUE-024 以 Fernet 加密，主密钥只来自环境变量 `ICG_SECRET_KEY`；设计要求正文和日志不含密钥 |
| ISSUE-024 引用 | 通过 | 交材料时 ISSUE-024 尚未建，单向引用不算缺陷；现已由 `9a079b0` 建档（状态 new），双向引用成立 |

## 缺陷与观察

- D-1（P2，成长AI与RAG集成 + 成长后端开发）：流式与 JSON 开关字段名互相推诿。设计“流式与 JSON 模式”一节写“开关的具体字段名以 ISSUE-024 的契约为准”，而 `issues/ISSUE-024.md` 第39行写“流式和 JSON 开关仍以 ISSUE-028 为准，这里不列成第二张字段表”。两边都不定义，实现时无归属。建议由项目经理指定一方写下字段名（基址、模型名、本地/云端标记同理），另一方改为引用。
- O-1（P3，成长AI与RAG集成）：决定记录“局限”一节仍写“ISSUE-024 留给后台模型配置契约，本仓库不建详情”，已被 `9a079b0` 推翻，建议顺手更新。
- O-2（P3，成长AI与RAG集成）：敏感项目 409→403 的改动在实现卡上尚无验收条目，建议实现卡写明同时更新 `domain.py`、`errors.py` 与相关测试。
