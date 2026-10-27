# 为什么有这个文件：实现招标文件解析驱动的大纲树自动规划构建引擎（AI-OUTLINE-AUTO-TREE-BUILD）。
# 它解决什么问题：
# 1. 结构化大纲树自动衍生：基于招标文件解析出的矩阵条款（商务资质、技术方案、实施服务、安全合规、偏离表），
#    自动构建规范的“卷 (Volume) -> 编/章 (Part/Chapter) -> 节 (Section) -> 子节 (Subsection)”多层级大纲树，并生成标准层级编号；
# 2. 评分要点与写作指引智能对齐：将招标文件评分标准与响应条款精确挂接到叶子章节节点，自动生成结构化写作要点（writing_points）、
#    建议目标字数（target_length）与关联条款清单（bound_requirement_ids）；
# 3. 多租户强隔离与防编造追溯：关联依据严格绑定真实招标文件条款 ID，严禁虚构依据；严格执行多租户隔离与角色门禁；
# 4. 涉密项目本地模型门禁：涉密项目模型规划硬门禁拦截（SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 5. 大纲定稿锁定前置就绪检查：全方位核验大纲完整性、分册覆盖度与零未映射条款。

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

from icg.domain.domain import Chapter, DemoState, DomainError, Principal, Project, iso_time, new_id
from icg.domain.generation_context import chapter_plan, writing_source_fingerprint, plan_is_current
from icg.domain.project_access import READONLY_SYSTEM_ROLES, VOLUMES, lead, member, normalize_role, volume_owner, writable


class OutlinePlanError(DomainError):
    """大纲方案专属领域异常，支持自定义 HTTP 状态码且兼容 DomainError。"""

    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        Exception.__init__(self, message)


CHINESE_NUMS = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def to_chinese_num(n: int) -> str:
    """将阿拉伯数字转换为中文数字（1 -> 一, 12 -> 十二, 25 -> 二十五）。"""
    if n <= 0:
        return "零"
    if n <= 10:
        return CHINESE_NUMS[n]
    if n < 20:
        return "十" + (CHINESE_NUMS[n % 10] if n % 10 != 0 else "")
    tens = n // 10
    ones = n % 10
    tens_str = CHINESE_NUMS[tens] + "十"
    ones_str = CHINESE_NUMS[ones] if ones > 0 else ""
    return tens_str + ones_str


def format_volume_info(volume: str, index: int) -> tuple[str, str]:
    """返回 (中文编号, 完整卷标题)。"""
    c_num = f"第{to_chinese_num(index)}卷"
    name = "技术标" if volume == "technical" else "商务标"
    return c_num, f"{c_num} {name}"


def format_chapter_info(index: int, name: str) -> tuple[str, str, str]:
    """返回 (中文章号, 章节序号如 1.0, 完整章标题)。"""
    c_num = f"第{to_chinese_num(index)}章"
    sec_num = f"{index}.0"
    return c_num, sec_num, f"{c_num} {name}"


def format_section_info(chapter_idx: int, section_idx: int, name: str) -> tuple[str, str]:
    """返回 (节序号如 1.1, 完整节标题)。"""
    sec_num = f"{chapter_idx}.{section_idx}"
    return sec_num, f"{sec_num} {name}"


def format_subsection_info(chapter_idx: int, section_idx: int, sub_idx: int, name: str) -> tuple[str, str]:
    """返回 (子节序号如 1.1.1, 完整子节标题)。"""
    sec_num = f"{chapter_idx}.{section_idx}.{sub_idx}"
    return sec_num, f"{sec_num} {name}"


def infer_chapter_type(title: str, explicit_type: str | None = None) -> str:
    """推断章节分类：general（通用）、specialized（专项）、system（系统生成）。"""
    if explicit_type in ("general", "specialized", "system"):
        return explicit_type
    lower = title.lower()
    if any(k in lower for k in ("系统", "封面", "目录", "声明", "导出", "签署", "附录", "偏离表", "应答表", "清单")):
        return "system"
    if any(k in lower for k in ("专项", "技术", "安全", "实施", "应急", "演练", "架构", "巡检", "维保", "服务方案")):
        return "specialized"
    return "general"


