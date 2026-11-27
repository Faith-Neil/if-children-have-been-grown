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
    project.pop("last_accessed_at", None)  # 列表访问时间只是查看行为，不参与写作输入指纹。
    project.pop("status", None)  # 列表状态缓存由工作流推导，不作为额外输入源参与指纹。
    positions = {identity: index for index, identity in enumerate(workflow.get("chapter_order", []))}
    chapters = sorted((c for c in state.chapters.values() if c.project_id == project_id),
                      key=lambda chapter: (positions.get(chapter.id, len(positions)), chapter.id))
    payload = {
        "project": project,
        "team": state.project_teams.get(project_id, {}),
        "member_company_roles": {identity: state.accounts[identity].role
                                 for identity in state.project_teams.get(project_id, {}).get("members", {})
                                 if identity in state.accounts},
        "files": [{k: v for k, v in item.items() if k not in ("content", "pages")}
                  for item in workflow.get("files", {}).values()],
        "requirements": list(workflow.get("requirements", {}).values()),
        "facts": list(workflow.get("facts", {}).values()),
        "conflicts": list(workflow.get("conflicts", {}).values()),
        "parse_confirmed": workflow.get("parse_confirmed", False),
        "plan_confirmed": workflow.get("plan_confirmed", False),
        "writing_plan": workflow.get("writing_plan", {}),
        "chapters": [{"id": c.id, "title": c.title, "volume": c.volume,
                      "revision": c.revision, "content": c.content} for c in chapters],
        # library/sla_templates 在条目层按 key 存储；dict 插入序取决于进程内创建顺序，
        # 热路径按主键序重读。指纹表达的是“集合内容”，必须先按 id 规范化，否则同一输入会跨进程误判过期。
        "library": sorted((item for item in state.library.values() if item["company_id"] == project["company_id"]),
                          key=lambda item: str(item.get("id") or "")),
        "sla": workflow.get("sla"),
        "sla_templates": sorted((item for item in state.sla_templates.values()
                                 if item["company_id"] == project["company_id"]), key=lambda item: str(item.get("id") or "")),
    }
    if workflow.get("proposed_staff"):
        # 拟派人员（R33）：换人后旧检查、旧导出过期。为空时不写入，保持既有指纹不变。
        payload["proposed_staff"] = workflow["proposed_staff"]
    attachments = [{k: a.get(k) for k in ("id", "library_id", "sha256", "page_from", "page_to", "is_sensitive",
                                          "shows_identity", "feature_tags")}
                   for a in ((state.service_stores.get("attachments") or {}).get("items") or {}).values()
                   if a.get("company_id") == project["company_id"]]
    if attachments:
        # 附件扫描件（导出插页、R38 功能点）：改附件后旧检查、旧导出过期。没有附件时不写入。
        payload["attachments"] = sorted(attachments, key=lambda a: a["id"])
    if workflow.get("related_bid_ack"):
        # R19 关联投标冲突的确认说明：确认或改动后旧检查过期，重新检查才不再报 R19。为空时不写入，保持既有指纹不变。
        ack = workflow["related_bid_ack"]
        payload["related_bid_ack"] = {"company_ids": ack.get("company_ids"), "reason": ack.get("reason")}
    if workflow.get("volume_epochs"):
        # 分册解锁轮次（Wave 11）：解锁后旧检查、旧导出一律过期。为空时不写入，保持既有指纹不变。
        payload["volume_epochs"] = workflow["volume_epochs"]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
