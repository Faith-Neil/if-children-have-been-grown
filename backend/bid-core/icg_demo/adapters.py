# 为什么有这个文件：提供内存存储、模拟建议和真实 Word 文件的演示实现。
# 它解决什么问题：不接数据库或外部模型，也能验证事务、替换接口和下载结果。

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Callable, TypeVar

from .docx_style import DEFAULT_DOCX_STYLE, DocxStyle, build_docx
from .domain import Account, Chapter, DemoState, Project

T = TypeVar("T")


def seed_state() -> DemoState:
    state = DemoState()
    for user in (
        Account("alpha-editor", "甲公司编写人（合成）", "alpha", "editor"),
        Account("alpha-manager", "甲公司项目经理（合成）", "alpha", "manager"),
        Account("alpha-viewer", "甲公司查看人（合成）", "alpha", "viewer"),
        Account("beta-editor", "乙公司编写人（合成）", "beta", "editor"),
        Account("alpha-tech", "甲公司技术编写人（合成）", "alpha", "editor"),
        Account("alpha-business", "甲公司商务编写人（合成）", "alpha", "editor"),
        Account("alpha-outsider-manager", "甲公司其他项目经理（合成）", "alpha", "manager"),
        Account("beta-manager", "乙公司项目经理（合成）", "beta", "manager"),
    ):
        state.accounts[user.id] = user
    for company in ("alpha", "beta"):
        project = Project(f"{company}-project", f"{'甲' if company == 'alpha' else '乙'}公司合成投标项目", company)
        state.projects[project.id] = project
        from .project_access import initial_team
        state.project_teams[project.id] = initial_team("alpha-manager" if company == "alpha" else "beta-manager")
        if company == "alpha":
            state.project_teams[project.id]["members"].update({
                "alpha-editor": {"user_id": "alpha-editor", "project_role": "writer", "volumes": ["technical", "business"]},
                "alpha-viewer": {"user_id": "alpha-viewer", "project_role": "readonly", "volumes": ["technical", "business"]}})
        else:
            state.project_teams[project.id]["members"]["beta-editor"] = {"user_id": "beta-editor", "project_role": "writer", "volumes": ["technical", "business"]}
        for suffix, volume, title in (("tech", "technical", "技术方案"),
                                      ("business", "business", "商务响应")):
            content = (f"{'甲' if company == 'alpha' else '乙'}公司合成项目的{title}。\n"
                       "本内容仅用于本地演示，不可作为真实承诺或正式递交文件。")
            chapter = Chapter(f"{company}-{suffix}", project.id, title, volume, content)
            chapter.assignee_id = "alpha-editor" if company == "alpha" else "beta-editor"
            chapter.versions.append({"revision": 1, "content": content,
                                     "actor_id": "demo-seed", "created_at": "2026-10-10T00:00:00+00:00"})
            state.chapters[chapter.id] = chapter
    return state


class MemoryRepository:
    mode = "memory"

    def __init__(self, initial_state: DemoState | None = None):
        self._lock = RLock()
        self._state = deepcopy(initial_state if initial_state is not None else seed_state())

    def read(self) -> DemoState:
        with self._lock:
            return deepcopy(self._state)

    def transaction(self, operation: Callable[[DemoState], T]) -> T:
        with self._lock:
            working = deepcopy(self._state)
            result = operation(working)
            # 连返回值拷贝或提交快照拷贝失败，也不能把部分修改写入当前状态。
            safe_result = deepcopy(result)
            committed = deepcopy(working)
            self._state = committed
            return safe_result


class DemoModelProvider:
    name = "demo"
    is_real_model = False
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return (f"{content}\n\n[模拟建议，未调用真实模型]\n"
                f"修改要求：{instruction}\n请由编写人核对内容；确认提交前不会写入正式正文。")
