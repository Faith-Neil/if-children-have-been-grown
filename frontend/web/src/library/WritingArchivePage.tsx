// 为什么有这个文件：落实 FE-WRITING-ARCHIVE 写作档案与风格规范主页面（PRD v1.8 §5.6、R35/R43）。
// 它解决什么问题：
// 1. 替换原 nav === 'writing' 的 PendingPage 占位壳，消灭系统全局导航中最后一个空壳；
// 2. 严格按登录会话的 company_id 强隔离展示公司专属语调偏好、自称口径、合规禁用词与优质样章；
// 3. 践行 Layout First 克制设计原则，依靠清晰的 Tabs/Card 布局自解释功能，杜绝说明书堆砌；
// 4. 提供内嵌式交互草稿快速合规检测工具，辅助投标编写人快速排查违规词与反常自称。

import { useMemo, useState } from 'react';
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
  Form,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AlertOutlined,
  BookOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  FileTextOutlined,
  FilterOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from '../shared/types.ts';
import {
  filterForbiddenWords,
  filterQualitySamples,
  FORBIDDEN_CATEGORY_MAP,
  getForbiddenCategoryLabel,
  getSeverityMeta,
  getVolumeLabel,
  getWritingProfile,
  scanDraftText,
  type DraftScanResult,
  type ForbiddenWord,
  type ForbiddenWordFilterParams,
  type QualitySample,
  type QualitySampleFilterParams,
  type TypographyRule,
} from './writing-archive-core.ts';
import { EmptyState } from '../status/StatusViews.tsx';

const { Text, Paragraph, Title } = Typography;
const { TextArea } = Input;

export interface WritingArchivePageProps {
  user?: Account | null;
  session?: ApplicationSession | null;
}

