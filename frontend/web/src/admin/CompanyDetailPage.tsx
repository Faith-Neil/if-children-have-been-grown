// 为什么有这个文件：ISSUE-052 公司详情——按公司查看并添加管理员/成员。
// 它解决什么问题：平台管理员点进公司管理该公司全部账号；公司管理员只管本公司成员。

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, App as AntApp, Button, Checkbox, Form, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Account, ApplicationSession } from '../shared/types';
import { userFacingMessage } from '../shared/api';
import { createUser, fetchUsers, type ApiUserModel } from './user-management-api';
import { listCompanies, type CompanySummary } from './company-manage-core';
import { request } from '../shared/api';
import { normalizeSystemRole } from '../shell/route-guard';

const { Title, Text } = Typography;

interface CompanyDetailPageProps {
  companyId: string;
  session?: ApplicationSession | null;
  currentUser?: Account | null;
  token?: string | null;
  onBack: () => void;
}

interface AddUserForm {
  username: string;
  name: string;
  display_name?: string;
  password: string;
  role: 'company_admin' | 'member';
  must_change_password: boolean;
}

export function CompanyDetailPage({ companyId, session, currentUser, token, onBack }: CompanyDetailPageProps) {
  const { message } = AntApp.useApp();
  const role = normalizeSystemRole(session?.user?.primary_role || currentUser?.role);
  const [company, setCompany] = useState<CompanySummary | null>(null);
  const [users, setUsers] = useState<ApiUserModel[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<AddUserForm>();

  const canAddAdmin = role === 'platform_admin';
  const canAdd = role === 'platform_admin' || role === 'company_admin';

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const listed = await listCompanies(request, token);
      const row = listed.items.find(item => item.id === companyId) ?? null;
      if (!row) {
        setCompany(null);
        setUsers([]);
        setError('未找到该公司。');
        return;
      }
      setCompany(row);
      const listedUsers = await fetchUsers({ companyId }, token);
      setUsers(listedUsers.items);
      setError(null);
    } catch (err) {
      setError(userFacingMessage(err));
    } finally {
      setLoading(false);
    }
  }, [token, companyId]);

  useEffect(() => { void load(); }, [load]);

  const roleOptions = useMemo(() => (
    canAddAdmin
      ? [
          { value: 'company_admin', label: '公司管理员' },
          { value: 'member', label: '普通成员' },
        ]
      : [{ value: 'member', label: '普通成员' }]
  ), [canAddAdmin]);

  async function submitAdd() {
    if (!token || !company) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      await createUser({
        username: values.username.trim(),
        name: values.name.trim(),
        display_name: (values.display_name || '').trim() || undefined,
        company_id: company.id,
        role: canAddAdmin ? values.role : 'member',
        password: values.password,
        must_change_password: values.must_change_password !== false,
      }, token);
      message.success(`已添加 ${values.username.trim()}`);
      setAddOpen(false);
      form.resetFields();
      await load();
    } catch (err) {
      message.error(userFacingMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const columns: ColumnsType<ApiUserModel> = [
    { title: '账号', dataIndex: 'id', key: 'id' },
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '显示名', dataIndex: 'display_name', key: 'display_name' },
    { title: '角色', dataIndex: 'role', key: 'role', width: 140,
      render: (value: string) => value === 'company_admin' ? '公司管理员' : value === 'member' ? '普通成员' : value },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (value: string) => <Tag color={value === 'active' ? 'success' : 'default'}>{value}</Tag> },
    { title: '待改密', key: 'must_change', width: 90,
      render: (_: unknown, row: ApiUserModel) => (row as ApiUserModel & { must_change_password?: boolean }).must_change_password ? '是' : '—' },
  ];

  return (
    <div className="company-detail-page" style={{ paddingBottom: 32 }} data-testid="company-detail-page">
      <Space style={{ marginBottom: 16 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={onBack} data-testid="company-detail-back">返回</Button>
      </Space>
      {company ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>{company.name}</Title>
            <Text type="secondary">{company.id} · {company.status === 'active' ? '启用' : '已停用'}</Text>
          </div>
          {canAdd && (
            <Button type="primary" icon={<PlusOutlined />} data-testid="company-detail-add-open"
              onClick={() => {
                form.setFieldsValue({ role: 'member', must_change_password: true });
                setAddOpen(true);
              }}>添加账号</Button>
          )}
        </div>
      ) : <Title level={4} style={{ marginBottom: 16 }}>公司详情</Title>}

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => void load()}>重试</Button>} />}

      <Table<ApiUserModel> rowKey="id" size="middle" loading={loading} dataSource={users}
        columns={columns} pagination={false} data-testid="company-users-table" />

      <Modal title="添加账号" open={addOpen} onCancel={() => { setAddOpen(false); form.resetFields(); }}
        okText="添加" confirmLoading={saving} onOk={() => void submitAdd()}
        okButtonProps={{ 'data-testid': 'company-detail-add-submit' } as never} destroyOnClose>
        <Form form={form} layout="vertical" initialValues={{ role: 'member', must_change_password: true }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请填写用户名' }]}>
            <Input data-testid="company-detail-username" autoComplete="off" />
          </Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请填写姓名' }]}>
            <Input data-testid="company-detail-name" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名">
            <Input data-testid="company-detail-display-name" />
          </Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true, message: '请填写初始密码' }]}>
            <Input.Password data-testid="company-detail-password" autoComplete="new-password" />
          </Form.Item>
          {canAddAdmin && (
            <Form.Item name="role" label="角色" rules={[{ required: true }]}>
              <Select options={roleOptions} data-testid="company-detail-role" />
            </Form.Item>
          )}
          <Form.Item name="must_change_password" valuePropName="checked">
            <Checkbox data-testid="company-detail-must-change">首次登录强制改密</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default CompanyDetailPage;
