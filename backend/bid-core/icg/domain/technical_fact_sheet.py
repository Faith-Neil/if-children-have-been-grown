# 为什么有这个文件：维护技术服务方案全书唯一的「全局项目事实表（Global Fact Sheet）」结构化 JSON。
# 它解决什么问题：分段并发写长标书时，前后章节容易出现工期、质保期、SLA、项目经理或投标产品型号口径打架；
# 在解析阶段自动汇总初稿、目录确认阶段供人工核对并冻结快照，作为每一节 Prompt 与后置核验的唯一事实基准。

from __future__ import annotations

from typing import Any

from icg.domain.domain import iso_time

FACT_SHEET_FIELDS = (
    "project_name",
    "client_name",
    "service_period",
    "warranty_period",
    "sla_response",
    "on_site_staff",
    "project_manager",
    "tech_route",
)

# 三层真相源结构化扩展（dict 类型，键值均为短文本）：
# sla_terms —— 合同与 SLA 硬参数分级（如 fault_response=15分钟/onsite_level1=40分钟/fix_level1=24小时/onsite_level2=2小时/dba_service_period=6个月）
# asset_profile —— 甲方真实资产画像（device_inventory/核心系统/数据库分布等，严禁编造）
# scoring_decisions —— 评分加分项决策（月度巡检/延保月数/重保驻场次数等）
FACT_SHEET_DICT_FIELDS = ("sla_terms", "asset_profile", "scoring_decisions")

# 四层结构化扩展（list[dict]）：多服务模块周期、异构资产明细、评分表逐项真实规则。
FACT_SHEET_LIST_FIELDS = ("service_modules", "asset_inventory", "scoring_rules")


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _fact_lookup(workflow: dict, keys: tuple[str, ...]) -> str:
    facts = workflow.get("facts") or {}
    items = facts.values() if isinstance(facts, dict) else facts
    for item in items:
        if not isinstance(item, dict) or item.get("status") == "rejected":
            continue
        if str(item.get("key") or "").strip() in keys:
            val = str(item.get("value") or "").strip()
            if val:
                return val
    return ""


def _staff_manager(state: Any, workflow: dict) -> str:
    staff = workflow.get("proposed_staff") or []
    library = getattr(state, "library", {}) if state is not None else {}
    for entry in staff:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "")
        if "项目经理" in role or "项目负责人" in role or entry.get("is_key_person"):
            person = library.get(entry.get("person_id") or "") or {}
            name = str(person.get("name") or entry.get("name") or "").strip()
            if name:
                return name
    return ""


