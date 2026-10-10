# 为什么有这个文件：给检查、候选和导出计算同一份项目输入指纹。
# 它解决什么问题：项目事实或证据已经变化时，旧建议不能仅凭正文版本号继续被接受。

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .domain import DemoState


def project_input_fingerprint(state: DemoState, project_id: str) -> str:
    workflow = state.workflows.get(project_id, {})
    project = asdict(state.projects[project_id])
    project.pop("revision")  # 记录检查、候选本身不改变用于写作的输入。
    positions = {identity: index for index, identity in enumerate(workflow.get("chapter_order", []))}
    chapters = sorted((c for c in state.chapters.values() if c.project_id == project_id),
                      key=lambda chapter: positions.get(chapter.id, len(positions)))
    payload = {
        "project": project,
        "files": [{k: v for k, v in item.items() if k not in ("content", "pages")}
                  for item in workflow.get("files", {}).values()],
        "requirements": list(workflow.get("requirements", {}).values()),
        "facts": list(workflow.get("facts", {}).values()),
        "conflicts": list(workflow.get("conflicts", {}).values()),
        "parse_confirmed": workflow.get("parse_confirmed", False),
        "plan_confirmed": workflow.get("plan_confirmed", False),
        "chapters": [{"id": c.id, "title": c.title, "volume": c.volume,
                      "revision": c.revision, "content": c.content} for c in chapters],
        "library": [item for item in state.library.values() if item["company_id"] == project["company_id"]],
        "sla": workflow.get("sla"),
        "sla_templates": [item for item in state.sla_templates.values()
                          if item["company_id"] == project["company_id"]],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
