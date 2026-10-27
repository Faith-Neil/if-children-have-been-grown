// 为什么有这个文件：落实 APP-M2-T024 (A-03 字典配置页) 与 PRD v1.8 §5.10.3、§6.9 规范。
// 它解决什么问题：
// 1. 集中调阅与管理 6 大核心业务状态码表与全量业务字段元数据；
// 2. 复用 StatusTag 组件提供全站统一的真实标签视觉呈现；
// 3. 严格落实“已使用代码只能停用，不可直接硬删除”安全红线；
// 4. 实现平台管理员/公司管理员与只读角色的精细化权限隔离与自适应控制；
// 5. 遵循 Layout First 克制原则，以清晰的卡片分栏、表格与操作反馈表达功能。

import React, { useMemo, useState } from 'react';
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
  Empty,
  Input,
  Modal,
  Popconfirm,
  Radio,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CheckCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  LockOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from '../shared/types.ts';
import { StatusTag } from '../shared/StatusTag.tsx';
import {
  buildInitialDictItems,
  checkDictPermission,
  computeCategorySummaries,
  filterDictItems,
  toggleDictItemActive,
  validateCodeDeactivation,
  type DictFilterParams,
  type DictItem,
} from './dict-config-core.ts';

const { Text, Paragraph, Title } = Typography;

export interface DictConfigPageProps {
  session?: ApplicationSession | null;
  currentUser?: Account;
  onNavigate?: (path: string) => void;
}

