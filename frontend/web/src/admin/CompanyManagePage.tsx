// 为什么有这个文件：A-01 公司管理（PRD v1.8 §5.10.1；APP-M2-T026，APP-M2-T260 验收③；ISSUE-052）。
// 它解决什么问题：列表与启停来自 /api/v1/companies；平台管理员可同弹窗开通公司并创建首个管理员；点进公司进入详情管人。

import { useCallback, useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Checkbox, Form, Input, Modal, Space, Table, Tag, Typography } from 'antd';
import { DatabaseOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Account, ApplicationSession } from '../shared/types';
import { request, userFacingMessage } from '../shared/api';
import { listCompanies, updateCompanyStatus, validateDisableConfirmation, type CompanyList, type CompanySummary } from './company-manage-core';
import {
  companyDetailPath,
  createCompany,
  validateCreateCompanyForm,
  type CreateCompanyFormValues,
} from './company-provision-core';
import { ModelConfigModal } from './ModelConfigModal';
import { RagflowConfigModal } from './RagflowConfigModal';
import { normalizeSystemRole } from '../shell/route-guard';

const { Title, Text } = Typography;

interface CompanyManagePageProps {
  session?: ApplicationSession | null;
  currentUser?: Account | null;
  token?: string | null;
  onNavigate?: (path: string) => void;
}

function changedAt(row: CompanySummary): string {
  if (!row.status_changed_at) return '';
  const when = new Date(row.status_changed_at).toLocaleString('zh-CN', { hour12: false });
  return row.status_changed_by ? `${when} · ${row.status_changed_by}` : when;
}

export function CompanyManagePage({ session, currentUser, token, onNavigate }: CompanyManagePageProps) {
  const { message } = AntApp.useApp();
  const [list, setList] = useState<CompanyList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<CompanySummary | null>(null);
  const [confirmName, setConfirmName] = useState('');
  const [working, setWorking] = useState<string | null>(null);
  const [modelOpen, setModelOpen] = useState(false);
  const [ragflowOpen, setRagflowOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm] = Form.useForm<CreateCompanyFormValues>();
  const role = normalizeSystemRole(session?.user?.primary_role || currentUser?.role);
  const canConfigureServices = role === 'platform_admin' || role === 'company_admin';
  const canCreateCompany = role === 'platform_admin';

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

  async function submitCreate() {
    if (!token) return;
    const values = await createForm.validateFields();
    const payload: CreateCompanyFormValues = {
      name: values.name,
      admin_username: values.admin_username,
      admin_name: values.admin_name,
      admin_password: values.admin_password,
      admin_display_name: values.admin_display_name,
      must_change_password: values.must_change_password !== false,
    };
    const local = validateCreateCompanyForm(payload);
    if (!local.valid) {
      message.error(local.issues[0]?.message || '请完整填写');
      return;
    }
    setCreating(true);
    try {
      const created = await createCompany(request, token, payload);
      message.success(`已开通 ${created.company.name}（${created.company.id}），管理员 ${created.admin.id}`);
      setCreateOpen(false);
      createForm.resetFields();
      await load();
    } catch (err) {
      message.error(userFacingMessage(err));
    } finally {
      setCreating(false);
    }
  }

  const columns: ColumnsType<CompanySummary> = [
    { title: '公司', key: 'name', render: (_: unknown, row: CompanySummary) => (
      <Space direction="vertical" size={0}>
        {onNavigate
          ? <Button type="link" style={{ padding: 0, height: 'auto' }} data-testid={`company-open-${row.id}`}
              onClick={() => onNavigate(companyDetailPath(row.id))}><Text strong>{row.name}</Text></Button>
          : <Text strong>{row.name}</Text>}
        <Text type="secondary" style={{ fontSize: 12 }}>{row.id}</Text>
      </Space>
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
        <Space wrap>
          {canCreateCompany && (
            <Button type="primary" icon={<PlusOutlined />} data-testid="company-create-open"
              onClick={() => {
                createForm.setFieldsValue({ must_change_password: true });
                setCreateOpen(true);
              }}>新建公司</Button>
          )}
          {canConfigureServices && (
            <>
              <Button data-testid="open-model-config-modal-btn" icon={<ThunderboltOutlined />} onClick={() => setModelOpen(true)}>模型配置</Button>
              <Button data-testid="open-ragflow-config-modal-btn" icon={<DatabaseOutlined />} onClick={() => setRagflowOpen(true)}>知识库服务</Button>
            </>
          )}
        </Space>
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

      <Modal title="新建公司" open={createOpen} onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        okText="开通" confirmLoading={creating} onOk={() => void submitCreate()}
        okButtonProps={{ 'data-testid': 'company-create-submit' } as never} destroyOnClose>
        <Form form={createForm} layout="vertical" initialValues={{ must_change_password: true }}>
          <Form.Item name="name" label="公司显示名" rules={[{ required: true, message: '请填写公司显示名' }]}>
            <Input data-testid="company-create-name" />
          </Form.Item>
          <Form.Item name="admin_username" label="管理员用户名" rules={[{ required: true, message: '请填写管理员用户名' }]}>
            <Input data-testid="company-create-admin-username" autoComplete="off" />
          </Form.Item>
          <Form.Item name="admin_name" label="管理员姓名" rules={[{ required: true, message: '请填写管理员姓名' }]}>
            <Input data-testid="company-create-admin-name" />
          </Form.Item>
          <Form.Item name="admin_display_name" label="管理员显示名">
            <Input data-testid="company-create-admin-display-name" />
          </Form.Item>
          <Form.Item name="admin_password" label="初始密码" rules={[{ required: true, message: '请填写初始密码' }]}>
            <Input.Password data-testid="company-create-admin-password" autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="must_change_password" valuePropName="checked">
            <Checkbox data-testid="company-create-must-change">首次登录强制改密</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <ModelConfigModal open={modelOpen} onClose={() => setModelOpen(false)} session={session} />
      <RagflowConfigModal open={ragflowOpen} onClose={() => setRagflowOpen(false)} session={session} />
    </div>
  );
}

export default CompanyManagePage;