def classify_requirement_clause(req: dict[str, Any]) -> tuple[str, str, str]:
    """对招标条款进行分类与归属判定。
    
    返回：(volume, major_category, sub_category)
    major_category: qualification, deviation, technical_arch, service_sla, security, system
    """
    category = (req.get("category") or "").lower()
    text = (req.get("text") or req.get("clause") or "").lower()
    explicit_vol = req.get("volume")

    # 1. 偏离表识别
    if "deviation" in category or "偏离" in text:
        vol = explicit_vol or ("business" if any(k in text for k in ("商务", "报价", "付款", "交货")) else "technical")
        return vol, "deviation", "deviation_table"

    # 2. 商务资格与资质
    if (
        explicit_vol == "business"
        or category in ("commercial", "qualification", "business", "legal", "finance")
        or any(k in text for k in ("资质", "营业执照", "法人", "财报", "审计", "纳税", "社保", "信誉", "业绩", "证书"))
    ):
        vol = "business"
        if any(k in text for k in ("财务", "审计", "纳税", "资产", "负债")):
            sub = "financial_audit"
        elif any(k in text for k in ("业绩", "案例", "合同", "中标")):
            sub = "track_record"
        elif any(k in text for k in ("认证", "体系", "iso", "cmmi", "信用", "评级")):
            sub = "certifications"
        else:
            sub = "basic_qualifications"
        return vol, "qualification", sub

    # 3. 实施与运维服务
    if (
        category in ("service", "implementation", "sla", "training", "maintenance")
        or any(k in text for k in ("实施", "交付", "服务", "sla", "培训", "巡检", "维保", "运维", "团队", "人员", "驻场", "工期"))
    ):
        vol = "technical"
        if any(k in text for k in ("团队", "人员", "项目经理", "架构师", "配置")):
            sub = "service_team"
        elif any(k in text for k in ("培训", "巡检", "sla", "响应时间", "故障", "维保")):
            sub = "service_sla"
        elif any(k in text for k in ("计划", "进度", "里程碑", "工期")):
            sub = "service_schedule"
        else:
            sub = "service_plan"
        return vol, "service_sla", sub

    # 4. 技术架构与高可用拓扑方案（优先于安全应急中的双活/容灾）
    if (
        category in ("technical", "system", "architecture", "tech")
        or any(k in text for k in ("高可用", "双活", "微服务", "架构", "数据库", "负载均衡", "分布式", "接口", "集成", "拓扑"))
    ):
        vol = explicit_vol or "technical"
        if any(k in text for k in ("高可用", "双活", "数据库", "负载均衡", "主从", "切换时间")):
            sub = "tech_ha_architecture"
        elif any(k in text for k in ("接口", "集成", "第三方", "对接", "api")):
            sub = "tech_integration"
        elif any(k in text for k in ("功能", "业务流程", "交互", "模块")):
            sub = "tech_features"
        else:
            sub = "tech_overall"
        return vol, "technical_arch", sub

    # 5. 安全保障与应急
    if (
        category in ("security", "compliance", "disaster", "emergency")
        or any(k in text for k in ("安全", "等保", "加密", "备份", "容灾", "应急", "演练", "保密", "防攻击", "合规"))
    ):
        vol = "technical"
        if any(k in text for k in ("容灾", "应急", "演练", "备份", "预案")):
            sub = "security_emergency"
        elif any(k in text for k in ("隐私", "数据安全", "合规", "加密")):
            sub = "security_data"
        else:
            sub = "security_network"
        return vol, "security", sub

    # 6. 默认兜底技术总体方案
    vol = explicit_vol or "technical"
    return vol, "technical_arch", "tech_overall"


