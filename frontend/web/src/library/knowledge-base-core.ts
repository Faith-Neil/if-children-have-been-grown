// 为什么有这个文件：放公司知识库（RAGFlow）同步状态的纯逻辑：状态文案、汇总与待处理清单。
// 它解决什么问题：资料管理员需要一眼看出哪些资料还没进入知识库、哪些失败及原因；逻辑与渲染分开便于测试。

export type KnowledgeBaseItemStatus = 'synced' | 'parsing' | 'unsynced' | 'failed';

export interface KnowledgeBaseItem {
  key: string;
  source_type: 'library' | 'snippet' | string;
  source_id: string;
  name: string;
  item_type: string;
  revision: number;
  status: KnowledgeBaseItemStatus | string;
  message: string;
  chunk_count: number;
  updated_at: string | null;
  document_id: string;
}

export interface KnowledgeBaseStatus {
  enabled: boolean;
  dataset_id: string;
  last_sync_at: string | null;
  last_error: string;
  counts: Record<string, number>;
  items: KnowledgeBaseItem[];
}

export interface KnowledgeBaseSyncResult {
  enabled: boolean;
  uploaded: number;
  deleted: number;
  failed: number;
  unchanged: number;
  message: string;
}

export const KB_STATUS_META: Record<string, { label: string; color: string }> = {
  synced: { label: '已入库可检索', color: 'green' },
  parsing: { label: '解析中', color: 'blue' },
  unsynced: { label: '待同步', color: 'gold' },
  failed: { label: '同步失败', color: 'red' },
};

export function kbStatusMeta(status: string): { label: string; color: string } {
  return KB_STATUS_META[status] ?? { label: status || '未知', color: 'default' };
}

/** 后端片段状态是 failed；旧前端用过 sync_failed，这里统一成 failed。 */
export function normalizeSnippetSyncStatus(status?: string | null): string {
  return status === 'sync_failed' ? 'failed' : status ?? '';
}

export function summarizeKnowledgeBase(status: KnowledgeBaseStatus | null) {
  const counts = status?.counts ?? {};
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
  const synced = counts.synced ?? 0;
  return {
    total,
    synced,
    parsing: counts.parsing ?? 0,
    pending: counts.unsynced ?? 0,
    failed: counts.failed ?? 0,
    coverage: total ? Math.round((synced / total) * 100) : 0,
  };
}

/** 需要人处理或等待的条目：失败在前，其次待同步、解析中。 */
export function attentionItems(status: KnowledgeBaseStatus | null): KnowledgeBaseItem[] {
  const order: Record<string, number> = { failed: 0, unsynced: 1, parsing: 2 };
  return (status?.items ?? [])
    .filter(item => item.status !== 'synced')
    .sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9) || a.name.localeCompare(b.name, 'zh-CN'));
}
