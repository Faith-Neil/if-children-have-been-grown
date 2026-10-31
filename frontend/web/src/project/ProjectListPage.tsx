// 为什么有这个文件：封装完善的项目列表与多维筛选页（ProjectListPage）。
// 它解决什么问题：落实 APP-M2-T095，提供状态（筹备中/编写中/审核中/已完成）、涉密属性、分册状态多维筛选，列表项支持一键进入项目工作台和查看项目元数据抽屉（集成 MaskedField 脱敏展示与倒计时提醒）。

import React, { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  Progress,
  Radio,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import {
  ClockCircleOutlined,
  EyeOutlined,
  FolderOpenOutlined,
  InfoCircleOutlined,
  LockOutlined,
  ProjectOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { ApplicationSession, Project, Volume } from '../shared/types.ts';
import { companyName, formatTime, volumeName } from '../app/context.tsx';
import { MaskedField } from '../admin/MaskedField.tsx';
import { calculateProjectCountdown, formatCurrencyAmount } from './ProjectHeader.tsx';
import { normalizeSystemRole, READONLY_SYSTEM_ROLES, type SystemRole } from '../shell/route-guard.ts';

import {
  deriveProjectStatus,
  deriveVolumeStatus,
  filterProjectList,
  PROJECT_STATUS_LABELS,
  type ProjectFilterCriteria,
  type ProjectStatusKey,
  type SensitiveFilterKey,
  type VolumeStatusFilterKey,
} from './project-list-core.ts';

export {
  deriveProjectStatus,
  deriveVolumeStatus,
  filterProjectList,
  PROJECT_STATUS_LABELS,
  type ProjectFilterCriteria,
  type ProjectStatusKey,
  type SensitiveFilterKey,
  type VolumeStatusFilterKey,
};

export interface ProjectListPageProps {
  projects: Project[];
  onOpenProject: (projectId: string) => void;
  session?: ApplicationSession | null;
  currentUser?: { id: string; name: string; company_id: string } | null;
  userRole?: string;
  onRefresh?: () => void;
  className?: string;
}

/**
 * 完善的项目列表页与筛选组件
 */
export function ProjectListPage({
  projects,
  onOpenProject,
  session = null,
  currentUser = null,
  userRole,
  className = '',
}: ProjectListPageProps) {
  // 1. 筛选条件状态
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<ProjectStatusKey>('all');
  const [sensitive, setSensitive] = useState<SensitiveFilterKey>('all');
  const [volumeStatus, setVolumeStatus] = useState<VolumeStatusFilterKey>('all');

  // 2. 元数据抽屉状态
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // 3. 权限判断
  const effectiveRole =
    userRole ||
    session?.user?.primary_role ||
    session?.user?.role ||
    'viewer';
  const normalizedRole = normalizeSystemRole(effectiveRole);
  const isReadonlyMember = READONLY_SYSTEM_ROLES.has(normalizedRole as SystemRole);

  // 4. 执行筛选
  const filteredList = useMemo(() => {
    return filterProjectList(projects, {
      keyword,
      status,
      sensitive,
      volumeStatus,
    });
  }, [projects, keyword, status, sensitive, volumeStatus]);

  // 5. 统计卡片指标
  const statistics = useMemo(() => {
    const total = projects.length;
    const writingCount = projects.filter(p => deriveProjectStatus(p) === 'writing').length;
    const sensitiveCount = projects.filter(p => !!p.sensitive).length;
    const urgentCount = projects.filter(p => {
      const countdown = calculateProjectCountdown(p.deadline);
      return countdown.isUrgent && !countdown.isExpired;
    }).length;

    return { total, writingCount, sensitiveCount, urgentCount };
  }, [projects]);

  return (
    <div className={`project-list-page ${className}`} data-testid="project-list-page">
      {/* 顶部统计卡片栏 */}
      <Row gutter={16} className="summary-row" style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" data-testid="stat-total-projects">
            <Statistic title="全部项目" value={statistics.total} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" data-testid="stat-writing-projects">
            <Statistic
              title="编写中项目"
              value={statistics.writingCount}
              valueStyle={{ color: '#1e4db7' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" data-testid="stat-urgent-projects">
            <Statistic
              title="临期紧急项目 (≤3天)"
              value={statistics.urgentCount}
              valueStyle={{ color: '#d9363e' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" data-testid="stat-sensitive-projects">
            <Statistic
              title="涉密安全项目"
              value={statistics.sensitiveCount}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<LockOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选工具栏 */}
      <Card
        size="small"
        className="project-filter-card"
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: '12px 16px' }}
        data-testid="project-filter-card"
      >
        <Row gutter={[16, 12]} align="middle">
          {/* 关键字搜索 */}
          <Col xs={24} sm={12} md={6}>
            <Input
              prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
              placeholder="搜索项目名称 / 招标编号"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              allowClear
              aria-label="项目搜索关键字"
              data-testid="project-search-input"
            />
          </Col>

          {/* 状态筛选 */}
          <Col xs={24} sm={12} md={6}>
            <Space direction="horizontal" size={6} style={{ width: '100%' }}>
              <span style={{ fontSize: 13, color: '#4e5969', whiteSpace: 'nowrap' }}>状态:</span>
              <Select
                value={status}
                onChange={setStatus}
                style={{ width: '100%', minWidth: 120 }}
                aria-label="按状态筛选"
                data-testid="status-filter-select"
                options={[
                  { value: 'all', label: '全部状态' },
                  { value: 'preparing', label: '筹备中' },
                  { value: 'writing', label: '编写中' },
                  { value: 'reviewing', label: '审核中' },
                  { value: 'completed', label: '已完成' },
                ]}
              />
            </Space>
          </Col>

          {/* 涉密属性筛选 */}
          <Col xs={24} sm={12} md={6}>
            <Space direction="horizontal" size={6} style={{ width: '100%' }}>
              <span style={{ fontSize: 13, color: '#4e5969', whiteSpace: 'nowrap' }}>属性:</span>
              <Select
                value={sensitive}
                onChange={setSensitive}
                style={{ width: '100%', minWidth: 120 }}
                aria-label="按涉密属性筛选"
                data-testid="sensitive-filter-select"
                options={[
                  { value: 'all', label: '全部属性' },
                  { value: 'sensitive', label: '涉密项目 (本地)' },
                  { value: 'normal', label: '普通项目' },
                ]}
              />
            </Space>
          </Col>

          {/* 分册状态筛选 */}
          <Col xs={24} sm={12} md={6}>
            <Space direction="horizontal" size={6} style={{ width: '100%' }}>
              <span style={{ fontSize: 13, color: '#4e5969', whiteSpace: 'nowrap' }}>分册:</span>
              <Select
                value={volumeStatus}
                onChange={setVolumeStatus}
                style={{ width: '100%', minWidth: 130 }}
                aria-label="按分册状态筛选"
                data-testid="volume-status-filter-select"
                options={[
                  { value: 'all', label: '全部分册状态' },
                  { value: 'technical_pending', label: '技术分册待写' },
                  { value: 'business_pending', label: '商务分册待写' },
                  { value: 'both_done', label: '两册已提交完成' },
                ]}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 项目列表表格 */}
      <Card
        title={
          <Space>
            <span>我参与的投标项目</span>
            <Tag color="blue">{filteredList.length} 个</Tag>
          </Space>
        }
        bodyStyle={{ padding: 0 }}
        data-testid="project-table-card"
      >
        <Table<Project>
          size="middle"
          rowKey="id"
          dataSource={filteredList}
          pagination={{ pageSize: 8, showTotal: t => `共 ${t} 个项目` }}
          locale={{ emptyText: <Empty description="暂无符合筛选条件的项目" /> }}
          columns={[
            {
              title: '项目名称',
              dataIndex: 'name',
              key: 'name',
              render: (name: string, record: Project) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <a
                    onClick={() => onOpenProject(record.id)}
                    style={{ fontWeight: 500 }}
                    data-testid={`project-item-link-${record.id}`}
                  >
                    {name}
                  </a>
                  {record.sensitive && (
                    <Tag
                      color="volcano"
                      icon={<LockOutlined />}
                      style={{ fontSize: 11 }}
                      data-testid="sensitive-tag"
                    >
                      涉密
                    </Tag>
                  )}
                </div>
              ),
            },
            {
              title: '招标编号',
              dataIndex: 'tender_number',
              key: 'tender_number',
              width: 160,
              render: (value: string) => value || <span style={{ color: '#8c8c8c' }}>未填写</span>,
            },
            {
              title: '标的金额',
              key: 'target_amount',
              width: 190,
              render: (_: unknown, record: Project) => {
                if (record.target_amount === undefined || record.target_amount === null) return <span style={{ color: '#8c8c8c' }}>未填写</span>;
                const amountText = formatCurrencyAmount(record.target_amount);
                return (
                  <MaskedField
                    value={amountText}
                    fieldType="custom"
                    fieldName="标的金额"
                    maskRule={{ prefix: 2, suffix: 3, maskChar: '*' }}
                    actionText="查看完整值"
                    canReveal={!isReadonlyMember}
                    unauthorizedMode="disabled"
                    unauthorizedTooltip="仅项目负责人和管理员有权调阅标的金额"
                    testId={`project-amount-field-${record.id}`}
                  />
                );
              },
            },
            {
              title: '状态',
              key: 'status',
              width: 100,
              render: (_: unknown, record: Project) => {
                const s = deriveProjectStatus(record);
                const meta = PROJECT_STATUS_LABELS[s] || { label: '待确认', color: 'default' };
                return <Tag color={meta.color}>{meta.label}</Tag>;
              },
            },
            {
              title: '投标截止时间 / 倒计时',
              key: 'deadline',
              width: 220,
              render: (_: unknown, record: Project) => {
                const countdown = calculateProjectCountdown(record.deadline);
                return (
                  <div>
                    <div>{formatTime(record.deadline)}</div>
                    {countdown.status !== 'none' && (
                      <Tag
                        color={countdown.color}
                        icon={<ClockCircleOutlined />}
                        style={{ fontSize: 11, marginTop: 2 }}
                        data-testid="project-countdown-badge"
                      >
                        {countdown.label}
                      </Tag>
                    )}
                  </div>
                );
              },
            },
            {
              title: '分册进度',
              key: 'volumes',
              width: 150,
              render: (_: unknown, record: Project) => {
                const vStatus = deriveVolumeStatus(record);
                return (
                  <Space size={4}>
                    <Tag color={vStatus.technical === 'completed' ? 'green' : 'blue'}>
                      技: {vStatus.technical === 'completed' ? '已提交' : '编写中'}
                    </Tag>
                    <Tag color={vStatus.business === 'completed' ? 'green' : 'blue'}>
                      商: {vStatus.business === 'completed' ? '已提交' : '编写中'}
                    </Tag>
                  </Space>
                );
              },
            },
            {
              title: '操作',
              key: 'actions',
              width: 170,
              render: (_: unknown, record: Project) => (
                <Space size={8}>
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => onOpenProject(record.id)}
                    data-testid={`enter-project-btn-${record.id}`}
                  >
                    进入工作台
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    icon={<InfoCircleOutlined />}
                    onClick={() => setSelectedProject(record)}
                    data-testid={`view-metadata-btn-${record.id}`}
                  >
                    元数据
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 项目元数据详情抽屉 */}
      <Drawer
        title={
          <Space>
            <FolderOpenOutlined style={{ color: '#1e4db7' }} />
            <span>项目元数据详情</span>
            {selectedProject?.sensitive && (
              <Tag color="volcano" icon={<LockOutlined />}>
                涉密项目
              </Tag>
            )}
          </Space>
        }
        open={!!selectedProject}
        onClose={() => setSelectedProject(null)}
        width={560}
        extra={
          selectedProject && (
            <Button
              type="primary"
              size="small"
              onClick={() => {
                const id = selectedProject.id;
                setSelectedProject(null);
                onOpenProject(id);
              }}
            >
              直接进入工作台
            </Button>
          )
        }
        data-testid="project-metadata-drawer"
      >
        {selectedProject && (
          <div className="project-metadata-detail" data-testid="project-metadata-content">
            {selectedProject.sensitive && (
              <Alert
                type="warning"
                showIcon
                icon={<LockOutlined />}
                message="涉密项目安全策略生效中"
                description="该项目标识为涉密级别，正文生成与检查均运行于本地环境，不调用任何公有云模型 API。"
                style={{ marginBottom: 16 }}
              />
            )}

            <Descriptions title="基本属性" column={1} bordered size="small">
              <Descriptions.Item label="项目名称">
                <b>{selectedProject.name}</b>
              </Descriptions.Item>
              <Descriptions.Item label="项目 ID">
                <code style={{ fontSize: 12 }}>{selectedProject.id}</code>
              </Descriptions.Item>
              <Descriptions.Item label="招标编号">
                {selectedProject.tender_number || '未填写'}
              </Descriptions.Item>
              <Descriptions.Item label="投标主体">
                {companyName(selectedProject.company_id || currentUser?.company_id || 'alpha')}
              </Descriptions.Item>
              <Descriptions.Item label="涉密属性">
                {selectedProject.sensitive ? (
                  <Tag color="volcano">涉密 · 强制本地运行</Tag>
                ) : (
                  <Tag color="default">普通项目</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="标的金额">
                {selectedProject.target_amount === undefined || selectedProject.target_amount === null ? <span style={{ color: '#8c8c8c' }}>未填写</span> : <MaskedField
                  value={formatCurrencyAmount(selectedProject.target_amount)}
                  fieldType="custom"
                  fieldName="标的金额"
                  maskRule={{ prefix: 2, suffix: 3, maskChar: '*' }}
                  actionText="调阅明细"
                  canReveal={!isReadonlyMember}
                  unauthorizedMode="disabled"
                  unauthorizedTooltip="仅项目负责人与公司管理员有权调阅完整标的金额"
                  testId="drawer-target-amount-field"
                />}
              </Descriptions.Item>
              <Descriptions.Item label="当前生命周期阶段">
                {(() => {
                  const s = deriveProjectStatus(selectedProject);
                  const meta = PROJECT_STATUS_LABELS[s] || { label: '待确认', color: 'default' };
                  return <Tag color={meta.color}>{meta.label}</Tag>;
                })()}
              </Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: '16px 0' }} />

            <Descriptions title="时间节点与截止提醒" column={1} bordered size="small">
              <Descriptions.Item label="投标截止时间">
                {formatTime(selectedProject.deadline)}
              </Descriptions.Item>
              <Descriptions.Item label="截止倒计时">
                {(() => {
                  const cd = calculateProjectCountdown(selectedProject.deadline);
                  return (
                    <Tag color={cd.color} icon={<ClockCircleOutlined />}>
                      {cd.label}
                    </Tag>
                  );
                })()}
              </Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: '16px 0' }} />

            <Descriptions title="分册编制概览" column={1} bordered size="small">
              <Descriptions.Item label="技术分册 (Technical)">
                <Tag color={selectedProject.volumes_status?.technical === 'completed' ? 'green' : 'blue'}>
                  {selectedProject.volumes_status?.technical === 'completed' ? '已提交正式稿' : '编写中'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="商务分册 (Business)">
                <Tag color={selectedProject.volumes_status?.business === 'completed' ? 'green' : 'blue'}>
                  {selectedProject.volumes_status?.business === 'completed' ? '已提交正式稿' : '编写中'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Drawer>
    </div>
  );
}
