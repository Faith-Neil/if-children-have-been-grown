为什么有这个文件：记录产品启动改为连接 MySQL 这一轮实际做了什么。

它解决什么问题：避免把虚拟机说明写成已经在公司机器上部署。

# OPS-M0-T03：产品启动连接 MySQL

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | OPS-M0-T03 |
| 代码解释 | [代码说明](../code/OPS-M0-T03.md) |
| 验收 | 2026-11-04 本机健康检查见下文。虚拟机未执行 compose |
| 项目进度 | 任务为 in-review。不标 done。公司虚拟机尚未部署 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-04。Issue：[ISSUE-049](../../issues/ISSUE-049.md)。
- 分支、提交、PR：未创建 PR，未合入。
- 合入 / 发布：未合入，未发布。

## 完成内容与变更文件

- `backend/bid-core/Start-Product.ps1`：探测 MySQL，设置 `ICG_REQUIRE_MYSQL=1`，迁移后启动一个 worker。
- `backend/bid-core/Start-Demo.ps1`：未加 `-AllowMemory` 时直接退出。
- `deploy/Dockerfile`、`deploy/entrypoint.sh`、`deploy/docker-compose.yml`、`deploy/env.example`：虚拟机上的 MySQL 8 与应用镜像。
- [部署说明](../operations/docker-vm-deployment.md)。

## 验收结果

2026-11-04 本机 `GET /health`：`status=ok`，`mode=development`，`repository=mysql`，`persistent=true`，`single_process=true`，`model=mock`。对话模型仍是替身，没有把 RAGFlow 或本地模型算进这次启动。

虚拟机上的 compose、反向代理和备份恢复没有执行。

## 项目进度

建议 PM 先看交付，不标 done。这不是公司虚拟机已上线。
