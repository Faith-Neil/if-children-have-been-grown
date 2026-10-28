// 为什么有这个文件：落实 APP-M2-T027 (A-02 用户与角色管理、新增与停用前转交安全表单)。
// 它解决什么问题：呈现多租户用户与 8 大标准 RBAC 角色列表、新增用户及公司密码策略即时强校验、停用前业务资产强制转交抽屉（交接约束 M1-P10-F2 未转交阻断停用）、“账号安全设置”面板（密码策略只能调严不能调宽），践行 Layout First 交互设计规范。

import { useMemo, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FolderOpenOutlined,
  InfoCircleOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  StopOutlined,
  SwapOutlined,
  UserAddOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from '../shared/types.ts';
import { SYSTEM_ROLE_LABELS, type SystemRole } from '../shared/roles.ts';
import {
  checkUserManagementPermission,
  countPasswordCharClasses,
  DEFAULT_COMPANY_PASSWORD_POLICY,
  executeUserHandoverAndDisable,
  filterUsersList,
  formatAssetSummary,
  hasActiveAssets,
  INITIAL_USERS,
  PLATFORM_PASSWORD_BASELINE,
  validateCompanyPasswordPolicy,
  validateHandoverBeforeDisable,
  validateNewUserForm,
  validatePasswordStrength,
  type CompanyPasswordPolicy,
  type NewUserFormData,
  type UserHandoverRecord,
  type UserItem,
} from './user-management-core.ts';

const { Title, Text, Paragraph } = Typography;

export interface UsersPageProps {
  session?: ApplicationSession | null;
  currentUser?: Account | null;
  onNavigate?: (path: string) => void;
}

export function UsersPage({ session, currentUser }: UsersPageProps) {
  const { message } = AntApp.useApp();

  // 1. 会话与当前角色权限
  const currentRole = currentUser?.role || session?.user?.role;
  const currentCompanyId = currentUser?.company_id || session?.scope.active_company_id || 'alpha';
  const permission = useMemo(() => checkUserManagementPermission(currentRole), [currentRole]);
  const isPlatformAdmin = permission.role === 'platform_admin';

  // 2. 用户状态集与公司密码策略
  const [users, setUsers] = useState<UserItem[]>(INITIAL_USERS);
  const [passwordPolicy, setPasswordPolicy] = useState<CompanyPasswordPolicy>(DEFAULT_COMPANY_PASSWORD_POLICY);
  const [handoverLogs, setHandoverLogs] = useState<UserHandoverRecord[]>([]);

  // 3. 筛选过滤状态
  const [keyword, setKeyword] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedCompany, setSelectedCompany] = useState<string>('all');

  // 4. 新增用户 Modal 状态
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [addForm] = Form.useForm<NewUserFormData>();
  const [formPasswordValue, setFormPasswordValue] = useState<string>('');

  // 5. 资产交接 Drawer 状态
  const [isHandoverDrawerOpen, setIsHandoverDrawerOpen] = useState<boolean>(false);
  const [handoverSourceUser, setHandoverSourceUser] = useState<UserItem | null>(null);
  const [handoverTargetUserId, setHandoverTargetUserId] = useState<string>('');
  const [handoverReason, setHandoverReason] = useState<string>('');

  // 6. 公司密码策略 Drawer 状态
  const [isPolicyDrawerOpen, setIsPolicyDrawerOpen] = useState<boolean>(false);
  const [policyForm] = Form.useForm<CompanyPasswordPolicy>();

  // 计算过滤后的用户列表
  const filteredUsers = useMemo(() => {
    return filterUsersList(
      users,
      {
        keyword,
        role: selectedRole,
        status: selectedStatus,
        companyId: selectedCompany,
      },
      currentCompanyId,
      isPlatformAdmin
    );
  }, [users, keyword, selectedRole, selectedStatus, selectedCompany, currentCompanyId, isPlatformAdmin]);

  // 统计概览指标
  const stats = useMemo(() => {
    const scopedUsers = isPlatformAdmin ? users : users.filter(u => u.company_id === currentCompanyId);
    const activeCount = scopedUsers.filter(u => u.status === 'active').length;
    const disabledCount = scopedUsers.filter(u => u.status === 'disabled').length;
    const totalAssetsHeld = scopedUsers.reduce((acc, u) => {
      return (
        acc +
        (u.assigned_assets.active_projects?.length || 0) +
        (u.assigned_assets.active_chapters?.length || 0) +
        (u.assigned_assets.kb_items?.length || 0)
      );
    }, 0);
    return {
      total: scopedUsers.length,
      active: activeCount,
      disabled: disabledCount,
      totalAssetsHeld,
    };
  }, [users, currentCompanyId, isPlatformAdmin]);

  // 候选资产接收人（同公司、正常在职、非待交接用户本人）
  const eligibleHandoverTargets = useMemo(() => {
    if (!handoverSourceUser) return [];
    return users.filter(
      u =>
        u.company_id === handoverSourceUser.company_id &&
        u.id !== handoverSourceUser.id &&
        u.status === 'active'
    );
  }, [users, handoverSourceUser]);

  // 处理新增用户提交
  const handleAddUserSubmit = async () => {
    try {
      const values = await addForm.validateFields();
      const validation = validateNewUserForm(values, users, passwordPolicy);
      if (!validation.valid) {
        message.error(validation.message || '用户参数校验失败');
        return;
      }

      const newUser: UserItem = {
        id: `u_${Date.now()}`,
        username: values.username.trim(),
        name: values.name.trim(),
        role: values.role,
        company_id: isPlatformAdmin ? values.company_id || currentCompanyId : currentCompanyId,
        status: 'active',
        created_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
        assigned_assets: {
          active_projects: [],
          active_chapters: [],
          kb_items: [],
        },
      };

      setUsers(prev => [newUser, ...prev]);
      message.success(`成功创建用户 "${newUser.name} (${newUser.username})"`);
      setIsAddModalOpen(false);
      addForm.resetFields();
      setFormPasswordValue('');
    } catch {
      // Form validation error handled by antd
    }
  };

  // 打开交接抽屉
  const handleOpenHandoverDrawer = (user: UserItem) => {
    if (permission.isReadOnly) {
      message.warning('当前为只读模式，无权执行停用与资产转交操作。');
      return;
    }
    setHandoverSourceUser(user);
    setHandoverTargetUserId('');
    setHandoverReason('');
    setIsHandoverDrawerOpen(true);
  };

  // 执行资产转交并停用
  const handleConfirmHandoverAndDisable = () => {
    if (!handoverSourceUser) return;

    const validation = validateHandoverBeforeDisable({
      sourceUser: handoverSourceUser,
      targetUserId: handoverTargetUserId,
      reason: handoverReason,
      availableUsers: users,
    });

    if (!validation.valid) {
      message.error(validation.message || '交接信息不满足合规要求');
      return;
    }

    const { updatedUsers, handoverRecord } = executeUserHandoverAndDisable({
      users,
      sourceUserId: handoverSourceUser.id,
      targetUserId: handoverTargetUserId,
      reason: handoverReason,
      operatorId: currentUser?.id || 'admin',
    });

    setUsers(updatedUsers);
    setHandoverLogs(prev => [handoverRecord, ...prev]);
    message.success(
      `已成功将 ${handoverRecord.transferred_projects_count} 个项目、${handoverRecord.transferred_chapters_count} 篇章节及 ${handoverRecord.transferred_kb_count} 项资料转交给 ${handoverRecord.target_username}，用户 ${handoverRecord.source_username} 已停用。`
    );
    setIsHandoverDrawerOpen(false);
    setHandoverSourceUser(null);
  };

  // 无资产用户直接停用
  const handleDirectDisable = (user: UserItem) => {
    if (permission.isReadOnly) {
      message.warning('当前为只读模式，无权停用账号。');
      return;
    }
    if (hasActiveAssets(user.assigned_assets)) {
      message.error('该用户持有未完结业务资产，严禁直接停用！请通过资产转交流程操作。');
      handleOpenHandoverDrawer(user);
      return;
    }

    setUsers(prev =>
      prev.map(u => (u.id === user.id ? { ...u, status: 'disabled' as const } : u))
    );
    message.success(`用户 "${user.name}" 已成功停用。`);
  };

  // 启用用户
  const handleEnableUser = (user: UserItem) => {
    if (permission.isReadOnly) {
      message.warning('当前为只读模式，无权启用账号。');
      return;
    }
    setUsers(prev =>
      prev.map(u => (u.id === user.id ? { ...u, status: 'active' as const } : u))
    );
    message.success(`用户 "${user.name}" 已恢复正常状态。`);
  };

  // 保存公司密码策略
  const handleSavePolicy = async () => {
    try {
      const values = await policyForm.validateFields();
      const validation = validateCompanyPasswordPolicy(values);
      if (!validation.valid) {
        message.error(validation.issues[0] || '密码策略不合规');
        return;
      }

      setPasswordPolicy({
        ...passwordPolicy,
        ...values,
      });
      message.success('公司密码安全策略已成功更新（只能调严不能调宽）。已有账号在下次改密时强制生效。');
      setIsPolicyDrawerOpen(false);
    } catch {
      // Form validation error
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '登录账号',
      dataIndex: 'username',
      key: 'username',
      render: (val: string) => <Text strong>{val}</Text>,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '系统角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: SystemRole) => {
        const label = SYSTEM_ROLE_LABELS[role] || role;
        const colorMap: Record<string, string> = {
          platform_admin: 'magenta',
          company_admin: 'geekblue',
          project_lead: 'blue',
          bid_writer: 'cyan',
          auditor: 'green',
          data_admin: 'gold',
          viewer: 'default',
        };
        return <Tag color={colorMap[role] || 'blue'}>{label}</Tag>;
      },
    },
    {
      title: '所属企业',
      dataIndex: 'company_id',
      key: 'company_id',
      render: (company: string) => <Tag>{company.toUpperCase()}</Tag>,
    },
    {
      title: '账号状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        if (status === 'active') {
          return <Badge status="success" text="正常在职" />;
        }
        if (status === 'locked') {
          return <Badge status="warning" text="已锁定" />;
        }
        return <Badge status="error" text="已停用" />;
      },
    },
    {
      title: '负责业务资产',
      dataIndex: 'assigned_assets',
      key: 'assigned_assets',
      render: (_: unknown, record: UserItem) => {
        const hasAssets = hasActiveAssets(record.assigned_assets);
        const summary = formatAssetSummary(record.assigned_assets);
        if (hasAssets) {
          return (
            <Tag color="orange" icon={<FolderOpenOutlined />}>
              {summary}
            </Tag>
          );
        }
        return <Text type="secondary">{summary}</Text>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => <Text type="secondary">{val}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserItem) => {
        const isSelf = record.id === currentUser?.id || record.username === currentUser?.name;
        if (record.status === 'active') {
          const hasAssets = hasActiveAssets(record.assigned_assets);
          if (hasAssets) {
            return (
              <Button
                type="link"
                danger
                icon={<SwapOutlined />}
                disabled={permission.isReadOnly || isSelf}
                onClick={() => handleOpenHandoverDrawer(record)}
                data-testid={`user-disable-btn-${record.id}`}
              >
                转交并停用
              </Button>
            );
          }
          return (
            <Popconfirm
              title="停用确认"
              description={`确认停用用户 "${record.name}"？该用户名下无进行中业务资产。`}
              onConfirm={() => handleDirectDisable(record)}
              okText="确认停用"
              cancelText="取消"
              disabled={permission.isReadOnly || isSelf}
            >
              <Button
                type="link"
                danger
                icon={<StopOutlined />}
                disabled={permission.isReadOnly || isSelf}
                data-testid={`user-disable-btn-${record.id}`}
              >
                停用
              </Button>
            </Popconfirm>
          );
        }

        return (
          <Button
            type="link"
            icon={<CheckCircleOutlined />}
            disabled={permission.isReadOnly}
            onClick={() => handleEnableUser(record)}
            data-testid={`user-enable-btn-${record.id}`}
          >
            启用
          </Button>
        );
      },
    },
  ];

  return (
    <div className="users-management-page" style={{ padding: '0 4px' }}>
      {/* 顶部概览卡片 (Layout First) */}
      <Card
        data-testid="user-management-overview"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <UserOutlined />
            <span>A-02 用户与角色管理</span>
            <Tag color={permission.canOperate ? 'green' : 'orange'} data-testid="user-permission-tag">
              {permission.roleLabel} · {permission.canOperate ? '读写管理' : '纯只读'}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<SafetyCertificateOutlined />}
              onClick={() => {
                policyForm.setFieldsValue(passwordPolicy);
                setIsPolicyDrawerOpen(true);
              }}
              data-testid="user-security-policy-btn"
            >
              账号安全策略
            </Button>
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              disabled={permission.isReadOnly}
              onClick={() => {
                addForm.resetFields();
                addForm.setFieldsValue({
                  role: 'bid_writer',
                  company_id: currentCompanyId,
                });
                setFormPasswordValue('');
                setIsAddModalOpen(true);
              }}
              data-testid="user-add-btn"
            >
              新增用户
            </Button>
          </Space>
        }
      >
        <Row gutter={[24, 16]}>
          <Col xs={12} sm={6}>
            <Statistic title="总用户数" value={stats.total} suffix="人" />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="正常在职"
              value={stats.active}
              valueStyle={{ color: '#3f8600' }}
              suffix="人"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="已停用"
              value={stats.disabled}
              valueStyle={{ color: '#cf1322' }}
              suffix="人"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="当前密码策略"
              value={`≥${passwordPolicy.password_min_length}位 · ${passwordPolicy.password_min_char_classes}类字符`}
              valueStyle={{ fontSize: 16, color: '#1677ff' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 只读模式警告条 */}
      {permission.isReadOnly && (
        <Alert
          data-testid="user-readonly-alert"
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="只读模式"
          description={permission.readOnlyNotice}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 筛选与检索工具栏 (Layout First) */}
      <Card data-testid="user-filter-bar" style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="搜索账号或姓名..."
              prefix={<SearchOutlined />}
              allowClear
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              data-testid="user-search-input"
            />
          </Col>
          <Col xs={12} sm={8} md={5}>
            <Select
              style={{ width: '100%' }}
              value={selectedRole}
              onChange={val => setSelectedRole(val)}
              data-testid="user-role-filter"
            >
              <Select.Option value="all">全部系统角色</Select.Option>
              {Object.entries(SYSTEM_ROLE_LABELS).map(([code, label]) => (
                <Select.Option key={code} value={code}>
                  {label}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select
              style={{ width: '100%' }}
              value={selectedStatus}
              onChange={val => setSelectedStatus(val)}
              data-testid="user-status-filter"
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="active">正常在职</Select.Option>
              <Select.Option value="disabled">已停用</Select.Option>
            </Select>
          </Col>
          {isPlatformAdmin && (
            <Col xs={12} sm={8} md={5}>
              <Select
                style={{ width: '100%' }}
                value={selectedCompany}
                onChange={val => setSelectedCompany(val)}
                data-testid="user-company-filter"
              >
                <Select.Option value="all">全部租户公司</Select.Option>
                <Select.Option value="alpha">Alpha 科技</Select.Option>
                <Select.Option value="beta">Beta 工业</Select.Option>
                <Select.Option value="system">系统管理空间</Select.Option>
              </Select>
            </Col>
          )}
          <Col xs={12} sm={8} md={4}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                setKeyword('');
                setSelectedRole('all');
                setSelectedStatus('all');
                setSelectedCompany('all');
              }}
              data-testid="user-filter-reset-btn"
            >
              重置筛选
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 用户列表 Table */}
      <Card bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          dataSource={filteredUsers}
          columns={columns}
          pagination={{ pageSize: 8, showTotal: t => `共 ${t} 名用户` }}
          data-testid="user-table"
        />
      </Card>

      {/* 新增用户 Modal */}
      <Modal
        title="新增系统用户"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        onOk={handleAddUserSubmit}
        okText="确认创建"
        cancelText="取消"
        data-testid="user-add-modal"
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" preserve={false}>
          <Form.Item
            name="username"
            label="登录账号"
            rules={[{ required: true, message: '请输入登录账号' }]}
          >
            <Input
              placeholder="3~32 位字母、数字或下划线"
              prefix={<UserOutlined />}
              data-testid="user-form-username"
            />
          </Form.Item>
          <Form.Item
            name="name"
            label="中文姓名"
            rules={[{ required: true, message: '请输入真实中文姓名' }]}
          >
            <Input placeholder="例如：李华" data-testid="user-form-name" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="role"
                label="系统角色"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select data-testid="user-form-role">
                  {Object.entries(SYSTEM_ROLE_LABELS).map(([code, label]) => (
                    <Select.Option key={code} value={code}>
                      {label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="company_id"
                label="所属租户"
                rules={[{ required: true, message: '请选择企业' }]}
              >
                {isPlatformAdmin ? (
                  <Select data-testid="user-form-company">
                    <Select.Option value="alpha">Alpha 科技</Select.Option>
                    <Select.Option value="beta">Beta 工业</Select.Option>
                    <Select.Option value="system">系统空间</Select.Option>
                  </Select>
                ) : (
                  <Input disabled value={currentCompanyId} data-testid="user-form-company" />
                )}
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="password"
            label={
              <Space>
                <span>初始登录密码</span>
                <Tag color="blue">
                  策略：≥{passwordPolicy.password_min_length}位 · {passwordPolicy.password_min_char_classes}类字符
                </Tag>
              </Space>
            }
            rules={[{ required: true, message: '请输入初始密码' }]}
            help={
              formPasswordValue ? (
                (() => {
                  const res = validatePasswordStrength(formPasswordValue, passwordPolicy);
                  return (
                    <Text type={res.valid ? 'success' : 'danger'}>
                      {res.valid
                        ? `密码强度合规（命中 ${res.charClassCount} 类字符）`
                        : res.message}
                    </Text>
                  );
                })()
              ) : (
                <Text type="secondary">
                  须同时包含大写字母、小写字母、数字、特殊符号中的至少 {passwordPolicy.password_min_char_classes} 类
                </Text>
              )
            }
          >
            <Input.Password
              placeholder="请输入符合安全策略的初始密码"
              prefix={<LockOutlined />}
              onChange={e => setFormPasswordValue(e.target.value)}
              data-testid="user-form-password"
            />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="确认初始密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请再次输入密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              placeholder="请再次确认初始密码"
              prefix={<LockOutlined />}
              data-testid="user-form-confirm-password"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 停用前资产强制转交 Drawer (交接约束 M1-P10-F2 红线门禁) */}
      <Drawer
        title="停用前业务资产强制交接"
        width={560}
        open={isHandoverDrawerOpen}
        onClose={() => setIsHandoverDrawerOpen(false)}
        data-testid="user-handover-drawer"
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setIsHandoverDrawerOpen(false)}>取消</Button>
            <Button
              type="primary"
              danger
              onClick={handleConfirmHandoverAndDisable}
              data-testid="handover-confirm-btn"
            >
              确认转交并停用该账号
            </Button>
          </Space>
        }
      >
        {handoverSourceUser && (
          <div>
            <Alert
              data-testid="handover-warning-alert"
              type="warning"
              showIcon
              icon={<ExclamationCircleOutlined />}
              message="合规红线门禁：未交接资产前阻断停用"
              description={`用户 "${handoverSourceUser.name} (${handoverSourceUser.username})" 当前持有未完结业务资产。根据系统资产安全规范，停用前必须将全部项目与章节转交同公司成员。`}
              style={{ marginBottom: 16 }}
            />

            <Descriptions title="待停用用户资料" size="small" bordered column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="账号">{handoverSourceUser.username}</Descriptions.Item>
              <Descriptions.Item label="姓名">{handoverSourceUser.name}</Descriptions.Item>
              <Descriptions.Item label="系统角色">
                {SYSTEM_ROLE_LABELS[handoverSourceUser.role] || handoverSourceUser.role}
              </Descriptions.Item>
              <Descriptions.Item label="所属企业">{handoverSourceUser.company_id.toUpperCase()}</Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">待移交业务资产明细清单</Divider>

            {handoverSourceUser.assigned_assets.active_projects?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text strong>负责项目 ({handoverSourceUser.assigned_assets.active_projects.length} 项)：</Text>
                <List
                  size="small"
                  bordered
                  dataSource={handoverSourceUser.assigned_assets.active_projects}
                  renderItem={item => (
                    <List.Item>
                      <Space>
                        <Tag color="blue">{item.role_in_project}</Tag>
                        <span>{item.name}</span>
                      </Space>
                    </List.Item>
                  )}
                  style={{ marginTop: 4 }}
                />
              </div>
            )}

            {handoverSourceUser.assigned_assets.active_chapters?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text strong>在编章节 ({handoverSourceUser.assigned_assets.active_chapters.length} 篇)：</Text>
                <List
                  size="small"
                  bordered
                  dataSource={handoverSourceUser.assigned_assets.active_chapters}
                  renderItem={item => (
                    <List.Item>
                      <Space>
                        <Tag color="cyan">{item.project_name}</Tag>
                        <span>{item.title}</span>
                      </Space>
                    </List.Item>
                  )}
                  style={{ marginTop: 4 }}
                />
              </div>
            )}

            {handoverSourceUser.assigned_assets.kb_items?.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>负责资料条目 ({handoverSourceUser.assigned_assets.kb_items.length} 条)：</Text>
                <List
                  size="small"
                  bordered
                  dataSource={handoverSourceUser.assigned_assets.kb_items}
                  renderItem={item => (
                    <List.Item>
                      <Space>
                        <Tag color="gold">{item.category}</Tag>
                        <span>{item.title}</span>
                      </Space>
                    </List.Item>
                  )}
                  style={{ marginTop: 4 }}
                />
              </div>
            )}

            <Divider orientation="left">指定资产接收人与交接说明</Divider>

            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ display: 'block', marginBottom: 6 }}>
                选择资产接收人（同公司在职成员）：
              </Text>
              <Select
                style={{ width: '100%' }}
                placeholder="请选择同公司合格的资产接收成员..."
                value={handoverTargetUserId || undefined}
                onChange={val => setHandoverTargetUserId(val)}
                data-testid="handover-target-select"
              >
                {eligibleHandoverTargets.map(target => (
                  <Select.Option key={target.id} value={target.id}>
                    {target.name} ({target.username}) - {SYSTEM_ROLE_LABELS[target.role]}
                  </Select.Option>
                ))}
              </Select>
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 6 }}>
                交接理由（不少于 5 个字，记入合规审计日志）：
              </Text>
              <Input.TextArea
                rows={3}
                placeholder="请输入详细的资产转交与账号停用原因..."
                value={handoverReason}
                onChange={e => setHandoverReason(e.target.value)}
                data-testid="handover-reason-input"
              />
            </div>
          </div>
        )}
      </Drawer>

      {/* 公司密码安全策略 Drawer (PRD §5.10.2 / Q28 定案：公司设置只能调严) */}
      <Drawer
        title="公司账号密码安全策略"
        width={480}
        open={isPolicyDrawerOpen}
        onClose={() => setIsPolicyDrawerOpen(false)}
        data-testid="user-security-policy-drawer"
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setIsPolicyDrawerOpen(false)}>取消</Button>
            <Button
              type="primary"
              disabled={permission.isReadOnly}
              onClick={handleSavePolicy}
              data-testid="security-policy-save-btn"
            >
              保存策略
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          icon={<SafetyCertificateOutlined />}
          message="平台底线与调严规则"
          description="公司管理员可根据企业安全合规要求调严密码策略，但严禁宽于平台基线（长度至少 8 位，字符种类至少 3 类）。新规则在账号下次修改密码时生效。"
          style={{ marginBottom: 16 }}
        />

        <Form form={policyForm} layout="vertical" initialValues={passwordPolicy}>
          <Form.Item
            name="password_min_length"
            label={
              <Space>
                <span>密码最少位数</span>
                <Tag color="blue">平台底线: {PLATFORM_PASSWORD_BASELINE.MIN_LENGTH} 位</Tag>
              </Space>
            }
            rules={[
              { required: true, message: '请输入最小长度' },
              {
                type: 'number',
                min: PLATFORM_PASSWORD_BASELINE.MIN_LENGTH,
                message: `公司只能调严，不可低于平台基线 ${PLATFORM_PASSWORD_BASELINE.MIN_LENGTH} 位`,
              },
            ]}
            extra="范围 8~32 位。各公司可以调高（例如 12 位及以上），不能低于平台默认值。"
          >
            <InputNumber
              min={PLATFORM_PASSWORD_BASELINE.MIN_LENGTH}
              max={32}
              style={{ width: '100%' }}
              disabled={permission.isReadOnly}
              data-testid="policy-min-length-input"
            />
          </Form.Item>

          <Form.Item
            name="password_min_char_classes"
            label={
              <Space>
                <span>至少包含字符类数</span>
                <Tag color="blue">平台底线: {PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES} 类</Tag>
              </Space>
            }
            rules={[
              { required: true, message: '请选择字符种类' },
              {
                type: 'number',
                min: PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES,
                message: `公司只能调严，不可低于平台基线 ${PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES} 类`,
              },
            ]}
            extra="字符类别包含：大写字母、小写字母、数字、特殊符号。默认为 3 类，可选 4 类全含。"
          >
            <Select disabled={permission.isReadOnly} data-testid="policy-min-classes-select">
              <Select.Option value={3}>3 类（任意包含其中三类）</Select.Option>
              <Select.Option value={4}>4 类（大写、小写、数字、符号四类全含）</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="max_login_attempts"
            label={
              <Space>
                <span>连续失败锁定阈值</span>
                <Tag color="blue">平台上限: {PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS} 次</Tag>
              </Space>
            }
            rules={[
              { required: true, message: '请输入失败锁定次数' },
              {
                type: 'number',
                max: PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS,
                message: `公司只能调严，不可高于平台上限 ${PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS} 次`,
              },
            ]}
            extra="达到失败次数后临时锁定账号防暴力破解（默认 5 次，可调严为 3 次等）。"
          >
            <InputNumber
              min={1}
              max={PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS}
              style={{ width: '100%' }}
              disabled={permission.isReadOnly}
              data-testid="policy-max-attempts-input"
            />
          </Form.Item>

          <Form.Item
            name="lockout_minutes"
            label="锁定时间 (分钟)"
            rules={[{ required: true, message: '请输入锁定时间' }]}
            extra="锁定后自动解锁或需管理员手动解锁等待时间（分钟）。"
          >
            <InputNumber min={5} max={60} style={{ width: '100%' }} disabled={permission.isReadOnly} />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}
