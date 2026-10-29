// 为什么有这个文件：站内提醒列表页 G-02（PRD v1.8 §5.12.2；APP-M2-T031、T032）。
// 它解决什么问题：按类型、已读/未读、所属项目、时间范围筛选本人的提醒，时间倒序；点击跳到对象并标已读，
// 对象已删除或无权限时提示；可标已读/未读、全部标为已读；同对象同类型的合并次数显示在摘要后。本页不设任何站外渠道。
import React, { useEffect, useState } from 'react';
import { App as AntApp, Button, Card, DatePicker, Segmented, Select, Space, Table, Tag } from 'antd';
import { request } from '../shared/api.ts';
import { formatTime } from '../app/context';
import type { Project } from '../shared/types';
import { NOT_AVAILABLE, listPath, mergedNote, notificationPaths, safeTarget,
  type NotificationFilter, type NotificationList, type OpenResult } from './notifications-core.ts';

export function NotificationsPage({ token, projects, onNavigate, report }: {
  token: string | null; projects: Project[]; onNavigate: (path: string) => void; report: (error: unknown) => void;
}) {
  const { message } = AntApp.useApp();
  const [filter, setFilter] = useState<NotificationFilter>({ status: 'all' });
  const [data, setData] = useState<NotificationList | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(next = filter) {
    if (!token) return;
    setLoading(true);
    try { setData(await request<NotificationList>(listPath(next, 200), token)); } catch (error) { report(error); } finally { setLoading(false); }
  }
  useEffect(() => { void load(filter); }, [token, filter.status, filter.type, filter.projectId, filter.since, filter.until]);

  async function openItem(id: string) {
    const result = await request<OpenResult>(notificationPaths.open(id), token, 'POST');
    const target = safeTarget(result);
    if (target) onNavigate(target); else { message.warning(result.message || NOT_AVAILABLE); await load(); }
  }

  return (
    <>
      <div className="page-heading">
        <div><h2>站内提醒</h2><p>只显示发给你的提醒；点击跳到需要处理的位置，同时标为已读。</p></div>
        <Button data-testid="notifications-read-all" disabled={!data?.unread} onClick={async () => { await request(notificationPaths.readAll, token, 'POST'); await load(); }}>
          全部标为已读{data?.unread ? `（${data.unread}）` : ''}
        </Button>
      </div>
      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <Segmented value={filter.status} onChange={value => setFilter({ ...filter, status: value as NotificationFilter['status'] })}
            options={[{ value: 'all', label: '全部' }, { value: 'unread', label: '未读' }, { value: 'read', label: '已读' }]} />
          <Select allowClear placeholder="类型" style={{ width: 180 }} aria-label="提醒类型" value={filter.type}
            onChange={value => setFilter({ ...filter, type: value })} options={data?.types ?? []} />
          <Select allowClear placeholder="所属项目" style={{ width: 220 }} aria-label="所属项目" value={filter.projectId}
            onChange={value => setFilter({ ...filter, projectId: value })} options={projects.map(p => ({ value: p.id, label: p.name }))} />
          <DatePicker.RangePicker aria-label="时间范围" onChange={range => setFilter({
            ...filter, since: range?.[0]?.startOf('day').toISOString(), until: range?.[1]?.endOf('day').toISOString() })} />
        </Space>
        <Table rowKey="id" size="small" loading={loading} dataSource={data?.items ?? []} pagination={{ pageSize: 20 }} data-testid="notifications-table"
          rowClassName={item => (item.read ? '' : 'notice-unread-row')}
          columns={[
            { title: '类型', dataIndex: 'type_label', width: 130, render: (value: string) => <Tag>{value}</Tag> },
            { title: '标题', dataIndex: 'title', render: (value: string, item) => <a onClick={() => void openItem(item.id)}>{value}</a> },
            { title: '内容摘要', dataIndex: 'body', render: (value: string, item) => <span className="muted">{value}{mergedNote(item)}</span> },
            { title: '所属项目', dataIndex: 'project_id', width: 160, render: (value: string | null) => projects.find(p => p.id === value)?.name ?? (value ? '—' : '') },
            { title: '时间', dataIndex: 'updated_at', width: 140, render: formatTime },
            { title: '状态', width: 120, render: (_, item) => (
              <a data-testid="notification-toggle" onClick={async () => { await request(notificationPaths.read(item.id), token, 'POST', { read: !item.read }); await load(); }}>
                {item.read ? '已读 · 改回未读' : '未读 · 标为已读'}
              </a>) },
          ]} />
      </Card>
    </>
  );
}
