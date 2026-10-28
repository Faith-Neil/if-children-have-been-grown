// 为什么有这个文件：公司知识库管理页（资料管理员/公司管理员）：设置与模型、ICG 摄入流程部署、
// 数据集与文档（上传原件、重解析、重建、停用、分块修正、证书生成资料草稿）、检索试查、操作审计。
// 它解决什么问题：此前知识库只能在 RAGFlow 自带界面里管理，本系统看不到流程、切块与检索效果，也没有留痕。

import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, Card, Descriptions, Drawer, Empty, Form, Input, InputNumber, List, Popconfirm, Select, Space,
  Switch, Table, Tabs, Tag, Typography, Upload,
} from 'antd';
import { CloudUploadOutlined, DeploymentUnitOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { encodeFile, request } from '../shared/api.ts';
import {
  KB_KIND_HINT, KB_KIND_LABEL, KB_UPLOAD_ACCEPT, datasetWarnings, embeddingChangeWarning, kbApi, kbPermissions,
  settingsDiff, type KbKind, type KbSearchKind, type KbSettings,
} from './kb-admin-core.ts';
import { kbStatusMeta } from './knowledge-base-core.ts';

type Row = Record<string, any>;

export interface KnowledgeBaseAdminPageProps {
  token: string | null;
  role?: string | null;
  report?: (error: unknown) => void;
}

export function KnowledgeBaseAdminPage({ token, role, report }: KnowledgeBaseAdminPageProps) {
  const perms = kbPermissions(role);
  const [overview, setOverview] = useState<Row | null>(null);
  const [notice, setNotice] = useState('');

  async function call<T>(path: string, method = 'GET', body?: unknown, revision?: number): Promise<T | null> {
    try {
      return await request<T>(path, token, method, body, revision);
    } catch (error) {
      report?.(error);
      return null;
    }
  }
  async function loadOverview() { setOverview(await call<Row>(kbApi.overview)); }
  useEffect(() => { if (perms.read) void loadOverview(); }, [token]);

  if (!perms.read) {
    return <Alert type="info" showIcon message="知识库管理仅对公司管理员、资料管理员与项目负责人开放。" />;
  }
  if (!overview) return <Card loading />;

  return (
    <div data-testid="kb-admin-page">
      {!overview.enabled && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="尚未连接 RAGFlow"
          description="请公司管理员在“知识库配置”中填写内网 RAGFlow 地址与 API Key 并启用。" />
      )}
      {notice && <Alert type="success" showIcon closable style={{ marginBottom: 12 }} message={notice} onClose={() => setNotice('')} />}
      <Tabs items={[
        { key: 'settings', label: '设置与摄入流程', children: <SettingsTab {...{ call, perms, overview, reload: loadOverview, setNotice }} /> },
        { key: 'datasets', label: '数据集与文档', children: <DatasetsTab {...{ call, perms, token, report, setNotice }} /> },
        { key: 'retrieval', label: '检索试查', children: <RetrievalTab call={call} /> },
        { key: 'audit', label: '操作审计', children: <AuditTab call={call} /> },
      ]} />
    </div>
  );
}

type Call = <T>(path: string, method?: string, body?: unknown, revision?: number) => Promise<T | null>;