def _clean_list_rows(raw: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return rows
    for item in raw[:80]:
        if not isinstance(item, dict):
            continue
        clean = {
            str(key)[:60]: str(value)[:240]
            for key, value in item.items()
            if str(key).strip() and str(value).strip()
        }
        if clean:
            rows.append(clean)
    return rows


def build_global_fact_sheet(state: Any, project_id: str, workflow: dict) -> dict[str, Any]:
    """汇总当前项目的全局事实表：人工保存字段优先，其余从模型读标事实、通用事实与拟派团队自动补齐。"""
    stored = dict(workflow.get("global_fact_sheet") or {})
    tech_facts = workflow.get("technical_facts") or {}
    promises = workflow.get("technical_promises") or {}
    project = (getattr(state, "projects", {}) or {}).get(project_id)
    project_title = getattr(project, "name", "") if project is not None else ""

    auto_models: list[str] = []
    for raw in tech_facts.get("目标型号") or []:
        clean = str(raw or "").strip()
        if clean and clean not in auto_models:
            auto_models.append(clean)

    has_custom_models = "target_models" in stored and isinstance(stored.get("target_models"), list)
    target_models = [
        str(m).strip() for m in (stored.get("target_models") if has_custom_models else auto_models) if str(m).strip()
    ]

    auto_values = {
        "project_name": _first_nonempty(
            _fact_lookup(workflow, ("项目名称", "采购项目名称", "招标项目名称", "project_name")),
            tech_facts.get("项目理解"),
            project_title,
        ),
        "client_name": _first_nonempty(
            tech_facts.get("客户名"),
            _fact_lookup(workflow, ("采购人", "招标人", "业主", "采购单位", "客户名称", "customer_name")),
        ),
        "service_period": _first_nonempty(
            tech_facts.get("服务期"),
            _fact_lookup(workflow, ("服务期", "工期", "维保期", "服务期限", "交付期")),
        ),
        "warranty_period": _first_nonempty(
            tech_facts.get("质保期"),
            _fact_lookup(workflow, ("质保期", "免费维保期", "保修期")),
        ),
        "sla_response": _first_nonempty(
            tech_facts.get("响应时限"),
            promises.get("响应时限"),
            _fact_lookup(workflow, ("响应时限", "故障响应", "服务响应")),
        ),
        "on_site_staff": _first_nonempty(
            tech_facts.get("驻场要求"),
            _fact_lookup(workflow, ("驻场人数", "驻场要求", "驻场服务")),
        ),
        "project_manager": _first_nonempty(
            _staff_manager(state, workflow),
            tech_facts.get("团队要求"),
        ),
        "tech_route": "",
    }

    sheet: dict[str, Any] = {}
    for key in FACT_SHEET_FIELDS:
        if key in stored and stored[key] is not None:
            sheet[key] = str(stored[key]).strip()
        else:
            sheet[key] = auto_values[key]
    sheet["target_models"] = target_models
    for field in FACT_SHEET_DICT_FIELDS:
        raw = stored.get(field)
        if isinstance(raw, dict):
            clean = {str(k)[:60]: str(val)[:160] for k, val in raw.items() if str(k).strip() and str(val).strip()}
            if clean:
                sheet[field] = clean
    for field in FACT_SHEET_LIST_FIELDS:
        rows = _clean_list_rows(stored.get(field))
        if rows:
            sheet[field] = rows
    snapshot = workflow.get("global_fact_sheet_snapshot")
    sheet["frozen_at"] = snapshot.get("frozen_at") if isinstance(snapshot, dict) else None
    return sheet


def update_global_fact_sheet(state: Any, project_id: str, workflow: dict, patch: dict[str, Any]) -> dict[str, Any]:
    """保存人工核对/修改后的全局项目事实表。修改后若与已冻结快照不同，标记快照更新。"""
    current = dict(workflow.get("global_fact_sheet") or {})
    for key in FACT_SHEET_FIELDS:
        if key in patch and patch[key] is not None:
            current[key] = str(patch[key]).strip()[:300]
    if "target_models" in patch and patch["target_models"] is not None:
        raw_models = patch["target_models"]
        if isinstance(raw_models, str):
            items = [part.strip() for part in raw_models.replace("，", ",").split(",")]
        elif isinstance(raw_models, list):
            items = [str(part).strip() for part in raw_models]
        else:
            items = []
        current["target_models"] = [item[:120] for item in items if item][:30]
    for field in FACT_SHEET_DICT_FIELDS:
        if field in patch and isinstance(patch[field], dict):
            current[field] = {
                str(k)[:60]: str(val)[:160]
                for k, val in patch[field].items()
                if str(k).strip() and str(val).strip()
            }
    for field in FACT_SHEET_LIST_FIELDS:
        if field in patch and patch[field] is not None:
            current[field] = _clean_list_rows(patch[field])
    workflow["global_fact_sheet"] = current
    # 目录确认后的冻结快照不是永久缓存：人工更新事实表时必须同步刷新，
    # 否则后续分节生成会继续读取旧快照，结构化 service_modules/scoring_rules 无法注入。
    if isinstance(workflow.get("global_fact_sheet_snapshot"), dict):
        workflow["global_fact_sheet_snapshot"].update(current)
    return build_global_fact_sheet(state, project_id, workflow)


def freeze_global_fact_sheet(state: Any, project_id: str, workflow: dict, *, now: float) -> dict[str, Any]:
    """目录确认时冻结一份全书事实基准快照，供分节生成与后置一致性核验读取。"""
    sheet = build_global_fact_sheet(state, project_id, workflow)
    stamped = iso_time(now)
    snapshot = {**sheet, "frozen_at": stamped}
    workflow["global_fact_sheet_snapshot"] = snapshot
    return snapshot


def prompt_fact_sheet_json(workflow: dict | None, *, state: Any = None, project_id: str = "") -> dict[str, Any]:
    """返回注入单节生成 Prompt 的精简全局事实字典（优先用确认冻结快照，去掉空值与内部时间戳）。"""
    wf = workflow or {}
    raw = wf.get("global_fact_sheet_snapshot")
    if not isinstance(raw, dict):
        raw = build_global_fact_sheet(state, project_id, wf)
    out: dict[str, Any] = {}
    for key in FACT_SHEET_FIELDS:
        val = str(raw.get(key) or "").strip()
        if val:
            out[key] = val
    models = [str(m).strip() for m in (raw.get("target_models") or []) if str(m).strip()]
    if models:
        out["target_models"] = models
    for field in FACT_SHEET_DICT_FIELDS:
        raw_dict = raw.get(field)
        if isinstance(raw_dict, dict) and raw_dict:
            out[field] = dict(raw_dict)
    for field in FACT_SHEET_LIST_FIELDS:
        rows = _clean_list_rows(raw.get(field))
        if rows:
            out[field] = rows
    from datetime import datetime
    # 生成期当前年份是反过时日程硬约束：2026 年项目不得排 2024/2025 重保计划。
    out["current_year"] = str(datetime.now().year)
    return out
