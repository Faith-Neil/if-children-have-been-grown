// 为什么有这个文件：A-01 公司管理（PRD v1.8 §5.10.1；APP-M2-T026，APP-M2-T260 验收③）。
// 它解决什么问题：原页面用写死的示例公司（信用代码、法人、人数都是编的），停用只改页面状态却提示“已阻断登录”。
// 现在列表与状态都来自 /api/v1/companies；只有平台管理员能停用或启用，停用须输入完整公司名称，后台使该公司账号无法登录。
// 公司的密码策略、编辑锁等参数在“企业设置”页维护（company-settings-sync.ts），这里不重复一份表单。

import { useCallback, useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Input, Modal, Space, Table, Tag, Typography } from 'antd';
import { DatabaseOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Account, ApplicationSession } from '../shared/types';
import { request, userFacingMessage } from '../shared/api';
import { listCompanies, updateCompanyStatus, validateDisableConfirmation, type CompanyList, type CompanySummary } from './company-manage-core';
import { ModelConfigModal } from './ModelConfigModal';
import { RagflowConfigModal } from './RagflowConfigModal';
import { normalizeSystemRole } from '../shell/route-guard';

const { Title, Text } = Typography;

interface CompanyManagePageProps {
  session?: ApplicationSession | null;
  currentUser?: Account | null;
  token?: string | null;
}

function changedAt(row: CompanySummary): string {
  if (!row.status_changed_at) return '';
  const when = new Date(row.status_changed_at).toLocaleString('zh-CN', { hour12: false });
  return row.status_changed_by ? `${when} · ${row.status_changed_by}` : when;
}

export function CompanyManagePage({ session, currentUser, token }: CompanyManagePageProps) {
  const { message } = AntApp.useApp();
  const [list, setList] = useState<CompanyList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<CompanySummary | null>(null);
  const [confirmName, setConfirmName] = useState('');
  const [working, setWorking] = useState<string | null>(null);
  const [modelOpen, setModelOpen] = useState(false);
  const [ragflowOpen, setRagflowOpen] = useState(false);
  const role = normalizeSystemRole(session?.user?.primary_role || currentUser?.role);
  const canConfigureServices = role === 'platform_admin' || role === 'company_admin';

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setList(await listCompanies(request, token));
      setError(null);
    } catch (err) {
      setError(userFacingMessage(err));
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function change(row: CompanySummary, status: 'active' | 'disabled', name?: string) {
    if (!token) return;
    setWorking(row.id);
    try {
      const updated = await updateCompanyStatus(request, token, row.id, status, name);
      setList(previous => previous ? { ...previous, items: previous.items.map(item => item.id === updated.id ? updated : item) } : previous);
      setTarget(null);
      setConfirmName('');
      message.success(status === 'disabled' ? `已停用 ${row.name}，该公司账号已退出且不能再登录` : `已启用 ${row.name}`);
    } catch (err) {
      message.error(userFacingMessage(err));
    } finally {
      setWorking(null);
    }
  }

  const columns: ColumnsType<CompanySummary> = [
    { title: '公司', key: 'name', render: (_: unknown, row: CompanySummary) => (
      <Space direction="vertical" size={0}><Text strong>{row.name}</Text><Text type="secondary" style={{ fontSize: 12 }}>{row.id}</Text></Space>
    ) },
    { title: '状态', key: 'status', width: 100, render: (_: unknown, row: CompanySummary) => (
      <Tag color={row.status === 'active' ? 'success' : 'error'} data-testid={`company-status-${row.id}`}>{row.status === 'active' ? '启用' : '已停用'}</Tag>
    ) },
    { title: '账号', dataIndex: 'user_count', key: 'user_count', width: 80 },
    { title: '项目', dataIndex: 'project_count', key: 'project_count', width: 80 },
    { title: '最近变更', key: 'changed', render: (_: unknown, row: CompanySummary) => <Text type="secondary">{changedAt(row)}</Text> },
    ...(list?.can_change_status ? [{ title: '', key: 'actions', width: 90, render: (_: unknown, row: CompanySummary) => (
      row.status === 'active'
        ? <Button danger size="small" loading={working === row.id} onClick={() => { setConfirmName(''); setTarget(row); }} data-testid={`company-disable-${row.id}`}>停用</Button>
        : <Button size="small" loading={working === row.id} onClick={() => void change(row, 'active')} data-testid={`company-enable-${row.id}`}>启用</Button>
    ) }] : []),
  ];

  return (
    <div className="company-manage-page" style={{ paddingBottom: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>公司管理</Title>
        {canConfigureServices && (
          <Space wrap>
            <Button data-testid="open-model-config-modal-btn" icon={<ThunderboltOutlined />} onClick={() => setModelOpen(true)}>模型配置</Button>
            <Button data-testid="open-ragflow-config-modal-btn" icon={<DatabaseOutlined />} onClick={() => setRagflowOpen(true)}>知识库服务</Button>
          </Space>
        )}
      </div>
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => void load()}>重试</Button>} />}
      <Table<CompanySummary> rowKey="id" size="middle" loading={!list && !error} dataSource={list?.items ?? []}
        columns={columns} pagination={false} data-testid="company-table" />

      <Modal title={target ? `停用 ${target.name}` : ''} open={!!target} onCancel={() => setTarget(null)}
        footer={[
          <Button key="cancel" onClick={() => setTarget(null)}>取消</Button>,
          <Button key="ok" danger type="primary" data-testid="company-disable-confirm" loading={working === target?.id}
            disabled={!target || !validateDisableConfirmation(confirmName, target.name)}
            onClick={() => { if (target) void change(target, 'disabled', confirmName.trim()); }}>停用</Button>,
        ]}>
        <Alert type="warning" showIcon message="停用后该公司所有账号立即退出且不能登录；资料、项目与审计记录保留，可再次启用。" style={{ marginBottom: 12 }} />
        <Input placeholder={target?.name} value={confirmName} onChange={event => setConfirmName(event.target.value)} data-testid="company-disable-name-input" />
      </Modal>

      <ModelConfigModal open={modelOpen} onClose={() => setModelOpen(false)} session={session} />
      <RagflowConfigModal open={ragflowOpen} onClose={() => setRagflowOpen(false)} session={session} />
    </div>
  );
}

export default CompanyManagePage;
