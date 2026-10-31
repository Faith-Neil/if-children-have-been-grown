# 为什么有这个文件：项目基本信息与设置的写入（PRD v1.8 §5.1.4；APP-M2-T096、WP-4 项目设置）。
# 它解决什么问题：workflow_orchestrator 有 350 行上限（BE-TECH-DEBT-03 门禁），项目设置的校验和后续设置组（合作方、
# 规则覆盖、分册格式等）放在这里，经 MatrixMixin 挂到 WorkflowService 上；事务、版本、幂等与审计仍走 _write。

from __future__ import annotations

from dataclasses import asdict

from .domain import DomainError, Principal, iso_time
from .project_access import project_volume_mode
from .project_lifecycle import ProjectLifecycleMixin
from .project_settings_groups import BASIC_KEYS, TRACKED_FIELDS, ProjectSettingsGroupsMixin, mark_manual_edits, validate_partners
from .volume_mode import switch_volume_mode


class ProjectSettingsMixin(ProjectLifecycleMixin, ProjectSettingsGroupsMixin):
    """WorkflowService 的项目设置能力。"""

    def patch_project(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            reason = payload.pop("related_bid_reason", None)
            identity_changed = "tender_number" in payload or "name" in payload
            partners = payload.pop("project_partners", None)
            if partners is not None:
                state.project_partners[project.id] = validate_partners(partners)  # 缺协议可先存，设置页与概览待办标出
            basic = payload.pop("basic_info", None) or {}
            before = {**{f: getattr(project, f, None) for f in TRACKED_FIELDS if hasattr(project, f)},
                      **(workflow.get("basic_info") or {})}
            if basic:
                workflow.setdefault("basic_info", {}).update({k: (v or "").strip() for k, v in basic.items() if k in BASIC_KEYS})
            switch_volume_mode(state, principal, project, workflow, payload.pop("volume_mode", None), now=self.demo._now())
            for field, value in payload.items():
                if value is None:
                    raise DomainError(422, "INVALID_PROJECT_FIELD", "项目字段不能设为空值，请使用空字符串清空文本。")
                if field == "name" and not value.strip():
                    raise DomainError(422, "INVALID_PROJECT_NAME", "项目名称不能为空。")
                if field == "deadline" and value:
                    self._date(value)
                setattr(project, field, value.strip() if isinstance(value, str) else value)
            after = {**{f: getattr(project, f, None) for f in TRACKED_FIELDS if hasattr(project, f)},
                     **(workflow.get("basic_info") or {})}
            # 人工修改标记（PRD 5.1.4 第 1 项）：值真的变了才标，保存相同内容不留痕
            mark_manual_edits(workflow, [f for f in TRACKED_FIELDS if after.get(f) != before.get(f)], principal,
                              iso_time(self.demo._now()))
            if identity_changed:
                # R19 关联投标冲突（APP-M2-T096 / PRD §5.1.2 规则 2）：未填写说明则整次修改不保存
                from .related_bids import require_ack
                require_ack(state, principal, project, workflow, reason, self.demo._now())
            return {"project": {**asdict(project), "volume_mode": project_volume_mode(state, project.id)},
                    "manual_edits": workflow.get("manual_edits") or {}, "basic_info": workflow.get("basic_info") or {}}

        return self._write(principal, project_id, "project.update", payload, expected, key, operation)
