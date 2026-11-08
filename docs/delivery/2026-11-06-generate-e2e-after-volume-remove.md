# 真服务 generate 验收（2026-11-06 续 · 去分册后）

## 环境
- 仓库：`E:\ICG-CURSOR\if-children-have-been-grown-1` · 分支 `feat/iss-047-technical-volume-mvp`（含未提交去分册改动）
- 服务：`Start-Product.ps1` → `127.0.0.1:8710` · MySQL · `/health` 仍报 `model=mock`（进程默认；不以 health 签收）
- 样本：`project-6d78bd3f9a5d4c3b8e0d7182201a164c` · chapter `chapter-3d7ae65b8de2440daba48991a8988d4b`

## 结论（分层）
| 层 | 结果 | 证据 |
|----|------|------|
| ① 前端模型配置 test | 此前 PASS | 主配置本地 Qwen test ok |
| ② health.model | 仍 mock | 不阻塞；生成不以 health 为准 |
| ③ generation/start + job.model_call | **PASS（真本地模型）** | 见下 |
| ④ 同步 `/generate` 写正文 | 进行中/耗时长 | 请求已发出，正文「待补」是否清除待该请求返回 |

## 关键证据
1. **确认目录补 `outline_revision`**：`POST /api/v1/projects/{id}/plan`（`confirm_outline` + chapters）200 后，`generation/start` 以 `If-Match: 1` 返回 **202**（此前缺修订号一直 409）。
2. **异步任务** `job-02ba018efa324cf1a68fc4dcd971efac`：
   - status=completed
   - `job.model_call`：`provider=openai-compatible`，`model=qwen3:30b-a3b-instruct-2507-q4_K_M`，`is_real_model=true`，`is_local=true`，`duration_ms≈1147`
   - 任务留言：正式正文仍由**同步生成入口**写入，本章正文未在本任务中修改（设计如此）
3. 同步 `POST .../generate`：验收时已发起，因章节「待补」节数多、真模型逐段生成，耗时较长；不以 mock 冒充完成。

## 与去分册改动关系
- Cursor 已在 `technical_outline.confirm_directory` 写入 `outline_revision`，本轮验收依赖该补丁。
- 产品仅技术方案；创建 API 仍写死 `volume_mode=technical_only`（兼容）。

## 待跟
- 等同步 `/generate` 返回后核对正文「待补」减少与内容变化。
- RAGFlow 解析仍为产品阻塞项（本轮未验）。
