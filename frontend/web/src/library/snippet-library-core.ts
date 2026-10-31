// 为什么有这个文件：提取知识库方案片段管理（FE-SNIPPET-LIBRARY / PRD v1.8 §5.5）的纯业务逻辑与状态诊断规则。
// 它解决什么问题：
// 1. 公司隔离：严格隔离当前登录会话的 company_id，杜绝跨租户片段泄露；
// 2. 状态机与元数据解析：套话组、产品线、变量标记（{{var}}）、发布版本号与知识库同步状态（synced/unsynced/failed；兼容旧值 sync_failed）；
// 3. 多维筛选与检索：支持关键字、分类、产品、同步状态及“仅已发布”筛选算法；
// 4. API 数据加载：调用 /api/v1/snippet-publications（兼容 /api/v1/snippet_publications）获取服务端数据；
// 5. 遵循 Layout First 原则，提供结构化指标与空状态数据判定。

import { normalizeSnippetSyncStatus } from './knowledge-base-core.ts';
import { request } from '../shared/api.ts';
import type { SnippetPublication, SnippetSyncStatus } from '../shared/types.ts';

export type { SnippetPublication, SnippetSyncStatus };

export interface SnippetFilterParams {
  search?: string;
  product?: string;
  snippet_type?: string;
  kb_sync_status?: string;
  onlyPublished?: boolean;
}

export interface SnippetStats {
  totalCount: number;
  publishedCount: number;
  syncedCount: number;
  variablesCount: number;
}

/**
 * 片段类型中文映射
 */
export const SNIPPET_TYPE_MAP: Record<string, string> = {
  all: '全部分类',
  solution: '技术方案',
  boilerplate: '通用套话',
  qualification: '资质证明',
  case: '经典案例',
  sla: '服务承诺',
  security: '安全合规',
  architecture: '系统架构',
  implementation: '实施方案',
};

/**
 * 获取片段分类友好中文标签
 */
export function getSnippetTypeLabel(type?: string | null): string {
  if (!type) return '方案片段';
  return SNIPPET_TYPE_MAP[type] || type;
}

/**
 * 知识库同步状态元数据
 */
export function getSnippetSyncStatusMeta(status?: SnippetSyncStatus | null): {
  label: string;
  color: string;
  badgeStatus: 'success' | 'warning' | 'error' | 'default';
} {
  switch (status) {
    case 'synced':
      return { label: '已同步知识库', color: 'green', badgeStatus: 'success' };
    case 'unsynced':
      return { label: '未同步知识库', color: 'gold', badgeStatus: 'warning' };
    case 'failed':
    case 'sync_failed':
      return { label: '同步失败', color: 'red', badgeStatus: 'error' };
    default:
      return { label: status || '未知状态', color: 'default', badgeStatus: 'default' };
  }
}

/**
 * 智能推导方案片段展示标题
 * 优先使用自身 title；若无则结合“产品线 + 套话组”或“产品线 + 分类”生成整洁标题
 */
export function resolveSnippetTitle(item?: Partial<SnippetPublication> | null): string {
  if (!item) return '方案片段';
  if (item.title && item.title.trim()) return item.title.trim();
  if (item.product && item.boilerplate_group && item.boilerplate_group.trim()) {
    return `${item.product} · ${item.boilerplate_group.trim()}`;
  }
  if (item.product && item.snippet_type) {
    return `${item.product} · ${getSnippetTypeLabel(item.snippet_type)}`;
  }
  if (item.product) {
    return `${item.product} 方案片段`;
  }
  return item.id ? `方案片段 #${item.id}` : '方案片段';
}

/**
 * 从片段文本中提取所有形如 {{variable_name}} 的占位符变量
 */
export function extractSnippetVariables(body?: string | null): string[] {
  if (!body) return [];
  const regex = /\{\{([A-Za-z0-9_.-]+)\}\}/g;
  const set = new Set<string>();
  let match: RegExpExecArray | null;
  while ((match = regex.exec(body)) !== null) {
    if (match[1]) set.add(match[1]);
  }
  return Array.from(set).sort();
}