function SettingsTab({ call, perms, overview, reload, setNotice }: {
  call: Call; perms: ReturnType<typeof kbPermissions>; overview: Row; reload: () => Promise<void>; setNotice: (s: string) => void;
}) {
  const [settings, setSettings] = useState<KbSettings | null>(null);
  const [models, setModels] = useState<Record<string, Row[]>>({ embedding: [], rerank: [], chat: [] });
  const [pipelines, setPipelines] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [form] = Form.useForm();

  async function load() {
    const [s, p] = await Promise.all([call<KbSettings>(kbApi.settings), call<{ items: Row[] }>(kbApi.pipelines)]);
    if (s) { setSettings(s); form.setFieldsValue(s); }
    setPipelines(p?.items ?? []);
    if (overview.enabled) setModels((await call<Record<string, Row[]>>(kbApi.models)) ?? { embedding: [], rerank: [], chat: [] });
  }
  useEffect(() => { void load(); }, []);

  async function save() {
    if (!settings) return;
    const diff = settingsDiff(settings, form.getFieldsValue());
    if (!Object.keys(diff).length) return;
    setBusy(true);
    const saved = await call<KbSettings>(kbApi.settings, 'PUT', diff, settings.revision);
    setBusy(false);
    if (saved) {
      setSettings(saved);
      setNotice(['设置已保存。', embeddingChangeWarning(settings, diff)].filter(Boolean).join(''));
      await reload();
    }
  }
  async function deploy() {
    setBusy(true);
    const result = await call<Row>(kbApi.deploy, 'POST', {});
    setBusy(false);
    if (result) { setNotice('摄入流程已部署并绑定数据集。已有文档需在“数据集与文档”中重新解析才按新流程切块。'); await load(); await reload(); }
  }
  const options = (rows: Row[]) => rows.map(m => ({ value: m.id, label: `${m.name}（${m.provider}）` }));

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title="检索与模型设置" extra={<Button type="primary" onClick={() => void save()} loading={busy} disabled={!perms.write}>保存</Button>}>
        <Form form={form} layout="vertical" disabled={!perms.write}>
          <Space wrap size="large" align="start">
            <Form.Item name="embedding_model" label="嵌入模型" tooltip="所有数据集必须使用同一嵌入模型；更换后需重建。生产须用内网模型。" style={{ width: 320 }}>
              <Select allowClear showSearch options={options(models.embedding)} placeholder="RAGFlow 租户默认" />
            </Form.Item>
            <Form.Item name="rerank_id" label="重排模型" style={{ width: 320 }}>
              <Select allowClear showSearch options={options(models.rerank)} placeholder="不重排" />
            </Form.Item>
            <Form.Item name="llm_id" label="摄入抽取模型" tooltip="用于生成招标式问法、关键词与元数据。" style={{ width: 320 }}>
              <Select allowClear showSearch options={options(models.chat)} placeholder="RAGFlow 租户默认" />
            </Form.Item>
          </Space>
          <Space wrap size="large">
            <Form.Item name="similarity_threshold" label="相似度阈值"><InputNumber min={0} max={1} step={0.05} /></Form.Item>
            <Form.Item name="keywords_weight" label="关键词权重" tooltip="余下为向量权重。"><InputNumber min={0} max={1} step={0.05} /></Form.Item>
            <Form.Item name="use_pipelines" label="使用 ICG 摄入流程" valuePropName="checked"><Switch /></Form.Item>
          </Space>
        </Form>
      </Card>
      <Card size="small" title="ICG 摄入流程（招投标专用）"
        extra={<Button icon={<DeploymentUnitOutlined />} onClick={() => void deploy()} loading={busy} disabled={!perms.write || !overview.enabled}>部署 / 升级</Button>}>
        <Table<Row> size="small" rowKey="key" pagination={false} dataSource={pipelines} columns={[
          { title: '流程', dataIndex: 'title', width: 200 },
          { title: '说明', dataIndex: 'description' },
          { title: '切块', dataIndex: 'chunker', width: 80, render: v => (v === 'title' ? '按标题' : '按长度') },
          { title: 'LLM 增强', width: 140, render: (_, r) => [r.questions_top_n ? `问法×${r.questions_top_n}` : '', r.keywords_top_n ? `关键词×${r.keywords_top_n}` : '', r.metadata_fields?.length ? '元数据' : ''].filter(Boolean).join('、') || '无' },
          { title: '部署', width: 130, render: (_, r) => (r.deployed ? <Tag color="green">v{r.deployed.version}</Tag> : <Tag>未部署</Tag>) },
        ]} />
      </Card>
    </Space>
  );
}

