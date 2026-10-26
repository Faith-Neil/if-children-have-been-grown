// 为什么有这个文件：提取通用状态组件的核心规则、属性解析与复制逻辑。
// 它解决什么问题：让状态逻辑、错误体解析、无权限上下文与对比度约束可脱离 DOM 单独测试并保障类型安全。
import type { ReactNode } from 'react';
import { ApiError } from '../shared/api.ts';

/**
 * WCAG 4.5:1 对比度锁定的色彩令牌
 */
export const STATUS_CONTRAST_TOKENS = {
  text: '#1d2129', // 正常正文深色
  muted: '#4e5969', // 次要说明文字，浅底上对比度 > 6.4:1
  primary: '#1e4db7', // 主品牌色，浅底上对比度 > 7.5:1
  error: '#d9363e', // 错误红色，白底上对比度 > 4.6:1
  warningText: '#9a5608', // 满足 WCAG 4.5:1 的高对比度警告深橙棕色
  warningDesc: '#5c3504', // 警告描述深褐色，对比度 > 8:1
  border: '#e8ebf0',
  cardBg: '#ffffff',
  pageBg: '#f5f7fa',
  warningBg: '#fffbe6',
  readonlyBg: '#f5f7fa',
} as const;

/**
 * 计算两个十六进制颜色的相对亮度与对比度
 */
export function luminance(hex: string): number {
  const sanitized = hex.replace('#', '');
  const r = parseInt(sanitized.substring(0, 2), 16) / 255;
  const g = parseInt(sanitized.substring(2, 4), 16) / 255;
  const b = parseInt(sanitized.substring(4, 6), 16) / 255;
  const srgb = [r, g, b].map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

export function contrastRatio(hex1: string, hex2: string): number {
  const l1 = luminance(hex1);
  const l2 = luminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * 复制文本到剪贴板工具函数
 */
export async function copyText(text: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // 降级到 execCommand
    }
  }
  if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      textarea.style.pointerEvents = 'none';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const success = document.execCommand ? document.execCommand('copy') : false;
      document.body.removeChild(textarea);
      if (success) return true;
    } catch {
      // 复制失败
    }
  }
  return false;
}

export interface ExtractedErrorInfo {
  code: string;
  message: string;
  traceId?: string;
  status?: number;
  details?: Record<string, unknown>;
}

/**
 * 从各类错误对象中提取统一错误体
 */
export function extractErrorInfo(error: unknown, fallbackMessage = '操作失败，请稍后重试。'): ExtractedErrorInfo {
  if (!error) {
    return { code: 'REQUEST_FAILED', message: fallbackMessage };
  }
  if (error instanceof ApiError) {
    return {
      code: error.code || 'REQUEST_FAILED',
      message: error.message || fallbackMessage,
      traceId: error.requestId,
      status: error.status,
      details: error.details,
    };
  }
  if (typeof error === 'object') {
    const record = error as Record<string, unknown>;
    const nested = record.error && typeof record.error === 'object' ? (record.error as Record<string, unknown>) : null;
    // 严格优先解构规范体 {code, message, details, traceId}，旧结构 {error, request_id} 仅作兼容兜底
    const code = (typeof record.code === 'string' ? record.code : null)
      ?? (typeof nested?.code === 'string' ? nested.code : null)
      ?? 'REQUEST_FAILED';
    const message = (typeof record.message === 'string' ? record.message : null)
      ?? (typeof nested?.message === 'string' ? nested.message : null)
      ?? fallbackMessage;
    const traceId = (typeof record.traceId === 'string' ? record.traceId : null)
      ?? (typeof record.requestId === 'string' ? record.requestId : null)
      ?? (typeof record.request_id === 'string' ? record.request_id : null)
      ?? (typeof nested?.traceId === 'string' ? nested.traceId : null)
      ?? undefined;
    const status = typeof record.status === 'number' ? record.status : undefined;
    const details = record.details && typeof record.details === 'object'
      ? (record.details as Record<string, unknown>)
      : nested?.details && typeof nested.details === 'object'
        ? (nested.details as Record<string, unknown>)
        : undefined;
    return { code, message, traceId, status, details };
  }
  if (typeof error === 'string') {
    return { code: 'ERROR', message: error };
  }
  return { code: 'REQUEST_FAILED', message: fallbackMessage };
}

/**
 * 空态属性预解析
 */
export function resolveEmptyState(props: {
  mode?: 'empty' | 'filtered' | 'search';
  title?: ReactNode;
  description?: ReactNode;
  actionText?: ReactNode;
  searchKeyword?: string;
}) {
  const mode = props.mode ?? 'empty';
  let title = props.title;
  let description = props.description;
  let actionText = props.actionText;

  if (mode === 'filtered') {
    title = title ?? '没有符合条件的记录';
    description = description ?? '请尝试调整或重置筛选条件';
    actionText = actionText ?? '清除筛选';
  } else if (mode === 'search') {
    title = title ?? '未找到匹配结果';
    description = description ?? (props.searchKeyword ? `没有找到名称包含“${props.searchKeyword}”的项目或资料` : '没有找到匹配的记录');
  } else {
    title = title ?? '暂无数据';
  }

  return { mode, title, description, actionText };
}

/**
 * 403 权限提示信息解析
 */
export function resolveForbidden(props: {
  title?: ReactNode;
  subTitle?: ReactNode;
  reason?: ReactNode;
  contextInfo?: { projectName?: string; roleName?: string; path?: string; retainedMessage?: string } | ReactNode;
  showRetainedNotice?: boolean;
  backText?: ReactNode;
  backPath?: string;
  switchRoleText?: ReactNode;
}) {
  const title = props.title ?? '没有访问权限';
  const reasonText = props.reason ?? props.subTitle ?? '你没有该页面的权限，请联系公司管理员。';
  const backText = props.backText ?? '返回工作台';
  const backPath = props.backPath ?? '/workbench';
  const switchRoleText = props.switchRoleText ?? '切换身份';
  const showRetained = Boolean(props.showRetainedNotice);
  return { title, reasonText, backText, backPath, switchRoleText, showRetained };
}

/**
 * 过期警告条信息解析
 */
export function resolveExpired(props: {
  message?: ReactNode;
  description?: ReactNode;
  reason?: ReactNode;
  currentRevision?: number | string;
  latestRevision?: number | string;
  actionText?: ReactNode;
}) {
  const message = props.message ?? '内容已修改，结果已过期';
  const actionText = props.actionText ?? '重新运行';
  const hasDiff = props.currentRevision !== undefined && props.latestRevision !== undefined;
  return { message, actionText, hasDiff };
}

/**
 * 只读保护横幅信息解析
 */
export function resolveReadonly(props: {
  reason?: string | ReactNode;
  message?: ReactNode;
  description?: ReactNode;
  scope?: string | ReactNode;
}) {
  const message = props.message ?? (props.reason ? `只读：${props.reason}` : '只读会话保护');
  const description = props.description ?? '当前页面处于只读状态，所有修改、保存与生成入口已关闭，仅供查阅。';
  return { message, description, scope: props.scope };
}
