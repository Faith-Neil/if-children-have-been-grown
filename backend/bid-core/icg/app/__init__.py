# 为什么有这个文件：组织应用入口、中间件与容器配置。
# 它解决什么问题：集中管理 FastAPI 应用组装、生命周期与异常处理器。

"""应用装配层。"""

from icg.app.main import create_app, app, DOCX_MEDIA_TYPE, error_responses

__all__ = ["create_app", "app", "DOCX_MEDIA_TYPE", "error_responses"]