/**
 * 格式化 ISO 时间为等宽紧凑可读时间（YYYY-MM-DD HH:mm:ss）
 */
export function formatMonospaceTime(timeStr?: string | null): string {
  if (!timeStr) return '-';
  const date = new Date(timeStr);
  if (Number.isNaN(date.getTime())) return timeStr;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`;
}

/**
 * 严格按照租户 company_id 隔离与多维条件过滤方案片段
 */
export function filterSnippets(
  items: SnippetPublication[] | undefined | null,
  params: SnippetFilterParams = {},
  activeCompanyId?: string | null
): SnippetPublication[] {
  if (!Array.isArray(items)) return [];

  return items.filter(item => {
    // 1. 公司隔离门禁：如果指定了当前租户 company_id，绝对排除其他租户数据
    if (activeCompanyId && item.company_id && item.company_id !== activeCompanyId) {
      return false;
    }

    // 2. 仅已发布门禁：published_revision > 0 或含有已发布正文
    if (params.onlyPublished) {
      const isPublished = (item.published_revision ?? 0) > 0 || !!(item.published_body && item.published_body.trim());
      if (!isPublished) return false;
    }

    // 3. 分类过滤
    if (params.snippet_type && params.snippet_type !== 'all' && item.snippet_type !== params.snippet_type) {
      return false;
    }

    // 4. 产品线过滤
    if (params.product && params.product !== 'all' && item.product !== params.product) {
      return false;
    }

    // 5. 知识库同步状态过滤
    if (params.kb_sync_status && params.kb_sync_status !== 'all' && normalizeSnippetSyncStatus(item.kb_sync_status) !== normalizeSnippetSyncStatus(params.kb_sync_status)) {
      return false;
    }

    // 6. 关键字多维匹配（标题、产品、套话组、来源组、正文、变量、ID）
    if (params.search && params.search.trim()) {
      const kw = params.search.trim().toLowerCase();
      const title = resolveSnippetTitle(item).toLowerCase();
      const product = (item.product || '').toLowerCase();
      const group = (item.boilerplate_group || '').toLowerCase();
      const source = (item.source_group || '').toLowerCase();
      const body = (item.published_body || item.draft_body || '').toLowerCase();
      const id = (item.id || '').toLowerCase();
      const vars = (item.variables || []).join(' ').toLowerCase();

      const matched =
        title.includes(kw) ||
        product.includes(kw) ||
        group.includes(kw) ||
        source.includes(kw) ||
        body.includes(kw) ||
        id.includes(kw) ||
        vars.includes(kw);

      if (!matched) return false;
    }

    return true;
  });
}

/**
 * 汇总当前公司片段统计指标
 */
export function computeSnippetStats(
  items: SnippetPublication[] | undefined | null,
  activeCompanyId?: string | null
): SnippetStats {
  const scoped = filterSnippets(items, {}, activeCompanyId);
  const totalCount = scoped.length;
  let publishedCount = 0;
  let syncedCount = 0;
  const variableSet = new Set<string>();

  for (const item of scoped) {
    if ((item.published_revision ?? 0) > 0 || (item.published_body && item.published_body.trim())) {
      publishedCount += 1;
    }
    if (item.kb_sync_status === 'synced') {
      syncedCount += 1;
    }
    for (const v of item.variables || []) {
      variableSet.add(v);
    }
  }

  return {
    totalCount,
    publishedCount,
    syncedCount,
    variablesCount: variableSet.size,
  };
}

/**
 * 服务端片段数据加载器（优先请求 /api/v1/snippet-publications，兼顾下划线路径 fallback）
 */
export async function loadSnippetPublications(token: string | null): Promise<SnippetPublication[]> {
  try {
    const res = await request<{ items: SnippetPublication[] }>('/api/v1/snippet-publications', token);
    return res.items || [];
  } catch (primaryError) {
    try {
      const fallbackRes = await request<{ items: SnippetPublication[] }>('/api/v1/snippet_publications', token);
      return fallbackRes.items || [];
    } catch {
      throw primaryError;
    }
  }
}

