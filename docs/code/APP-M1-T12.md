为什么有这个文件：解释后台怎样把本章计划变成真实写作输入。

它解决什么问题：让接手者能找到来源核对、变量校验和失效保护的实际入口。

# APP-M1-T12代码解释

日期2026-10-10，reference-writing-1，ISSUE-007。后台位于`backend/bid-core/icg_demo/`，验证见[写作验收](../testing/2026-10-10-writing-input.md)。

`workflow.plan`保存每章`fact_ids`、`writing_points`、`target_length`和实际确认人/时间。选中可选事实及全部必备事实须已确认且来源可核对；确认只开放manager，当前未建章节编写人/分册负责人分配。公司由登录账号推导，外公司/外项目资源拒绝。

`generation_context.py`共用组装器：读取本章确认矩阵、挂接证据、计划事实和唯一SLA项目值；证据重新校验状态、公司/项目、类型及北京时间截止日。未采用事实记录原因；当前预览带`ready/issues`，生成和旧整章建议只有ready才调用原`ModelProvider.suggest(instruction, content)`接口。

`workflow.generate`及`domain.suggest`都保存/返回当次`input_snapshot`；里面的`model_input/model_instruction`是实际传给接口的文字，另存事实、矩阵、证据版本、方案、正式正文和时间。`source_scope=whole_chapter`是实施新增字段，不能当逐段来源证明。独立旧demo无项目输入时继续只改写正文，快照为空。

`writing_source_fingerprint`核对计划与来源，提交正文不使方案失效；`project_input_fingerprint`同时含正式正文，用于候选、检查和输出失效。候选、草稿、租约和生成记录不加入摘要。摘要就是“参与这次工作的资料组合的指纹”，变了一项，旧候选就需重新核对。

模型输出检查空/过长/非法XML文字、未知/未确认/未选变量、单位冲突、明确SLA手写值以及删掉既有变量。通用`{{fact:事实ID}}`与`{{sla:指标键}}`在检查和两册导出使用同一解析器；只有正式正文参加输出。来源在调用期间改变，事务内再次核对并拒绝保存候选，正文不受影响。

来源版本、选择、确认与候选在内存Repository内保存；模型仍为替身，接口未绑定真实服务。完整事实语义、段落绑定、片段治理、字数动态预算、拒绝事件完整审计与选区助手另交付。HTTP脚本`smoke_writing.py`使用新建合成项目验证实际端口；独立回归位于`tests/backend/test_generation_context.py`。

收尾复核补两处真实缺陷：通用事实值是完整“数字+字典单位”（如12个月）时，即使unit字段为空也核对正文后缀；不同单位或重复单位都阻断检查/模型输出，普通名称/地点文本不猜单位。来源项目的草稿/提交必须带input_fingerprint，domain在同一写事务核对当前摘要、编辑权和正文版本；草稿保存原来源基准，提交重复请求把基准纳入幂等判断。缺基准或过期返回409，不能靠页面之前GET代替写入核对。新独立写入回归见tests/backend/test_candidate_write_guard.py。
