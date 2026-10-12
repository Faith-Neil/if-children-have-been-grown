为什么有这个文件：说明条款挂证据时在哪一处拒绝过期、缺协议和受限资料。

它解决什么问题：避免把推导出来的协议有无，或内存里的授权行，写成新的资料列或新的错误码。

# BE-M0-T18：代码解释

- 对应任务：[BE-M0-T18](../tasks/BE-M0.md#be-m0-t18)；Issue：[ISSUE-033](../../issues/ISSUE-033.md)；交付：[BE-M0-T18](../delivery/BE-M0-T18.md)
- 日期：2026-10-12。挂接判断在 `icg_demo/workflow.py` 的条款 PATCH。过期比较在 `icg_demo/generation_context.py`。

## 改了什么以及为什么

资料创建和修改接受 `source_tier`、`is_restricted`、`is_long_term`、`valid_to`、`partner_entity_id`。授权用户放在请求的 `acl_user_ids`，保存前取出，写成内存里的 `resource_acl` 行，不放进资料对象。响应里不出现 `restricted`。

项目 PATCH 接受 `project_partners`。这一列表留在 `DemoState.project_partners`，不写进 `Project`。协议是否存在只看匹配 `partner_entity_id` 的行有没有非空 `agreement_attachment_id`。

挂接顺序仍先看资料是否存在、是否本公司、是否历史标书或未确认。然后才看受限、仅供参考、缺协议和过期。重复编号仍是 422 `DUPLICATE_EVIDENCE`。

公司管理员和资料管理员如果已经是项目成员，可以办理成员能做的写入。经理和编辑的原有分工不变。演示种子账号仍是编辑、经理和只读。测试在登录后改内存账号角色，所以账号响应里的角色字面量包含这两种管理员。

## 入口和调用顺序

1. `PATCH /api/v1/library/{id}` 与 `POST /api/v1/library` 写入资料字段。只改授权名单不会把已确认资料打回未确认。
2. `PATCH /api/v1/projects/{id}` 可以带 `project_partners`。
3. `PATCH /api/v1/projects/{id}/requirements/{id}` 在保存 `evidence_ids` 前逐条拒绝不能挂的资料。
4. 项目检查和写作输入调用同一个 `evidence_expired`。有截止日时按截止日；挂接在没有截止日时不因日期拒绝。

## 数据与状态

`valid_to` 有值时用它，否则用既有 `valid_until`。`is_long_term` 为真时两种日期都不导致过期。没有截止日期的资料不在这条 PATCH 上返回 409。合作方和授权不入库。

## 关键判断与异常

| 条件 | 状态 | 错误码 | 说明要点 |
|---|---|---|---|
| 有效期早于截止日，且非长期 | 409 | `EVIDENCE_EXPIRED` | 不能覆盖投标截止时间 |
| `source_tier=reference` | 409 | `EVIDENCE_NOT_USABLE` | 仅供参考 |
| 合作方没有协议附件 | 409 | `EVIDENCE_NOT_USABLE` | 缺协议 |
| 受限且无管理员身份、无授权 | 403 | `FORBIDDEN` | 受限 |
| 请求使用 `restricted` | 422 | `VALIDATION_ERROR` | 字段名不对 |

没有新的错误码名字。

## 验证与限制

后台测试覆盖上述四类拒绝，以及长期有效和已授权可以挂上。前端抽屉不在本卡。正式项目表对齐不在本卡。
