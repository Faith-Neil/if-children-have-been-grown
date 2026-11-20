# 昆明航空 Oracle 招标文件全流程冒烟 — 阻塞与体验问题

为什么有这个文件：用户要求用真实招标文件 `昆明航空Oracle数据库一体机软硬件维保和DBA服.doc` 跑主路径，并记录阻塞/影响使用的点供后续整改。

日期：2026-11-05  
项目：`Kunming-Oracle-E2E-API-1105B`（`project-a7ee826f92fa46a5bf188f4ac1f512f9`）  
入口：`http://127.0.0.1:8710`（Start-Product，MySQL，`model=mock`，`single_process=true`）  
账号：`alpha-manager`  
证据 JSON：`docs/testing/2026-11-05-kunming-oracle-e2e-run.json`  
导出 Word：`docs/testing/2026-11-05-kunming-oracle-e2e.docx`（50174 bytes，SHA-256 指纹见 run.json）

## 本轮阻塞 / 影响使用（按严重度）

| # | 严重度 | 现象 | 影响 | 建议整改 |
|---|--------|------|------|----------|
| 1 | 高 | `/health` 为 `model=mock` | 大纲主题编排与正文生成走替身模型；质量门未过、大量「待补」不能当生产可用 | 联调/验收前切内网 Qwen；工作台显著提示当前为 mock，禁止把「生成成功」写成可递交 |
| 2 | 高 | 解析任务约 **4 分 16 秒** 停在 **5%**「正在提取文字与抽取条款」；采样间隔也被拉长到 ~250s | 用户误以为卡死；[进度条](https://vibe-hub.org/progress)几乎无反馈 | 第一次 `_parse_once` 内按 RAGFlow/本地子步骤推送 5→10+；文案区分「本地提取」vs「等待 RAGFlow」 |
| 3 | 高 | `single_process` 下同步解析/生成占满 worker 时，`GET /jobs/{id}` 轮询也长时间无响应 | 进度 SSE/轮询连带卡住，界面更像死机 | 解析/生成与 API 读写隔离（或缩短单次阻塞、心跳事件） |
| 4 | 高 | 整册生成后正文 **待补=108、需要核对=14**（chars≈32k） | 导出的内部稿仍像半成品，业务不可用 | 真实模型 + 收紧「空槽」写入；writable 有值时禁止批量写「待补」壳 |
| 5 | 中 | 质量八条未通过（1/7/8），仍允许内部稿导出并提示「须可见警告」 | 警告若 UI 不明显，易当成可递交 | 内部稿显著黄条；递交版继续硬拦截 |
| 6 | 中 | `GET /api/v1/exports/{id}/download` **404**；须用 `/projects/{pid}/exports/{id}/technical` | 前端若走错下载 URL 会「导出成功但下不了」 | 统一 download_url；废弃或转发全局 `/exports/{id}/download` |
| 7 | 中 | 校验错误文案写「不符合**演示**接口要求」 | 关演示正式路径仍像 demo，信任感差 | 改为「请求字段不符合接口契约」 |
| 8 | 中 | 解析结果 **facts=0**；消息仍写「须人工逐项核对」但 `parse_confirmed=true` 已自动成立 | 人工核对环节被跳过或事实抽取空壳 | 核对页强制过一遍；facts 为空时提示是否预期 |
| 9 | 中 | `.doc` 强依赖 RAGFlow DeepDOC（本轮约 4+ 分钟才完成） | 内网 RAGFlow 慢/断则主路径不可用 | 连接失败尽早失败；提供换服务/超时重试入口 |
| 10 | 低 | 脚本误传 `checks` 的 `kind`（契约为 `volume`）触发 422 | 自动化易踩；产品侧契约需在 OpenAPI/错误里写清字段名 | 以 `volume` 为准；错误 details 点名合法枚举 |
| 11 | UI | 登录后浏览器「保存密码」遮挡新建项目 | 首次桌面使用被挡 | 文档提示忽略；无法产品侧禁用 |
| 12 | UI | 文件选择常落到无关默认目录 | 微信附件深层路径难找 | 记住上次目录 |

未出现本轮：`RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS`（内部稿 `technical-internal` 放行）。**不得**据此声称递交版可上线。

## 主路径执行记录（API [端到端测试](https://vibe-hub.org/e2e-test) / [冒烟测试](https://vibe-hub.org/smoke-test)）

- [x] 登录 `alpha-manager`
- [x] 新建 `Kunming-Oracle-E2E-API-1105B`（`technical_only`）
- [x] 上传 `昆明航空Oracle数据库一体机软硬件维保和DBA服.doc`（504832 bytes）
- [x] `POST .../parse/jobs` → 约 257s 完成：75 条条款、0 项事实
- [x] 矩阵：writable=75（全部 `history`），ResponseTask=14，大纲 headings=28（主题化标题可见）
- [x] 确认技术大纲
- [x] 整册生成约 322s，job completed，质量门未全过
- [x] 内部稿导出 + 项目路径下载 Word 成功（全局 download 404）

总耗时约 **9.8 分钟**（解析 ~4.3 min + 生成 ~5.4 min）。

## 进度采样（节选）

| elapsed_s | status | progress | message |
|-----------|--------|----------|---------|
| 1.0 | running | 5 | 正在提取文字与抽取条款。 |
| 251.4 | running | 5 | 正在提取文字与抽取条款。 |
| 256.8 | completed | 100 | 解析完成：75 条条款、0 项事实… |

## 说明

- 脚本：`docs/testing/_tv_e2e_kunming_run.py`
- mock 下「链路跑通 ≠ 产品可递交」；后续整改优先：真实模型、解析进度/API 不卡死、待补占位、导出下载 URL。
