为什么有这个文件：说明 TV-M0-T33 的代码变化口径。

# TV-M0-T33 代码说明

TV-M0-T33 是真实环境验证与回归留档卡，本身不新增独立业务代码。验证对象是 TV-M0-T31/T32 已实现的以下链路：

- `backend/bid-core/icg/domain/technical_clause_cleaning.py`：条款清洗、补全、分流与假判断清理；
- `backend/bid-core/icg/domain/technical_digest_outline.py`：两阶段模型目录规划、JSON/截断修复、评分加权仲裁与失败上浮；
- `frontend/web/src/project/outline-rebuild-core.ts` 与 `OutlineRebuildNotice.tsx`：目录失败可见与管理员重跑入口。

本卡新增的仅是验证登记与交付文档；实证脚本运行在仓库外临时目录，读取 `.audit/` 中既有客户导出和审计页文本，不写入仓库、不回写客户项目数据。

## PR #57 Review 修复轮补充

- 2026-11-28 使用真实 MySQL 3407 与 `qwen3:30b-a3b-instruct-2507-q4_K_M` 复测：161 输入行、115 technical、28 non_technical、18 fragment_filtered、35 completed；目录 33 标题、23 非空叶子、113/114 挂载、空叶子 0、最大叶子 11 条（9.65%）。
- 验证文档如实记录 `S-02-2` 未挂载、人员类标题启发式警告与模型标题质量问题；不把局部验证夸大为导出全链路验收。
