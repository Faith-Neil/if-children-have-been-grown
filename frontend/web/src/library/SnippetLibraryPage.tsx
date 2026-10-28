// 为什么有这个文件：落实 FE-SNIPPET-LIBRARY 方案片段知识库最小页（PRD v1.8 §5.5）。
// 它解决什么问题：
// 1. 替换原 nav === 'knowledge' 的 PendingPage 占位壳，提供可查看真实方案片段的主路径体验；
// 2. 严格按登录会话的 company_id 进行租户级隔离展示，防止跨租户泄密；
// 3. 按照 Layout First 原则，视觉层级分明，无堆砌次级标签和说明书长文；
// 4. 支持查看片段标题、分类/产品、套话组、版本与更新时间，点击可展开查看正文及变量；
// 5. 提供标准 Empty 空状态、加载态与一键快速检索过滤。

import { useEffect, useMemo, useState } from 'react';
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
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CheckCircleOutlined,
  CopyOutlined,
  DatabaseOutlined,
  EyeOutlined,
  FilterOutlined,
  ReloadOutlined,
  SearchOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from '../shared/types.ts';
import {
  computeSnippetStats,
  filterSnippets,
  formatMonospaceTime,
  getSnippetSyncStatusMeta,
  getSnippetTypeLabel,
  loadSnippetPublications,
  resolveSnippetTitle,
  SNIPPET_TYPE_MAP,
  type SnippetFilterParams,
  type SnippetPublication,
} from './snippet-library-core.ts';
import { EmptyState } from '../status/StatusViews.tsx';
import { request } from '../shared/api.ts';
import { SnippetEditorDrawer } from './SnippetEditorDrawer.tsx';

const { Text, Paragraph, Title } = Typography;

export interface SnippetLibraryPageProps {
  token?: string | null;
  user?: Account | null;
  session?: ApplicationSession | null;
  initialSnippets?: SnippetPublication[];
  onSelectSnippet?: (snippet: SnippetPublication) => void;
}

/**
 * 高亮正文中的 {{variable}} 变量
 */
