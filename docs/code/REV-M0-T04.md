为什么有这个文件：解释smoke_t06.py的运行过程。

它解决什么问题：说明贯通冒烟入口、核对内容和局限。

# REV-M0-T04：代码解释

- 对应：REV-M0-T04 / [ISSUE-015](../../issues/ISSUE-015.md) / [交付](../delivery/REV-M0-T04.md)；路径`backend/bid-core/smoke_t06.py`。

## 改了什么以及为什么

T06证据分散在多个冒烟且需手动起服务。新增脚本一次完成E1～E7并交叉核对接口与Word。

## 入口和调用顺序

`main()`：未给`--base-url`时取空闲端口启动`uvicorn icg_demo.main:app` → 轮询`/api/demo/accounts`就绪 → `run()`调用`smoke_members.run`（建合成项目、团队、逐节方案、生成、提交、交接、检查、两册导出）→ 读回workspace与各章节 → 下载两册、`word_text`比对正文、`inspect_docx`提取版式结构 → 新提交后验证旧导出409 → 终止服务，打印JSON，全部通过退出0否则1。

## 数据与状态

只用内存种子账号与合成项目；服务结束即清空。`--output-dir`仅把Word写到指定目录。

## 关键判断与异常

只允许本机地址（沿用`smoke_members`校验）；任一请求状态不符即抛出并以非零退出；`word_layout_verified`恒为false，结构字段只做记录不判定视觉。

## 验证与限制

见[记录](../testing/2026-10-12-t06-smoke-word-render.md)。不驱动浏览器、不调真实模型、不渲染（渲染在QA机器手工执行）。
