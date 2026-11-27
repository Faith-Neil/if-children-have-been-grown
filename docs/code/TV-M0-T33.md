为什么有这个文件：说明 TV-M0-T33 的代码变化口径。

# TV-M0-T33 代码说明

TV-M0-T33 是真实环境验证与回归留档卡，本身不新增独立业务代码。验证对象是 TV-M0-T31/T32 已实现的以下链路：

- `backend/bid-core/icg/domain/technical_clause_cleaning.py`：条款清洗、补全、分流与假判断清理；
- `backend/bid-core/icg/domain/technical_digest_outline.py`：两阶段模型目录规划、JSON/截断修复、评分加权仲裁与失败上浮；
- `frontend/web/src/project/outline-rebuild-core.ts` 与 `OutlineRebuildNotice.tsx`：目录失败可见与管理员重跑入口。

本卡新增的仅是验证登记与交付文档；实证脚本运行在仓库外临时目录，读取 `.audit/` 中既有客户导出和审计页文本，不写入仓库、不回写客户项目数据。
