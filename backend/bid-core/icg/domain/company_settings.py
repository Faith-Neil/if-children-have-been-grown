# 为什么有这个文件：落实 PRD v1.8 §5.10.2、§5.11.9、§6.9 与字典 v1.9 §4.10 企业设置与安全策略领域服务。
# 它解决什么问题：
# 1. 提供企业级安全策略（密码最少位数、字符分类数、连续失败锁定等）与编辑台参数持久化；
# 2. 贯彻“企业设置只能调严不能调宽”安全基线门禁（SETTING_VALUE_OUT_OF_BOUNDS）；
# 3. 保障多租户数据强隔离（非平台超级管理员跨公司访问严格 404 NOT_FOUND 拦截）；
# 4. 实施精细化 RBAC 角色门禁（仅 platform_admin 与 company_admin 拥有配置写权限，非管理员拦截 403 FORBIDDEN）。

from __future__ import annotations

import copy
import time
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from .domain import DomainError, Principal
from .auth_service import is_super_admin
from .project_access import ROLE_NORMALIZATION_MAP, ROLE_COMPANY_ADMIN, ROLE_PLATFORM_ADMIN


# 平台基线与不可调宽门禁常量 (PRD v1.8 §5.10.2 / §5.11.9 / §6.9 及数据字典 v1.9 §4.10 / §4.17)
PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND = 8
PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND = 32
PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND = 3
PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND = 4
PLATFORM_LOGIN_MAX_FAILURES_UPPER_BOUND = 5
PLATFORM_LOGIN_MAX_FAILURES_LOWER_BOUND = 1
PLATFORM_LOCK_TIMEOUT_UPPER_BOUND = 60
PLATFORM_LOCK_TIMEOUT_LOWER_BOUND = 6  # 须大于释放前提示阈值 5 分钟
PLATFORM_HEARTBEAT_LOWER_BOUND = 15
PLATFORM_HEARTBEAT_UPPER_BOUND = 120
PLATFORM_AUTOSAVE_LOWER_BOUND = 5
PLATFORM_AUTOSAVE_UPPER_BOUND = 60
PLATFORM_LOOP_MAX_ROUNDS_UPPER_BOUND = 5
PLATFORM_LOOP_MAX_ROUNDS_LOWER_BOUND = 1
PLATFORM_SUGGESTION_COUNT_LOWER_BOUND = 3
PLATFORM_SUGGESTION_COUNT_UPPER_BOUND = 5
PLATFORM_SESSION_TIMEOUT_LOWER_BOUND = 30
PLATFORM_SESSION_TIMEOUT_UPPER_BOUND = 480


