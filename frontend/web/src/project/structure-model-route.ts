// 为什么有这个文件：项目设置要单独选目录、抽取与偏离的模型，不能跟写作模型绑在同一个控件上。
// 它解决什么问题：选项只放本地真实模型，文案带上名称、模型名和主机；保存只改 technical_structure，其它任务原样提交。

export type StructureRouteTask = {
  task: string;
  primary_config_id: string | null;
  fallback_config_id: string | null;
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
