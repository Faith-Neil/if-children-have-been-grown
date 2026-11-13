为什么有这个文件：说明 TV-M0-T02 的代码改在哪里。

它解决什么问题：下次改知识库页时，能看出历史标书上传和数据集配置是分开的。

# TV-M0-T02 代码说明

知识库路由在 `frontend/web/src/app/GlobalPagesContent.tsx`。现在只渲染 `KnowledgeBaseAdminPage`，并传入 `historyOnly`。方案片段页不再挂在这个路由上。

`historyOnly` 时，页面只留「历史标书」。公司管理员另外看到「数据集配置」。上传按钮使用 `canUploadHistory`：项目经理和项目负责人可以传，只读账号不行。没有 `dataset_id` 时按钮禁用。建立数据集仍走原来的 ensure 接口，只有资料管理员和公司管理员能调。

后台 `KbAdminService.upload` 对历史标书不再在上传时创建数据集。数据集不存在时返回 `KNOWLEDGE_BASE_NOT_CONFIGURED`。接受的扩展名改为 `.pdf`、`.docx`、`.doc`。证书上传的权限和文件类型没有改。