class CompanySettingsModel(BaseModel):
    company_id: str = Field(description="企业租户唯一标识")
    company_name: str = Field(default="", description="企业名称")
    # 账号安全与密码策略 (PRD §5.10.2 / Q28)
    password_min_length: int = Field(default=8, description="密码最少位数（默认8，只能调严 >= 8）")
    password_min_char_classes: int = Field(default=3, description="至少包含的字符类别数（默认3类，只能调严 3～4）")
    max_login_attempts: int = Field(default=5, description="连续登录失败锁定次数（默认5，只能调严 <= 5）")
    session_timeout_minutes: int = Field(default=120, description="会话超时时长（分钟，范围 30～480）")
    # 编辑锁与自动保存参数 (PRD §5.11.9 / §6.9)
    edit_lock_timeout_minutes: int = Field(default=30, description="编辑锁超时时间（分钟，上限 60，只能调严 <= 60）")
    edit_lock_heartbeat_seconds: int = Field(default=60, description="编辑锁心跳间隔（秒，范围 15～120）")
    editor_autosave_seconds: int = Field(default=10, description="编辑草稿自动保存间隔（秒，范围 5～60）")
    # 生成循环与助手参数 (PRD §5.7.4 / §6.9)
    loop_max_rounds: int = Field(default=3, description="章节生成最大循环轮数（默认3，上限 5，只能调严 <= 5）")
    assistant_suggestion_count: int = Field(default=3, description="修改样例条数（范围 3～5）")
    assistant_enabled: bool = Field(default=True, description="是否启用对话助手")
    assistant_kb_default: bool = Field(default=True, description="新会话中知识库开关默认值")
    assistant_allow_kb_off: bool = Field(default=True, description="是否允许用户关闭知识库")
    model_review_enabled: bool = Field(default=True, description="是否启用章节模型评审")
    # 查重与合规 (PRD §5.8.3 / §5.10.4)
    dup_min_chars: int = Field(default=8, description="查重连续相同字数阈值")
    dup_history_months: int = Field(default=24, description="查重历史标书比对年限（月）")
    # 招标解析 (PRD §5.2.2 规则 2：低于阈值的条目高亮提示人工核对)
    parse_confidence_threshold: float = Field(default=0.8, description="解析置信度高亮阈值（0.5～0.99，示例 0.8）")
    # 审计与扩展
    updated_at: str | None = Field(default=None, description="最后更新时间（ISO 8601）")
    updated_by: str | None = Field(default=None, description="最后更新人账号ID")
    custom_settings: dict[str, Any] = Field(default_factory=dict, description="企业扩展键值配置")


class UpdateCompanySettingsRequest(BaseModel):
    company_name: str | None = Field(default=None, description="企业名称")
    password_min_length: int | None = Field(default=None, description="密码最少位数（只能调严 >= 8，上限 32）")
    password_min_char_classes: int | None = Field(default=None, description="至少包含的字符类别数（只能调严 3～4）")
    max_login_attempts: int | None = Field(default=None, description="连续登录失败锁定次数（只能调严 <= 5，下限 1）")
    session_timeout_minutes: int | None = Field(default=None, description="会话超时时长（分钟，范围 30～480）")
    edit_lock_timeout_minutes: int | None = Field(default=None, description="编辑锁超时时间（分钟，只能调严 <= 60，下限 6）")
    edit_lock_heartbeat_seconds: int | None = Field(default=None, description="编辑锁心跳间隔（秒，范围 15～120）")
    editor_autosave_seconds: int | None = Field(default=None, description="自动保存间隔（秒，范围 5～60）")
    loop_max_rounds: int | None = Field(default=None, description="章节生成最大循环轮数（只能调严 <= 5，下限 1）")
    assistant_suggestion_count: int | None = Field(default=None, description="修改样例条数（范围 3～5）")
    assistant_enabled: bool | None = Field(default=None, description="是否启用对话助手")
    assistant_kb_default: bool | None = Field(default=None, description="新会话中知识库开关默认值")
    assistant_allow_kb_off: bool | None = Field(default=None, description="是否允许用户关闭知识库")
    model_review_enabled: bool | None = Field(default=None, description="是否启用章节模型评审")
    dup_min_chars: int | None = Field(default=None, description="查重连续相同字数阈值")
    dup_history_months: int | None = Field(default=None, description="查重历史标书比对年限（月）")
    parse_confidence_threshold: float | None = Field(default=None, description="解析置信度高亮阈值（0.5～0.99）")
    custom_settings: dict[str, Any] | None = Field(default=None, description="企业扩展键值配置")


def parse_confidence_threshold(state, company_id: str) -> float:
    stored = (getattr(state, "service_stores", {}).get("company_settings") or {}).get(company_id) or {}
    value = stored.get("parse_confidence_threshold")
    return float(value) if isinstance(value, (int, float)) else 0.8


def company_display_name(state, company_id: str) -> str:
    """投标主体名称：公司设置里的公司名称；未设置时与 _get_or_create 的默认值一致。"""
    stored = (getattr(state, "service_stores", {}).get("company_settings") or {}).get(company_id) or {}
    return stored.get("company_name") or ("Alpha 科技" if company_id == "alpha" else "Beta 建设" if company_id == "beta" else f"{company_id} 企业")


