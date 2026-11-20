// 为什么有这个文件：项目设置要单独选目录、抽取与偏离的模型，不能跟写作模型绑在同一个控件上。
// 它解决什么问题：选项只放本地真实模型，文案带上名称、模型名和主机；保存只改 technical_structure，其它任务原样提交。

export type StructureRouteTask = {
  task: string;
  primary_config_id: string | null;
  fallback_config_id: string | null;
  primary_name?: string | null;
  primary_model?: string | null;
  primary_missing?: boolean;
};

export type StructureRoutes = {
  revision: number;
  tasks: StructureRouteTask[];
};

type StructureModel = {
  id: string;
  name: string;
  model: string;
  base_url: string;
  provider: string;
  is_local: boolean;
};

export function structureModelHost(baseUrl: string): string {
  const raw = (baseUrl || '').trim();
  if (!raw) return '';
  try {
    return new URL(raw).hostname;
  } catch {
    return raw;
  }
}

export function structureModelLabel(config: { name: string; model: string; base_url: string }): string {
  const host = structureModelHost(config.base_url);
  return host ? `${config.name} (${config.model}) ${host}` : `${config.name} (${config.model})`;
}

/** 目录任务已保存的实际模型。与任务表同一口径：模型字符串、未指定、配置失效。 */
export function structureEffectiveLabel(row: StructureRouteTask | null | undefined): string {
  if (!row) return '未指定';
  if (row.primary_missing || (row.primary_config_id && !row.primary_model)) return '配置失效';
  return row.primary_model || '未指定';
}

export function structureModelOptions(configs: StructureModel[]) {
  return configs
    .filter(item => item.provider !== 'demo' && item.is_local)
    .map(item => ({ value: item.id, label: structureModelLabel(item) }));
}

export function structureRouteBody(current: StructureRoutes, primaryId: string | null) {
  return {
    revision: current.revision,
    routes: current.tasks.map(row => {
      if (row.task !== 'technical_structure') {
        return {
          task: row.task,
          primary_config_id: row.primary_config_id,
          fallback_config_id: row.fallback_config_id,
        };
      }
      const fallback = primaryId && row.fallback_config_id !== primaryId ? row.fallback_config_id : null;
      return { task: row.task, primary_config_id: primaryId, fallback_config_id: fallback };
    }),
  };
}

/** 优先用接口展开的 primary_model，与运行时 resolve 一致。 */
export function structureBoundLabel(
  routes: StructureRoutes | null | undefined,
  configs: StructureModel[],
): string {
  const row = routes?.tasks.find(item => item.task === 'technical_structure');
  const primaryId = row?.primary_config_id ?? null;
  if (row?.primary_model) {
    const name = row.primary_name;
    if (name && name !== row.primary_model) return `${name} · ${row.primary_model}`;
    return row.primary_model;
  }
  const cfg = configs.find(item => item.id === primaryId);
  if (!cfg) return primaryId || '未指定';
  return cfg.model || cfg.name || primaryId || '未指定';
}