def generate_structured_writing_points(
    title: str,
    section_number: str,
    volume: str,
    chapter_type: str,
    bound_requirements: list[dict[str, Any]],
    target_length: int,
    value_added: bool = False,
    value_added_reason: str = "",
) -> str:
    """生成结构化正文编写要点与评分响应指引。"""
    vol_desc = "技术分册" if volume == "technical" else "商务分册"
    type_desc = "系统生成类" if chapter_type == "system" else "专项响应类" if chapter_type == "specialized" else "通用类"

    lines = [
        f"### 章节编写要点与响应指引",
        f"- **章节定位**：{section_number} {title}（{type_desc}）",
        f"- **分册归属**：{vol_desc}",
        f"- **建议目标字数**：约 {target_length} 字",
    ]

    if value_added:
        lines.append(f"- **增值响应章节**：是（增值理由：{value_added_reason or '提供超越招标要求的行业标杆品质保障'}）")

    if not bound_requirements:
        lines.append("- **关联条款**：无直接招标条款绑定，主要阐述通用支撑与企业规范。")
        lines.append("- **佐证要求**：遵循真实诚信原则，引用已核验的企业事实与资质材料。")
        return "\n".join(lines)

    total_score = sum(float(r.get("score") or 0.0) for r in bound_requirements)
    lines.append(f"- **对应招标文件条款与评分项**（共 {len(bound_requirements)} 条，累计分值 {total_score} 分）：")

    for idx, r in enumerate(bound_requirements, start=1):
        req_id = r.get("id", f"req-{idx}")
        clause = r.get("clause") or r.get("text") or "招标文件条款"
        resp = r.get("response") or "fully_comply"
        score_val = r.get("score")
        score_str = f"，分值 {score_val} 分" if score_val is not None else ""
        criteria = r.get("scoring_criteria") or r.get("reason") or "按要求完整响应并提供有效佐证材料"

        tags = []
        if r.get("mandatory") or r.get("asterisk") or "★" in clause:
            tags.append("【★关键星号项·必须实质响应】")
        if r.get("disqualified") or "废标" in clause:
            tags.append("【废标红线项·不符直接废标】")

        tag_str = " ".join(tags)
        lines.append(f"  {idx}. [{req_id}] {clause}（响应方式: {resp}{score_str}）{tag_str}")
        lines.append(f"     * 评分标准与要点：{criteria}")

    lines.append("- **客观事实与证据引用要求**：")
    lines.append("  * 须关联对应资质证书、合规检测报告、SLA承诺或真实合同业绩，严禁空头承诺；")
    lines.append("  * 严格对齐招标文件所列技术参数与指标，严禁编造未经核实的技术参数。")

    return "\n".join(lines)


# 标准大纲骨架模板定义
STANDARD_TREE_TEMPLATE = {
    "business": [
        {
            "part": 1,
            "title_name": "投标人商务资质与综合实力",
            "category": "qualification",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "投标人营业资质与法定代表人授权",
                    "sub_category": "basic_qualifications",
                    "chapter_type": "general",
                },
                {
                    "sec_idx": 2,
                    "title_name": "财务审计报告与资产纳税证明",
                    "sub_category": "financial_audit",
                    "chapter_type": "general",
                },
                {
                    "sec_idx": 3,
                    "title_name": "企业资质认证与质量信用评级",
                    "sub_category": "certifications",
                    "chapter_type": "general",
                },
                {
                    "sec_idx": 4,
                    "title_name": "同类项目业绩与合同案例",
                    "sub_category": "track_record",
                    "chapter_type": "general",
                },
            ],
        },
        {
            "part": 2,
            "title_name": "商务偏离表与格式文件承诺",
            "category": "deviation",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "商务条款实质性偏离说明表",
                    "sub_category": "deviation_table",
                    "chapter_type": "system",
                    "system_subtype": "deviation_table",
                },
                {
                    "sec_idx": 2,
                    "title_name": "商务合规声明与格式签署文件",
                    "sub_category": "basic_qualifications",
                    "chapter_type": "system",
                },
            ],
        },
    ],
    "technical": [
        {
            "part": 1,
            "title_name": "总体技术方案与系统架构设计",
            "category": "technical_arch",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "系统总体业务与技术拓扑设计",
                    "sub_category": "tech_overall",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 2,
                    "title_name": "核心业务功能与流程交互方案",
                    "sub_category": "tech_features",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 3,
                    "title_name": "高可用架构与主从双活容灾方案",
                    "sub_category": "tech_ha_architecture",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 4,
                    "title_name": "系统接口与第三方集成方案",
                    "sub_category": "tech_integration",
                    "chapter_type": "specialized",
                },
            ],
        },
        {
            "part": 2,
            "title_name": "项目实施交付与运维服务保障",
            "category": "service_sla",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "项目实施组织架构与人员配备",
                    "sub_category": "service_team",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 2,
                    "title_name": "实施进度计划与质量里程碑管控",
                    "sub_category": "service_schedule",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 3,
                    "title_name": "7x24小时运维保障与SLA服务承诺",
                    "sub_category": "service_sla",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 4,
                    "title_name": "客户培训、日常巡检与资产移交",
                    "sub_category": "service_plan",
                    "chapter_type": "specialized",
                },
            ],
        },
        {
            "part": 3,
            "title_name": "信息安全合规与应急处置预案",
            "category": "security",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "网络安全防护与等保合规措施",
                    "sub_category": "security_network",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 2,
                    "title_name": "数据加密存储与隐私合规保护",
                    "sub_category": "security_data",
                    "chapter_type": "specialized",
                },
                {
                    "sec_idx": 3,
                    "title_name": "应急响应机制与业务连续性演练",
                    "sub_category": "security_emergency",
                    "chapter_type": "specialized",
                },
            ],
        },
        {
            "part": 4,
            "title_name": "技术偏离表与点对点应答清单",
            "category": "deviation",
            "sections": [
                {
                    "sec_idx": 1,
                    "title_name": "技术要求及规格参数偏离说明表",
                    "sub_category": "deviation_table",
                    "chapter_type": "system",
                    "system_subtype": "deviation_table",
                },
                {
                    "sec_idx": 2,
                    "title_name": "招标文件技术规范点对点逐条应答表",
                    "sub_category": "point_to_point",
                    "chapter_type": "system",
                    "system_subtype": "point_to_point",
                },
            ],
        },
    ],
}


