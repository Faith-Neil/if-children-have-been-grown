// 为什么有这个文件：任务与模型对应表的下拉过滤规则（PRD v1.8 §6.4 降级口径；APP-M2-T040）。
// 它解决什么问题：首选下拉不放示例模型，“只能本地”的任务只放本地模型；备用下拉不放首选本身，首选为本地时只放本地模型。

import type { ModelConfigItem } from './model-config-core.ts';

export type TaskRoute = { task: string; name: string; local_only: boolean; primary_config_id: string | null; fallback_config_id: string | null };
export type TaskRoutes = { tasks: TaskRoute[]; revision: number; updated_by?: string | null; updated_at?: string | null };

const label = (c: ModelConfigItem) => `${c.name} (${c.model})${c.is_local ? ' · 本地' : ' · 非本地'}`;

export function routePrimaryOptions(configs: ModelConfigItem[], row: TaskRoute) {
  return configs.filter(c => c.provider !== 'demo').map(c => ({ value: c.id, label: label(c), disabled: row.local_only && !c.is_local }));
}

export function routeFallbackOptions(configs: ModelConfigItem[], row: TaskRoute) {
  const primary = configs.find(c => c.id === row.primary_config_id);
  return configs.filter(c => c.provider !== 'demo' && c.id !== row.primary_config_id)
    .map(c => ({ value: c.id, label: label(c), disabled: (row.local_only || !!primary?.is_local) && !c.is_local }));
}
