// 为什么有这个文件：落实 PRD v1.8 §2.3 权限矩阵与 §5.11.9 多粒度数据权限判定（项目 / 分册 / 章节）。
// 它解决什么问题：提供统一的多粒度数据权限解析算法，在只读模式下区分项目级、分册级与章节级原因，支撑前端视图向排版文本切换而非渲染输入控件。

import type { ApplicationSession, Chapter, Project, Volume, Workspace } from '../shared/types.ts';
import {
  getSystemRoleLabel,
  isReadonlyRole,
  normalizeSystemRole,
  type SystemRole,
} from './route-guard.ts';

/**
 * 权限判定粒度范围
 */
export type DataPermissionScope = 'project' | 'volume' | 'chapter' | 'none';

/**
 * 只读原因分类
 */
export type ReadOnlyReasonType =
  | 'role_readonly'     // 系统只读角色（集团管理员、只读成员、审计员、平台管理员）
  | 'project_readonly'  // 项目成员角色为 readonly
  | 'not_member'        // 非本项目团队成员
  | 'wrong_volume'      // 非本人主管分册（分册负责人跨分册）或未分配该分册
  | 'not_assigned'      // 普通编写人未被指派该章节
  | 'custom';           // 自定义只读原因

/**
 * 多粒度数据权限判定入参
 */
export interface DataPermissionContext {
  session?: ApplicationSession | null;
  role?: string | string[] | null;
  userId?: string | null;
  project?: Pick<Project, 'id' | 'company_id' | 'name'> | null;
  workspace?: Pick<Workspace, 'permissions' | 'team' | 'chapters'> | null;
  volume?: Volume | 'all' | null;
  volumeId?: Volume | string | null;
  chapter?: (Pick<Chapter, 'id' | 'volume' | 'assignee_id'> & { title?: string }) | null;
  chapterId?: string | null;
}

/**
 * 数据权限判定结果
 */
export interface DataPermissionResult {
  /** 是否处于只读状态 */
  readOnly: boolean;
  /** 是否具备可编辑资质（!readOnly） */
  canEdit: boolean;
  /** 只读作用域范围（'project' | 'volume' | 'chapter' | 'none'） */
  scope: DataPermissionScope;
  /** 作用域中文名称（如“全项目”、“技术分册”、“第1章 综述”） */
  scopeName: string;
  /** 只读时的中文友好解释文案 */
  readOnlyReason?: string;
  /** 只读原因分类类型 */
  reasonType?: ReadOnlyReasonType;
  /** 归一化后的标准系统角色 */
  role: SystemRole;
  /** 系统角色中文名 */
  roleLabel: string;
}

/**
 * 分册名称转换辅助函数
 */
export function getVolumeDisplayName(volume?: Volume | string | null): string {
  if (volume === 'technical') return '技术分册';
  if (volume === 'business') return '商务分册';
  return '全部分册';
}

/**
 * 作用域类型中文友好标签
 */
export function getScopeLabel(scope: DataPermissionScope): string {
  switch (scope) {
    case 'project':
      return '全项目';
    case 'volume':
      return '分册';
    case 'chapter':
      return '章节';
    default:
      return '无限制';
  }
}

/**
 * 核心算法：多粒度数据权限判定
 *
 * 遵循严格优先级层级：
 * 1. 角色级只读（group_admin, viewer, auditor, platform_admin）-> scope: 'project'
 * 2. 项目成员资格与项目角色只读 -> scope: 'project'
 * 3. 项目负责人（project_lead）/ 公司管理员（company_admin）-> 放行全项目/全分册/全章节
 * 4. 分册负责人（volume_lead）-> 主管分册全放行；进入非主管分册 -> scope: 'volume' 只读
 * 5. 普通编写人（bid_writer）-> 未参与分册 -> scope: 'volume' 只读；已参与分册但未被分配章节 -> scope: 'chapter' 只读；已分配章节 -> 放行
 */