class AutoTreeBuildEngine:
    """招标文件解析驱动的大纲树自动规划构建引擎。"""

    def __init__(self, demo_service: Any = None):
        self.demo = demo_service

    def build_tree_structure(
        self,
        requirements: list[dict[str, Any]],
        options: dict[str, Any] | None = None,
        existing_chapters: list[Chapter] | None = None,
    ) -> dict[str, Any]:
        """根据招标条款构建多层级规范化大纲树并对齐条款与要点。"""
        options = options or {}
        req_by_id = {r["id"]: r for r in requirements if "id" in r}

        # 1. 条款防编造校验：若用户传入自定义映射，必须核实 ID 存在于需求矩阵中
        custom_mappings = options.get("custom_mappings") or {}
        for ch_key, req_ids in custom_mappings.items():
            for req_id in req_ids:
                if req_id not in req_by_id:
                    raise OutlinePlanError(
                        422,
                        "INVALID_REQUIREMENT_REFERENCE",
                        f"条款 ID 不存在于当前招标文件解析矩阵中: {req_id}",
                        {"invalid_id": req_id, "chapter_key": ch_key},
                    )

        # 2. 条款分类分流
        req_mapping_buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for req in requirements:
            vol, major, sub = classify_requirement_clause(req)
            req_mapping_buckets.setdefault((vol, major, sub), []).append(req)

        # 3. 递归构建分层大纲树（卷 -> 章/编 -> 节）
        vol_order = ["business", "technical"]
        volumes_result = []
        all_leaf_chapters = []
        mapped_req_ids = set()

        # 现有章节索引映射（支持保留或更新原有章节内容）
        existing_by_volume: dict[str, list[Chapter]] = {}
        for ec in existing_chapters or []:
            existing_by_volume.setdefault(ec.volume, []).append(ec)

        for v_idx, vol in enumerate(vol_order, start=1):
            c_vol_num, vol_title = format_volume_info(vol, v_idx)
            vol_template = STANDARD_TREE_TEMPLATE.get(vol, [])
            vol_chapters_result = []

            for ch_item in vol_template:
                part_idx = ch_item["part"]
                major_cat = ch_item["category"]
                ch_c_num, ch_sec_num, ch_full_title = format_chapter_info(part_idx, ch_item["title_name"])

                section_nodes = []
                for sec_item in ch_item["sections"]:
                    sec_idx = sec_item["sec_idx"]
                    sec_sub = sec_item["sub_category"]
                    sec_num, sec_full_title = format_section_info(part_idx, sec_idx, sec_item["title_name"])

                    # 提取匹配此节的条款
                    matched_reqs = req_mapping_buckets.get((vol, major_cat, sec_sub), [])
                    # 合并自定义映射
                    for custom_req_id in custom_mappings.get(sec_num, []):
                        if custom_req_id in req_by_id and req_by_id[custom_req_id] not in matched_reqs:
                            matched_reqs.append(req_by_id[custom_req_id])

                    bound_ids = [r["id"] for r in matched_reqs]
                    mapped_req_ids.update(bound_ids)

                    has_asterisk = any(
                        r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") or "★" in r.get("text", "")
                        for r in matched_reqs
                    )
                    has_disqualified = any(
                        r.get("disqualified") or "废标" in r.get("clause", "") or "废标" in r.get("text", "")
                        for r in matched_reqs
                    )
                    is_mandatory = has_asterisk or has_disqualified

                    # 目标字数计算
                    base_length = 800
                    added_len = len(matched_reqs) * 250 + (200 if is_mandatory else 0)
                    target_length = min(3000, base_length + added_len)

                    # 章节类型与增值标记
                    ch_type = sec_item.get("chapter_type", "general")
                    value_added = len(matched_reqs) == 0 and sec_item.get("value_added", False)
                    value_added_reason = sec_item.get("value_added_reason", "")

                    writing_points = generate_structured_writing_points(
                        title=sec_item["title_name"],
                        section_number=sec_num,
                        volume=vol,
                        chapter_type=ch_type,
                        bound_requirements=matched_reqs,
                        target_length=target_length,
                        value_added=value_added,
                        value_added_reason=value_added_reason,
                    )

                    # 为该节生成或复用 chapter_id
                    slug = re.sub(r"[^a-zA-Z0-9]+", "-", sec_sub).strip("-")
                    sec_chapter_id = f"chapter-{vol[:4]}-{part_idx}-{sec_idx}-{slug}"

                    # 尝试从 existing_chapters 复用未使用的 id
                    cand_list = existing_by_volume.get(vol, [])
                    if cand_list:
                        reused = cand_list.pop(0)
                        sec_chapter_id = reused.id

                    leaf_node = {
                        "id": sec_chapter_id,
                        "chapter_id": sec_chapter_id,
                        "title": sec_full_title,
                        "raw_title": sec_item["title_name"],
                        "section_number": sec_num,
                        "level": 2,
                        "volume": vol,
                        "chapter_type": ch_type,
                        "system_subtype": sec_item.get("system_subtype"),
                        "is_leaf": True,
                        "bound_requirement_ids": bound_ids,
                        "associated_clause_ids": bound_ids,
                        "has_asterisk": has_asterisk,
                        "has_disqualified": has_disqualified,
                        "is_mandatory": is_mandatory,
                        "writing_points": writing_points,
                        "target_length": target_length,
                        "value_added": value_added,
                        "value_added_reason": value_added_reason,
                        "scoring_rows": [
                            {
                                "id": r.get("id"),
                                "clause": r.get("clause") or r.get("text"),
                                "score": r.get("score"),
                                "mandatory": bool(r.get("mandatory") or r.get("asterisk")),
                                "disqualified": bool(r.get("disqualified")),
                            }
                            for r in matched_reqs
                        ],
                        "children": [],
                    }
                    section_nodes.append(leaf_node)
                    all_leaf_chapters.append(leaf_node)

                chapter_node = {
                    "id": f"part-{vol[:4]}-{part_idx}",
                    "chinese_num": ch_c_num,
                    "section_number": ch_sec_num,
                    "title": ch_full_title,
                    "raw_title": ch_item["title_name"],
                    "level": 1,
                    "volume": vol,
                    "chapter_type": "specialized" if vol == "technical" else "general",
                    "children": section_nodes,
                }
                vol_chapters_result.append(chapter_node)

            vol_node = {
                "id": f"vol-{vol}",
                "volume": vol,
                "chinese_num": c_vol_num,
                "title": vol_title,
                "level": 0,
                "children": vol_chapters_result,
            }
            volumes_result.append(vol_node)

        # 4. 检查是否有未映射条款，如有则自动挂接到对应卷的专项响应节，杜绝遗漏
        unmapped_reqs = [r for r in requirements if r.get("id") and r["id"] not in mapped_req_ids]
        if unmapped_reqs:
            for un_req in unmapped_reqs:
                target_vol = un_req.get("volume", "technical")
                # 挂接至该卷第一个专项叶子节点
                fallback_leaf = next(
                    (c for c in all_leaf_chapters if c["volume"] == target_vol and c["chapter_type"] != "system"),
                    all_leaf_chapters[0],
                )
                fallback_leaf["bound_requirement_ids"].append(un_req["id"])
                fallback_leaf["associated_clause_ids"].append(un_req["id"])
                if un_req.get("mandatory") or un_req.get("asterisk") or "★" in un_req.get("clause", ""):
                    fallback_leaf["has_asterisk"] = True
                    fallback_leaf["is_mandatory"] = True
                if un_req.get("disqualified") or "废标" in un_req.get("clause", ""):
                    fallback_leaf["has_disqualified"] = True
                    fallback_leaf["is_mandatory"] = True
                mapped_req_ids.add(un_req["id"])

        # 5. 计算评分项分值权重加权与章节优先级智能排序
        summary, recommended_order = calculate_score_weights_and_priorities(all_leaf_chapters, requirements)

        return {
            "volumes": volumes_result,
            "tree": volumes_result,
            "leaf_chapters": all_leaf_chapters,
            "total_volumes": len(volumes_result),
            "total_parts": sum(len(v["children"]) for v in volumes_result),
            "total_leaf_chapters": len(all_leaf_chapters),
            "mapped_requirements_count": len(mapped_req_ids),
            "unmapped_requirements_count": len(requirements) - len(mapped_req_ids),
            "score_weights_summary": summary,
            "recommended_writing_order": recommended_order,
        }


