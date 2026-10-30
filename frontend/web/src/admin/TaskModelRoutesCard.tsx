// 为什么有这个文件：企业设置里的“任务与模型”对应表（PRD v1.8 §6.4、§5.10.5 A-10；APP-M2-T040）。
// 它解决什么问题：公司管理员为章节写作、对话助手问答、修改样例分别选首选与备用模型；首选为本地时备用下拉只放本地模型，
// 后台保存时同样核对。没有单独绑定模型的项目按此表取模型。

import { useEffect, useState } from 'react';
import { App as AntApp, Button, Card, Select, Table, Tag } from 'antd';
import { request, userFacingMessage } from '../shared/api.ts';
import type { ModelConfigItem } from './model-config-core.ts';
import { routeFallbackOptions, routePrimaryOptions, type TaskRoutes } from './task-model-routes-core.ts';

type Props = { token: string | null; canEdit: boolean };

export function TaskModelRoutesCard({ token, canEdit }: Props) {
  const { message } = AntApp.useApp();
  const [data, setData] = useState<TaskRoutes | null>(null);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    request<TaskRoutes>('/api/v1/task-model-routes', token).then(setData).catch(error => message.error(userFacingMessage(error)));
    request<{ items: ModelConfigItem[] }>('/api/v1/model-configs', token).then(value => setConfigs(value.items)).catch(() => undefined);
  }, [token]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (!data) return null;
  const update = (task: string, patch: Partial<TaskRoutes['tasks'][number]>) =>
    setData(current => current && { ...current, tasks: current.tasks.map(row => (row.task === task ? { ...row, ...patch } : row)) });

  async function save() {
    if (!data) return;
    setSaving(true);
    try {
      const saved = await fetchSave(data, token);
      setData(saved);
      message.success('任务与模型对应表已保存，没有单独绑定模型的项目按此取模型。');
    } catch (error) { message.error(userFacingMessage(error)); } finally { setSaving(false); }
  }

  return (
    <Card size="small" title="任务与模型" data-testid="task-model-routes-card"
      extra={canEdit && <Button size="small" type="primary" loading={saving} onClick={() => void save()} data-testid="task-model-routes-save">保存</Button>}>
      <Table size="small" rowKey="task" pagination={false} dataSource={data.tasks}
        columns={[
          { title: '任务', dataIndex: 'name', render: (name: string, row) => <>{name}{row.local_only && <Tag color="purple" style={{ marginLeft: 6 }}>只能本地</Tag>}</> },
          { title: '首选模型', key: 'primary', width: 240, render: (_, row) => (
            <Select allowClear style={{ width: '100%' }} placeholder="沿用项目绑定或本公司默认" disabled={!canEdit}
              value={row.primary_config_id ?? undefined} options={routePrimaryOptions(configs, row)}
              onChange={value => update(row.task, { primary_config_id: value ?? null, fallback_config_id: null })} />
          ) },
          { title: '备用模型', key: 'fallback', width: 240, render: (_, row) => (
            <Select allowClear style={{ width: '100%' }} placeholder="不配备用" disabled={!canEdit || !row.primary_config_id}
              value={row.fallback_config_id ?? undefined} options={routeFallbackOptions(configs, row)}
              onChange={value => update(row.task, { fallback_config_id: value ?? null })} />
          ) },
        ]} />
    </Card>
  );
}

async function fetchSave(data: TaskRoutes, token: string | null): Promise<TaskRoutes> {
  return request<TaskRoutes>('/api/v1/task-model-routes', token, 'PUT', {
    routes: data.tasks.map(({ task, primary_config_id, fallback_config_id }) => ({ task, primary_config_id, fallback_config_id })),
  }, data.revision);
}
