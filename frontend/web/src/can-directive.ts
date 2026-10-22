// 为什么有这个文件：落实 PRD v1.8 §2.3 权限矩阵与细粒度按钮级权限核验。
// 它解决什么问题：统一提供八角色体系及项目/分册/章节细粒度权限裁决，支持指令级按钮从 DOM 中彻底隐藏，杜绝非法写操作与越权绕过。

import type { ApplicationSession, Chapter, Project, Volume, Workspace } from './types.ts';
import {
  checkChapterEditPermission,
  getSystemRoleLabel,
  isReadonlyRole,
  normalizeSystemRole,
  PROJECT_CREATOR_ROLES,
  type SystemRole,
} from './route-guard.ts';

/**
 * 权限上下文入参
 */
export interface CanContext {
  session?: ApplicationSession | null;
  role?: string | string[] | null;
  userId?: string | null;
  project?: Pick<Project, 'id' | 'company_id'> | null;
  workspace?: Pick<Workspace, 'permissions' | 'team' | 'chapters' | 'parse_confirmed'> | null;
  chapter?: Pick<Chapter, 'id' | 'volume' | 'assignee_id'> | null;
  volume?: Volume | 'all' | null;
  allowedActions?: string[];
}

/**
 * 权限核验输出结果
 */
export interface CanResult {
  allowed: boolean;
  reason?: string;
  role: SystemRole;
  roleLabel: string;
  code?: string;
}

/**
 * 细粒度操作类型
 */
export type CanAction =
  | 'project:create'
  | 'project:confirm'
  | 'parse:confirm'
  | 'matrix:confirm'
  | 'chapter:edit'
  | 'chapter:submit'
  | 'chapter:takeover'
  | 'chapter:assign'
  | 'plan:confirm'
  | 'volume:finalize'
  | 'volume:check'
  | 'volume:unlock'
  | 'volume:export_internal'
  | 'submission:export'
  | 'id_card:view'
  | 'partner:upload'
  | 'rules:configure'
  | string;

/**
 * 规范化操作标识符与目标资源
 */
export function normalizeAction(
  perform: string,
  on?: string | object | null
): { action: string; resourceType?: string; resourceData?: any } {
  const cleanPerform = (perform || '').trim().toLowerCase();
  let action = cleanPerform;
  let resourceType: string | undefined;
  let resourceData: any = undefined;

  if (typeof on === 'string') {
    const cleanOn = on.trim().toLowerCase();
    if (cleanOn === 'technical' || cleanOn === 'business' || cleanOn === 'all') {
      resourceType = 'volume';
    } else {
      resourceType = cleanOn;
    }
  } else if (on && typeof on === 'object') {
    resourceData = on;
    if ('volume' in on && 'assignee_id' in on) {
      resourceType = 'chapter';
    } else if ('tender_number' in on || 'company_id' in on) {
      resourceType = 'project';
    }
  }

  // 支持冒号前缀如 "project:create"、"chapter:edit"、"submission:export"
  if (cleanPerform.includes(':')) {
    const [domain] = cleanPerform.split(':');
    action = cleanPerform;
    if (!resourceType) resourceType = domain;
  } else if (resourceType) {
    // 组合规范化 action
    if (resourceType === 'project' && ['create', 'confirm', 'manage'].includes(cleanPerform)) {
      action = `project:${cleanPerform}`;
    } else if (resourceType === 'chapter' && ['edit', 'submit', 'takeover', 'assign'].includes(cleanPerform)) {
      action = `chapter:${cleanPerform}`;
    } else if (resourceType === 'volume' && ['finalize', 'check', 'unlock', 'export_internal'].includes(cleanPerform)) {
      action = `volume:${cleanPerform}`;
    } else if (resourceType === 'submission' && cleanPerform === 'export') {
      action = 'submission:export';
    } else if (cleanPerform === 'confirm' && (resourceType === 'parse' || resourceType === 'parse_result')) {
      action = 'parse:confirm';
    } else if (cleanPerform === 'confirm' && (resourceType === 'matrix' || resourceType === 'response_matrix')) {
      action = 'matrix:confirm';
    }
  }

  return { action, resourceType, resourceData };
}

/**
 * 判断是否为写操作（只读角色全面阻断）
 */
function isWriteAction(action: string): boolean {
  const writeKeywords = [
    'create',
    'edit',
    'submit',
    'write',
    'delete',
    'modify',
    'takeover',
    'lock',
    'unlock',
    'finalize',
    'confirm',
    'assign',
    'upload',
    'configure',
    'patch',
    'post',
    'put',
  ];
  return writeKeywords.some(keyword => action.includes(keyword));
}

/**
 * 核心纯函数权限核验器
 */