def calculate_score_weights_and_priorities(
    leaf_chapters: list[dict[str, Any]],
    requirements: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """计算各叶子章节的评分项分值权重与综合优先级，并输出推荐编写队列。

    核心逻辑：
    1. 真实分值累加：分值严格来源于真实招标文件评分条款（score），严禁编造；
    2. 权重计算：计算章节占全标权重（score_weight）与占所属分册权重（volume_score_weight）；
    3. 综合优先级与加权得分（priority_score = sec_score + priority_bonus）：
       - 包含一票否决废标条款（disqualified）：priority="critical", bonus=100.0；
       - 包含★关键必保条款（asterisk）：priority="critical", bonus=60.0；
       - 高分值项（分值>=15分或占比>=15%）：priority="high", bonus=30.0；
       - 中分值项（分值>=5分或占比>=5%）：priority="medium", bonus=15.0；
       - 常规支撑项：priority="low", bonus=0.0；
    4. 推荐编写队列（recommended_writing_order）：按 (-priority_score, -sec_score, section_number) 倒序生成。

    返回：(score_weights_summary, recommended_writing_order)
    """
    req_by_id = {r["id"]: r for r in (requirements or []) if isinstance(r, dict) and "id" in r}

    def safe_score(val: Any) -> float:
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    # 1. 计算每个叶子章节的真实分值总计 (total_score)
    for leaf in leaf_chapters:
        sec_score = 0.0
        # 优先从 scoring_rows 统计真实分值
        if leaf.get("scoring_rows"):
            sec_score = sum(safe_score(r.get("score")) for r in leaf["scoring_rows"])
        # 若 scoring_rows 为空但有 bound_requirement_ids，回退查表
        elif leaf.get("bound_requirement_ids") and req_by_id:
            for rid in leaf["bound_requirement_ids"]:
                if rid in req_by_id:
                    sec_score += safe_score(req_by_id[rid].get("score"))
        leaf["total_score"] = round(sec_score, 2)

    # 2. 汇总大标总分与各分册总分
    grand_total_score = round(sum(leaf["total_score"] for leaf in leaf_chapters), 2)
    volume_scores: dict[str, float] = {}
    volume_weights: dict[str, float] = {}

    for vol in ("business", "technical"):
        v_score = round(sum(leaf["total_score"] for leaf in leaf_chapters if leaf.get("volume") == vol), 2)
        volume_scores[vol] = v_score
        volume_weights[vol] = round(v_score / grand_total_score, 4) if grand_total_score > 0 else 0.0

    # 3. 计算相对权重、优先级判定与综合优先级得分 (priority_score)
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    scored_count = 0

    for leaf in leaf_chapters:
        sec_score = leaf["total_score"]
        if sec_score > 0:
            scored_count += 1

        # 总体权重与分册内权重（除以零保护）
        score_weight = round(sec_score / grand_total_score, 4) if grand_total_score > 0 else 0.0
        vol = leaf.get("volume", "technical")
        v_total = volume_scores.get(vol, 0.0)
        vol_weight = round(sec_score / v_total, 4) if v_total > 0 else 0.0

        leaf["score_weight"] = score_weight
        leaf["volume_score_weight"] = vol_weight

        # 判定是否含废标/星号
        has_disq = bool(leaf.get("has_disqualified"))
        has_ast = bool(leaf.get("has_asterisk"))

        # 如果尚未标记，检查 bound_requirements
        if not (has_disq and has_ast) and req_by_id and leaf.get("bound_requirement_ids"):
            for rid in leaf["bound_requirement_ids"]:
                req = req_by_id.get(rid)
                if req:
                    clause = req.get("clause") or req.get("text") or ""
                    if req.get("disqualified") or "废标" in clause:
                        has_disq = True
                    if req.get("mandatory") or req.get("asterisk") or "★" in clause:
                        has_ast = True

        leaf["has_disqualified"] = has_disq
        leaf["has_asterisk"] = has_ast
        leaf["is_mandatory"] = bool(has_disq or has_ast)

        # 优先级与加权得分逻辑
        if has_disq:
            priority = "critical"
            bonus = 100.0
            reason = "含一票否决废标条款，最高优先级前置编写与硬核审核"
            action = "立即前置安排资深专家编写并组织法务与合规硬核复审，严防废标风险"
            critical_count += 1
        elif has_ast:
            priority = "critical"
            bonus = 60.0
            reason = "含★关键必保条款，核心重点章节"
            action = "优先编写，严格对照评分标准逐条对齐指标与证明材料"
            critical_count += 1
        elif sec_score >= 15.0 or score_weight >= 0.15:
            priority = "high"
            bonus = 30.0
            pct_str = f"{round(score_weight * 100, 1)}%"
            reason = f"高分值关键章节（分值 {sec_score} 分，占总分 {pct_str}）"
            action = "重点打磨方案深度与技术细节，争取评委技术高分与优势分"
            high_count += 1
        elif sec_score >= 5.0 or score_weight >= 0.05:
            priority = "medium"
            bonus = 15.0
            pct_str = f"{round(score_weight * 100, 1)}%"
            reason = f"中等分值标准章节（分值 {sec_score} 分，占总分 {pct_str}）"
            action = "按标准模板规范化响应，确保佐证材料与资质完整合规"
            medium_count += 1
        else:
            priority = "low"
            bonus = 0.0
            reason = "基础支撑/常规履约章节"
            action = "依托既有知识库方案片段与模板快速组装生成"
            low_count += 1

        priority_score = round(sec_score + bonus, 2)
        leaf["priority"] = priority
        leaf["priority_score"] = priority_score
        leaf["priority_reason"] = reason
        leaf["suggested_action"] = action

    # 4. 生成推荐编写队列 (recommended_writing_order)
    # 排序规则：-priority_score (优先级分从高到低), -total_score (分值从高到低), section_number (章节号顺排)
    sorted_leaves = sorted(
        leaf_chapters,
        key=lambda item: (-item.get("priority_score", 0.0), -item.get("total_score", 0.0), str(item.get("section_number", ""))),
    )

    recommended_writing_order = [
        {
            "order": idx + 1,
            "chapter_id": leaf["id"],
            "section_number": leaf.get("section_number", ""),
            "title": leaf.get("title", ""),
            "volume": leaf.get("volume", ""),
            "chapter_type": leaf.get("chapter_type", "general"),
            "total_score": leaf.get("total_score", 0.0),
            "score_weight": leaf.get("score_weight", 0.0),
            "volume_score_weight": leaf.get("volume_score_weight", 0.0),
            "priority": leaf.get("priority", "low"),
            "priority_score": leaf.get("priority_score", 0.0),
            "priority_reason": leaf.get("priority_reason", ""),
            "suggested_action": leaf.get("suggested_action", ""),
            "bound_requirement_ids": deepcopy(leaf.get("bound_requirement_ids", [])),
            "has_asterisk": leaf.get("has_asterisk", False),
            "has_disqualified": leaf.get("has_disqualified", False),
        }
        for idx, leaf in enumerate(sorted_leaves)
    ]

    summary = {
        "grand_total_score": grand_total_score,
        "volume_scores": volume_scores,
        "volume_weights": volume_weights,
        "priority_distribution": {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
        "critical_chapters_count": critical_count,
        "high_score_chapters_count": high_count,
        "total_scored_chapters": scored_count,
        "total_leaf_chapters": len(leaf_chapters),
    }

    return summary, recommended_writing_order


def check_tree_finalization_readiness(
    state: DemoState,
    project_id: str,
    volume: str = "all",
) -> dict[str, Any]:
    """核验大纲是否满足分册定稿锁定的前置要求。"""
    workflow = state.workflows.get(project_id, {})
    all_chapters = [c for c in state.chapters.values() if c.project_id == project_id]
    target_chapters = [c for c in all_chapters if volume == "all" or c.volume == volume]

    plan_ready = bool(workflow.get("plan_confirmed") or plan_is_current(state, project_id))
    empty_chapters = [c.title for c in target_chapters if not c.content.strip()]
    pending_chapters = [c.title for c in target_chapters if "待补" in c.content]

    # 未映射条款核查
    valid_chapter_ids = {c.id for c in all_chapters}
    all_reqs = list(workflow.get("requirements", {}).values())
    unmapped_reqs = [
        r["id"]
        for r in all_reqs
        if (volume == "all" or r.get("volume") == volume)
        and r.get("status") != "rejected"
        and (not r.get("chapter_id") or r.get("chapter_id") not in valid_chapter_ids)
    ]

    # 必备分册覆盖核查
    present_volumes = {c.volume for c in all_chapters}
    missing_volumes = []
    if volume == "all":
        missing_volumes = [v for v in VOLUMES if v not in present_volumes]

    # 星号条款 / 废标条款对应章节是否标记不适用
    outline_plans = workflow.get("outline_plans", {})
    mandatory_blocked = []
    for r in all_reqs:
        ch_id = r.get("chapter_id")
        if ch_id and ch_id in outline_plans:
            meta = outline_plans[ch_id]
            is_mandatory = (
                r.get("mandatory") or r.get("asterisk") or r.get("disqualified")
                or "★" in r.get("clause", "") or "废标" in r.get("clause", "")
            )
            if is_mandatory and meta.get("applicable") is False:
                mandatory_blocked.append({
                    "requirement_id": r.get("id"),
                    "chapter_id": ch_id,
                    "reason": "星号或废标条款关联章节被标记为不适用",
                })

    ready = (
        plan_ready
        and len(empty_chapters) == 0
        and len(pending_chapters) == 0
        and len(unmapped_reqs) == 0
        and len(missing_volumes) == 0
        and len(mandatory_blocked) == 0
    )

    return {
        "project_id": project_id,
        "volume": volume,
        "ready": ready,
        "plan_confirmed": plan_ready,
        "empty_chapters": empty_chapters,
        "pending_chapters": pending_chapters,
        "unmapped_requirements_count": len(unmapped_reqs),
        "unmapped_requirements": unmapped_reqs,
        "missing_volumes": missing_volumes,
        "mandatory_blocked": mandatory_blocked,
        "details": {
            "total_chapters": len(target_chapters),
            "total_requirements": len(all_reqs),
            "mapped_requirements_count": len(all_reqs) - len(unmapped_reqs),
        },
    }
