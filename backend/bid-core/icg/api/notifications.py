# 为什么有这个文件：站内提醒接口（PRD v1.8 §5.12.2；APP-M2-T029～T032）。
# 它解决什么问题：顶栏铃铛读未读数，下拉读最近几条，G-02 列表页按类型、已读、项目、时间筛选；
# 点开提醒先标已读再核对对象与权限后给出跳转地址；只返回发给本人的提醒。

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.notifications import NotificationService
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class Notification(ResponseBody):
    id: str
    type: str
    type_label: str
    title: str
    body: str
    project_id: str | None = None
    target_id: str | None = None
    read: bool
    read_at: str | None = None
    created_at: str
    updated_at: str = Field(description="同一对象同类型未读期间再次发生时更新")
    count: int = Field(description="未读期间合并的次数")


class NotificationType(ResponseBody):
    value: str
    label: str


class NotificationList(ResponseBody):
    items: list[Notification]
    total: int
    unread: int
    types: list[NotificationType]


class UnreadCount(ResponseBody):
    unread: int


class MarkRead(RequestBody):
    read: bool = True


class MarkAllResult(ResponseBody):
    updated: int


class OpenResult(ResponseBody):
    notification: Notification
    ok: bool
    path: str | None = None
    message: str | None = Field(default=None, description="对象已不存在或无权限时的提示；提醒仍标为已读")


def include_notification_routes(application, service: DemoService, current_user) -> None:
    notices = NotificationService(service)
    application.state.notifications = notices
    router = APIRouter(prefix="/api/v1/notifications", responses=v1_error_responses(401, 404, 422))

    @router.get("", response_model=NotificationList, operation_id="listNotifications", summary="本人的站内提醒")
    def list_notifications(status: Literal["all", "unread", "read"] = Query(default="all"),
                           type: str | None = Query(default=None, max_length=60),
                           project_id: str | None = Query(default=None, max_length=120),
                           since: str | None = Query(default=None, max_length=40, description="ISO 时间，按更新时间筛选"),
                           until: str | None = Query(default=None, max_length=40),
                           limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                           user: Principal = Depends(current_user)):
        return notices.list(user, status=status, kind=type, project_id=project_id, since=since, until=until,
                            limit=limit, offset=offset)

    @router.get("/unread-count", response_model=UnreadCount, operation_id="getUnreadNotificationCount")
    def unread(user: Principal = Depends(current_user)):
        return notices.unread_count(user)

    @router.post("/read-all", response_model=MarkAllResult, operation_id="markAllNotificationsRead")
    def read_all(user: Principal = Depends(current_user)):
        return notices.mark_all(user)

    @router.post("/{notice_id}/read", response_model=Notification, operation_id="markNotificationRead",
                 summary="标为已读或改回未读")
    def mark(notice_id: str, body: MarkRead, user: Principal = Depends(current_user)):
        return notices.mark(user, notice_id, body.read)

    @router.post("/{notice_id}/open", response_model=OpenResult, operation_id="openNotification",
                 summary="点开提醒：标已读并核对对象与权限后返回跳转地址")
    def open_notice(notice_id: str, user: Principal = Depends(current_user)):
        return notices.open(user, notice_id)

    application.include_router(router)