export function can(
  perform: string,
  on?: string | object | null,
  context?: CanContext
): CanResult {
  const { action, resourceType, resourceData } = normalizeAction(perform, on);

  // 1. 提取角色与身份信息
  const rawRole =
    context?.role ??
    context?.session?.user?.primary_role ??
    context?.session?.user?.role ??
    'viewer';
  const normRole = normalizeSystemRole(rawRole);
  const roleLabel = getSystemRoleLabel(normRole);
  const userId = context?.userId ?? context?.session?.user?.id ?? '';
  const workspace = context?.workspace;

  // 提取章节上下文
  const chapter =
    (resourceData && 'volume' in resourceData ? resourceData : null) ??
    context?.chapter ??
    null;

  // 提取分册上下文
  const volume =
    (typeof on === 'string' && (on === 'technical' || on === 'business' || on === 'all')
      ? on
      : (resourceData && 'volume' in resourceData ? resourceData.volume : null)) ??
    context?.volume ??
    chapter?.volume ??
    null;

  // 2. 项目内角色解析
  const member = workspace?.team?.members?.find(m => m.user_id === userId);
  const isLeadInProject = member
    ? member.project_role === 'lead'
    : (normRole === 'project_lead' || normRole === 'company_admin');

  // 3. 通用只读角色拦截
  if (isReadonlyRole(normRole) && isWriteAction(action)) {
    return {
      allowed: false,
      reason: `抱歉，您当前的角色（${roleLabel}）处于只读状态，无权执行此写操作。`,
      role: normRole,
      roleLabel,
      code: 'READONLY_FORBIDDEN',
    };
  }

  // 4. 新建项目：project:create
  if (action === 'project:create') {
    if (PROJECT_CREATOR_ROLES.has(normRole)) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: `抱歉，您当前的角色（${roleLabel}）无权新建投标项目，仅项目负责人与公司管理员具备新建资质。`,
      role: normRole,
      roleLabel,
      code: 'PROJECT_CREATE_FORBIDDEN',
    };
  }

  // 5. 确认解析结果与响应矩阵：project:confirm / parse:confirm / matrix:confirm
  if (
    action === 'project:confirm' ||
    action === 'parse:confirm' ||
    action === 'matrix:confirm'
  ) {
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: `抱歉，您当前的角色（${roleLabel}）无权确认解析结果或响应矩阵，仅项目负责人可执行确认。`,
      role: normRole,
      roleLabel,
      code: 'CONFIRM_FORBIDDEN',
    };
  }

  // 6. 章节编辑与提交：chapter:edit / chapter:submit
  if (action === 'chapter:edit' || action === 'chapter:submit') {
    if (!chapter) {
      // 若无具体章节上下文，判断是否有通用的编写资质
      if (isLeadInProject || normRole === 'bid_writer') {
        return { allowed: true, role: normRole, roleLabel };
      }
      return {
        allowed: false,
        reason: `抱歉，您当前的角色（${roleLabel}）无权编辑章节。`,
        role: normRole,
        roleLabel,
        code: 'CHAPTER_EDIT_FORBIDDEN',
      };
    }

    if (!workspace) {
      // 无 workspace 保护上下文时降级为角色资质判断
      if (normRole === 'project_lead' || normRole === 'bid_writer' || normRole === 'company_admin') {
        return { allowed: true, role: normRole, roleLabel };
      }
      return {
        allowed: false,
        reason: `抱歉，您当前的角色（${roleLabel}）无权编辑本章节。`,
        role: normRole,
        roleLabel,
        code: 'CHAPTER_EDIT_FORBIDDEN',
      };
    }

    const guardResult = checkChapterEditPermission({
      role: normRole,
      userId,
      chapter,
      workspace,
    });

    return {
      allowed: guardResult.allowed,
      reason: guardResult.reason,
      role: normRole,
      roleLabel,
      code: guardResult.allowed ? undefined : 'CHAPTER_EDIT_FORBIDDEN',
    };
  }

  // 7. 编辑锁接管：chapter:takeover / chapter:lock_takeover
  if (action === 'chapter:takeover' || action === 'chapter:lock_takeover') {
    // 仅项目负责人、公司管理员或本分册负责人可以接管编辑锁
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    const isVolumeOwner =
      volume &&
      workspace?.team?.volumes?.some(
        v => v.volume === volume && v.owner_id === userId
      );
    if (isVolumeOwner) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，仅项目负责人或本分册负责人有权接管编辑锁。',
      role: normRole,
      roleLabel,
      code: 'LOCK_TAKEOVER_FORBIDDEN',
    };
  }

  // 8. 递交版导出：submission:export (PRD v1.5/v1.8: 仅项目负责人可导出递交版，分册负责人仅导出内部稿)
  if (action === 'submission:export') {
    const isStrictLead = member ? member.project_role === 'lead' : (normRole === 'project_lead');
    if (isStrictLead) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，正式递交版 Word 仅限项目负责人导出。',
      role: normRole,
      roleLabel,
      code: 'SUBMISSION_EXPORT_FORBIDDEN',
    };
  }

  // 9. 内部稿导出：volume:export_internal
  if (action === 'volume:export_internal') {
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    if (volume === 'all') {
      return {
        allowed: false,
        reason: '抱歉，生成两册内部稿仅限项目负责人。',
        role: normRole,
        roleLabel,
        code: 'INTERNAL_EXPORT_FORBIDDEN',
      };
    }
    const isVolumeOwner =
      volume &&
      workspace?.team?.volumes?.some(
        v => v.volume === volume && v.owner_id === userId
      );
    if (isVolumeOwner) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，仅项目负责人或本分册负责人有权导出内部稿。',
      role: normRole,
      roleLabel,
      code: 'INTERNAL_EXPORT_FORBIDDEN',
    };
  }

  // 10. 分册定稿与检查：volume:finalize / volume:check
  if (action === 'volume:finalize' || action === 'volume:check') {
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    const isVolumeOwner =
      volume &&
      workspace?.team?.volumes?.some(
        v => v.volume === volume && v.owner_id === userId
      );
    if (isVolumeOwner) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，仅项目负责人或本分册负责人有权发起分册检查与定稿。',
      role: normRole,
      roleLabel,
      code: 'VOLUME_FINALIZE_FORBIDDEN',
    };
  }

  // 11. 分册解锁：volume:unlock
  if (action === 'volume:unlock') {
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    const isVolumeOwner =
      volume &&
      workspace?.team?.volumes?.some(
        v => v.volume === volume && v.owner_id === userId
      );
    if (isVolumeOwner) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，仅项目负责人或本分册负责人有权解锁分册。',
      role: normRole,
      roleLabel,
      code: 'VOLUME_UNLOCK_FORBIDDEN',
    };
  }

  // 12. 写作方案与大纲确认：plan:confirm
  if (action === 'plan:confirm') {
    if (isLeadInProject || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    const isVolumeOwner =
      volume &&
      workspace?.team?.volumes?.some(
        v => v.volume === volume && v.owner_id === userId
      );
    if (isVolumeOwner) {
      return { allowed: true, role: normRole, roleLabel };
    }
    if (chapter && chapter.assignee_id === userId) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，仅项目负责人、分册负责人或被分配章节的编写人可确认写作方案。',
      role: normRole,
      roleLabel,
      code: 'PLAN_CONFIRM_FORBIDDEN',
    };
  }

  // 13. 查看完整身份证号：id_card:view
  if (action === 'id_card:view') {
    if (normRole === 'company_admin' || normRole === 'data_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，查看完整身份证号码仅限公司管理员与资料管理员。',
      role: normRole,
      roleLabel,
      code: 'ID_CARD_VIEW_FORBIDDEN',
    };
  }

  // 14. 合作伙伴资料上传：partner:upload
  if (action === 'partner:upload') {
    if (normRole === 'company_admin' || normRole === 'data_admin' || isLeadInProject) {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，合作伙伴资料上传仅限公司管理员、资料管理员或项目负责人。',
      role: normRole,
      roleLabel,
      code: 'PARTNER_UPLOAD_FORBIDDEN',
    };
  }

  // 15. 合规规则配置：rules:configure
  if (action === 'rules:configure') {
    if (normRole === 'platform_admin' || normRole === 'company_admin') {
      return { allowed: true, role: normRole, roleLabel };
    }
    return {
      allowed: false,
      reason: '抱歉，规则配置仅限平台管理员与公司管理员。',
      role: normRole,
      roleLabel,
      code: 'RULES_CONFIGURE_FORBIDDEN',
    };
  }

  // 16. 后台 allowedActions 动态核对
  const allowedActions =
    context?.allowedActions ?? context?.session?.allowedActions ?? [];
  if (allowedActions.includes(action) || allowedActions.includes(perform)) {
    return { allowed: true, role: normRole, roleLabel };
  }

  // 17. 兜底回退：如果属于平台管理员且操作业务，阻断
  if (normRole === 'platform_admin') {
    return {
      allowed: false,
      reason: '平台管理员不参与具体业务项目操作。',
      role: normRole,
      roleLabel,
      code: 'PLATFORM_ADMIN_FORBIDDEN',
    };
  }

  // 非写操作允许展示
  if (!isWriteAction(action)) {
    return { allowed: true, role: normRole, roleLabel };
  }

  return {
    allowed: false,
    reason: `抱歉，您当前的角色（${roleLabel}）无权执行此操作。`,
    role: normRole,
    roleLabel,
    code: 'ACTION_FORBIDDEN',
  };
}
