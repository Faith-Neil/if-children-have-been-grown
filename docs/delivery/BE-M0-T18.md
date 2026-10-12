为什么有这个文件：记录挂证据规则这张卡实际交了什么。

它解决什么问题：把过期、仅供参考、缺协议和无权受限资料挡在条款之外，并且不新增错误码。

# BE-M0-T18：挂证据规则交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T18 |
| 代码解释 | [BE-M0-T18](../code/BE-M0-T18.md) |
| 验收 | 2026-10-12：未设连接串时后台测试见验证记录。过期挂接返回 409 `EVIDENCE_EXPIRED`；仅供参考和缺协议都返回 409 `EVIDENCE_NOT_USABLE` 且说明不同；无权受限资料返回 403 `FORBIDDEN`。长期有效和已授权资料可以挂接。错误码名单仍是 143 个名字。治理检查见验证记录 |
| 项目进度 | 任务看板是准绳。并入上游 QA 卡后，本卡从 planned 改为 in-review，并新增 planned 的 BE-M0-T19。BE-M0-T13 随后依据 QA ae38ec3，PM 17:16 确认 done。看板为 386 项：50 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready。BE-M0 为 19 项，8 项 done。本卡 in-review。ISSUE-033 为 in-review，不关闭。ISSUE-035 为 new |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-033](../../issues/ISSUE-033.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待 QA 重签后，项目经理才能标 done。

## 完成内容与变更文件

条款 PATCH 在原有的缺失、他公司、历史标书和未确认检查之后，再拒绝四类资料：

- 有效期早于项目截止日，且不是长期有效：409 `EVIDENCE_EXPIRED`。
- `source_tier` 为 `reference`：409 `EVIDENCE_NOT_USABLE`，说明含「仅供参考」。
- `source_tier` 为 `partner`，且本项目没有该合作方的非空 `agreement_attachment_id`：409 `EVIDENCE_NOT_USABLE`，说明含「缺协议」。
- `is_restricted` 为真，且调用者不是 `company_admin` 或 `data_admin`，也不在该资料的授权行上：403 `FORBIDDEN`。

资料响应使用 `is_restricted`。请求体里的 `restricted` 被拒绝。协议是否存在不写成资料列。合作方列表和授权行留在内存，不进 MySQL。

OpenAPI 只替换了发生变化的组件模式，并补上 `ProjectPartnerInput`。没有重跑 `export_openapi.py`。

## 代码解释

见 [代码解释](../code/BE-M0-T18.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t18-evidence-mount.md)。检查和写作输入对过期的判断与挂接使用同一规则：长期有效不算过期，`valid_to` 优先于 `valid_until`。没有截止日时，挂接不因日期拒绝；检查和写作输入仍用当天。

## 项目进度

任务看板是准绳。BE-M0-T18 改为 in-review，并加上 planned 的 BE-M0-T19 后，看板为 386 项：50 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready。BE-M0 19 项，8 项 done。ISSUE-033 仍为 in-review。ISSUE-018 仍为 in-progress。T13 已依据 QA ae38ec3，PM 17:16 确认 done。T078 与 T114 保持上游 done。T124 保持 ready。

## 限制与未完成

- 不标 done，不关闭 ISSUE-033。
- 不新增错误码。
- 不把合作方和授权写入 MySQL。项目表对齐见 ISSUE-035，本卡不改表。
- 不改 `.github`，不改 `docs/reference/`，不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑计数。
- 前端抽屉仍可能使用旧字段名。本卡只改后台挂接。
