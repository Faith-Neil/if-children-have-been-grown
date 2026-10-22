// 为什么有这个文件：提取项目列表多维筛选、生命周期阶段推导与分册状态计算的核心纯业务逻辑。
// 它解决什么问题：支持在 Node.js 原生测试环境中零依赖高效运行，保障状态、涉密属性与分册状态多维组合筛选的确定性与健壮性。

import type { Project } from '../shared/types.ts';

export type ProjectStatusKey = 'all' | 'preparing' | 'writing' | 'reviewing' | 'completed';
export type SensitiveFilterKey = 'all' | 'sensitive' | 'normal';
export type VolumeStatusFilterKey = 'all' | 'technical_pending' | 'business_pending' | 'both_done';

export interface ProjectFilterCriteria {
  keyword?: string;
  status?: ProjectStatusKey;
  sensitive?: SensitiveFilterKey;
  volumeStatus?: VolumeStatusFilterKey;
}

export const PROJECT_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  preparing: { label: '筹备中', color: 'default' },
  writing: { label: '编写中', color: 'blue' },
  reviewing: { label: '审核中', color: 'orange' },
  completed: { label: '已完成', color: 'green' },
};

/**
 * 纯函数：根据项目属性智能推导项目生命周期状态
 */
export function deriveProjectStatus(project: Project): 'preparing' | 'writing' | 'reviewing' | 'completed' {
  if (project.status && ['preparing', 'writing', 'reviewing', 'completed'].includes(project.status)) {
    return project.status as 'preparing' | 'writing' | 'reviewing' | 'completed';
  }
  if (project.stage && ['preparing', 'writing', 'reviewing', 'completed'].includes(project.stage)) {
    return project.stage as 'preparing' | 'writing' | 'reviewing' | 'completed';
  }
  // 缺省智能推导：根据分册状态与截止时间
  if (project.volumes_status?.technical === 'completed' && project.volumes_status?.business === 'completed') {
    return 'completed';
  }
  if (project.volumes_status?.technical === 'submitted' || project.volumes_status?.business === 'submitted') {
    return 'reviewing';
  }
  if (project.revision && project.revision > 1) {
    return 'writing';
  }
  return 'preparing';
}

/**
 * 纯函数：推导项目分册综合状态
 */
export function deriveVolumeStatus(project: Project): {
  technical: 'pending' | 'writing' | 'completed';
  business: 'pending' | 'writing' | 'completed';
  isBothDone: boolean;
} {
  const tech = (project.volumes_status?.technical as 'pending' | 'writing' | 'completed') || 'writing';
  const biz = (project.volumes_status?.business as 'pending' | 'writing' | 'completed') || 'writing';
  return {
    technical: tech,
    business: biz,
    isBothDone: tech === 'completed' && biz === 'completed',
  };
}

/**
 * 纯函数：执行项目列表多维筛选过滤
 */
export function filterProjectList(
  projects: Project[],
  criteria: ProjectFilterCriteria
): Project[] {
  const { keyword = '', status = 'all', sensitive = 'all', volumeStatus = 'all' } = criteria;
  const kw = keyword.trim().toLowerCase();

  return projects.filter(project => {
    // 1. 关键词筛选（匹配项目名称或招标编号）
    if (kw) {
      const matchName = (project.name || '').toLowerCase().includes(kw);
      const matchTender = (project.tender_number || '').toLowerCase().includes(kw);
      if (!matchName && !matchTender) {
        return false;
      }
    }

    // 2. 状态筛选（筹备中、编写中、审核中、已完成）
    if (status !== 'all') {
      const currentStatus = deriveProjectStatus(project);
      if (currentStatus !== status) {
        return false;
      }
    }

    // 3. 涉密属性筛选（全部、涉密、普通）
    if (sensitive === 'sensitive' && !project.sensitive) {
      return false;
    }
    if (sensitive === 'normal' && !!project.sensitive) {
      return false;
    }

    // 4. 分册状态筛选
    if (volumeStatus !== 'all') {
      const vStatus = deriveVolumeStatus(project);
      if (volumeStatus === 'technical_pending' && vStatus.technical === 'completed') {
        return false;
      }
      if (volumeStatus === 'business_pending' && vStatus.business === 'completed') {
        return false;
      }
      if (volumeStatus === 'both_done' && !vStatus.isBothDone) {
        return false;
      }
    }

    return true;
  });
}
