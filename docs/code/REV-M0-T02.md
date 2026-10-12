为什么有这个文件：解释会话实时HTTP复核脚本的运行过程。

它解决什么问题：说明脚本如何启动后台、检查什么以及不覆盖什么。

# REV-M0-T02：代码解释

- 对应任务、Issue、交付文档：REV-M0-T02 / [ISSUE-013](../../issues/ISSUE-013.md) / [交付](../delivery/REV-M0-T02.md)
- 日期、实际代码路径：2026-10-12，`tests/backend/session_live_http.py`

## 改了什么以及为什么

原真实会话HTTP验证器在仓库外。新增独立脚本，在真实监听端口上验证`/api/v1/session`，不改应用代码。

## 入口和调用顺序

`main()`取空闲端口 → 以当前Python启动`uvicorn icg_demo.main:app --app-dir backend/bid-core` → 轮询就绪 → `run_checks()`经`POST /api/demo/login`取演示令牌并逐项请求 → 终止服务 → 打印JSON结果与`TOTAL n PASS m`，全部通过退出0，否则1。

## 数据与状态

只使用进程内内存种子数据（alpha/beta合成公司与账号），服务结束即清空，不写文件。

## 关键判断与异常

角色映射与导航不含公司/平台入口；缺/坏Bearer 401；伪造参数及GET正文422；跨公司、非成员、不存在项目404。服务未就绪时最多等待约10秒，`finally`中必定终止子进程。

## 验证与限制

见[复跑记录](../testing/2026-10-12-qa-rerun.md)。不覆盖撤权竞态、GUI和原16项中无法还原的1项；这些由`test_application_session.py`及阶段GUI记录承担。
