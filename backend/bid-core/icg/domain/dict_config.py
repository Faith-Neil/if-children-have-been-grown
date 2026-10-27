# 为什么有这个文件：落实 APP-M2-T024 (A-03 字典配置页) 与 PRD v1.8 §5.10.3、§6.9 字典管理领域逻辑。
# 它解决什么问题：
# 1. 集中管理业务状态码表、需求分类、信源层级、SLA 指标等标准数据字典；
# 2. 贯彻“已使用代码只能停用，严禁物理硬删除”安全红线（DICT_ITEM_IN_USE）；
# 3. 提供新增自定义字典项的代码重复冲突检查（DICT_CODE_DUPLICATED）；
# 4. 实现严格的角色权限门禁（仅 platform_admin 与 company_admin 可执行写操作，其他角色拦截 403 FORBIDDEN）；
# 5. 保障多租户数据隔离（公司自定义字典项绑定 company_id，系统内置字典项全局共享）。

from __future__ import annotations

import copy
from typing import Any
from pydantic import BaseModel, Field

from .domain import DomainError, Principal
from .project_access import ROLE_NORMALIZATION_MAP


class DictTypeItem(BaseModel):
    type_code: str = Field(description="字典类型代码")
    type_name: str = Field(description="字典类型中文名称")
    scope: str = Field(default="system", description="作用域：system, business, custom")
    description: str = Field(default="", description="字典类型业务描述")
    total_items: int = Field(default=0, description="代码项总数")
    active_items: int = Field(default=0, description="有效启用项总数")


class DictTypeListResponse(BaseModel):
    total: int = Field(description="字典类型总数")
    items: list[DictTypeItem] = Field(description="字典类型列表")


class DictItemModel(BaseModel):
    id: str = Field(description="字典项全局唯一标识")
    type_code: str = Field(description="所属字典类型代码")
    item_code: str = Field(description="字典代码")
    label: str = Field(description="字典显示名称")
    description: str = Field(default="", description="业务释义或描述")
    sort_order: int = Field(default=100, description="显示排序权重")
    is_disabled: bool = Field(default=False, description="是否停用")
    in_use: bool = Field(default=False, description="是否已被业务使用")
    is_builtin: bool = Field(default=True, description="是否系统内置")
    company_id: str | None = Field(default=None, description="公司租户ID")
    metadata: dict[str, Any] | None = Field(default=None, description="扩展元数据")


class DictItemListResponse(BaseModel):
    type_code: str = Field(description="所属字典类型代码")
    type_name: str = Field(description="字典类型中文名称")
    total: int = Field(description="字典项总数")
    items: list[DictItemModel] = Field(description="字典项列表")


class CreateDictItemRequest(BaseModel):
    type_code: str = Field(description="所属字典类型代码")
    item_code: str = Field(description="字典代码")
    label: str = Field(description="字典显示名称")
    description: str = Field(default="", description="业务释义或描述")
    sort_order: int = Field(default=100, description="显示排序权重")
    metadata: dict[str, Any] | None = Field(default=None, description="扩展元数据")


class UpdateDictItemRequest(BaseModel):
    label: str | None = Field(default=None, description="字典显示名称")
    description: str | None = Field(default=None, description="业务释义或描述")
    sort_order: int | None = Field(default=None, description="显示排序权重")
    is_disabled: bool | None = Field(default=None, description="是否停用")
    metadata: dict[str, Any] | None = Field(default=None, description="扩展元数据")


class DeleteDictItemResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(description="提示消息")
    type_code: str = Field(description="字典类型代码")
    item_code: str = Field(description="已删除字典代码")


