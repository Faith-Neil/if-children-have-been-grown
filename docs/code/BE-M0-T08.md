为什么有这个文件：说明这张卡为什么没有代码解释可写。

它解决什么问题：避免空的代码路径被当成已经接上 MySQL。

# BE-M0-T08 代码解释

无代码影响。

本卡只提交 [持久化方案](../architecture/mysql-8-persistence-plan.md)。`Repository`、`MemoryRepository`、`requirements.txt` 和 CI 工作流都没有修改。SQLAlchemy、PyMySQL、cryptography、Alembic 都未安装。测试仍然使用内存仓库。
