为什么有这个文件：记录 Wave 12 续（去掉演示环境、知识库接入业务页面、招标条款结构化抽取）的开发自测。

它解决什么问题：说明改了什么、怎么验证、哪些还没验；本记录不是 QA 签署。

# Wave 12 续开发自测（2026-10-28）

分支 `feat/wave-11-main-path`，提交 `a184490`、`de25d64`、`51de392`、`5ebe616`。

## 改动要点

| 卡片 | 内容 |
|---|---|
| BE-AUTH-PRODUCTION-ONLY | 删除 `/api/demo/*` 与 `/demo` 页、三角色兼容会话；所有账号按 8 角色会话（资料管理员、公司管理员可正常登录）；无密码摘要不能登录；`ICG_ENV=production` 下拒绝合成种子账号、管理员初始密码只能由 `ICG_ADMIN_INITIAL_PASSWORD` 设定、MySQL 仓储不加载合成种子数据；前端去掉内置管理员口令、令牌直登、离线令牌、演示横幅与示例数据回填 |
| FE-E2E-LIBRARY-DRIFT | 资料类别与后端一致（修复提交“财务审计/通用模板”被 422 拒绝）；证据抽屉 e2e 按现行页面重写 |
| FE-KB-BUSINESS-FLOWS | 写作输入显示知识库候选；资料库逐条入库状态与“从证书附件识别”；片段新建/保存/发布与真实同步；知识库管理页解析进度 |
| AI-TENDER-STRUCTURED-EXTRACTION | 招标条款按章节与条目抽取，合同条款/格式附件不抽，★/▲/废标必抽，评分项带分值 |
| AI-KB-RAG-EVAL | 真实 RAGFlow 内置解析评测完成，默认阈值 0.45、关键词权重 0.3（[报告](rag-eval-golden-v1-builtin.md)） |

## 结果

| 检查 | 结果 |
|---|---|
| 后端全量（内存） | 891 passed、47 skipped |
| MySQL 标记用例（含 `ICG_REQUIRE_MYSQL=1`） | 40 passed |
| 真实会话 HTTP / 错误与幂等 HTTP / T06 冒烟 | 15/15、49/49、通过 |
| 前端单测 / lint / build | 295 pass；通过；通过 |
| e2e（无 `VITE_DEMO`） | 18 passed（含新增 `knowledge-flows.spec.ts` 2 项、修复的证据抽屉用例） |
| CI `de25d64` | frontend、backend、governance、e2e 通过；backend-mysql 因 `ICG_REQUIRE_MYSQL=1` 被当作生产模式而失败，`5ebe616` 已改为只认 `ICG_ENV=production` |

## 未验证 / 已知缺口

- 招标扫描件、.doc/.xls 仍不能解析（`OCR_REQUIRED` / `FILE_TYPE_UNSUPPORTED`），RAGFlow DeepDOC 接入未做。
- ICG 结构化资料流程的检索对比数字未出：RAGFlow 单解析进程 + 每块一次 LLM 调用太慢，且有模型超时。
- 前端 `tests/*.test.mjs` 28 个文件从未执行、8 项失败（ISSUE-044）。
- 条款抽取只在合成招标文本上验证，未用真实招标文件验证。