function DatasetsTab({ call, perms, token, report, setNotice }: {
  call: Call; perms: ReturnType<typeof kbPermissions>; token: string | null; report?: (e: unknown) => void; setNotice: (s: string) => void;
}) {
  const [kind, setKind] = useState<KbKind>('history');
  const [datasets, setDatasets] = useState<Row[]>([]);
  const [docs, setDocs] = useState<Row[]>([]);
  const [chunksOf, setChunksOf] = useState<Row | null>(null);
  const [chunks, setChunks] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const info = useMemo(() => datasets.find(d => d.kind === kind), [datasets, kind]);

  async function load() {
    setDatasets((await call<{ items: Row[] }>(kbApi.datasets))?.items ?? []);
    setDocs((await call<{ items: Row[] }>(kbApi.documents(kind)))?.items ?? []);
  }
  useEffect(() => { void load(); }, [kind]);
  // 有文档在解析时每 8 秒刷新一次状态与分块数。
  const parsing = docs.some(d => d.status === 'unsynced');
  useEffect(() => {
    if (!parsing) return undefined;
    const timer = setInterval(() => { void load(); }, 8000);
    return () => clearInterval(timer);
  }, [parsing, kind]);

  async function action(path: string, method = 'POST', body: unknown = {}, done = '') {
    setBusy(true);
    const result = await call<Row>(path, method, body);
    setBusy(false);
    if (result) { if (done) setNotice(done); await load(); }
    return result;
  }
  async function upload(file: File) {
    if (kind === 'library') return false;
    try {
      const content_base64 = await encodeFile(file);
      await action(kbApi.documents(kind).split('?')[0], 'POST', { filename: file.name, content_base64, content_type: file.type }, `已上传并开始解析：${file.name}`);
    } catch (error) { report?.(error); }
    return false;
  }
  async function openChunks(doc: Row) {
    setChunksOf(doc);
    setChunks((await call<{ chunks: Row[] }>(kbApi.chunks(kind, doc.document_id)))?.chunks ?? []);
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Space wrap>
        <Select<KbKind> value={kind} onChange={setKind} style={{ width: 260 }}
          options={(Object.keys(KB_KIND_LABEL) as KbKind[]).map(k => ({ value: k, label: KB_KIND_LABEL[k] }))} />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
        {kind !== 'library' && (
          <Upload accept={KB_UPLOAD_ACCEPT[kind]} showUploadList={false} beforeUpload={file => upload(file)} disabled={!perms.write}>
            <Button icon={<CloudUploadOutlined />} disabled={!perms.write} loading={busy}>上传原件</Button>
          </Upload>
        )}
        <Popconfirm title="按当前流程重新解析该类全部文档？" onConfirm={() => void action(kbApi.datasetAction(kind, 'reparse'), 'POST', {}, '已开始重新解析。')} disabled={!perms.write || !info?.dataset_id}>
          <Button disabled={!perms.write || !info?.dataset_id}>全部重新解析</Button>
        </Popconfirm>
        <Popconfirm title="重建会新建数据集、迁移原件并删除旧数据集，期间检索可能不完整。确定？" onConfirm={() => void action(kbApi.datasetAction(kind, 'rebuild'), 'POST', {}, '重建完成，文档正在解析。')} disabled={!perms.write || !info?.dataset_id}>
          <Button danger disabled={!perms.write || !info?.dataset_id}>重建</Button>
        </Popconfirm>
      </Space>
      <Alert type="info" showIcon message={KB_KIND_HINT[kind]} />
      <Descriptions size="small" bordered column={4}>
        <Descriptions.Item label="数据集">{info?.name ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="解析方式">{info?.mode === 'pipeline' ? `ICG 流程（${info.profile}）` : info?.mode ? '内置解析器' : '未建立'}</Descriptions.Item>
        <Descriptions.Item label="文档 / 分块">{info?.document_count ?? '-'} / {info?.chunk_count ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="提示">{datasetWarnings(info?.dataset_id ? info : null).map(w => <Tag key={w} color="orange">{w}</Tag>)}</Descriptions.Item>
      </Descriptions>
      <Table<Row> size="small" rowKey="document_id" dataSource={docs} pagination={{ pageSize: 15 }} locale={{ emptyText: <Empty description="暂无文档" /> }} columns={[
        { title: '文档', dataIndex: 'name', ellipsis: true },
        { title: '进度', dataIndex: 'progress', width: 90, render: (v: number, r) => (r.status === 'unsynced' ? `${Math.round((v || 0) * 100)}%` : '') },
        { title: '状态', dataIndex: 'status', width: 110, render: v => { const m = kbStatusMeta(v === 'unsynced' ? 'parsing' : v); return <Tag color={m.color}>{m.label}</Tag>; } },
        { title: '分块', dataIndex: 'chunk_count', width: 70 },
        { title: '说明', dataIndex: 'message', width: 160, ellipsis: true, render: (v: string, r) => (r.status === 'failed' ? <Typography.Text type="danger">{v}</Typography.Text> : '') },
        { title: '元数据', dataIndex: 'meta_fields', ellipsis: true, render: (m: Row) => Object.entries(m || {}).filter(([k]) => !['company_id', 'source_type', 'source_id', 'knowledge_kind'].includes(k)).map(([k, v]) => `${k}=${v}`).join('；') },
        { title: '启用', dataIndex: 'enabled', width: 70, render: (v, r) => <Switch size="small" checked={v} disabled={!perms.write} onChange={checked => void action(kbApi.document(kind, r.document_id), 'PATCH', { enabled: checked })} /> },
        { title: '操作', width: 300, render: (_, r) => (
          <Space size={4} wrap>
            <Button size="small" onClick={() => void openChunks(r)}>分块</Button>
            <Button size="small" disabled={!perms.write} onClick={() => void action(`${kbApi.document(kind, r.document_id)}/reparse`, 'POST', {}, '已开始重新解析。')}>重解析</Button>
            {kind === 'certificate' && <Button size="small" disabled={!perms.write || r.status !== 'synced'} onClick={() => void action(kbApi.certificateDraft(r.document_id), 'POST', {}, '已生成“待核验”资料，请到企业资料库核对原件后确认。')}>生成资料草稿</Button>}
            {kind !== 'library' && (
              <Popconfirm title="从知识库删除该原件？" onConfirm={() => void action(kbApi.document(kind, r.document_id), 'DELETE', undefined, '已删除。')}>
                <Button size="small" danger disabled={!perms.write}>删除</Button>
              </Popconfirm>
            )}
          </Space>
        ) },
      ]} />
      <Drawer width={720} open={!!chunksOf} title={chunksOf ? `分块：${chunksOf.name}` : ''} onClose={() => setChunksOf(null)}>
        <List dataSource={chunks} renderItem={c => (
          <List.Item actions={[
            <Switch key="a" size="small" checked={c.available} disabled={!perms.write} checkedChildren="用" unCheckedChildren="停"
              onChange={async checked => { await call(kbApi.chunk(kind, chunksOf!.document_id, c.id), 'PATCH', { available: checked }); await openChunks(chunksOf!); }} />,
          ]}>
            <List.Item.Meta
              title={<Space wrap>{c.important_keywords?.map((k: string) => <Tag key={k}>{k}</Tag>)}</Space>}
              description={<>
                <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 4 }} ellipsis={{ rows: 6, expandable: true }}>{c.content}</Typography.Paragraph>
                {c.questions?.length > 0 && <Typography.Text type="secondary">招标式问法：{c.questions.join('；')}</Typography.Text>}
              </>}
            />
          </List.Item>
        )} />
      </Drawer>
    </Space>
  );
}

