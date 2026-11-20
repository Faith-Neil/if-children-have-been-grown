// 为什么有这个文件：任务与模型对应表的下拉过滤规则（PRD v1.8 §6.4 降级口径；APP-M2-T040）。
// 它解决什么问题：首选下拉不放示例模型，“只能本地”的任务只放本地模型；备用下拉不放首选本身，首选为本地时只放本地模型。
// 另提供 bound 文案：优先用接口返回的真实 model 字符串，避免 UI 选中值与运行时调用不一致时看不见。

import type { ModelConfigItem } from './model-config-core.ts';

export type TaskRoute = {
  task: string;
  name: string;
  local_only: boolean;
  primary_config_id: string | null;
  fallback_config_id: string | null;
  primary_name?: string | null;
  primary_model?: string | null;
  fallback_name?: string | null;
  fallback_model?: string | null;
  /** 首选 id 已保存，但配置缺失或不属于本公司 */
  primary_missing?: boolean;
};
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

/** 展示已绑定的真实模型；优先服务端展开字段，编辑中再回落到配置列表。 */
export function routeBoundLabel(
  row: TaskRoute,
  which: 'primary' | 'fallback',
  configs: ModelConfigItem[],
): string {
  const name = which === 'primary' ? row.primary_name : row.fallback_name;
  const model = which === 'primary' ? row.primary_model : row.fallback_model;
  if (model) {
    return name ? `${name} · ${model}` : model;
  }
  const id = which === 'primary' ? row.primary_config_id : row.fallback_config_id;
  const cfg = configs.find(item => item.id === id);
  if (!cfg) return id || '';
  return cfg.model || cfg.name || cfg.id;
}

/** 已保存首选的实际模型字符串。没绑定时是「未指定」，id 失效时是「配置失效」。 */
export function routeEffectiveLabel(row: Pick<TaskRoute, 'primary_config_id' | 'primary_model' | 'primary_missing'>): string {
  if (row.primary_missing || (row.primary_config_id && !row.primary_model)) return '配置失效';
  return row.primary_model || '未指定';
}
