# 为什么有这个文件：导出文件命名（PRD v1.8 §5.1.4 第 9 项“导出设置”、§5.9.1 第 11 条与命名变量说明、验收⑤；
# 8.2 节第四十条：递交版不得出现编写人；APP-M2-T086、T150）。
# 它解决什么问题：
# 1. 内部稿按“{编写人}_{版本}_{日期}_{项目名称}”命名：编写人取分册负责人姓名，版本为本分册内部稿的导出序号（V1.0、V2.0…），
#    日期为北京时间 YYYYMMDD；
# 2. 递交版按招标要求的规则命名，招标无要求时默认“{项目名称}_{分册名称}”；规则里含 {编写人} 时不能保存，导出时也再拦一次；
# 3. 只认识登记过的变量；文件名里去掉 Windows 不允许的字符；同一批次两册重名时自动补分册名称；
# 4. 规则保存在项目工作流里（项目负责人修改），导出记录保存当时用的规则快照。

from __future__ import annotations

import re
from typing import Any

from .domain import DomainError, Principal, iso_time

VARIABLES = {"编写人": "分册负责人姓名（仅内部稿）", "版本": "本分册内部稿导出序号，如 V2.0", "日期": "导出日期 YYYYMMDD",
             "项目名称": "项目名称", "分册名称": "技术分册 / 商务分册", "招标编号": "招标编号"}
DEFAULT_INTERNAL = "{编写人}_{版本}_{日期}_{项目名称}"
DEFAULT_SUBMIT = "{项目名称}_{分册名称}"
_VAR = re.compile(r"\{([^{}]+)\}")
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def settings(workflow: dict) -> dict:
    saved = workflow.get("export_settings") or {}
    return {"internal_template": saved.get("internal_template") or DEFAULT_INTERNAL,
            "submit_rule": saved.get("submit_rule") or DEFAULT_SUBMIT,
            "updated_by": saved.get("updated_by"), "updated_at": saved.get("updated_at"),
            "variables": [{"name": k, "description": v} for k, v in VARIABLES.items()]}


def problems(rule: str, kind: str) -> list[str]:
    found = []
    unknown = sorted({v for v in _VAR.findall(rule) if v not in VARIABLES})
    if unknown:
        found.append("不认识的变量：" + "、".join("{" + v + "}" for v in unknown))
    if kind == "submission" and "{编写人}" in rule:
        found.append("递交版命名不能含 {编写人}：投标文件出现编写人信息，可能被用来判断不同投标人的文件由同一人编制")
    if not _ILLEGAL.sub("", _VAR.sub("x", rule)).strip("._ "):
        found.append("命名规则不能为空")
    if len(rule) > 200:
        found.append("命名规则不能超过 200 字")
    return found


def render(rule: str, values: dict[str, str]) -> str:
    name = _VAR.sub(lambda m: values.get(m.group(1), ""), rule)
    name = _ILLEGAL.sub("_", name).strip(" ._") or "投标文件"
    return name[:150]


def internal_version(workflow: dict, volume: str) -> str:
    done = sum(1 for record in (workflow.get("exports") or {}).values()
               if record.get("kind") in ("internal", "internal_review") and record.get("export_status") != "failed"
               and any(v.get("volume") == volume for v in record.get("volumes") or []))
    return f"V{done + 1}.0"


def filenames(state: Any, project: Any, workflow: dict, kind: str, volumes: dict[str, str], date: str) -> tuple[dict[str, str], str]:
    """每册文件名（含 .docx）与所用规则快照。volumes：分册代码 → 分册名称。"""
    current = settings(workflow)
    submission = kind == "submission"
    rule = current["submit_rule"] if submission else current["internal_template"]
    issues = problems(rule, "submission" if submission else "internal")
    if issues:
        raise DomainError(422, "VALIDATION_ERROR", "导出命名规则不可用：" + "；".join(issues), {"rule": rule})
    owners = (state.project_teams.get(project.id) or {}).get("owners") or {}
    names: dict[str, str] = {}
    for volume, label in volumes.items():
        writer = state.accounts.get(owners.get(volume) or "")
        values = {"项目名称": project.name, "分册名称": label, "招标编号": project.tender_number or "", "日期": date,
                  "版本": internal_version(workflow, volume), "编写人": "" if submission else (writer.name if writer else "")}
        custom = (workflow.get("volume_settings") or {}).get(volume, {}).get("submit_file_name") if submission else None
        names[volume] = render(custom, {}) if custom else render(rule, values)  # 分册设置的递交文件名优先（PRD 5.1.4 第 8 项）
    if len(set(names.values())) < len(names):
        names = {volume: f"{name}_{volumes[volume]}" for volume, name in names.items()}
    return {volume: name + ".docx" for volume, name in names.items()}, rule


class ExportNamingMixin:
    """挂在 WorkflowService 上：读取与保存导出命名规则（保存仅项目负责人；动作名 export_settings.update）。"""

    def export_settings(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        return settings(self._workflow(state, project_id))

    def save_export_settings(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        internal = (payload.get("internal_template") or "").strip() or DEFAULT_INTERNAL
        submit = (payload.get("submit_rule") or "").strip() or DEFAULT_SUBMIT
        issues = [f"内部稿：{p}" for p in problems(internal, "internal")] + [f"递交版：{p}" for p in problems(submit, "submission")]
        if issues:
            raise DomainError(422, "VALIDATION_ERROR", "；".join(issues), {"internal_template": internal, "submit_rule": submit})

        def operation(state, project, workflow):
            workflow["export_settings"] = {"internal_template": internal, "submit_rule": submit,
                                           "updated_by": principal.user.id, "updated_at": iso_time(self.demo._now())}
            return settings(workflow)
        return self._write(principal, project_id, "export_settings.update", payload, expected, key, operation)