export function WritingArchivePage({ user, session }: WritingArchivePageProps) {
  const companyId = user?.company_id ?? session?.scope?.active_company_id ?? 'alpha';

  // 严格根据当前登录租户读取写作档案配置（租户强隔离）
  const profile = useMemo(() => {
    return getWritingProfile(companyId);
  }, [companyId]);

  // Tab 状态
  const [activeTab, setActiveTab] = useState('style_rules');

  // 禁用词筛选状态
  const [fwSearch, setFwSearch] = useState('');
  const [fwCategory, setFwCategory] = useState('all');
  const [fwSeverity, setFwSeverity] = useState('all');

  // 样章库筛选状态
  const [sampleSearch, setSampleSearch] = useState('');
  const [sampleVolume, setSampleVolume] = useState('all');
  const [selectedSample, setSelectedSample] = useState<QualitySample | null>(null);

  // 交互式草稿检测器状态
  const [draftInput, setDraftInput] = useState('');
  const [scanResult, setScanResult] = useState<DraftScanResult | null>(null);

  function handleScanDraft() {
    if (!draftInput.trim()) {
      setScanResult(null);
      return;
    }
    const res = scanDraftText(draftInput, profile);
    setScanResult(res);
  }

  // 过滤禁用词
  const filteredForbiddenWords = useMemo(() => {
    const params: ForbiddenWordFilterParams = {
      search: fwSearch,
      category: fwCategory,
      severity: fwSeverity,
    };
    return filterForbiddenWords(profile.forbidden_words, params);
  }, [profile.forbidden_words, fwSearch, fwCategory, fwSeverity]);

  // 过滤样章
  const filteredQualitySamples = useMemo(() => {
    const params: QualitySampleFilterParams = {
      search: sampleSearch,
      volume: sampleVolume,
    };
    return filterQualitySamples(profile.quality_samples, params);
  }, [profile.quality_samples, sampleSearch, sampleVolume]);

  // 排版规范表格列
  const typographyColumns: ColumnsType<TypographyRule> = [
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (cat: string) => <Tag color="blue">{cat}</Tag>,
    },
    {
      title: '规范条目',
      dataIndex: 'rule_name',
      key: 'rule_name',
      width: 240,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '详细准则说明',
      dataIndex: 'standard',
      key: 'standard',
    },
    {
      title: '错误示例',
      dataIndex: 'bad_case',
      key: 'bad_case',
      width: 240,
      render: (text?: string) =>
        text ? (
          <Text type="danger" delete style={{ fontSize: 13, background: '#fff1f0', padding: '2px 4px', borderRadius: 4 }}>
            {text}
          </Text>
        ) : '-',
    },
    {
      title: '合规推荐写法',
      dataIndex: 'good_case',
      key: 'good_case',
      width: 240,
      render: (text?: string) =>
        text ? (
          <Text type="success" style={{ fontSize: 13, background: '#f6ffed', padding: '2px 4px', borderRadius: 4, fontWeight: 500 }}>
            {text}
          </Text>
        ) : '-',
    },
  ];

  // 禁用词表格列
  const forbiddenColumns: ColumnsType<ForbiddenWord> = [
    {
      title: '禁用词条',
      dataIndex: 'word',
      key: 'word',
      width: 180,
      render: (text: string, record) => {
        const meta = getSeverityMeta(record.severity);
        return (
          <Space>
            <Tag color={meta.color} style={{ fontSize: 13, fontWeight: 600 }}>
              {text}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 160,
      render: (cat: string) => <Tag>{getForbiddenCategoryLabel(cat)}</Tag>,
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 110,
      render: (sev: any) => {
        const meta = getSeverityMeta(sev);
        return <Badge status={meta.badgeStatus} text={meta.label} />;
      },
    },
    {
      title: '推荐合规替代词',
      dataIndex: 'replacement_suggestion',
      key: 'replacement_suggestion',
      width: 260,
      render: (text: string) => (
        <Text type="success" style={{ fontWeight: 500 }}>
          {text}
        </Text>
      ),
    },
    {
      title: '违规原因与法治审查点',
      dataIndex: 'reason',
      key: 'reason',
    },
  ];

  return (
    <div className="writing-archive-page" style={{ paddingBottom: 24 }}>
      {/* 头部标题区：Layout First 紧凑自解释布局 */}
      <div
        className="page-heading"
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0, fontWeight: 600 }}>
            <FileTextOutlined style={{ marginRight: 8, color: '#1677ff' }} />
            公司写作档案与规范
          </Title>
          <Text type="secondary" style={{ fontSize: 13, marginTop: 4, display: 'block' }}>
            沉淀 {profile.company_name} 专属写作语气偏好、自称口径、排版标准、合规禁用词与标杆样章。
          </Text>
        </div>
        <Space size="large" style={{ background: '#fafafa', padding: '8px 16px', borderRadius: 6, border: '1px solid #f0f0f0' }}>
          <Statistic title="合规禁用词" value={profile.forbidden_words.length} valueStyle={{ fontSize: 18, color: '#cf1322', fontWeight: 600 }} />
          <Statistic title="排版格式规范" value={profile.typography_rules.length} valueStyle={{ fontSize: 18, color: '#1677ff', fontWeight: 600 }} />
          <Statistic title="标杆优质样章" value={profile.quality_samples.length} valueStyle={{ fontSize: 18, color: '#52c41a', fontWeight: 600 }} />
        </Space>
      </div>

      {/* 主 Tabs 分区 */}
      <Card bodyStyle={{ padding: '8px 16px 20px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'style_rules',
              label: (
                <span>
                  <SafetyCertificateOutlined /> 风格与排版规范
                </span>
              ),
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%', marginTop: 8 }}>
                  {/* 第一栏：基础口径偏好 + 交互式快速检测 */}
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={12}>
                      <Card
                        title="自称口径与语调风格偏好"
                        size="small"
                        headStyle={{ background: '#fafafa', fontWeight: 600 }}
                      >
                        <Descriptions size="small" column={1} bordered>
                          <Descriptions.Item label="统一自称口径">
                            <Tag color="geekblue" style={{ fontSize: 13, fontWeight: 600 }}>
                              {profile.self_reference}
                            </Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              （严格保持全标书自称一致，杜绝采购人口吻）
                            </Text>
                          </Descriptions.Item>
                          <Descriptions.Item label="招标人称谓规范">
                            <Tag color="cyan" style={{ fontSize: 13 }}>
                              {profile.tenderer_reference}
                            </Tag>
                          </Descriptions.Item>
                          <Descriptions.Item label="基本语气偏好">
                            <Text style={{ fontWeight: 500 }}>{profile.tone_preference}</Text>
                          </Descriptions.Item>
                          <Descriptions.Item label="段落总结句策略">
                            <Text>{profile.summary_sentence_strategy}</Text>
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card
                        title="草稿段落合规快速诊断"
                        size="small"
                        headStyle={{ background: '#fafafa', fontWeight: 600 }}
                        extra={
                          <Button type="primary" size="small" onClick={handleScanDraft}>
                            合规检测
                          </Button>
                        }
                      >
                        <TextArea
                          rows={4}
                          placeholder="在此粘贴待检查的草稿段落，实时检验是否包含夸大词、绝对化承诺或反常自称口吻..."
                          value={draftInput}
                          onChange={e => {
                            setDraftInput(e.target.value);
                            if (scanResult) setScanResult(null);
                          }}
                          style={{ fontSize: 13 }}
                        />

                        {scanResult && (
                          <div style={{ marginTop: 12 }}>
                            {scanResult.valid ? (
                              <Alert
                                type="success"
                                showIcon
                                message="检测通过"
                                description={`段落字数：${scanResult.totalWordCount} 字。未检出合规禁用词，自称口径符合标准。`}
                              />
                            ) : (
                              <Alert
                                type="warning"
                                showIcon
                                message="检测到潜在合规风险"
                                description={
                                  <Space direction="vertical" size={4} style={{ width: '100%', marginTop: 4 }}>
                                    {scanResult.selfReferenceMismatches.length > 0 && (
                                      <div>
                                        <Text type="danger" strong>
                                          自称错用警告：
                                        </Text>
                                        <Text>
                                          检出采购人口吻/异称：{scanResult.selfReferenceMismatches.map(m => `“${m}”`).join('、')}，请按规范统一修正为“{profile.self_reference}”。
                                        </Text>
                                      </div>
                                    )}
                                    {scanResult.forbiddenHits.length > 0 && (
                                      <div>
                                        <Text type="danger" strong>
                                          命中禁用词 ({scanResult.forbiddenHits.length} 处)：
                                        </Text>
                                        <Space wrap size={[4, 4]} style={{ marginTop: 4 }}>
                                          {scanResult.forbiddenHits.map((h, i) => (
                                            <Tooltip key={i} title={`建议改写为：${h.suggestion}（${h.reason}）`}>
                                              <Tag color={h.severity === 'blocker' ? 'red' : 'gold'}>
                                                {h.word} → {h.suggestion}
                                              </Tag>
                                            </Tooltip>
                                          ))}
                                        </Space>
                                      </div>
                                    )}
                                  </Space>
                                }
                              />
                            )}
                          </div>
                        )}
                      </Card>
                    </Col>
                  </Row>

                  {/* 第二栏：排版与格式规范全景表 */}
                  <Card title="国家公文与投标文件排版规范" size="small" headStyle={{ background: '#fafafa', fontWeight: 600 }}>
                    <Table
                      dataSource={profile.typography_rules}
                      columns={typographyColumns}
                      rowKey="id"
                      pagination={false}
                      size="middle"
                    />
                  </Card>
                </Space>
              ),
            },
            {
              key: 'forbidden_words',
              label: (
                <span>
                  <AlertOutlined /> 禁用词库与合规扫描
                </span>
              ),
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%', marginTop: 8 }}>
                  {/* 检索过滤条 */}
                  <Row gutter={[16, 12]} align="middle">
                    <Col xs={24} sm={10} md={8}>
                      <Input
                        placeholder="搜索禁用词 / 替换建议 / 违规原因..."
                        prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
                        allowClear
                        value={fwSearch}
                        onChange={e => setFwSearch(e.target.value)}
                      />
                    </Col>
                    <Col xs={12} sm={7} md={5}>
                      <Select
                        style={{ width: '100%' }}
                        value={fwCategory}
                        onChange={setFwCategory}
                        options={[
                          { value: 'all', label: '全部类别' },
                          ...Object.entries(FORBIDDEN_CATEGORY_MAP)
                            .filter(([k]) => k !== 'all')
                            .map(([value, label]) => ({ value, label })),
                        ]}
                      />
                    </Col>
                    <Col xs={12} sm={7} md={5}>
                      <Select
                        style={{ width: '100%' }}
                        value={fwSeverity}
                        onChange={setFwSeverity}
                        options={[
                          { value: 'all', label: '全部级别' },
                          { value: 'blocker', label: '强阻断' },
                          { value: 'warning', label: '合规警告' },
                          { value: 'suggestion', label: '润色建议' },
                        ]}
                      />
                    </Col>
                    <Col xs={24} md={6} style={{ textAlign: 'right' }}>
                      <Text type="secondary" style={{ fontSize: 13 }}>
                        共筛选出 {filteredForbiddenWords.length} 条禁用词
                      </Text>
                    </Col>
                  </Row>

                  {/* 禁用词表格 */}
                  <Table
                    dataSource={filteredForbiddenWords}
                    columns={forbiddenColumns}
                    rowKey="id"
                    pagination={{ pageSize: 10, showSizeChanger: true }}
                    size="middle"
                  />
                </Space>
              ),
            },
            {
              key: 'quality_samples',
              label: (
                <span>
                  <BookOutlined /> 典型标杆样章库
                </span>
              ),
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%', marginTop: 8 }}>
                  {/* 检索过滤条 */}
                  <Row gutter={[16, 12]} align="middle">
                    <Col xs={24} sm={12} md={8}>
                      <Input
                        placeholder="搜索样章标题 / 适用章节 / 评分维度..."
                        prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
                        allowClear
                        value={sampleSearch}
                        onChange={e => setSampleSearch(e.target.value)}
                      />
                    </Col>
                    <Col xs={12} sm={6} md={5}>
                      <Select
                        style={{ width: '100%' }}
                        value={sampleVolume}
                        onChange={setSampleVolume}
                        options={[
                          { value: 'all', label: '全部两册' },
                          { value: 'technical', label: '技术分册' },
                          { value: 'business', label: '商务分册' },
                        ]}
                      />
                    </Col>
                    <Col xs={12} sm={6} md={11} style={{ textAlign: 'right' }}>
                      <Text type="secondary" style={{ fontSize: 13 }}>
                        共 {filteredQualitySamples.length} 篇参考样章（供模型 few-shot 学习标准文风）
                      </Text>
                    </Col>
                  </Row>

                  {/* 样章卡片列表 */}
                  {filteredQualitySamples.length === 0 ? (
                    <EmptyState
                      mode="search"
                      searchKeyword={sampleSearch}
                      title="未检索到匹配的标杆样章"
                      description="请尝试调整搜索词或分册筛选条件。"
                      actionText="清空筛选"
                      onAction={() => {
                        setSampleSearch('');
                        setSampleVolume('all');
                      }}
                    />
                  ) : (
                    <Row gutter={[16, 16]}>
                      {filteredQualitySamples.map(sample => (
                        <Col xs={24} md={12} key={sample.id}>
                          <Card
                            hoverable
                            title={
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text strong style={{ fontSize: 14 }}>
                                  {sample.title}
                                </Text>
                                <Tag color={sample.volume === 'technical' ? 'blue' : 'purple'}>
                                  {getVolumeLabel(sample.volume)}
                                </Tag>
                              </div>
                            }
                            extra={
                              <Button
                                type="link"
                                size="small"
                                icon={<EyeOutlined />}
                                onClick={() => setSelectedSample(sample)}
                              >
                                查看范本
                              </Button>
                            }
                            size="small"
                          >
                            <Space direction="vertical" size={8} style={{ width: '100%' }}>
                              <Space size={6} wrap>
                                <Tag color="cyan">{sample.scoring_dimension}</Tag>
                                <Tag style={{ fontFamily: 'monospace' }}>约 {sample.word_count} 字</Tag>
                                <Tag color="default">v{sample.revision}</Tag>
                              </Space>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                适用章节：{sample.chapter_name}
                              </Text>
                              <Paragraph
                                ellipsis={{ rows: 2 }}
                                style={{ fontSize: 13, color: '#4e5969', margin: 0, background: '#fafafa', padding: '6px 10px', borderRadius: 4 }}
                              >
                                {sample.excerpt}
                              </Paragraph>
                            </Space>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 标杆样章完整查阅抽屉 */}
      <Drawer
        title={
          selectedSample ? (
            <Space>
              <span>{selectedSample.title}</span>
              <Tag color={selectedSample.volume === 'technical' ? 'blue' : 'purple'}>
                {getVolumeLabel(selectedSample.volume)}
              </Tag>
            </Space>
          ) : '样章详情'
        }
        open={!!selectedSample}
        onClose={() => setSelectedSample(null)}
        width={720}
      >
        {selectedSample && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions size="small" bordered column={2}>
              <Descriptions.Item label="适用章节" span={2}>
                {selectedSample.chapter_name}
              </Descriptions.Item>
              <Descriptions.Item label="评分维度">{selectedSample.scoring_dimension}</Descriptions.Item>
              <Descriptions.Item label="范本体量">约 {selectedSample.word_count} 字</Descriptions.Item>
              <Descriptions.Item label="版本号">v{selectedSample.revision}</Descriptions.Item>
              <Descriptions.Item label="入库时间">
                <Text style={{ fontFamily: 'monospace' }}>{selectedSample.updated_at.slice(0, 10)}</Text>
              </Descriptions.Item>
            </Descriptions>

            <div>
              <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
                样章全文范本（已满足字数与排版规范）：
              </Text>
              <Card
                size="small"
                style={{
                  background: '#fafafa',
                  borderColor: '#e8e8e8',
                  borderRadius: 6,
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                  fontSize: 14,
                  fontFamily: 'serif, SimHei',
                }}
              >
                {selectedSample.full_content}
              </Card>
            </div>
          </Space>
        )}
      </Drawer>
    </div>
  );
}
export default WritingArchivePage;