class CompanySettingsService:
    """企业设置与安全策略领域服务。"""

    def __init__(self) -> None:
        self._local: dict[str, CompanySettingsModel] = {}
        # 绑定仓储后企业设置保存在 DemoState.service_stores["company_settings"]，随其他状态持久化（ISSUE-041）。
        self.repository = None

    @property
    def _store(self) -> dict[str, CompanySettingsModel]:
        if self.repository is None:
            return self._local
        stored = self.repository.read().service_stores.get("company_settings") or {}
        return {cid: CompanySettingsModel(**data) for cid, data in stored.items()}

    def _save(self, company_id: str, model: CompanySettingsModel) -> None:
        if self.repository is None:
            self._local[company_id] = model
            return
        data = model.model_dump()

        def write(state):
            state.service_stores.setdefault("company_settings", {})[company_id] = data

        self.repository.transaction(write)

    def _get_or_create(self, company_id: str) -> CompanySettingsModel:
        current = self._store.get(company_id)
        if current is None:
            name = "Alpha 科技" if company_id == "alpha" else ("Beta 建设" if company_id == "beta" else f"{company_id} 企业")
            current = CompanySettingsModel(company_id=company_id, company_name=name)
            if self.repository is None:
                self._local[company_id] = current
        return copy.deepcopy(current)

    def get_settings(self, company_id: str, principal: Principal) -> CompanySettingsModel:
        """获取指定企业的设置与安全策略配置。"""
        user = principal.user
        if not is_super_admin(user):
            if user.company_id != company_id:
                raise DomainError(404, "NOT_FOUND", f"未找到指定企业 {company_id} 或当前账号无权访问。")
        return self._get_or_create(company_id)

    def update_settings(self, company_id: str, request: UpdateCompanySettingsRequest, principal: Principal) -> CompanySettingsModel:
        """更新指定企业的设置与安全策略，严格核对“只能调严不能调宽”安全红线与 RBAC 权限。"""
        user = principal.user
        # 1. 租户隔离校验
        if not is_super_admin(user):
            if user.company_id != company_id:
                raise DomainError(404, "NOT_FOUND", f"未找到指定企业 {company_id} 或当前账号无权访问。")
            # 2. RBAC 权限核验：仅企业管理员可修改
            normalized_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if normalized_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台超级管理员可修改企业设置与安全策略。")

        # 3. 获取现有设置
        current = self._get_or_create(company_id)

        # 4. “只能调严不能调宽”安全基线规则校验 (SETTING_VALUE_OUT_OF_BOUNDS)
        if request.password_min_length is not None:
            if request.password_min_length < PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"密码最少位数只能调严，不能低于平台下限 {PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND} 位。",
                    details={"field": "password_min_length", "min": PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND, "value": request.password_min_length},
                )
            if request.password_min_length > PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"密码最少位数不能超过平台上限 {PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND} 位。",
                    details={"field": "password_min_length", "max": PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND, "value": request.password_min_length},
                )

        if request.password_min_char_classes is not None:
            if request.password_min_char_classes < PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"密码字符类别数只能调严，不能低于平台下限 {PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND} 类。",
                    details={"field": "password_min_char_classes", "min": PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND, "value": request.password_min_char_classes},
                )
            if request.password_min_char_classes > PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"密码字符类别数不能超过平台上限 {PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND} 类。",
                    details={"field": "password_min_char_classes", "max": PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND, "value": request.password_min_char_classes},
                )

        if request.max_login_attempts is not None:
            if request.max_login_attempts > PLATFORM_LOGIN_MAX_FAILURES_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"连续登录失败锁定次数只能调严，不能超过平台上限 {PLATFORM_LOGIN_MAX_FAILURES_UPPER_BOUND} 次。",
                    details={"field": "max_login_attempts", "max": PLATFORM_LOGIN_MAX_FAILURES_UPPER_BOUND, "value": request.max_login_attempts},
                )
            if request.max_login_attempts < PLATFORM_LOGIN_MAX_FAILURES_LOWER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"连续登录失败锁定次数不能低于 {PLATFORM_LOGIN_MAX_FAILURES_LOWER_BOUND} 次。",
                    details={"field": "max_login_attempts", "min": PLATFORM_LOGIN_MAX_FAILURES_LOWER_BOUND, "value": request.max_login_attempts},
                )

        if request.edit_lock_timeout_minutes is not None:
            if request.edit_lock_timeout_minutes > PLATFORM_LOCK_TIMEOUT_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"编辑锁超时时长只能调严，不能超过平台上限 {PLATFORM_LOCK_TIMEOUT_UPPER_BOUND} 分钟。",
                    details={"field": "edit_lock_timeout_minutes", "max": PLATFORM_LOCK_TIMEOUT_UPPER_BOUND, "value": request.edit_lock_timeout_minutes},
                )
            if request.edit_lock_timeout_minutes < PLATFORM_LOCK_TIMEOUT_LOWER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"编辑锁超时时长必须大于释放提醒阈值 5 分钟（最少 {PLATFORM_LOCK_TIMEOUT_LOWER_BOUND} 分钟）。",
                    details={"field": "edit_lock_timeout_minutes", "min": PLATFORM_LOCK_TIMEOUT_LOWER_BOUND, "value": request.edit_lock_timeout_minutes},
                )

        if request.edit_lock_heartbeat_seconds is not None:
            if request.edit_lock_heartbeat_seconds < PLATFORM_HEARTBEAT_LOWER_BOUND or request.edit_lock_heartbeat_seconds > PLATFORM_HEARTBEAT_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"编辑锁心跳间隔必须在 {PLATFORM_HEARTBEAT_LOWER_BOUND}～{PLATFORM_HEARTBEAT_UPPER_BOUND} 秒之间。",
                    details={"field": "edit_lock_heartbeat_seconds", "min": PLATFORM_HEARTBEAT_LOWER_BOUND, "max": PLATFORM_HEARTBEAT_UPPER_BOUND, "value": request.edit_lock_heartbeat_seconds},
                )

        if request.editor_autosave_seconds is not None:
            if request.editor_autosave_seconds < PLATFORM_AUTOSAVE_LOWER_BOUND or request.editor_autosave_seconds > PLATFORM_AUTOSAVE_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"自动保存间隔必须在 {PLATFORM_AUTOSAVE_LOWER_BOUND}～{PLATFORM_AUTOSAVE_UPPER_BOUND} 秒之间。",
                    details={"field": "editor_autosave_seconds", "min": PLATFORM_AUTOSAVE_LOWER_BOUND, "max": PLATFORM_AUTOSAVE_UPPER_BOUND, "value": request.editor_autosave_seconds},
                )

        # 关联约束校验 (PRD §6.9):
        # ① editor_autosave_seconds <= edit_lock_heartbeat_seconds
        # ② edit_lock_heartbeat_seconds * 10 <= edit_lock_timeout_minutes * 60
        eff_autosave = request.editor_autosave_seconds if request.editor_autosave_seconds is not None else current.editor_autosave_seconds
        eff_heartbeat = request.edit_lock_heartbeat_seconds if request.edit_lock_heartbeat_seconds is not None else current.edit_lock_heartbeat_seconds
        eff_timeout = request.edit_lock_timeout_minutes if request.edit_lock_timeout_minutes is not None else current.edit_lock_timeout_minutes

        if eff_autosave > eff_heartbeat:
            raise DomainError(
                422,
                "SETTING_VALUE_OUT_OF_BOUNDS",
                f"自动保存间隔（{eff_autosave}秒）不能大于编辑锁心跳间隔（{eff_heartbeat}秒）。",
                details={"editor_autosave_seconds": eff_autosave, "edit_lock_heartbeat_seconds": eff_heartbeat},
            )

        if eff_heartbeat * 10 > eff_timeout * 60:
            raise DomainError(
                422,
                "SETTING_VALUE_OUT_OF_BOUNDS",
                f"编辑锁心跳间隔的 10 倍（{eff_heartbeat * 10}秒）不能超过锁超时总时长（{eff_timeout * 60}秒）。",
                details={"edit_lock_heartbeat_seconds": eff_heartbeat, "edit_lock_timeout_minutes": eff_timeout},
            )

        if request.loop_max_rounds is not None:
            if request.loop_max_rounds > PLATFORM_LOOP_MAX_ROUNDS_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"章节生成最大循环轮数只能调严，不能超过平台上限 {PLATFORM_LOOP_MAX_ROUNDS_UPPER_BOUND} 轮。",
                    details={"field": "loop_max_rounds", "max": PLATFORM_LOOP_MAX_ROUNDS_UPPER_BOUND, "value": request.loop_max_rounds},
                )
            if request.loop_max_rounds < PLATFORM_LOOP_MAX_ROUNDS_LOWER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"章节生成最大循环轮数不能低于 {PLATFORM_LOOP_MAX_ROUNDS_LOWER_BOUND} 轮。",
                    details={"field": "loop_max_rounds", "min": PLATFORM_LOOP_MAX_ROUNDS_LOWER_BOUND, "value": request.loop_max_rounds},
                )

        if request.assistant_suggestion_count is not None:
            if request.assistant_suggestion_count < PLATFORM_SUGGESTION_COUNT_LOWER_BOUND or request.assistant_suggestion_count > PLATFORM_SUGGESTION_COUNT_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"修改样例条数必须在 {PLATFORM_SUGGESTION_COUNT_LOWER_BOUND}～{PLATFORM_SUGGESTION_COUNT_UPPER_BOUND} 之间。",
                    details={"field": "assistant_suggestion_count", "min": PLATFORM_SUGGESTION_COUNT_LOWER_BOUND, "max": PLATFORM_SUGGESTION_COUNT_UPPER_BOUND, "value": request.assistant_suggestion_count},
                )

        if request.session_timeout_minutes is not None:
            if request.session_timeout_minutes < PLATFORM_SESSION_TIMEOUT_LOWER_BOUND or request.session_timeout_minutes > PLATFORM_SESSION_TIMEOUT_UPPER_BOUND:
                raise DomainError(
                    422,
                    "SETTING_VALUE_OUT_OF_BOUNDS",
                    f"会话超时时长必须在 {PLATFORM_SESSION_TIMEOUT_LOWER_BOUND}～{PLATFORM_SESSION_TIMEOUT_UPPER_BOUND} 分钟之间。",
                    details={"field": "session_timeout_minutes", "min": PLATFORM_SESSION_TIMEOUT_LOWER_BOUND, "max": PLATFORM_SESSION_TIMEOUT_UPPER_BOUND, "value": request.session_timeout_minutes},
                )

        if request.parse_confidence_threshold is not None and not 0.5 <= request.parse_confidence_threshold <= 0.99:
            raise DomainError(
                422,
                "SETTING_VALUE_OUT_OF_BOUNDS",
                "解析置信度阈值必须在 0.5～0.99 之间。",
                details={"field": "parse_confidence_threshold", "min": 0.5, "max": 0.99, "value": request.parse_confidence_threshold},
            )

        # 5. 合并更新字段
        data = current.model_dump()
        update_data = request.model_dump(exclude_unset=True)
        if "custom_settings" in update_data and update_data["custom_settings"] is not None:
            custom = data.get("custom_settings", {})
            custom.update(update_data["custom_settings"])
            update_data["custom_settings"] = custom

        data.update(update_data)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data["updated_by"] = user.id

        updated_model = CompanySettingsModel(**data)
        self._save(company_id, updated_model)
        return copy.deepcopy(updated_model)
