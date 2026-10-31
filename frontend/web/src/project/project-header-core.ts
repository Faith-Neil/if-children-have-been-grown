// 为什么有这个文件：提取 ProjectHeader 摘要条的核心纯业务逻辑与八角色页签过滤算法。
// 它解决什么问题：支持在 Node.js 原生测试环境中零依赖高效运行，保障倒计时推导、标的金额格式化与只读角色设置权限隔离的确定性。

import { normalizeSystemRole, READONLY_SYSTEM_ROLES, type SystemRole } from '../shell/route-guard.ts';
import { sessionAllowsProjectTab } from '../app/session-navigation.ts';
import type { ApplicationSession } from '../shared/types.ts';

export const URGENT_DAYS = 3;

export interface CountdownInfo {
  status: 'none' | 'expired' | 'urgent' | 'normal';
  label: string;
  days: number;
  hours: number;
  minutes: number;
  isUrgent: boolean;
  isExpired: boolean;
  color: 'default' | 'red' | 'orange' | 'blue' | 'green';
}

/**
 * 纯函数：计算项目投标截止倒计时
 * @param deadline 截止时间 ISO 字符串
 * @param now 当前时间戳毫秒数（缺省为 Date.now()）
 */
export function calculateProjectCountdown(
  deadline: string | null | undefined,
  now: number = Date.now()
): CountdownInfo {
  if (!deadline) {
    return {
      status: 'none',
      label: '未设定截止时间',
      days: 0,
      hours: 0,
      minutes: 0,
      isUrgent: false,
      isExpired: false,
      color: 'default',
    };
  }

  const targetTime = new Date(deadline).getTime();
  if (isNaN(targetTime)) {
    return {
      status: 'none',
      label: '截止时间格式无效',
      days: 0,
      hours: 0,
      minutes: 0,
      isUrgent: false,
      isExpired: false,
      color: 'default',
    };
  }

  const diff = targetTime - now;
  if (diff <= 0) {
    return {
      status: 'expired',
      label: '已截止',
      days: 0,
      hours: 0,
      minutes: 0,
      isUrgent: true,
      isExpired: true,
      color: 'red',
    };
  }

  const oneMinute = 60 * 1000;
  const oneHour = 60 * oneMinute;
  const oneDay = 24 * oneHour;

  const days = Math.floor(diff / oneDay);
  const hours = Math.floor((diff % oneDay) / oneHour);
  const minutes = Math.floor((diff % oneHour) / oneMinute);

  // PRD v1.8 5.1.1：距投标截止不超过 3 天（含恰好 3 天）标红；天数示例 3 天，后续可配置
  const isUrgent = diff <= URGENT_DAYS * oneDay;
  let label = '';
  if (days > 0) {
    label = `剩余 ${days} 天 ${hours} 小时`;
  } else if (hours > 0) {
    label = `剩余 ${hours} 小时 ${minutes} 分钟`;
  } else {
    label = `剩余 ${Math.max(1, minutes)} 分钟`;
  }

  return {
    status: isUrgent ? 'urgent' : 'normal',
    label,
    days,
    hours,
    minutes,
    isUrgent,
    isExpired: false,
    color: isUrgent ? 'red' : 'blue',
  };
}

/**
 * 纯函数：格式化标的金额为千分位货币文本
 */
export function formatCurrencyAmount(amount: number | string | undefined | null): string {
  if (amount === undefined || amount === null || amount === '') {
    return '未填写';
  }
  const numeric = typeof amount === 'number' ? amount : parseFloat(String(amount).replace(/[^0-9.-]+/g, ''));
  if (isNaN(numeric)) {
    return String(amount);
  }
  return `¥ ${numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * 纯函数：八角色权限判断当前用户是否有权访问项目设置与管理
 */
export function canAccessProjectSettings(
  role: string | undefined | null,
  customPermissions?: { manage_project?: boolean }
): boolean {
  if (customPermissions?.manage_project !== undefined) {
    return customPermissions.manage_project;
  }
  const normalized = normalizeSystemRole(role);
  if (!normalized) return false;
  // 只读成员、审核人与外部只读均无权访问项目设置
  if (READONLY_SYSTEM_ROLES.has(normalized as SystemRole)) {
    return false;
  }
  return true;
}

/**
 * 标准项目业务页签定义
 */
export const PROJECT_HEADER_TABS: Array<{ key: string; label: string }> = [
  { key: 'overview', label: '概览' },
  { key: 'tender', label: '招标文件' },
  { key: 'parse', label: '解析结果' },
  { key: 'matrix', label: '响应矩阵' },
  { key: 'facts', label: '项目事实表' },
  { key: 'editor', label: '编辑台' },
  { key: 'manual', label: '人工处理队列' },
  { key: 'checks', label: '合规检查' },
  { key: 'export', label: '导出' },
  { key: 'settings', label: '项目设置' },
];

export type ProjectTabPermissions = {
  manage_project?: boolean;
  export_internal?: boolean;
  export_volumes?: string[];
  check_all?: boolean;
  check_volumes?: string[];
};

/** 只在权限字段明确给出时才收紧：导出页签看 export_internal / export_volumes，与会话 project.export 路由口径一致；合规检查只读成员仍可查看，不收紧 */
export function tabAllowedByPermissions(tab: string, permissions?: ProjectTabPermissions): boolean {
  if (!permissions) return true;
  if (tab === 'export' && permissions.export_internal !== undefined) {
    return permissions.export_internal === true || (permissions.export_volumes?.length ?? 0) > 0;
  }
  return true;
}

/**
 * 纯函数：根据当前会话与角色过滤可用页签
 */
export function filterProjectTabs(
  tabs: Array<{ key: string; label: string }>,
  session: ApplicationSession | null,
  projectId: string,
  userRole?: string | null,
  customPermissions?: ProjectTabPermissions
): Array<{ key: string; label: string }> {
  const allowSettings = canAccessProjectSettings(userRole, customPermissions);
  return tabs.filter(item => {
    // 0. 有项目权限读回时，导出页签按实际可办理范围显示（会话另行过滤，两者取交集）
    if (!tabAllowedByPermissions(item.key, customPermissions)) return false;
    // 1. 设置页签专门受项目设置权限感知控制
    if (item.key === 'settings' && !allowSettings) {
      return false;
    }
    // 2. 会话级权限过滤
    if (session && !sessionAllowsProjectTab(session, projectId, item.key)) {
      return false;
    }
    return true;
  });
}
