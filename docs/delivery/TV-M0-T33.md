为什么有这个文件：登记 TV-M0-T33 重庆中烟真实 MySQL、真实内网模型实证与回归留档。

# TV-M0-T33 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review；建议 PM 复核后决定是否标 done |
| Issue | [ISSUE-060](../../issues/ISSUE-060.md) |
| 任务卡 | [TV-M0-T33](../tasks/TV-M0.md#tv-m0-t33) |
| 代码说明 | [TV-M0-T33](../code/TV-M0-T33.md) |
| 验证登记 | [ISSUE-060 重庆中烟真实环境验证](../testing/2026-11-28-iss060-cq-real-validation.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | TV-M0-T33 |
| 代码解释 | [代码说明](../code/TV-M0-T33.md)（本卡无独立业务代码） |
| 验收 | 本地 MySQL 3407 实连；内网 `qwen3:30b-a3b-instruct-2507-q4_K_M` 实跑；161 条覆盖视图清洗后 115 technical / 28 non_technical / 18 fragment_filtered / 35 completed；模型目录 `source=model`、113/114 digest 编号挂载、空叶子 0、最大叶子 11 条（9.65%）、无 9 条截断、无「其他服务承诺」。 |
| 项目进度 | in-review。真机实证与回归留档完成；QA/PD 独立签署未执行，建议 PM 标 done 前复核 PR 与实证限制。 |
<!-- task-delivery:end -->

## 完成内容

1. 通过 PyMySQL 实连 `127.0.0.1:3407`，读取重庆中烟项目元数据：revision 19、status preparing、company alpha、1 行章节正文最长 102582 字符；验证只读，不回写客户项目。
2. 用内网模型实跑清洗后的两阶段目录规划；模型审计保留在仓库外，入库文档只保留统计和短样本。
3. 登记清洗前后数量、过滤/补全样本、模型目录分布、评分点落位、负偏离重分类与 validation 警告。
4. 复核回归：后端聚焦测试、OpenAPI 契约、前端类型检查与生产构建、前端目录失败/重跑聚焦测试。

## 限制

- `demo_state_entry` 没有该项目 workflow 快照，因此实证输入按项目导出 161 行与审计页文本重建，未伪造生产 workflow 读取路径。
- 模型目录 validation 仍暴露行级覆盖/标题启发式警告；实证文档如实记录，未把 114/114 编号挂载夸大为所有确定性校验全绿。
- 未执行完整两卷导出，不能说导出全链路已验收。