export const DictConfigPage: React.FC<DictConfigPageProps> = ({
  session,
  currentUser,
}) => {
  const { message } = AntApp.useApp?.() ?? {
    message: {
      success: (msg: string) => console.log('success:', msg),
      error: (msg: string) => console.error('error:', msg),
      info: (msg: string) => console.log('info:', msg),
      warning: (msg: string) => console.warn('warning:', msg),
    },
  };

  // 1. 角色感知与权限判定
  const userRole = session?.user?.primary_role || session?.user?.role || currentUser?.role;
  const permission = useMemo(() => checkDictPermission(userRole), [userRole]);

  // 2. 字典数据状态
  const [items, setItems] = useState<DictItem[]>(() => buildInitialDictItems());
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

  // 3. 详情抽屉
  const [detailItem, setDetailItem] = useState<DictItem | null>(null);

  // 4. 数据计算与统计
  const categorySummaries = useMemo(() => computeCategorySummaries(items), [items]);

  const filteredItems = useMemo(() => {
    return filterDictItems(items, {
      category: selectedCategory,
      keyword: searchKeyword,
      statusFilter,
    });
  }, [items, selectedCategory, searchKeyword, statusFilter]);

  const stats = useMemo(() => {
    const total = items.length;
    const active = items.filter(i => i.isActive).length;
    const inUse = items.filter(i => i.isInUse).length;
    const statusCodes = items.filter(i => !!i.domain).length;
    return { total, active, inUse, statusCodes };
  }, [items]);

  // 5. 停用 / 启用状态切换处理
  const handleToggleActive = (item: DictItem, targetActive: boolean) => {
    if (!permission.canToggleStatus) {
      message.error('当前用户为只读权限，无法修改字典代码状态');
      return;
    }

    const res = toggleDictItemActive(items, item.id, targetActive);
    if (res.error) {
      message.error(res.error);
      return;
    }

    setItems(res.updatedItems);
    if (detailItem && detailItem.id === item.id) {
      setDetailItem(res.modifiedItem);
    }
    message.success(
      targetActive
        ? `代码【${item.code}】已成功启用`
        : `代码【${item.code}】已成功停用（保留历史数据一致性）`
    );
  };

  // 6. 硬删除拦截（规则红线：已使用代码只能停用，不可直接硬删除）
  const handleAttemptHardDelete = (item: DictItem) => {
    const check = validateCodeDeactivation(item);
    if (!check.canHardDelete) {
      Modal.warning({
        title: '不可删除受保护代码',
        icon: <ExclamationCircleOutlined style={{ color: '#d9363e' }} />,
        content: (
          <div>
            <Paragraph strong style={{ color: '#d9363e' }}>
              {check.reason}
            </Paragraph>
            <Paragraph type="secondary">
              代码 <code>{item.code}</code> 已在生产环境业务（项目、章节、长任务或检查项）中使用。直接物理删除会导致历史标书、审计日志与版本快照数据损坏。请采用【停用】方式停止后续新建选用。
            </Paragraph>
          </div>
        ),
      });
      return;
    }

    // 允许删除自定义未引用项
    setItems(prev => prev.filter(i => i.id !== item.id));
    if (detailItem?.id === item.id) setDetailItem(null);
    message.success(`自定义代码【${item.code}】已物理删除`);
  };

  // 7. 表格列配置
  const columns: ColumnsType<DictItem> = [
    {
      title: '字典代码 (Key)',
      dataIndex: 'code',
      key: 'code',
      width: 170,
      render: (code: string, record: DictItem) => (
        <Space direction="vertical" size={2}>
          <Text code strong copyable style={{ fontSize: 13 }}>
            {code}
          </Text>
          {record.isBuiltin && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              系统内置
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '视觉呈现 (StatusTag)',
      key: 'tagPreview',
      width: 140,
      render: (_: unknown, record: DictItem) => {
        if (record.domain) {
          return <StatusTag type={record.domain} status={record.code} showIcon />;
        }
        return (
          <Tag color="cyan">
            {record.metadata?.renderType || 'field'}
          </Tag>
        );
      },
    },
    {
      title: '显示名称',
      dataIndex: 'label',
      key: 'label',
      width: 160,
      render: (label: string, record: DictItem) => (
        <Space>
          <Text strong>{label}</Text>
          {record.metadata?.isStarred && (
            <Tag color="volcano" style={{ fontSize: 11, padding: '0 4px', margin: 0 }}>
              ★ 关键
            </Tag>
          )}
          {record.metadata?.isBlocker && (
            <Tag color="error" style={{ fontSize: 11, padding: '0 4px', margin: 0 }}>
              废标红线
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '所属分类',
      dataIndex: 'categoryLabel',
      key: 'categoryLabel',
      width: 190,
      ellipsis: true,
      render: (cat: string) => <Tag color="blue">{cat}</Tag>,
    },
    {
      title: '使用状态',
      key: 'statusFlags',
      width: 140,
      render: (_: unknown, record: DictItem) => (
        <Space size={4}>
          {record.isActive ? (
            <Badge status="success" text={<Text type="success">启用中</Text>} />
          ) : (
            <Badge status="default" text={<Text type="secondary">已停用</Text>} />
          )}
          {record.isInUse && (
            <Tooltip title="已在业务数据中被引用：受系统保护，禁止硬删除">
              <Tag color="orange" style={{ margin: 0, fontSize: 11, padding: '0 4px' }}>
                在用保护
              </Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '业务说明与语义描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => (
        <Tooltip title={desc}>
          <Text type="secondary" ellipsis>
            {desc || '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: DictItem) => {
        return (
          <Space direction="horizontal" size="small">
            <Button
              type="link"
              size="small"
              onClick={() => setDetailItem(record)}
              data-testid={`dict-view-btn-${record.code}`}
            >
              详情
            </Button>

            {permission.canToggleStatus ? (
              <Popconfirm
                title={record.isActive ? '确认停用此代码？' : '确认重新启用此代码？'}
                description={
                  record.isActive
                    ? '停用后新建流程中不可选用，历史数据保持引用不受影响。'
                    : '启用后所有业务模块可继续选用此代码。'
                }
                onConfirm={() => handleToggleActive(record, !record.isActive)}
                okText="确认"
                cancelText="取消"
              >
                <Button
                  type="link"
                  size="small"
                  danger={record.isActive}
                  data-testid={`dict-toggle-btn-${record.code}`}
                >
                  {record.isActive ? '停用' : '启用'}
                </Button>
              </Popconfirm>
            ) : (
              <Tooltip title="只读角色无权变更代码状态">
                <Text type="secondary" style={{ fontSize: 12 }}>
                  只读
                </Text>
              </Tooltip>
            )}

            <Tooltip
              title={
                record.isInUse
                  ? '核心红线：已使用代码只能停用，不可直接硬删除'
                  : '删除代码'
              }
            >
              <Button
                type="link"
                size="small"
                danger
                disabled={!permission.canEdit || record.isInUse || record.isBuiltin}
                onClick={() => handleAttemptHardDelete(record)}
                data-testid={`dict-delete-btn-${record.code}`}
              >
                删除
              </Button>
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  return (
    <div className="dict-config-page" style={{ padding: '4px 0' }} data-testid="dict-config-page">
      {/* 顶部概览与角色身份标识 */}
      <Card
        style={{ marginBottom: 16, borderRadius: 8 }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} md={14}>
            <Space align="center" size="middle">
              <Title level={4} style={{ margin: 0 }}>
                A-03 字典配置与元数据中心
              </Title>
              <Tag
                color={permission.canEdit ? 'blue' : 'default'}
                icon={permission.canEdit ? <SafetyCertificateOutlined /> : <LockOutlined />}
                data-testid="dict-permission-tag"
              >
                {permission.roleLabel}
              </Tag>
            </Space>
            <Paragraph type="secondary" style={{ margin: '6px 0 0 0', fontSize: 13 }}>
              收口 6 大业务状态码表与全量业务字段元数据，提供统一的 StatusTag 色彩与对比度保证。
            </Paragraph>
          </Col>

          <Col xs={24} md={10}>
            <Row gutter={16} justify="end">
              <Col span={6}>
                <Statistic title="字典项总数" value={stats.total} valueStyle={{ fontSize: 20 }} />
              </Col>
              <Col span={6}>
                <Statistic
                  title="有效启用"
                  value={stats.active}
                  valueStyle={{ fontSize: 20, color: '#237804' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="在用受保护"
                  value={stats.inUse}
                  valueStyle={{ fontSize: 20, color: '#d46b08' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="状态码表数"
                  value={stats.statusCodes}
                  valueStyle={{ fontSize: 20, color: '#1e4db7' }}
                />
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* 核心红线警示横幅 */}
      <Alert
        data-testid="dict-redline-alert"
        type={permission.canEdit ? 'warning' : 'info'}
        showIcon
        icon={permission.canEdit ? <SafetyCertificateOutlined /> : <InfoCircleOutlined />}
        message="数据完整性与防篡改红线"
        description="系统核心规则：已在生产业务中使用的状态代码只能停用，不可直接硬删除。非管理员身份严格处于只读保护态。"
        style={{ marginBottom: 16, borderRadius: 6 }}
      />

      {/* 主工作区卡片 */}
      <Card style={{ borderRadius: 8 }} bodyStyle={{ padding: '16px 20px' }}>
        {/* 顶部过滤控制条 */}
        <Row justify="space-between" align="middle" gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
              placeholder="检索代码名称、显示名或描述..."
              allowClear
              value={searchKeyword}
              onChange={e => setSearchKeyword(e.target.value)}
              data-testid="dict-search-input"
            />
          </Col>

          <Col xs={24} sm={12} md={10}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Text type="secondary">状态过滤：</Text>
              <Radio.Group
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                size="middle"
                data-testid="dict-status-filter"
              >
                <Radio.Button value="all">全部 ({items.length})</Radio.Button>
                <Radio.Button value="active">仅启用 ({stats.active})</Radio.Button>
                <Radio.Button value="inactive">已停用 ({items.length - stats.active})</Radio.Button>
              </Radio.Group>
            </Space>
          </Col>
        </Row>

        {/* 分类切换 Tabs */}
        <Tabs
          activeKey={selectedCategory}
          onChange={setSelectedCategory}
          type="line"
          data-testid="dict-category-tabs"
          items={[
            {
              key: 'all',
              label: `全部代码 (${items.length})`,
            },
            ...categorySummaries.map(c => ({
              key: c.category,
              label: `${c.categoryLabel} (${c.activeCount}/${c.totalCount})`,
            })),
          ]}
          style={{ marginBottom: 12 }}
        />

        {/* 核心字典表格 */}
        <Table<DictItem>
          rowKey="id"
          columns={columns}
          dataSource={filteredItems}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 项 / 共 ${total} 项代码`,
          }}
          size="middle"
          bordered
          data-testid="dict-table"
        />
      </Card>

      {/* 字典项详情侧边抽屉 */}
      <Drawer
        title="字典与元数据详情"
        placement="right"
        width={480}
        open={!!detailItem}
        onClose={() => setDetailItem(null)}
        data-testid="dict-detail-drawer"
        extra={
          detailItem &&
          permission.canToggleStatus && (
            <Popconfirm
              title={detailItem.isActive ? '停用此代码？' : '启用此代码？'}
              description="停用后仅阻断新建选用，历史关联数据保持完好。"
              onConfirm={() => handleToggleActive(detailItem, !detailItem.isActive)}
            >
              <Button type="primary" danger={detailItem.isActive} size="small">
                {detailItem.isActive ? '停用代码' : '重新启用'}
              </Button>
            </Popconfirm>
          )
        }
      >
        {detailItem && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 视觉形态呈现 */}
            <Card size="small" style={{ backgroundColor: '#fafafa' }}>
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
                  全站统一标签渲染效果
                </Text>
                {detailItem.domain ? (
                  <Space size="middle">
                    <StatusTag type={detailItem.domain} status={detailItem.code} showIcon size="default" />
                    <StatusTag type={detailItem.domain} status={detailItem.code} variant="solid" size="default" />
                    <StatusTag type={detailItem.domain} status={detailItem.code} variant="outline" size="default" />
                  </Space>
                ) : (
                  <Tag color="blue" style={{ fontSize: 14, padding: '2px 10px' }}>
                    {detailItem.label} ({detailItem.code})
                  </Tag>
                )}
              </div>
            </Card>

            {/* 详细元信息 */}
            <Descriptions title="代码元数据详情" column={1} bordered size="small">
              <Descriptions.Item label="字典代码 (Code)">
                <Text code copyable>
                  {detailItem.code}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="显示名称 (Label)">
                {detailItem.label}
              </Descriptions.Item>
              <Descriptions.Item label="所属分类">
                {detailItem.categoryLabel}
              </Descriptions.Item>
              <Descriptions.Item label="启用状态">
                {detailItem.isActive ? (
                  <Badge status="success" text="有效启用中" />
                ) : (
                  <Badge status="default" text="已停用" />
                )}
              </Descriptions.Item>
              <Descriptions.Item label="业务在用保护">
                {detailItem.isInUse ? (
                  <Tag color="orange">已在生产业务中引用（禁止删除）</Tag>
                ) : (
                  <Tag>未引用</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="数据类型">
                <Text code>{detailItem.metadata?.dataType || 'string'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="渲染控件">
                <Text code>{detailItem.metadata?.renderType || 'tag'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="业务规则红线">
                <Text type={detailItem.isInUse ? 'warning' : 'secondary'}>
                  {validateCodeDeactivation(detailItem).reason}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="完整描述说明">
                {detailItem.description || '暂无详细描述'}
              </Descriptions.Item>
            </Descriptions>

            {/* 针对只读用户的说明提示 */}
            {permission.isReadOnly && (
              <Alert
                type="info"
                showIcon
                message="只读保护提示"
                description="您当前的角色无权直接修改字典参数配置。如需启用、停用或扩展自定义代码，请提报管理员审批。"
              />
            )}
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default DictConfigPage;