export function resolveDataPermission(context: DataPermissionContext): DataPermissionResult {
  const { session, workspace } = context;

  // 1. 提取并归一化角色与用户标识
  const rawRole = context.role ?? session?.user?.role ?? (session as any)?.roles;
  const normRole = normalizeSystemRole(rawRole);
  const roleLabel = getSystemRoleLabel(normRole);

  const userId = (context.userId ?? session?.user?.id ?? '').trim();

  // 2. 提取分册与章节标识
  const rawVol = context.volume ?? context.volumeId;
  let targetVolume: Volume | null =
    rawVol === 'technical' || rawVol === 'business' ? rawVol : null;

  let targetChapter = context.chapter ?? null;
  if (!targetChapter && context.chapterId && workspace?.chapters) {
    targetChapter = workspace.chapters.find(c => c.id === context.chapterId) ?? null;
  }

  // 若传入了章节对象，以章节所属分册为权威有效分册
  if (targetChapter?.volume && !targetVolume) {
    targetVolume = targetChapter.volume;
  }

  // =========================================================================
  // 规则 1：系统级只读角色（集团管理员、只读成员、审计员、平台管理员）
  // =========================================================================
  if (isReadonlyRole(normRole)) {
    return {
      readOnly: true,
      canEdit: false,
      scope: 'project',
      scopeName: '全项目',
      readOnlyReason: `抱歉，您当前的角色（${roleLabel}）处于只读状态，仅可查阅项目数据。`,
      reasonType: 'role_readonly',
      role: normRole,
      roleLabel,
    };
  }

  // =========================================================================
  // 规则 2：公司管理员（具备公司级运维管理权限，放行）
  // =========================================================================
  if (normRole === 'company_admin') {
    return {
      readOnly: false,
      canEdit: true,
      scope: 'none',
      scopeName: '公司管理员',
      role: normRole,
      roleLabel,
    };
  }

  // =========================================================================
  // 规则 3：项目团队成员资格核验
  // =========================================================================
  if (workspace?.team) {
    const member = workspace.team.members?.find(m => m.user_id === userId);

    // 3.1 非项目成员阻断
    if (userId && !member) {
      return {
        readOnly: true,
        canEdit: false,
        scope: 'project',
        scopeName: '项目成员',
        readOnlyReason: '抱歉，您不是当前项目团队成员，处于只读浏览状态。',
        reasonType: 'not_member',
        role: normRole,
        roleLabel,
      };
    }

    if (member) {
      // 3.2 显式项目只读成员阻断
      if (member.project_role === 'readonly') {
        return {
          readOnly: true,
          canEdit: false,
          scope: 'project',
          scopeName: '只读成员',
          readOnlyReason: '抱歉，您在当前项目中为只读成员，无权修改数据。',
          reasonType: 'project_readonly',
          role: normRole,
          roleLabel,
        };
      }

      // 3.3 项目负责人全项目放行
      if (member.project_role === 'lead' || normRole === 'project_lead') {
        return {
          readOnly: false,
          canEdit: true,
          scope: 'none',
          scopeName: '项目负责人',
          role: normRole,
          roleLabel,
        };
      }

      // 3.4 提取分册主管信息
      const ownedVolumes =
        workspace.team.volumes?.filter(v => v.owner_id === userId).map(v => v.volume) ?? [];
      const memberVolumes = member.volumes ?? [];

      // =====================================================================
      // 规则 4：分册级数据权限核验（当存在明确分册上下文时）
      // =====================================================================
      if (targetVolume) {
        const isOwnerOfTarget = ownedVolumes.includes(targetVolume);
        const targetVolName = getVolumeDisplayName(targetVolume);

        if (isOwnerOfTarget) {
          // 本分册负责人：在所主管的分册内拥有全部编辑权（包括该分册全部章节）
          return {
            readOnly: false,
            canEdit: true,
            scope: 'none',
            scopeName: targetVolName,
            role: normRole,
            roleLabel,
          };
        }

        // 若用户是其他分册的负责人，进入非主管分册自动触发分册只读态
        if (ownedVolumes.length > 0) {
          const ownedNames = ownedVolumes.map(getVolumeDisplayName).join('、');
          return {
            readOnly: true,
            canEdit: false,
            scope: 'volume',
            scopeName: targetVolName,
            readOnlyReason: `您当前是【${ownedNames}】负责人，在【${targetVolName}】中处于只读浏览状态。`,
            reasonType: 'wrong_volume',
            role: normRole,
            roleLabel,
          };
        }

        // 普通成员未被分配参与该分册
        if (!memberVolumes.includes(targetVolume)) {
          return {
            readOnly: true,
            canEdit: false,
            scope: 'volume',
            scopeName: targetVolName,
            readOnlyReason: `您未被分配参与【${targetVolName}】，处于只读浏览状态。`,
            reasonType: 'wrong_volume',
            role: normRole,
            roleLabel,
          };
        }
      }

      // =====================================================================
      // 规则 5：章节级数据权限核验（普通编写人细粒度指派校验）
      // =====================================================================
      if (targetChapter) {
        const chapterTitle = targetChapter.title || targetChapter.id;
        const isAssigned = targetChapter.assignee_id === userId;

        if (isAssigned) {
          return {
            readOnly: false,
            canEdit: true,
            scope: 'none',
            scopeName: chapterTitle,
            role: normRole,
            roleLabel,
          };
        }

        return {
          readOnly: true,
          canEdit: false,
          scope: 'chapter',
          scopeName: chapterTitle,
          readOnlyReason: `本章节【${chapterTitle}】未分配给您，当前仅可只读浏览。`,
          reasonType: 'not_assigned',
          role: normRole,
          roleLabel,
        };
      }

      // 若指定了分册上下文但未指定具体章节，普通编写人不能编辑分册结构
      if (targetVolume) {
        return {
          readOnly: true,
          canEdit: false,
          scope: 'volume',
          scopeName: getVolumeDisplayName(targetVolume),
          readOnlyReason: '您是章节编写人，仅可编辑具体被分配的章节。',
          reasonType: 'not_assigned',
          role: normRole,
          roleLabel,
        };
      }
    }
  }

  // 缺省/兜底：可编辑
  return {
    readOnly: false,
    canEdit: true,
    scope: 'none',
    scopeName: '默认',
    role: normRole,
    roleLabel,
  };
}