# 内置字典类型元数据定义
BUILTIN_DICT_TYPES: list[dict[str, Any]] = [
    {"type_code": "project_status", "type_name": "项目状态", "scope": "system", "description": "标书编制全流程项目生命周期状态"},
    {"type_code": "chapter_status", "type_name": "章节状态", "scope": "system", "description": "标书章节编排、撰写与定稿状态"},
    {"type_code": "job_status", "type_name": "长任务状态", "scope": "system", "description": "异步生成与检查后台任务执行状态"},
    {"type_code": "check_status", "type_name": "合规检查状态", "scope": "system", "description": "合规排查通过/警告/废标阻断状态"},
    {"type_code": "export_status", "type_name": "导出交付状态", "scope": "system", "description": "双卷 Word 导出交付生命周期状态"},
    {"type_code": "lock_status", "type_name": "编辑租约状态", "scope": "system", "description": "协同编辑分布式租约锁状态"},
    {"type_code": "requirement_category", "type_name": "需求分类", "scope": "business", "description": "招标文件解析需求条目分类"},
    {"type_code": "source_tier", "type_name": "信源层级", "scope": "business", "description": "知识库与方案证据事实信源等级"},
    {"type_code": "sla_group", "type_name": "SLA指标分组", "scope": "business", "description": "服务承诺与交付指标归类分组"},
    {"type_code": "field_project", "type_name": "项目字段元数据", "scope": "system", "description": "项目基础字段属性元数据"},
    {"type_code": "field_tender", "type_name": "招标文件元数据", "scope": "system", "description": "招标文件解析字段元数据"},
    {"type_code": "field_evidence", "type_name": "企业资质元数据", "scope": "system", "description": "企业知识库资质字段元数据"},
]

