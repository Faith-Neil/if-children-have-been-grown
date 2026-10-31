为什么有这个文件：记录 APP-M2-T166 问题标注与侧栏联动的验证方式、结果与局限。

它解决什么问题：说明本机与 CI 各跑了什么、第一次 CI 的问题和处理。

# APP-M2-T166 问题标注与侧栏联动验证（2026-10-31）

## 环境
同 [T260 验证](2026-10-31-t260-password-login.md)：开发沙箱无外网，只能跑不依赖 antd/react 的前端单测、治理检查与语法编译；后端、MySQL、类型检查、构建与浏览器用例在 GitHub Actions `offline-check` 上运行。不调用模型与 RAGFlow。

## 结果
| 验证 | 命令 / 位置 | 结果 |
|---|---|---|
| 本机新单测 | `node --test tests/unit/chapter-issues.test.mjs` | 5 通过 |
| 本机前端单测全量 | `node --test tests/*.test.mjs tests/**/*.test.mjs` | 失败项与改前相同（本机缺 antd/react 的 5 个文件） |
| CI 第一次（`0dc05d5`） | offline-check | frontend 类型检查失败：`ChapterIssue` 未声明 `issue_id`；e2e 因构建失败未执行 |
| CI 第二次（`c12b3af`） | offline-check | 结论写入交付文档 |

## 局限
- 本机未运行后端测试与浏览器用例，以 CI 为准。
- 未在 1280～1679 与 ≥1680 三种宽度下截图（T160）。
