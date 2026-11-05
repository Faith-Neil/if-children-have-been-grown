为什么有这个文件：说明工单 1 管道去闸门改动了哪些代码与为何这样改。

它解决什么问题：后续改目录确认 / 矩阵后台化时，知道抽取确认闸门已从主路径拿掉。

# TV-M0-T08 代码说明

## 后端

- `backend/bid-core/icg/domain/tender_orchestrator.py`：技术分册在远程/本地解析收齐后，若有 `technical_clause` 则 `apply_technical_outline` 并设 `parse_confirmed=True`；为空则清目录且 `parse_confirmed=False`。任务完成文案改为「已拟技术目录草稿」或「未抽到技术响应内容」。
- 内部矩阵填充 `fill_technical_responses` 仍跑，但不要求用户先点抽取确认。

## 前端

- `parse-postprocess-core.ts`：新增 `shouldAutoStartTechnicalParse`（有招标文件、指纹未抽过、无进行中任务、无失败文件才自动启动）。
- `TenderTab.tsx`：上传 `reload` 后用**返回的 revision** 调 `parse/jobs`（避免闭包旧 If-Match）；成功有 `technical_outline` → `navigate('editor')`；主按钮改为「重新解析」。
- `ParseTab.tsx` / `OverviewTab.tsx`：技术分册去掉「确认解析结果并进入矩阵」主闸门与两册式步骤条。

## 测试

- 后端断言成功抽出后 `parse_confirmed is True`、空抽出为 `False`。
- 前端单测覆盖自动启动条件。