function RetrievalTab({ call }: { call: Call }) {
  const [form] = Form.useForm();
  const [result, setResult] = useState<Row | null>(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    const values = form.getFieldsValue();
    if (!values.query?.trim()) return;
    setBusy(true);
    const body = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== undefined && v !== null && v !== ''));
    setResult(await call<Row>(kbApi.retrieval, 'POST', body));
    setBusy(false);
  }
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Form form={form} layout="inline" initialValues={{ kinds: ['evidence', 'snippet', 'history'] as KbSearchKind[], limit: 8 }} onFinish={() => void run()}>
        <Form.Item name="query" style={{ width: 420 }}><Input placeholder="例如：投标人须具备信息安全管理体系认证" /></Form.Item>
        <Form.Item name="kinds"><Select mode="multiple" style={{ width: 260 }} options={[{ value: 'evidence', label: '资料' }, { value: 'snippet', label: '片段' }, { value: 'history', label: '历史参考' }]} /></Form.Item>
        <Form.Item name="similarity_threshold" label="阈值"><InputNumber min={0} max={1} step={0.05} placeholder="默认" /></Form.Item>
        <Form.Item name="keywords_weight" label="关键词权重"><InputNumber min={0} max={1} step={0.05} placeholder="默认" /></Form.Item>
        <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={busy}>试查</Button>
      </Form>
      {result && (result.items.length ? (
        <List dataSource={result.items as Row[]} renderItem={h => (
          <List.Item>
            <List.Item.Meta title={<Space>{h.cite_tag}<span>{h.name}</span><Tag>{h.score}</Tag>{h.reference_only ? <Tag color="orange">仅参考</Tag> : h.attachable ? <Tag color="green">可人工挂接为证据</Tag> : <Tag color="blue">写作素材</Tag>}</Space>}
              description={<Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }} ellipsis={{ rows: 4, expandable: true }}>{h.content}</Typography.Paragraph>} />
          </List.Item>
        )} />
      ) : <Empty description={`没有命中：${result.skipped_reason || '无'}`} />)}
    </Space>
  );
}

function AuditTab({ call }: { call: Call }) {
  const [rows, setRows] = useState<Row[]>([]);
  useEffect(() => { void (async () => setRows((await call<{ items: Row[] }>(kbApi.audit))?.items ?? []))(); }, []);
  return <Table<Row> size="small" rowKey="id" dataSource={rows} pagination={{ pageSize: 20 }} columns={[
    { title: '时间', dataIndex: 'at', width: 200 }, { title: '操作人', dataIndex: 'actor_name', width: 160 },
    { title: '操作', dataIndex: 'action', width: 160 }, { title: '对象', dataIndex: 'target', ellipsis: true },
    { title: '详情', dataIndex: 'detail', ellipsis: true, render: v => JSON.stringify(v) },
  ]} />;
}

export default KnowledgeBaseAdminPage;
