// 为什么有这个文件：站内提醒（PRD v1.8 §5.12.2；APP-M2-T029～T032）的纯计算部分。
// 它解决什么问题：铃铛徽标超过 99 显示 99+；轮询间隔；筛选条件拼成查询参数；点开后按后端核对结果跳转或提示。

export type NotificationItem = {
  id: string; type: string; type_label: string; title: string; body: string; project_id: string | null;
  target_id: string | null; read: boolean; read_at: string | null; created_at: string; updated_at: string; count: number;
};
export type NotificationList = { items: NotificationItem[]; total: number; unread: number; types: { value: string; label: string }[] };
export type OpenResult = { notification: NotificationItem; ok: boolean; path: string | null; message: string | null };
export type NotificationFilter = { status: 'all' | 'unread' | 'read'; type?: string; projectId?: string; since?: string; until?: string };

export const POLL_MS = 60_000;
export const DROPDOWN_SIZE = 7;
export const NOT_AVAILABLE = '对象已不存在或你没有查看权限';

export function badgeText(unread: number): string {
  if (!unread || unread < 0) return '';
  return unread > 99 ? '99+' : String(unread);
}

export function listPath(filter: NotificationFilter, limit = 50, offset = 0): string {
  const params = new URLSearchParams({ status: filter.status, limit: String(limit), offset: String(offset) });
  if (filter.type) params.set('type', filter.type);
  if (filter.projectId) params.set('project_id', filter.projectId);
  if (filter.since) params.set('since', filter.since);
  if (filter.until) params.set('until', filter.until);
  return `/api/v1/notifications?${params.toString()}`;
}

export const notificationPaths = {
  unread: '/api/v1/notifications/unread-count',
  readAll: '/api/v1/notifications/read-all',
  read: (id: string) => `/api/v1/notifications/${encodeURIComponent(id)}/read`,
  open: (id: string) => `/api/v1/notifications/${encodeURIComponent(id)}/open`,
};

/** 只接受站内相对地址，防止提醒里出现外部链接。 */
export function safeTarget(result: OpenResult): string | null {
  if (!result.ok || !result.path) return null;
  return result.path.startsWith('/') && !result.path.startsWith('//') ? result.path : null;
}

export function mergedNote(item: Pick<NotificationItem, 'count'>): string {
  return item.count > 1 ? `（未读期间合并 ${item.count} 次）` : '';
}
