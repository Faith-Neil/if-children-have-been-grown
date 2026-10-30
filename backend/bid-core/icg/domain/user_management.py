# 为什么有这个文件：落实 PRD v1.8 §5.10.1、§5.10.2 与 APP-M2-T027 用户管理与账号停用资产交接领域服务。
# 它解决什么问题：
# 1. 规范用户列表与安全增删改查契约，确保密码加盐哈希严格脱敏不外泄；
# 2. 贯彻 Q28 定案密码强度校验（最少 8 位且至少包含大写、小写、数字、符号中的三类，不足拦截 422 PASSWORD_WEAK）；
# 3. 严格落实核心业务红线：“停用用户前须把其负责的资料和项目转交他人”（未转交拦截 409 USER_TRANSFER_REQUIRED）；
# 4. 支持在停用请求中附带 successor_user_id 实现名下项目负责人与编写人资产原子平滑交接；
# 5. 坚守多租户强隔离（跨租户访问严格返回 404 NOT_FOUND）与 RBAC 权限隔离（非管理员写操作拦截 403 FORBIDDEN）。

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any
from pydantic import BaseModel, Field

from .domain import Account, DemoService, DomainError, Principal, iso_time
from . import security_audit
from .auth_service import hash_password, is_super_admin
from .project_access import ROLE_COMPANY_ADMIN, ROLE_NORMALIZATION_MAP, VOLUMES


class UserModel(BaseModel):
    """用户信息安全对外视图（严格脱敏密码哈希与盐）。"""
    id: str = Field(description="用户唯一账号ID")
    name: str = Field(description="真实姓名")
    display_name: str = Field(description="展示昵称")
    company_id: str = Field(description="所属企业租户ID")
    role: str = Field(description="系统角色代码")
    status: str = Field(default="active", description="账号状态：active / disabled")
    is_locked: bool = Field(default=False, description="是否被锁定")
    failed_login_attempts: int = Field(default=0, description="连续登录失败次数")
    must_change_password: bool = Field(default=False, description="新建或被重置后尚未本人改密")
    created_at: str | None = Field(default=None, description="创建时间（ISO 8601）")
    updated_at: str | None = Field(default=None, description="最后更新时间（ISO 8601）")


class UserListResponse(BaseModel):
    total: int = Field(description="满足条件的用户总数")
    items: list[UserModel] = Field(description="用户列表")


class CreateUserRequest(BaseModel):
    username: str = Field(description="登录账号 / 用户ID")
    name: str = Field(description="用户真实姓名")
    company_id: str = Field(description="所属企业租户ID")
    role: str = Field(description="分配的标准系统角色")
    password: str = Field(description="初始登录密码")
    display_name: str | None = Field(default=None, description="展示昵称")


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, description="真实姓名")
    display_name: str | None = Field(default=None, description="展示昵称")
    role: str | None = Field(default=None, description="分配的标准系统角色")
    status: str | None = Field(default=None, description="账号状态：active / disabled")
    successor_user_id: str | None = Field(default=None, description="停用时资产交接接收人ID")
    reason: str | None = Field(default=None, description="变更或交接原因")


class UpdateUserStatusRequest(BaseModel):
    status: str = Field(description="账号状态：active / disabled")
    successor_user_id: str | None = Field(default=None, description="停用时资产交接接收人ID")
    reason: str | None = Field(default=None, description="状态变更或交接原因")


class TransferUserAssetsRequest(BaseModel):
    successor_user_id: str = Field(description="资产交接接收人用户ID")


class TransferUserAssetsResponse(BaseModel):
    success: bool = Field(default=True, description="是否交接成功")
    from_user_id: str = Field(description="原资产负责人ID")
    successor_user_id: str = Field(description="新资产接收人ID")
    transferred_projects: list[dict[str, Any]] = Field(description="已平滑交接的在投项目列表")
    message: str = Field(description="交接执行结果说明")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=1, description="新登录密码")


class ResetPasswordResponse(BaseModel):
    success: bool = Field(default=True, description="是否重置成功")
    user_id: str = Field(description="被重置用户ID")
    message: str = Field(description="重置操作结果说明")
    updated_at: str = Field(description="更新时间")


