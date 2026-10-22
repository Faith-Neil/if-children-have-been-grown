// 为什么有这个文件：落实 APP-M2-T157 (A-06 审计日志页) 与 PRD v1.8 §5.10.6、§6.7、§7.3。
// 它解决什么问题：集中展示敏感数据调阅、章节独占编辑锁抢占/释放、模型密钥变更及云端调用审计日志，提供多维检索与只读不可篡改安全防护。

import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  FileProtectOutlined,
  FilterOutlined,
  KeyOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from './types.ts';
import {
  computeAuditSummaryStats,
  DEFAULT_AUDIT_LOGS,
  filterAuditLogs,
  formatMaskedKeyFingerprint,
  formatMonospaceTime,
  getAuditActionMeta,
  validateRevealReason,
  type AuditActionType,
  type AuditCategory,
  type AuditFilterParams,
  type AuditLogEntry,
} from './audit-log-core.ts';

const { Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;

export interface AuditLogPageProps {
  session?: ApplicationSession | null;
  user?: Account | null;
  initialProjectId?: string;
  onNavigate?: (path: string) => void;
  logs?: AuditLogEntry[];
}

export function AuditLogPage({
  session,
  user,
  initialProjectId,
  logs: propLogs,
}: AuditLogPageProps) {
  // 1. 数据与状态
  const allLogs = useMemo(() => propLogs || DEFAULT_AUDIT_LOGS, [propLogs]);

  const [categoryFilter, setCategoryFilter] = useState<AuditCategory>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [operatorKeyword, setOperatorKeyword] = useState<string>('');
  const [projectKeyword, setProjectKeyword] = useState<string>(initialProjectId || '');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [resultFilter, setResultFilter] = useState<'all' | 'success' | 'failed'>('all');
  const [dateRange, setDateRange] = useState<[string | null, string | null]>([null, null]);

  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 2. 多维过滤应用
  const filteredLogs = useMemo(() => {
    const filters: AuditFilterParams = {
      category: categoryFilter !== 'all' ? categoryFilter : undefined,
      actionType: actionFilter !== 'all' ? actionFilter : undefined,
      operator: operatorKeyword.trim() || undefined,
      projectId: projectKeyword.trim() || undefined,
      keyword: searchKeyword.trim() || undefined,
      result: resultFilter,
      dateStart: dateRange[0] || undefined,
      dateEnd: dateRange[1] || undefined,
    };
    return filterAuditLogs(allLogs, filters);
  }, [allLogs, categoryFilter, actionFilter, operatorKeyword, projectKeyword, searchKeyword, resultFilter, dateRange]);

  // 3. 统计汇总计算
  const stats = useMemo(() => computeAuditSummaryStats(allLogs), [allLogs]);

  // 4. 重置筛选
  const handleResetFilters = () => {
    setCategoryFilter('all');
    setActionFilter('all');
    setOperatorKeyword('');
    setProjectKeyword('');
    setSearchKeyword('');
    setResultFilter('all');
    setDateRange([null, null]);
  };

  // 5. 审计表格列定义 (只读展示，严禁提供任何编辑或删除按钮)
  const columns: ColumnsType<AuditLogEntry> = [
    {
      title: '发生时间',
      dataIndex: 'occurred_at',
      key: 'occurred_at',
      width: 170,
      render: (val: string) => (
        <span style={{ fontFamily: 'SFMono-Regular, Consolas, monospace', fontSize: 13, color: '#1d2129' }}>
          {formatMonospaceTime(val)}
        </span>
      ),
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 160,
      render: (action: AuditActionType, record) => {
        const meta = getAuditActionMeta(action);
        return (
          <Space direction="vertical" size={2}>
            <Tag color={meta.color} style={{ fontWeight: 500 }}>
              {record.action_label || meta.label}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '操作人',
      key: 'operator',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: 13 }}>
            <UserOutlined style={{ marginRight: 4, color: '#1e4db7' }} />
            {record.user_name}
          </Text>
          <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>
            {record.user_id}
          </Text>
        </Space>
      ),
    },
    {
      title: '所属租户',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 140,
      ellipsis: true,
      render: (val, record) => (
        <Tooltip title={`租户ID: ${record.company_id}`}>
          <Text style={{ fontSize: 12 }}>{val || record.company_id}</Text>
        </Tooltip>
      ),
    },
    {
      title: '目标对象',
      key: 'target',
      width: 190,
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>{record.target_name || record.target_id}</Text>
          {record.project_name && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              项目: {record.project_name}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '调阅理由 / 关键留痕详情',
      key: 'reason_detail',
      render: (_, record) => {
        // 敏感数据调阅：突出显示调阅理由与字数合规性
        if (record.action === 'sensitive.reveal') {
          const reasonCheck = validateRevealReason(record.reveal_reason);
          return (
            <div>
              <Space size={6} wrap>
                <Tag color={reasonCheck.valid ? 'purple' : 'red'}>
                  {record.sensitive_field_name || '敏感个人信息'}
                </Tag>
                {reasonCheck.valid ? (
                  <Badge count={`理由合规 (${reasonCheck.length}字)`} style={{ backgroundColor: '#52c41a' }} />
                ) : (
                  <Badge count={`理由不合规 (${reasonCheck.length}字 < 5)`} style={{ backgroundColor: '#f5222d' }} />
                )}
              </Space>
              <div style={{ marginTop: 4, fontSize: 12, color: '#4e5969', fontStyle: 'italic' }}>
                “{record.reveal_reason}”
              </div>
            </div>
          );
        }

        // 编辑锁相关事件
        if (record.action.startsWith('lock.')) {
          return (
            <div>
              <Space size={4}>
                <LockOutlined style={{ color: '#fa8c16' }} />
                <Text style={{ fontSize: 12 }}>
                  章节: {record.lock_chapter_id || record.target_id}
                </Text>
                {record.lock_volume && (
                  <Tag color="blue">{record.lock_volume === 'technical' ? '技术分册' : '商务分册'}</Tag>
                )}
              </Space>
              {record.lock_takeover_reason && (
                <div style={{ marginTop: 4, fontSize: 12, color: '#d46b08' }}>
                  接管原因: {record.lock_takeover_reason}
                </div>
              )}
            </div>
          );
        }

        // 模型密钥变更事件
        if (record.action.startsWith('model_key.')) {
          const masked = formatMaskedKeyFingerprint(record.key_fingerprint);
          return (
            <div>
              <Space size={6}>
                <KeyOutlined style={{ color: '#13c2c2' }} />
                <Tag color="cyan">脱敏指纹: {masked}</Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {record.model_provider || record.model_name}
                </Text>
              </Space>
              <div style={{ marginTop: 2, fontSize: 11, color: '#86909c' }}>
                密钥密文加密落库，严禁前端明文显示
              </div>
            </div>
          );
        }

        // 云端调用
        if (record.is_cloud_call || record.category === 'cloud') {
          return (
            <Space size={6}>
              <ThunderboltOutlined style={{ color: '#eb2f96' }} />
              <Tag color="magenta">公网云端外发</Tag>
              {record.tokens_used && <Text style={{ fontSize: 12 }}>消耗: {record.tokens_used} tokens</Text>}
              {record.duration_ms && <Text type="secondary" style={{ fontSize: 12 }}>耗时: {record.duration_ms}ms</Text>}
            </Space>
          );
        }

        return (
          <Text style={{ fontSize: 12, color: '#4e5969' }}>
            {record.target_name || record.target_id}
          </Text>
        );
      },
    },
    {
      title: '来源 IP',
      dataIndex: 'ip',
      key: 'ip',
      width: 120,
      render: (val: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#86909c' }}>{val || '-'}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'result',
      key: 'result',
      width: 85,
      render: (val: string) =>
        val === 'success' ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            成功
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">
            失败
          </Tag>
        ),
    },
    {
      title: '操作',
      key: 'action_btn',
      width: 90,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedEntry(record);
            setDrawerOpen(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div className="audit-log-page" style={{ paddingBottom: 24 }}>
      {/* 顶部安全只读防护指示条 */}
      <Alert
        type="info"
        showIcon
        icon={<SafetyCertificateOutlined style={{ fontSize: 18, color: '#1e4db7' }} />}
        message="【安全只读防护机制已启用】依据 ICG 安全合规与电子数据审计规范"
        description="所有审计记录（敏感数据调阅、章节排他锁调度、模型服务密钥变更、云端调用外发）均通过只追加防篡改存储写入，对全量系统角色保持严格只读，前端彻底阻断任何修改、删除或篡改接口。"
        action={
          <Space>
            <Tag color="blue">不可篡改</Tag>
            <Tag color="cyan">纯只读归档</Tag>
          </Space>
        }
        style={{ marginBottom: 16, backgroundColor: '#f0f5ff', borderColor: '#adc6ff' }}
      />

      {/* 审计概览统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small" style={{ borderRadius: 6, borderColor: '#e8ebf0' }}>
            <Statistic
              title="总审计事件数"
              value={stats.totalCount}
              valueStyle={{ color: '#1d2129', fontWeight: 600 }}
              prefix={<FileProtectOutlined style={{ color: '#1e4db7' }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small" style={{ borderRadius: 6, borderColor: '#e8ebf0' }}>
            <Statistic
              title="敏感数据调阅"
              value={stats.sensitiveRevealCount}
              valueStyle={{ color: '#722ed1', fontWeight: 600 }}
              suffix={<small style={{ fontSize: 11, color: '#86909c' }}>次留痕</small>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small" style={{ borderRadius: 6, borderColor: '#e8ebf0' }}>
            <Statistic
              title="编辑锁接管与释放"
              value={stats.lockEventCount}
              valueStyle={{ color: '#fa8c16', fontWeight: 600 }}
              suffix={<small style={{ fontSize: 11, color: '#86909c' }}>次事件</small>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small" style={{ borderRadius: 6, borderColor: '#e8ebf0' }}>
            <Statistic
              title="模型密钥安全变更"
              value={stats.keyEventCount}
              valueStyle={{ color: '#13c2c2', fontWeight: 600 }}
              suffix={<small style={{ fontSize: 11, color: '#86909c' }}>次轮换/更新</small>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small" style={{ borderRadius: 6, borderColor: '#e8ebf0' }}>
            <Statistic
              title="操作成功率"
              value={stats.successRate}
              precision={0}
              suffix="%"
              valueStyle={{ color: stats.successRate >= 95 ? '#52c41a' : '#faad14', fontWeight: 600 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 多维检索过滤栏 */}
      <Card
        size="small"
        style={{ marginBottom: 16, borderRadius: 6, borderColor: '#e8ebf0', background: '#ffffff' }}
        title={
          <Space>
            <FilterOutlined style={{ color: '#1e4db7' }} />
            <span style={{ fontSize: 14, fontWeight: 500 }}>多维审计检索与条件过滤</span>
          </Space>
        }
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={handleResetFilters}>
            重置检索
          </Button>
        }
      >
        <Row gutter={[12, 12]}>
          <Col xs={24} sm={12} md={6}>
            <div style={{ fontSize: 12, color: '#86909c', marginBottom: 4 }}>时间范围</div>
            <RangePicker
              style={{ width: '100%' }}
              onChange={dates => {
                if (!dates || !dates[0] || !dates[1]) {
                  setDateRange([null, null]);
                } else {
                  setDateRange([dates[0].format('YYYY-MM-DD'), dates[1].format('YYYY-MM-DD')]);
                }
              }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <div style={{ fontSize: 12, color: '#86909c', marginBottom: 4 }}>审计分类</div>
            <Select
              style={{ width: '100%' }}
              value={categoryFilter}
              onChange={setCategoryFilter}
              options={[
                { value: 'all', label: '全部事件类别' },
                { value: 'sensitive', label: '敏感数据调阅' },
                { value: 'lock', label: '排他编辑锁调度' },
                { value: 'key', label: '模型密钥管理' },
                { value: 'cloud', label: '云端调用外发' },
                { value: 'project', label: '项目与业务资料' },
              ]}
            />
          </Col>
          <Col xs={12} sm={6} md={5}>
            <div style={{ fontSize: 12, color: '#86909c', marginBottom: 4 }}>具体操作类型</div>
            <Select
              style={{ width: '100%' }}
              value={actionFilter}
              onChange={setActionFilter}
              options={[
                { value: 'all', label: '全部操作动作' },
                { value: 'sensitive.reveal', label: '脱敏数据调阅' },
                { value: 'lock.acquire', label: '获取章节编辑锁' },
                { value: 'lock.takeover', label: '抢占/接管编辑锁' },
                { value: 'lock.release', label: '主动释放编辑锁' },
                { value: 'lock.timeout', label: '编辑锁超时释放' },
                { value: 'model_key.update', label: '更新模型配置密钥' },
                { value: 'model_key.rotate', label: '安全密钥定期轮换' },
                { value: 'cloud.llm_call', label: '云端大模型生成' },
                { value: 'cloud.parse_call', label: '云端招标文件解析' },
                { value: 'project.create', label: '新建投标项目' },
              ]}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <div style={{ fontSize: 12, color: '#86909c', marginBottom: 4 }}>操作人 (姓名/ID)</div>
            <Input
              placeholder="搜索操作人"
              prefix={<UserOutlined style={{ color: '#c2c7d0' }} />}
              value={operatorKeyword}
              onChange={e => setOperatorKeyword(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={5}>
            <div style={{ fontSize: 12, color: '#86909c', marginBottom: 4 }}>项目编号 / 关键词</div>
            <Input
              placeholder="项目ID或综合关键词"
              prefix={<SearchOutlined style={{ color: '#c2c7d0' }} />}
              value={projectKeyword || searchKeyword}
              onChange={e => {
                setProjectKeyword(e.target.value);
                setSearchKeyword(e.target.value);
              }}
              allowClear
            />
          </Col>
        </Row>
      </Card>

      {/* 审计日志列表表格 */}
      <Card
        size="small"
        style={{ borderRadius: 6, borderColor: '#e8ebf0' }}
        title={
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>审计日志明细清单</span>
            <Tag color="default">共 {filteredLogs.length} 条记录</Tag>
          </Space>
        }
      >
        <Table<AuditLogEntry>
          rowKey="id"
          columns={columns}
          dataSource={filteredLogs}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
          size="middle"
          scroll={{ x: 1100 }}
          locale={{
            emptyText: <Empty description="未检索到符合条件的审计日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
          }}
        />
      </Card>

      {/* 结构化审计详情抽屉 (只读展示，严禁前端提供修改接口) */}
      <Drawer
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#1e4db7' }} />
            <span>只读审计存证详情</span>
            {selectedEntry && (
              <Tag color={selectedEntry.result === 'success' ? 'green' : 'red'}>
                {selectedEntry.result === 'success' ? '执行成功' : '执行失败'}
              </Tag>
            )}
          </Space>
        }
        placement="right"
        width={560}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {selectedEntry && (
          <div>
            <Alert
              type="warning"
              message="防篡改存证记录"
              description="该条记录已计算密码学审计指纹并完成不可篡改固化，记录内容为最终权威留痕。"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions title="基本审计元数据" column={1} bordered size="small">
              <Descriptions.Item label="审计日志 ID">
                <Text code copyable>{selectedEntry.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="发生时间">
                <Text strong style={{ fontFamily: 'monospace' }}>
                  {formatMonospaceTime(selectedEntry.occurred_at)}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="操作动作">
                <Tag color={getAuditActionMeta(selectedEntry.action).color}>
                  {selectedEntry.action_label} ({selectedEntry.action})
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="操作人员">
                {selectedEntry.user_name} ({selectedEntry.user_id})
                {selectedEntry.user_role && <Tag style={{ marginLeft: 6 }}>{selectedEntry.user_role}</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="所属公司">
                {selectedEntry.company_name} ({selectedEntry.company_id})
              </Descriptions.Item>
              <Descriptions.Item label="客户端 IP">
                <Text code>{selectedEntry.ip}</Text>
              </Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: '16px 0' }} />

            {/* 敏感数据调阅专属卡片 */}
            {selectedEntry.action === 'sensitive.reveal' && (
              <Card size="small" title="敏感数据调阅留痕凭据" style={{ marginBottom: 16, borderColor: '#d3adf7' }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="调阅字段">
                    <Tag color="purple">{selectedEntry.sensitive_field_name || selectedEntry.target_name}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="脱敏掩码值">
                    <Text code>{selectedEntry.masked_value || '***'}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="调阅业务理由">
                    <Paragraph style={{ margin: 0, color: '#1d2129', background: '#f9f0ff', padding: 8, borderRadius: 4 }}>
                      {selectedEntry.reveal_reason}
                    </Paragraph>
                  </Descriptions.Item>
                  <Descriptions.Item label="理由合规校验">
                    {validateRevealReason(selectedEntry.reveal_reason).valid ? (
                      <Tag color="success">合规（已达到 5 字以上业务说明门禁）</Tag>
                    ) : (
                      <Tag color="error">违规（理由未达到 5 个字）</Tag>
                    )}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            {/* 编辑锁专属卡片 */}
            {selectedEntry.action.startsWith('lock.') && (
              <Card size="small" title="章节排他锁调度详情" style={{ marginBottom: 16, borderColor: '#ffd591' }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="章节编号">
                    <Text strong>{selectedEntry.lock_chapter_id || selectedEntry.target_id}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="所属分册">
                    <Tag color="blue">{selectedEntry.lock_volume === 'technical' ? '技术分册' : '商务分册'}</Tag>
                  </Descriptions.Item>
                  {selectedEntry.lock_takeover_reason && (
                    <Descriptions.Item label="强制接管理由">
                      <Paragraph style={{ margin: 0, color: '#d46b08' }}>
                        {selectedEntry.lock_takeover_reason}
                      </Paragraph>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            )}

            {/* 模型密钥变更专属卡片 */}
            {selectedEntry.action.startsWith('model_key.') && (
              <Card size="small" title="模型密钥安全凭证留痕" style={{ marginBottom: 16, borderColor: '#87e8de' }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="服务提供商">
                    {selectedEntry.model_provider || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="模型名称">
                    {selectedEntry.model_name || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="脱敏密钥指纹">
                    <Text code copyable>{formatMaskedKeyFingerprint(selectedEntry.key_fingerprint)}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="安全说明">
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      依据安全管理要求，系统已记录密钥轮换审计，原始密钥明文永不上报也不回显。
                    </Text>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            {/* 详细扩展 JSON Payload (只读不可编辑) */}
            {selectedEntry.detail && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#4e5969', marginBottom: 6 }}>
                  系统扩展审计上下文 (JSON 只读)
                </div>
                <pre
                  style={{
                    backgroundColor: '#f7f8fa',
                    border: '1px solid #e8ebf0',
                    borderRadius: 4,
                    padding: 10,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    maxHeight: 200,
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(selectedEntry.detail, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}

export default AuditLogPage;