# 初始内置字典项列表
INITIAL_BUILTIN_ITEMS: list[dict[str, Any]] = [
    # 1. project_status
    {"type_code": "project_status", "item_code": "draft", "label": "草稿中", "description": "项目新建初始化", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "parsing", "label": "解析中", "description": "招标文件正在后台深度解析", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "parsed", "label": "解析待确认", "description": "解析完成，等待人工核验关键字段", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "confirmed", "label": "已确认", "description": "解析字段已由项目负责人确认无误", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "writing", "label": "编写中", "description": "多成员分工协同编写正文中", "sort_order": 50, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "checking", "label": "检查中", "description": "正文合规与废标红线核查进行中", "sort_order": 60, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "submitted", "label": "已递交", "description": "标书已完成导出与封标递交", "sort_order": 70, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "project_status", "item_code": "archived", "label": "已归档", "description": "项目已结项归档", "sort_order": 80, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 2. chapter_status
    {"type_code": "chapter_status", "item_code": "draft", "label": "待编写", "description": "章节已创建，正文尚为空白", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "chapter_status", "item_code": "generating", "label": "AI生成中", "description": "大模型方案正在后台异步生成", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "chapter_status", "item_code": "reviewing", "label": "评审中", "description": "编写人提交章节，等待复核", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "chapter_status", "item_code": "approved", "label": "已定稿", "description": "章节内容经负责人确认定稿锁定", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "chapter_status", "item_code": "blocked", "label": "阻断中", "description": "章节命中废标红线，禁止提交定稿", "sort_order": 50, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 3. job_status
    {"type_code": "job_status", "item_code": "queued", "label": "排队中", "description": "任务进入并发队列等待调度", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "job_status", "item_code": "running", "label": "进行中", "description": "后台 Worker 正在执行任务", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "job_status", "item_code": "completed", "label": "已完成", "description": "任务顺利结束并产出结果", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "job_status", "item_code": "failed", "label": "异常失败", "description": "执行遇异常中断，保留错误追踪日志", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "job_status", "item_code": "cancelled", "label": "已取消", "description": "任务已被主动取消终止", "sort_order": 50, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 4. check_status
    {"type_code": "check_status", "item_code": "passed", "label": "合规通过", "description": "规则检查全部合规", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "check_status", "item_code": "warning", "label": "合规提醒", "description": "存在轻微偏离或次要风险提醒", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "check_status", "item_code": "blocker", "label": "废标阻断", "description": "命中废标红线，强力阻断导出交付", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False, "metadata": {"is_blocker": True, "is_starred": True}},

    # 5. export_status
    {"type_code": "export_status", "item_code": "idle", "label": "待导出", "description": "尚未触发正式导出请求", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "export_status", "item_code": "processing", "label": "排版中", "description": "正在生成双卷 Word 与防伪指纹", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "export_status", "item_code": "completed", "label": "已生成", "description": "导出成功，文档包就绪可下载", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "export_status", "item_code": "failed", "label": "导出失败", "description": "导出中断，请根据错误提示修复重试", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 6. lock_status
    {"type_code": "lock_status", "item_code": "unlocked", "label": "空闲可编辑", "description": "章节无人占用，可随时进入编辑", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "lock_status", "item_code": "locked_self", "label": "本人编辑中", "description": "当前租约处于活跃续约状态", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "lock_status", "item_code": "locked_other", "label": "他人占用", "description": "其他团队成员正在协同编写", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "lock_status", "item_code": "expired", "label": "租约过期", "description": "心跳超时，锁释放等待被接管", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 7. requirement_category
    {"type_code": "requirement_category", "item_code": "qualification", "label": "资质要求", "description": "必须具备的企业与人员准入门槛", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "requirement_category", "item_code": "technical", "label": "技术要求", "description": "技术规格、架构与实现指标", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "requirement_category", "item_code": "commercial", "label": "商务要求", "description": "付款条件、交付周期与履约保证", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "requirement_category", "item_code": "scoring", "label": "评分标准", "description": "评标专家评分细则与分值分布", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "requirement_category", "item_code": "other", "label": "其他条款", "description": "其他常规声明或通用约定", "sort_order": 50, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 8. source_tier
    {"type_code": "source_tier", "item_code": "t1_authoritative", "label": "T1 权威信源", "description": "企业盖章资质原件、中标通知书等核心事实", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "source_tier", "item_code": "t2_department", "label": "T2 部门级信源", "description": "部门技术白皮书、历史成熟方案库", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "source_tier", "item_code": "t3_external", "label": "T3 外部/参考资料", "description": "行业公开资料、同行竞品对比（仅供参考）", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 9. sla_group
    {"type_code": "sla_group", "item_code": "response_time", "label": "响应时限", "description": "故障响应、上门支持与技术支援时效", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "sla_group", "item_code": "availability", "label": "可用性保障", "description": "系统 99.9% 在线率、容灾保障承诺", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "sla_group", "item_code": "quality_metric", "label": "质量指标", "description": "工程交付质量、缺陷率指标", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "sla_group", "item_code": "penalty_rule", "label": "罚则标准", "description": "违约赔偿与考核扣款标准", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 10. field_project
    {"type_code": "field_project", "item_code": "project_name", "label": "项目全称", "description": "招标项目正式法定全称", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "field_project", "item_code": "tender_no", "label": "招标编号", "description": "招标文件载明的招标或采购编号", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "field_project", "item_code": "budget_amount_cents", "label": "预算金额(分)", "description": "控制价上限金额", "sort_order": 30, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "field_project", "item_code": "security_level", "label": "项目密级", "description": "涉密项目强制使用内网本地模型", "sort_order": 40, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 11. field_tender
    {"type_code": "field_tender", "item_code": "tender_type", "label": "招标方式", "description": "公开招标/邀请招标/竞争性谈判", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
    {"type_code": "field_tender", "item_code": "deadline_at", "label": "投标截止时限", "description": "开标与投标书最终递交时限", "sort_order": 20, "is_builtin": True, "in_use": True, "is_disabled": False},

    # 12. field_evidence
    {"type_code": "field_evidence", "item_code": "evidence_type", "label": "证据资质类型", "description": "营业执照、ISO体系认证等资质证据类型", "sort_order": 10, "is_builtin": True, "in_use": True, "is_disabled": False},
]


class DictConfigService:
    def __init__(self) -> None:
        # 内存存储字典类型和字典项，支持租户数据隔离
        self._types: dict[str, dict[str, Any]] = {
            t["type_code"]: copy.deepcopy(t) for t in BUILTIN_DICT_TYPES
        }
        self._items: list[dict[str, Any]] = [
            {
                "id": f"dict_{item['type_code']}_{item['item_code']}",
                **copy.deepcopy(item),
                "company_id": None,
                "metadata": item.get("metadata", {}),
            }
            for item in INITIAL_BUILTIN_ITEMS
        ]

    def _check_admin_write_permission(self, principal: Principal) -> None:
        """角色权限门禁：仅平台管理员与公司管理员具备字典写操作权限，写作者与审计员严格只读"""
        if not principal or not principal.user:
            raise DomainError(401, "UNAUTHENTICATED", "未登录或会话凭据已失效。")
        user_role = getattr(principal.user, "role", "viewer")
        norm_role = ROLE_NORMALIZATION_MAP.get(user_role, user_role)
        if norm_role not in ("platform_admin", "company_admin"):
            raise DomainError(
                403,
                "FORBIDDEN",
                f"当前用户身份为【{user_role}】，仅拥有字典配置调阅权限；新建、修改、启停用与删除操作仅限平台管理员或公司管理员执行。",
            )

    def _get_tenant_company_id(self, principal: Principal) -> str | None:
        if not principal or not principal.user:
            return None
        return getattr(principal.user, "company_id", None)

    def list_dict_types(self, principal: Principal) -> DictTypeListResponse:
        """调阅所有字典类型及当前有效统计"""
        company_id = self._get_tenant_company_id(principal)
        norm_role = "viewer"
        if principal and principal.user:
            norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)

        result: list[DictTypeItem] = []
        for type_code, defn in self._types.items():
            # 统计当前租户可见的字典项
            matching_items = [
                i for i in self._items
                if i["type_code"] == type_code and (
                    i["company_id"] is None or norm_role == "platform_admin" or i["company_id"] == company_id
                )
            ]
            total = len(matching_items)
            active = sum(1 for i in matching_items if not i.get("is_disabled", False))
            result.append(
                DictTypeItem(
                    type_code=defn["type_code"],
                    type_name=defn["type_name"],
                    scope=defn.get("scope", "system"),
                    description=defn.get("description", ""),
                    total_items=total,
                    active_items=active,
                )
            )

        return DictTypeListResponse(total=len(result), items=result)

    def list_dict_items(
        self,
        type_code: str,
        principal: Principal,
        include_disabled: bool = True,
        keyword: str | None = None,
    ) -> DictItemListResponse:
        """获取指定字典类型下的所有代码项列表"""
        if type_code not in self._types:
            raise DomainError(404, "NOT_FOUND", f"未找到指定的字典类型：{type_code}。")

        company_id = self._get_tenant_company_id(principal)
        norm_role = "viewer"
        if principal and principal.user:
            norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)

        type_def = self._types[type_code]
        items_data: list[DictItemModel] = []

        kw = keyword.strip().lower() if keyword else None

        for item in self._items:
            if item["type_code"] != type_code:
                continue
            # 租户隔离校验
            if item["company_id"] is not None and norm_role != "platform_admin" and item["company_id"] != company_id:
                continue
            if not include_disabled and item.get("is_disabled", False):
                continue
            if kw and (kw not in item["item_code"].lower() and kw not in item["label"].lower()):
                continue

            items_data.append(DictItemModel(**item))

        # 按 sort_order 升序排序
        items_data.sort(key=lambda x: x.sort_order)

        return DictItemListResponse(
            type_code=type_code,
            type_name=type_def["type_name"],
            total=len(items_data),
            items=items_data,
        )

    def create_dict_item(self, payload: CreateDictItemRequest, principal: Principal) -> DictItemModel:
        """新增自定义字典代码项（需管理员权限，校验代码重复）"""
        self._check_admin_write_permission(principal)

        if payload.type_code not in self._types:
            raise DomainError(404, "NOT_FOUND", f"未找到指定的字典类型：{payload.type_code}。")

        company_id = self._get_tenant_company_id(principal)
        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)

        # 规则红线校验：同分类下代码不可重复（包括内置或本租户）
        item_code_norm = payload.item_code.strip()
        for existing in self._items:
            if existing["type_code"] == payload.type_code and existing["item_code"] == item_code_norm:
                if existing["company_id"] is None or norm_role == "platform_admin" or existing["company_id"] == company_id:
                    raise DomainError(
                        409,
                        "DICT_CODE_DUPLICATED",
                        f"字典分类【{payload.type_code}】下已存在代码【{item_code_norm}】，禁止重复创建。",
                        details={"type_code": payload.type_code, "item_code": item_code_norm},
                    )

        new_id = f"dict_{payload.type_code}_{item_code_norm}"
        new_item = {
            "id": new_id,
            "type_code": payload.type_code,
            "item_code": item_code_norm,
            "label": payload.label.strip(),
            "description": payload.description or "",
            "sort_order": payload.sort_order,
            "is_disabled": False,
            "in_use": False,
            "is_builtin": False,
            "company_id": company_id if norm_role != "platform_admin" else None,
            "metadata": payload.metadata or {},
        }
        self._items.append(new_item)
        return DictItemModel(**new_item)

    def update_dict_item(
        self,
        type_code: str,
        item_code: str,
        payload: UpdateDictItemRequest,
        principal: Principal,
    ) -> DictItemModel:
        """更新字典项配置（标签、排序、启停用等）"""
        self._check_admin_write_permission(principal)

        company_id = self._get_tenant_company_id(principal)
        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)

        target_idx = -1
        for idx, item in enumerate(self._items):
            if item["type_code"] == type_code and item["item_code"] == item_code:
                if item["company_id"] is None or norm_role == "platform_admin" or item["company_id"] == company_id:
                    target_idx = idx
                    break

        if target_idx == -1:
            raise DomainError(404, "NOT_FOUND", f"未找到字典代码项：{type_code}/{item_code}。")

        target = self._items[target_idx]

        if payload.label is not None:
            target["label"] = payload.label.strip()
        if payload.description is not None:
            target["description"] = payload.description
        if payload.sort_order is not None:
            target["sort_order"] = payload.sort_order
        if payload.is_disabled is not None:
            target["is_disabled"] = payload.is_disabled
        if payload.metadata is not None:
            target["metadata"] = payload.metadata

        return DictItemModel(**target)

    def delete_dict_item(
        self,
        type_code: str,
        item_code: str,
        principal: Principal,
    ) -> DeleteDictItemResponse:
        """删除字典项（核心红线：系统内置与已使用代码严禁硬删除，拦截 409 DICT_ITEM_IN_USE）"""
        self._check_admin_write_permission(principal)

        company_id = self._get_tenant_company_id(principal)
        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)

        target_idx = -1
        for idx, item in enumerate(self._items):
            if item["type_code"] == type_code and item["item_code"] == item_code:
                if item["company_id"] is None or norm_role == "platform_admin" or item["company_id"] == company_id:
                    target_idx = idx
                    break

        if target_idx == -1:
            raise DomainError(404, "NOT_FOUND", f"未找到字典代码项：{type_code}/{item_code}。")

        target = self._items[target_idx]

        # 核心红线：“已使用的字典代码/状态只能停用，严禁物理硬删除”
        if target.get("is_builtin", False):
            raise DomainError(
                409,
                "DICT_ITEM_IN_USE",
                f"字典代码【{item_code}】属于系统内置核心代码，严禁物理硬删除；如需禁用请执行停用操作（is_disabled=true）。",
                details={"type_code": type_code, "item_code": item_code, "is_builtin": True},
            )

        if target.get("in_use", False):
            raise DomainError(
                409,
                "DICT_ITEM_IN_USE",
                f"字典代码【{item_code}】已在生产业务（项目、章节或合规检查）中引用，严禁物理硬删除；如需停用请执行停用操作（is_disabled=true）。",
                details={"type_code": type_code, "item_code": item_code, "in_use": True},
            )

        # 仅未被引用的自定义代码允许删除
        self._items.pop(target_idx)
        return DeleteDictItemResponse(
            success=True,
            message=f"自定义字典代码【{item_code}】已成功物理删除。",
            type_code=type_code,
            item_code=item_code,
        )
