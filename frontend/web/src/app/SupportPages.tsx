// 为什么有这个文件：展示已经接通的资料与任务，并标明其余页面的真实边界。
// 它解决什么问题：辅助页面不再硬编码成功，也不会把待实现能力误当作完成。
import { useState } from 'react';
import { Alert, Button, Card, Progress, Table, Tabs, Tag } from 'antd';
import { formatTime } from './context';
import type { Job } from '../shared/types';
import { EmptyState } from '../status/StatusViews';

export { LibraryPage } from '../library/LibraryPages';

export function JobsPage({ jobs, openProject }: { jobs: Job[]; openProject: (id: string) => void }) {
  const [status, setStatus] = useState('completed');
  const filtered = jobs.filter(item => item.status === status);
  return <><div className="page-heading"><div><h2>后台任务中心</h2><p>查看当前公司的实际解析与生成任务。</p></div></div><Alert showIcon type="info" className="page-notice" message="当前为同步执行任务" description="后台真实记录执行结果和失败原因。排队、断点恢复、重试与取消尚未实现，因此不会提供假操作按钮。" /><Card><Tabs activeKey={status} onChange={setStatus} items={[{ key: 'running', label: '运行中' }, { key: 'queued', label: '排队' }, { key: 'failed', label: `失败 ${jobs.filter(item => item.status === 'failed').length}` }, { key: 'completed', label: `已完成 ${jobs.filter(item => item.status === 'completed').length}` }]} /><Table rowKey="id" size="small" dataSource={filtered} columns={[{ title: '任务类型', dataIndex: 'type', render: value => value === 'parse' ? '招标文件解析' : value === 'generate' ? '章节候选生成' : value }, { title: '执行情况', dataIndex: 'message' }, { title: '进度', width: 170, render: (_, item) => <Progress percent={item.progress} size="small" status={item.status === 'failed' ? 'exception' : undefined} /> }, { title: '开始时间', dataIndex: 'created_at', render: formatTime }, { title: '失败原因', render: (_, item) => item.error?.message ?? '—' }, { title: '操作', render: (_, item) => <Button type="link" onClick={() => openProject(item.project_id)}>前往项目</Button> }]} /></Card></>;
}

export function PendingPage({ title, detail }: { title: string; detail: string }) {
  return <><div className="page-heading"><div><h2>{title}</h2></div><Tag color="orange">尚未实现</Tag></div><Card><EmptyState description={detail} /><Alert className="page-notice" type="info" message="当前先贯通项目主流程，再按 ICG 示例补齐此页" showIcon /></Card></>;
}