function renderHighlightedBody(text?: string | null) {
  if (!text) return <Text type="secondary">（无正文内容）</Text>;
  const parts = text.split(/(\{\{[A-Za-z0-9_.-]+\}\})/g);
  return (
    <span style={{ lineHeight: 1.8, fontSize: 14 }}>
      {parts.map((part, index) => {
        if (part.startsWith('{{') && part.endsWith('}}')) {
          const varName = part.slice(2, -2);
          return (
            <Tag
              key={index}
              color="cyan"
              style={{
                margin: '0 2px',
                fontFamily: 'ui-monospace, monospace',
                fontWeight: 600,
                color: '#005C66',
                backgroundColor: '#E6F7F7',
                borderColor: '#87E8DE',
              }}
            >
              {`{{${varName}}}`}
            </Tag>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </span>
  );
}

export function SnippetLibraryPage({
  token,
  user,
  session,
  initialSnippets,
  onSelectSnippet,
}: SnippetLibraryPageProps) {
  const companyId = user?.company_id ?? session?.scope?.active_company_id ?? 'alpha';

  const [snippets, setSnippets] = useState<SnippetPublication[]>(() => initialSnippets ?? []);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedSnippet, setSelectedSnippet] = useState<SnippetPublication | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // 筛选参数
  const [search, setSearch] = useState('');
  const [snippetType, setSnippetType] = useState('all');
  const [syncStatus, setSyncStatus] = useState('all');
  const [onlyPublished, setOnlyPublished] = useState(true);

  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [editing, setEditing] = useState<SnippetPublication | null | undefined>(undefined); // undefined=关闭，null=新建
  const canWrite = ['editor', 'manager', 'bid_writer', 'project_lead', 'company_admin', 'data_admin', 'platform_admin'].includes(user?.role ?? '');
  function upsertSnippet(item: SnippetPublication) {
    setSnippets(prev => (prev.some(row => row.id === item.id) ? prev.map(row => (row.id === item.id ? item : row)) : [item, ...prev]));
  }
  const [syncNotice, setSyncNotice] = useState<{ type: 'success' | 'warning' | 'error'; text: string } | null>(null);

  // 同步到公司知识库：只有 RAGFlow 解析完成才显示“已同步”；解析需要时间时如实提示稍后刷新。
  async function syncSnippet(record: SnippetPublication) {
    setSyncingId(record.id);
    setSyncNotice(null);
    try {
      const result = await request<{ synced: boolean; item: SnippetPublication }>(
        `/api/v1/snippet-publications/${encodeURIComponent(record.id)}/sync`, token ?? null, 'POST', {}, record.published_revision ?? 0);
      setSnippets(prev => prev.map(item => (item.id === record.id ? { ...item, ...result.item } : item)));
      setSyncNotice(result.synced
        ? { type: 'success', text: `“${resolveSnippetTitle(record)}”已进入知识库，可在写作时检索。` }
        : result.item.kb_sync_status === 'failed'
          ? { type: 'error', text: `“${resolveSnippetTitle(record)}”同步失败，请到知识库管理查看原因。` }
          : { type: 'warning', text: `“${resolveSnippetTitle(record)}”已提交知识库，正在解析，稍后刷新查看。若未配置知识库，请联系公司管理员。` });
    } catch (error) {
      setSyncNotice({ type: 'error', text: error instanceof Error ? error.message : '同步失败' });
    } finally {
      setSyncingId(null);
    }
  }

  // 加载数据：只显示后台真实片段，失败时如实提示，不用示例数据顶替。
  async function reloadSnippets() {
    setLoading(true);
    setLoadError(null);
    try {
      setSnippets((await loadSnippetPublications(token ?? null)) ?? []);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '方案片段加载失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialSnippets && initialSnippets.length > 0) {
      setSnippets(initialSnippets);
      return;
    }
    void reloadSnippets();
  }, [token, companyId]);

  // 严格隔离后的过滤列表
  const filteredSnippets = useMemo(() => {
    const params: SnippetFilterParams = {
      search,
      snippet_type: snippetType,
      kb_sync_status: syncStatus,
      onlyPublished,
    };
    return filterSnippets(snippets, params, companyId);
  }, [snippets, search, snippetType, syncStatus, onlyPublished, companyId]);

  // 统计指标
  const stats = useMemo(() => {
    return computeSnippetStats(snippets, companyId);
  }, [snippets, companyId]);

  function handleCopySnippetId(id: string) {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(id).then(() => {
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      }).catch(() => {});
    }
  }

  // 表格列定义
  const columns: ColumnsType<SnippetPublication> = [
    {
      title: '方案片段',
      key: 'title',
      dataIndex: 'title',
      width: 260,
      render: (_, record) => {
        const displayTitle = resolveSnippetTitle(record);
        return (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Button
              type="link"
              style={{ padding: 0, height: 'auto', fontWeight: 600, textAlign: 'left', whiteSpace: 'normal' }}
              onClick={() => {
                setSelectedSnippet(record);
                onSelectSnippet?.(record);
              }}
            >
              {displayTitle}
            </Button>
            <Space size={6} wrap>
              <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
                {record.id}
              </Text>
              {record.source_group && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  · {record.source_group}
                </Text>
              )}
            </Space>
          </Space>
        );
      },
    },
    {
      title: '分类 / 产品',
      key: 'category_product',
      width: 170,
      render: (_, record) => {
        return (
          <Space direction="vertical" size={2}>
            <Text style={{ fontWeight: 500 }}>{record.product || '-'}</Text>
            <div>
              <Tag color="blue" style={{ margin: 0, fontSize: 12 }}>
                {getSnippetTypeLabel(record.snippet_type)}
              </Tag>
            </div>
          </Space>
        );
      },
    },
    {
      title: '套话组',
      dataIndex: 'boilerplate_group',
      key: 'boilerplate_group',
      width: 140,
      render: (val: string | undefined) => val || <Text type="secondary">-</Text>,
    },
    {
      title: '版本',
      key: 'revision',
      width: 90,
      render: (_, record) => {
        const isPublished = (record.published_revision ?? 0) > 0;
        return (
          <Tag
            color={isPublished ? 'cyan' : 'default'}
            style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 600 }}
          >
            {isPublished ? `v${record.published_revision}` : `草稿 v${record.draft_revision ?? 1}`}
          </Tag>
        );
      },
    },
    {
      title: '声明变量',
      key: 'variables',
      width: 150,
      render: (_, record) => {
        const count = record.variables?.length ?? 0;
        if (count === 0) return <Text type="secondary">0 个</Text>;
        const firstTwo = record.variables.slice(0, 2);
        return (
          <Space size={4} wrap>
            <Tag color="purple" style={{ margin: 0 }}>
              {count} 个变量
            </Tag>
            {firstTwo.map(v => (
              <Tag key={v} style={{ margin: 0, fontSize: 11, fontFamily: 'monospace' }}>
                {`{{${v}}}`}
              </Tag>
            ))}
            {count > 2 && <Text type="secondary" style={{ fontSize: 11 }}>+{count - 2}</Text>}
          </Space>
        );
      },
    },
    {
      title: '知识库同步',
      key: 'kb_sync_status',
      width: 130,
      render: (_, record) => {
        const meta = getSnippetSyncStatusMeta(record.kb_sync_status);
        const published = (record.published_revision ?? 0) > 0;
        return (
          <Space size={4}>
            <Badge status={meta.badgeStatus} text={meta.label} />
            {published && record.kb_sync_status !== 'synced' && (
              <Button type="link" size="small" loading={syncingId === record.id} disabled={!!syncingId}
                onClick={() => void syncSnippet(record)} data-testid={`snippet-sync-${record.id}`}>
                同步
              </Button>
            )}
          </Space>
        );
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (val: string) => (
        <Text style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>
          {formatMonospaceTime(val)}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedSnippet(record);
            onSelectSnippet?.(record);
          }}
        >
          查看正文
        </Button>
        <Button type="link" size="small" style={{ padding: 0 }} onClick={() => setEditing(record)} data-testid={`snippet-edit-${record.id}`}>
          {canWrite ? '编辑 / 发布' : '查看草稿'}
        </Button>
        </Space>
      ),
    },
  ];

  const hasFilterActive = search.trim() !== '' || snippetType !== 'all' || syncStatus !== 'all' || !onlyPublished;

  return (
    <div className="snippet-library-page" style={{ paddingBottom: 24 }}>
      {/* 头部标题区：Layout First，通过清晰的布局表达功能 */}
      <div className="page-heading" style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={3} style={{ margin: 0, fontWeight: 600 }}>
            <DatabaseOutlined style={{ marginRight: 8, color: '#0E8A8A' }} />
            知识库方案片段
          </Title>
          <Text type="secondary" style={{ fontSize: 13, marginTop: 4, display: 'block' }}>
            管理并沉淀经核验的方案切片与标准套话，支持按变量注入章节生成。已严格隔离当前租户（{companyId}）。
          </Text>
        </div>
        <Space size="large" align="center">
        {canWrite && <Button type="primary" onClick={() => setEditing(null)} data-testid="snippet-create-button">新建片段</Button>}
        <Space size="large" style={{ background: '#fafafa', padding: '8px 16px', borderRadius: 6, border: '1px solid #f0f0f0' }}>
          <Statistic title="已发布片段" value={stats.publishedCount} suffix={`/ ${stats.totalCount}`} valueStyle={{ fontSize: 18, fontWeight: 600 }} />
          <Statistic title="已同步知识库" value={stats.syncedCount} valueStyle={{ fontSize: 18, color: '#52c41a', fontWeight: 600 }} />
          <Statistic title="已声明变量" value={stats.variablesCount} valueStyle={{ fontSize: 18, color: '#1677ff', fontWeight: 600 }} />
        </Space>
        </Space>
      </div>

      {/* 检索与操作条 */}
      <Card bodyStyle={{ padding: 16 }} style={{ marginBottom: 16 }}>
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} sm={10} md={8}>
            <Input
              placeholder="搜索片段标题 / 产品 / 套话组 / 变量 / 正文"
              prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
              allowClear
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </Col>
          <Col xs={12} sm={7} md={5}>
            <Select
              style={{ width: '100%' }}
              value={snippetType}
              onChange={setSnippetType}
              options={[
                { value: 'all', label: '全部分类' },
                ...Object.entries(SNIPPET_TYPE_MAP)
                  .filter(([k]) => k !== 'all')
                  .map(([value, label]) => ({ value, label })),
              ]}
            />
          </Col>
          <Col xs={12} sm={7} md={5}>
            <Select
              style={{ width: '100%' }}
              value={syncStatus}
              onChange={setSyncStatus}
              options={[
                { value: 'all', label: '全部同步状态' },
                { value: 'synced', label: '已同步知识库' },
                { value: 'unsynced', label: '未同步知识库' },
                { value: 'failed', label: '同步失败' },
              ]}
            />
          </Col>
          <Col xs={24} md={6} style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Space size="middle">
              <Space size={6}>
                <Switch size="small" checked={onlyPublished} onChange={setOnlyPublished} id="only-published-switch" />
                <label htmlFor="only-published-switch" style={{ fontSize: 13, cursor: 'pointer', color: '#4e5969' }}>
                  仅已发布
                </label>
              </Space>
              <Button
                icon={<ReloadOutlined spin={loading} />}
                onClick={() => void reloadSnippets()}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 主数据列表 */}
      {loadError && <Alert type="error" showIcon style={{ marginBottom: 12 }} message={loadError} data-testid="snippet-load-error" />}
      {syncNotice && <Alert type={syncNotice.type} showIcon closable style={{ marginBottom: 12 }} message={syncNotice.text} onClose={() => setSyncNotice(null)} />}
      <Card bodyStyle={{ padding: 0 }}>
        <Spin spinning={loading}>
          {filteredSnippets.length === 0 ? (
            <div style={{ padding: '48px 16px' }}>
              {hasFilterActive ? (
                <EmptyState
                  mode="search"
                  searchKeyword={search}
                  title="未检索到匹配的方案片段"
                  description="请尝试调整搜索关键词或重置分类筛选条件。"
                  actionText="清空筛选条件"
                  onAction={() => {
                    setSearch('');
                    setSnippetType('all');
                    setSyncStatus('all');
                    setOnlyPublished(true);
                  }}
                />
              ) : (
                <EmptyState
                  mode="empty"
                  title="暂无方案片段"
                  description="当前企业知识库暂无已发布方案片段。创建并发布方案片段后可在此集中查阅。"
                />
              )}
            </div>
          ) : (
            <Table
              dataSource={filteredSnippets}
              columns={columns}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showTotal: total => `共 ${total} 条片段`,
                showSizeChanger: true,
              }}
              expandable={{
                expandedRowRender: record => (
                  <div style={{ padding: '12px 16px', background: '#fafafa', borderRadius: 4 }}>
                    <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong style={{ fontSize: 13, color: '#1d2129' }}>
                        正文预览（已高亮变量）：
                      </Text>
                      <Button
                        type="link"
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => {
                          setSelectedSnippet(record);
                          onSelectSnippet?.(record);
                        }}
                      >
                        在新侧抽屉中完整查看
                      </Button>
                    </div>
                    <Card size="small" bordered={false} style={{ background: '#fff' }}>
                      {renderHighlightedBody(record.published_body || record.draft_body)}
                    </Card>
                  </div>
                ),
                rowExpandable: record => Boolean(record.published_body || record.draft_body),
              }}
            />
          )}
        </Spin>
      </Card>

      {/* 方案片段详情查看抽屉 */}
      <Drawer
        title={
          selectedSnippet ? (
            <Space>
              <span>{resolveSnippetTitle(selectedSnippet)}</span>
              <Tag
                color={(selectedSnippet.published_revision ?? 0) > 0 ? 'cyan' : 'default'}
                style={{ fontFamily: 'monospace' }}
              >
                v{selectedSnippet.published_revision || selectedSnippet.draft_revision || 1}
              </Tag>
            </Space>
          ) : '方案片段详情'
        }
        open={!!selectedSnippet}
        onClose={() => setSelectedSnippet(null)}
        width={680}
        extra={
          selectedSnippet && (
            <Space>
              <Tooltip title={copiedId === selectedSnippet.id ? '已复制' : '复制片段 ID'}>
                <Button
                  size="small"
                  icon={copiedId === selectedSnippet.id ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
                  onClick={() => handleCopySnippetId(selectedSnippet.id)}
                >
                  {selectedSnippet.id}
                </Button>
              </Tooltip>
            </Space>
          )
        }
      >
        {selectedSnippet && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions size="small" bordered column={2}>
              <Descriptions.Item label="归属产品">{selectedSnippet.product || '-'}</Descriptions.Item>
              <Descriptions.Item label="片段分类">
                <Tag color="blue">{getSnippetTypeLabel(selectedSnippet.snippet_type)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="套话组">{selectedSnippet.boilerplate_group || '-'}</Descriptions.Item>
              <Descriptions.Item label="来源组">{selectedSnippet.source_group || '-'}</Descriptions.Item>
              <Descriptions.Item label="知识库同步">
                <Badge
                  status={getSnippetSyncStatusMeta(selectedSnippet.kb_sync_status).badgeStatus}
                  text={getSnippetSyncStatusMeta(selectedSnippet.kb_sync_status).label}
                />
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                <Text style={{ fontFamily: 'monospace' }}>
                  {formatMonospaceTime(selectedSnippet.updated_at)}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            <div>
              <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
                声明变量 ({selectedSnippet.variables?.length ?? 0})
              </Text>
              {selectedSnippet.variables && selectedSnippet.variables.length > 0 ? (
                <Space size={[6, 8]} wrap>
                  {selectedSnippet.variables.map(v => (
                    <Tag
                      key={v}
                      color="purple"
                      style={{
                        padding: '2px 8px',
                        fontFamily: 'ui-monospace, monospace',
                        fontSize: 13,
                      }}
                    >
                      {`{{${v}}}`}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">本片段无声明变量，为静态标准正文。</Text>
              )}
            </div>

            <Divider style={{ margin: '8px 0' }} />

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Text strong style={{ fontSize: 14 }}>
                  已发布正文
                </Text>
                <Tag color="green">当前生效版本</Tag>
              </div>
              <Card
                size="small"
                style={{
                  background: '#fcfcfc',
                  borderColor: '#e8e8e8',
                  borderRadius: 6,
                }}
              >
                {renderHighlightedBody(selectedSnippet.published_body)}
              </Card>
            </div>

            {selectedSnippet.draft_body && selectedSnippet.draft_body !== selectedSnippet.published_body && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 14, color: '#fa8c16' }}>
                    未发布草稿预览
                  </Text>
                  <Tag color="orange">草稿版本 v{selectedSnippet.draft_revision}</Tag>
                </div>
                <Card
                  size="small"
                  style={{
                    background: '#fffbf6',
                    borderColor: '#ffd591',
                    borderRadius: 6,
                  }}
                >
                  {renderHighlightedBody(selectedSnippet.draft_body)}
                </Card>
              </div>
            )}
          </Space>
        )}
      </Drawer>
      <SnippetEditorDrawer open={editing !== undefined} token={token ?? null} snippet={editing ?? null} canWrite={canWrite}
        onClose={() => setEditing(undefined)} onSaved={item => { upsertSnippet(item); setEditing(item); }} />
    </div>
  );
}
export default SnippetLibraryPage;