class UnlockUserResponse(BaseModel):
    success: bool = Field(default=True, description="是否解锁成功")
    user_id: str = Field(description="被解锁用户ID")
    is_locked: bool = Field(default=False, description="当前锁定状态")
    failed_login_attempts: int = Field(default=0, description="重置后的失败尝试次数")
    message: str = Field(description="操作结果说明")


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., description="分配的新系统角色")


def account_to_user_model(acc: Account) -> UserModel:
    """将内部 Account 实体转化为严格脱敏的外部 UserModel。"""
    c_time = iso_time(acc.created_at) if acc.created_at else None
    u_time = iso_time(acc.updated_at) if acc.updated_at else None
    return UserModel(
        id=acc.id,
        name=acc.name,
        display_name=acc.display_name or acc.name,
        company_id=acc.company_id,
        role=acc.role,
        status=getattr(acc, "status", "active") or "active",
        is_locked=getattr(acc, "is_locked", False),
        failed_login_attempts=getattr(acc, "failed_login_attempts", 0),
        must_change_password=bool(getattr(acc, "must_change_password", False)),
        created_at=c_time,
        updated_at=u_time,
    )


class UserManagementService:
    """用户管理与资产交接领域服务。"""

    def __init__(self, service: DemoService) -> None:
        self.service = service

    @property
    def repository(self):
        return self.service.repository

    def list_users(
        self,
        principal: Principal,
        company_id: str | None = None,
        role: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> UserListResponse:
        """调阅用户列表，超管可查全平台或指定公司，企管与其他角色严格隔离在所属企业。"""
        user = principal.user
        target_company = company_id

        if not is_super_admin(user):
            if target_company and target_company != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"未找到指定企业 {target_company} 或当前账号无权访问。")
            target_company = user.company_id

        accounts = list(self.repository.read().accounts.values())
        filtered: list[UserModel] = []

        for acc in accounts:
            if target_company and acc.company_id != target_company:
                continue
            if role and acc.role != role:
                continue
            acc_status = getattr(acc, "status", "active") or "active"
            if status and acc_status != status:
                continue
            if keyword:
                kw = keyword.lower()
                if kw not in acc.id.lower() and kw not in acc.name.lower() and kw not in acc.display_name.lower():
                    continue
            filtered.append(account_to_user_model(acc))

        filtered.sort(key=lambda u: u.id)
        return UserListResponse(total=len(filtered), items=filtered)

    def get_user(self, user_id: str, principal: Principal) -> UserModel:
        """获取单个用户详情（脱敏）。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        if not is_super_admin(user) and acc.company_id != user.company_id:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")

        return account_to_user_model(acc)

    def create_user(self, request: CreateUserRequest, principal: Principal) -> UserModel:
        """新增用户，执行密码强度校验与企业/RBAC权限门禁。"""
        user = principal.user

        # 1. RBAC 与租户隔离门禁
        if not is_super_admin(user):
            if request.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"未找到指定企业 {request.company_id} 或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可新增用户。")

        # 2. 账号重复冲突校验
        if request.username in self.repository.read().accounts:
            raise DomainError(409, "DICT_CODE_DUPLICATED", f"账号 {request.username} 已存在，请更换用户名。")

        # 3. 按新账号所属公司的密码规则核验 (PRD §5.10.2、§5.12.1 规则 3 / Q28；APP-M2-T260)
        from .password_login import require_strong_password
        require_strong_password(self.repository.read(),
                                Account(id=request.username, name=request.name, company_id=request.company_id,
                                        role=request.role),
                                request.password, field="password")

        # 4. 加盐哈希加密 (PBKDF2-HMAC-SHA256)
        pwd_hash, salt = hash_password(request.password)
        now_ts = time.time()

        new_acc = Account(
            id=request.username,
            name=request.name,
            company_id=request.company_id,
            role=request.role,
            _DEMO_ONLY=False,
            password_hash=pwd_hash,
            salt=salt,
            display_name=request.display_name or request.name,
            status="active",
            created_at=now_ts,
            updated_at=now_ts,
            # 管理员设定的初始密码，本人首次登录须先改密（PRD §5.12.1 验收④）
            must_change_password=True,
        )

        self.repository.transaction(lambda state: state.accounts.__setitem__(new_acc.id, new_acc))
        return account_to_user_model(new_acc)

    def _find_untransferred_assets(self, user_id: str, company_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """查找指定用户名下仍处于负责状态且未归档的在投项目与未完结/锁定章节列表。"""
        state = self.repository.read()
        active_projects: list[dict[str, Any]] = []
        active_chapters: list[dict[str, Any]] = []

        # 1. 扫描未归档项目中的负责人、分册负责人或团队成员
        for p_id, project in state.projects.items():
            if project.company_id != company_id or project.is_archived:
                continue
            team = state.project_teams.get(p_id, {})
            is_lead = (
                team.get("assembly_owner_id") == user_id
                or any(owner == user_id for owner in team.get("owners", {}).values())
                or team.get("members", {}).get(user_id, {}).get("project_role") in ("lead", "project_lead")
            )
            is_writer = (
                not is_lead
                and team.get("members", {}).get(user_id, {}).get("project_role") in ("writer", "bid_writer")
            )
            if is_lead:
                active_projects.append({
                    "project_id": p_id,
                    "project_name": project.name,
                    "role_in_project": "lead",
                })
            elif is_writer:
                active_projects.append({
                    "project_id": p_id,
                    "project_name": project.name,
                    "role_in_project": "writer",
                })
            elif project.created_by == user_id:
                active_projects.append({
                    "project_id": p_id,
                    "project_name": project.name,
                    "role_in_project": "creator",
                })

        # 2. 扫描未归档项目中由该用户负责编写或处于该用户编辑锁定的章节
        for c_id, chapter in state.chapters.items():
            proj = state.projects.get(chapter.project_id)
            if not proj or proj.company_id != company_id or proj.is_archived:
                continue
            is_assigned = (chapter.assignee_id == user_id)
            is_locked = (chapter.lock is not None and getattr(chapter.lock, "user_id", None) == user_id)
            if is_assigned or is_locked:
                active_chapters.append({
                    "chapter_id": c_id,
                    "project_id": chapter.project_id,
                    "title": chapter.title,
                    "volume": chapter.volume,
                    "is_assigned": is_assigned,
                    "is_locked": is_locked,
                })

        return active_projects, active_chapters

    def _execute_asset_transfer(
        self,
        from_user_id: str,
        successor_user_id: str,
        company_id: str,
        operator_id: str | None = None,
        reason: str | None = None,
    ) -> list[dict[str, Any]]:
        """执行名下在投项目与章节资产的原子平滑交接。"""
        state = self.repository.read()
        successor = state.accounts.get(successor_user_id)
        if not successor:
            raise DomainError(404, "NOT_FOUND", f"指定的交接接收人 {successor_user_id} 不存在。")
        if successor_user_id == from_user_id:
            raise DomainError(422, "VALIDATION_ERROR", "交接接收人不能是当前被停用的用户本人。")
        if successor.company_id != company_id and not is_super_admin(successor):
            raise DomainError(422, "VALIDATION_ERROR", f"交接接收人必须属于本企业（{company_id}）。")
        if getattr(successor, "status", "active") == "disabled":
            raise DomainError(422, "VALIDATION_ERROR", f"交接接收人 {successor_user_id} 账号已被停用，不能作为资产接交人。")

        now_iso = iso_time(time.time())
        transferred_list: list[dict[str, Any]] = []
        transferred_chapters: list[dict[str, Any]] = []

        def _do_transfer(st):
            # 1. 项目责任平滑交接
            for p_id, project in st.projects.items():
                if project.company_id != company_id or project.is_archived:
                    continue
                team = st.project_teams.get(p_id)
                if not team:
                    continue

                affected = False
                prev_role = None

                # 1.1 负责整卷/标段总装交接
                if team.get("assembly_owner_id") == from_user_id:
                    team["assembly_owner_id"] = successor_user_id
                    affected = True
                    prev_role = "lead"

                # 1.2 分册负责人交接
                for vol, owner in list(team.get("owners", {}).items()):
                    if owner == from_user_id:
                        team["owners"][vol] = successor_user_id
                        affected = True
                        prev_role = prev_role or "lead"

                # 1.3 团队成员角色交接
                members = team.get("members", {})
                if from_user_id in members:
                    old_mem = members.pop(from_user_id)
                    old_role = old_mem.get("project_role", "lead")
                    prev_role = prev_role or old_role
                    if successor_user_id not in members:
                        members[successor_user_id] = {
                            "user_id": successor_user_id,
                            "project_role": old_role,
                            "volumes": old_mem.get("volumes", list(VOLUMES)),
                        }
                    else:
                        if old_role in ("lead", "project_lead"):
                            members[successor_user_id]["project_role"] = "lead"
                    affected = True

                # 1.4 创建人记录平滑交接
                if project.created_by == from_user_id:
                    project.created_by = successor_user_id
                    affected = True

                if affected:
                    handoffs = team.setdefault("handoffs", [])
                    handoffs.append({
                        "from_user_id": from_user_id,
                        "to_user_id": successor_user_id,
                        "transferred_at": now_iso,
                        "reason": reason or "user_deactivated_handoff",
                    })
                    transferred_list.append({
                        "project_id": p_id,
                        "project_name": project.name,
                        "transferred_role": prev_role or "lead",
                    })

            # 2. 章节编写人变更与编辑锁释放
            for c_id, chapter in st.chapters.items():
                proj = st.projects.get(chapter.project_id)
                if not proj or proj.company_id != company_id or proj.is_archived:
                    continue
                if chapter.assignee_id == from_user_id:
                    chapter.assignee_id = successor_user_id
                    transferred_chapters.append({
                        "chapter_id": c_id,
                        "project_id": chapter.project_id,
                        "action": "reassigned_writer",
                    })
                if chapter.lock and getattr(chapter.lock, "user_id", None) == from_user_id:
                    chapter.lock = None
                    transferred_chapters.append({
                        "chapter_id": c_id,
                        "project_id": chapter.project_id,
                        "action": "lock_released",
                    })

            # 3. 记录安全审计日志
            security_audit.record(
                st, "user.deactivate_and_transfer",
                operator=operator_id or from_user_id,
                from_user_id=from_user_id,
                to_user_id=successor_user_id,
                transferred_projects=transferred_list,
                transferred_chapters=transferred_chapters,
                reason=reason or "user_deactivated_handoff",
            )

            # 4. 销毁待停用用户的所有活跃会话
            for tok, uid in list(st.sessions.items()):
                if uid == from_user_id:
                    del st.sessions[tok]

        self.repository.transaction(_do_transfer)
        return transferred_list

    def update_user(self, user_id: str, request: UpdateUserRequest, principal: Principal) -> UserModel:
        """更新用户信息。当 status='disabled' 时执行交接门禁检查。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        # 1. 租户隔离与 RBAC 权限校验
        if not is_super_admin(user):
            if acc.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可修改用户信息。")

        # 2. 超级管理员 admin 保护门禁与管理员防自降权
        if user_id == "admin":
            if request.status == "disabled":
                raise DomainError(403, "FORBIDDEN", "系统超级管理员 admin 不允许被停用。")
            if request.role is not None and request.role != "platform_admin":
                raise DomainError(403, "SUPER_ADMIN_PROTECTED", "系统超级管理员 admin 角色受到保护，不可被修改或降权。")

        if request.role is not None:
            norm_curr = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            norm_target = ROLE_NORMALIZATION_MAP.get(request.role, request.role)
            if user_id == user.id and norm_curr in (ROLE_COMPANY_ADMIN, "platform_admin") and norm_target != norm_curr:
                raise DomainError(403, "CANNOT_DEMOTE_SELF", "管理员账号不能对自己进行降权操作，请由其他管理员执行。")
            if request.role not in ROLE_NORMALIZATION_MAP:
                raise DomainError(422, "VALIDATION_ERROR", f"角色代码 '{request.role}' 不属于标准系统角色。")

        # 3. 停用前资产交接门禁 (PRD §5.10.1 / M1-P10-F2 核心红线：USER_TRANSFER_REQUIRED)
        if request.status == "disabled" and getattr(acc, "status", "active") != "disabled":
            untransferred_projects, untransferred_chapters = self._find_untransferred_assets(user_id, acc.company_id)
            if untransferred_projects or untransferred_chapters:
                if not request.successor_user_id:
                    raise DomainError(
                        409,
                        "USER_TRANSFER_REQUIRED",
                        f"用户 {user_id} 仍作为项目负责人或章节编写人绑定在 {len(untransferred_projects)} 个未完结在投项目及 {len(untransferred_chapters)} 个进行中章节，停用前必须转交名下资产。",
                        details={
                            "user_id": user_id,
                            "untransferred_projects": untransferred_projects,
                            "untransferred_chapters": untransferred_chapters,
                            "required_action": "请指定 successor_user_id 执行资产交接后再停用",
                        },
                    )
                # 附带有效交接人时执行平滑交接
                self._execute_asset_transfer(
                    from_user_id=user_id,
                    successor_user_id=request.successor_user_id,
                    company_id=acc.company_id,
                    operator_id=user.id,
                    reason=request.reason,
                )
            elif request.successor_user_id:
                # 即使没有活跃资产，若明确指定了交接人也必须校验其合法性
                self._execute_asset_transfer(
                    from_user_id=user_id,
                    successor_user_id=request.successor_user_id,
                    company_id=acc.company_id,
                    operator_id=user.id,
                    reason=request.reason,
                )

        # 4. 合并更新字段
        now_ts = time.time()
        new_name = request.name if request.name is not None else acc.name
        new_display = request.display_name if request.display_name is not None else acc.display_name
        new_role = request.role if request.role is not None else acc.role
        new_status = request.status if request.status is not None else getattr(acc, "status", "active")

        # 用 replace 保留锁定状态、失败次数、须改密标记等未在本请求里的字段；
        # 原先逐字段新建 Account，修改姓名就会顺带解除锁定和须改密。
        updated_acc = replace(
            acc,
            name=new_name,
            role=new_role,
            display_name=new_display,
            status=new_status,
            created_at=acc.created_at or now_ts,
            updated_at=now_ts,
        )

        self.repository.transaction(lambda state: state.accounts.__setitem__(user_id, updated_acc))
        return account_to_user_model(updated_acc)

    def transfer_assets(
        self,
        user_id: str,
        request: TransferUserAssetsRequest,
        principal: Principal,
    ) -> TransferUserAssetsResponse:
        """独立转交指定用户名下全部在投项目与资产。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        if not is_super_admin(user):
            if acc.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可执行资产交接。")

        transferred = self._execute_asset_transfer(user_id, request.successor_user_id, acc.company_id)
        return TransferUserAssetsResponse(
            success=True,
            from_user_id=user_id,
            successor_user_id=request.successor_user_id,
            transferred_projects=transferred,
            message=f"已成功将用户 {user_id} 名下 {len(transferred)} 个项目的管理职责转交给 {request.successor_user_id}。",
        )

    def reset_password(
        self,
        user_id: str,
        request: ResetPasswordRequest,
        principal: Principal,
    ) -> ResetPasswordResponse:
        """重置指定用户的密码，严格校验 Q28 密码强度策略并作废既有会话。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        # 1. 租户隔离与 RBAC 权限校验
        if not is_super_admin(user):
            if acc.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可重置用户密码。")

        # 2. 按目标账号适用的密码规则核验 (PRD §5.10.2、§5.12.1 规则 3 / Q28；APP-M2-T260)
        from .password_login import require_strong_password
        require_strong_password(self.repository.read(), acc, request.new_password, field="new_password")

        # 3. 重新加盐哈希
        pwd_hash, salt = hash_password(request.new_password)
        now_ts = time.time()

        def _do_reset(st):
            target = st.accounts.get(user_id)
            if not target:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")
            updated = replace(
                target,
                password_hash=pwd_hash,
                salt=salt,
                is_locked=False,
                failed_login_attempts=0,
                locked_at=None,
                # 被重置后本人须先改密才能使用系统（PRD §5.12.1 操作）
                must_change_password=True,
                updated_at=now_ts,
            )
            st.accounts[user_id] = updated
            # 作废该用户的所有活跃会话
            for tok, uid in list(st.sessions.items()):
                if uid == user_id:
                    del st.sessions[tok]
            security_audit.record(st, "user.reset_password", operator=user.id, target_user_id=user_id)

        self.repository.transaction(_do_reset)
        return ResetPasswordResponse(
            success=True,
            user_id=user_id,
            message=f"已成功重置用户 {user_id} 的密码并安全登出该账号的所有活跃会话。",
            updated_at=iso_time(now_ts),
        )

    def unlock_user(self, user_id: str, principal: Principal) -> UnlockUserResponse:
        """管理员一键清空连续失败计数并解除账号锁定。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        # 1. 租户隔离与 RBAC 权限校验
        if not is_super_admin(user):
            if acc.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可解锁用户。")

        now_ts = time.time()

        def _do_unlock(st):
            target = st.accounts.get(user_id)
            if not target:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")
            updated = replace(
                target,
                is_locked=False,
                status="active",
                failed_login_attempts=0,
                locked_at=None,
                updated_at=now_ts,
            )
            st.accounts[user_id] = updated
            security_audit.record(st, "user.unlock", operator=user.id, target_user_id=user_id)

        self.repository.transaction(_do_unlock)
        return UnlockUserResponse(
            success=True,
            user_id=user_id,
            is_locked=False,
            failed_login_attempts=0,
            message=f"已成功解除用户 {user_id} 的锁定状态并清零连续失败计数。",
        )

    def update_role(
        self,
        user_id: str,
        request: UpdateUserRoleRequest,
        principal: Principal,
    ) -> UserModel:
        """调整用户角色，执行超管保护与管理员防自降权门禁。"""
        user = principal.user
        acc = self.repository.read().accounts.get(user_id)
        if not acc:
            raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")

        # 1. 租户隔离与 RBAC 权限校验
        if not is_super_admin(user):
            if acc.company_id != user.company_id:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在或当前账号无权访问。")
            norm_role = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            if norm_role != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有企业管理员或平台管理员可分配用户角色。")

        # 2. 超管 admin 保护门禁（SUPER_ADMIN_PROTECTED 403）
        if user_id == "admin":
            raise DomainError(403, "SUPER_ADMIN_PROTECTED", "系统超级管理员 admin 角色受到保护，不可被修改或降权。")

        # 3. 管理员防自降权门禁（CANNOT_DEMOTE_SELF 403）
        if user_id == user.id:
            norm_curr = ROLE_NORMALIZATION_MAP.get(user.role, user.role)
            norm_target = ROLE_NORMALIZATION_MAP.get(request.role, request.role)
            if norm_curr in (ROLE_COMPANY_ADMIN, "platform_admin") and norm_target != norm_curr:
                raise DomainError(403, "CANNOT_DEMOTE_SELF", "管理员账号不能对自己进行降权操作，请由其他管理员执行。")

        # 4. 目标角色合法性校验
        if request.role not in ROLE_NORMALIZATION_MAP:
            raise DomainError(422, "VALIDATION_ERROR", f"角色代码 '{request.role}' 不属于标准系统角色。")

        now_ts = time.time()

        def _do_change_role(st):
            target = st.accounts.get(user_id)
            if not target:
                raise DomainError(404, "NOT_FOUND", f"用户 {user_id} 不存在。")
            updated = replace(target, role=request.role, updated_at=now_ts)
            st.accounts[user_id] = updated
            security_audit.record(st, "user.change_role", operator=user.id, target_user_id=user_id,
                                  old_role=target.role, new_role=request.role)

        self.repository.transaction(_do_change_role)
        updated_acc = self.repository.read().accounts[user_id]
        return account_to_user_model(updated_acc)
