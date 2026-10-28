// 为什么有这个文件：按 ICG 示例实现项目主链路中的业务页签。
// 它解决什么问题：上传与解析、响应和证据、检查与两册导出都调用后台真实结果。
import { useEffect, useRef, useState } from 'react';
import { Alert, App as AntApp, Badge, Button, Card, Col, Collapse, Descriptions, Drawer, Empty, Form, Input, List, Modal, Progress, Radio, Row, Select, Space, Statistic, Steps, Table, Tabs, Tag, Tooltip, Upload } from 'antd';
import { CheckCircleOutlined, DownloadOutlined, FileTextOutlined, LinkOutlined, PlusOutlined, ReloadOutlined, SearchOutlined, StopOutlined, UploadOutlined, WarningOutlined } from '@ant-design/icons';
import { download, encodeFile, request } from '../shared/api';
import { projectCan, volumeOperationAllowed } from './project-team';
import { categoryName, formatTime, paginationName, useProject, volumeName } from '../app/context';
import type { Check, CheckIssue, Conflict, Fact, Preview, Requirement, Source, TenderFile, Volume } from '../shared/types';
import { SlaMatrixPage } from '../admin/SlaPages';
import { displaySlaValue } from '../admin/sla-form';
import { EvidenceDrawer } from '../library/EvidenceDrawer';
import { applyRefreshedAttachment, attachmentStale, evidenceInvalid } from '../library/evidence-drawer';
import {
  isBlocker,
  deriveBlockerSummary,
  canExportSubmission,
  formatFileSize,
  formatSha256Fingerprint,
  getExportKindMeta,
  getExportVolumeLabel,
} from './export-checks-core';
import {
  useVolumesStatus,
  areAllVolumesFinalized,
  isVolumeFinalized,
  deriveFinalizePremise,
} from './volume-api';

const statusName = (value: string) => value === 'confirmed' ? '已确认' : value === 'needs_review' ? '需重新核对' : value === 'rejected' ? '已排除' : '待确认';
const statusColor = (value: string) => value === 'confirmed' ? 'green' : value === 'rejected' ? 'default' : 'orange';
const ignoreFailure = () => undefined;

import { SourceLink } from './SourceLink';
import { OriginalPreview } from './OriginalPreview';
import { ConflictCards } from './ConflictCards';
import { VolumeFinalizePanel } from './VolumeFinalizePanel';
export { OverviewPage } from './OverviewTab';
export { TenderPage } from './TenderTab';
export { ParsePage } from './ParseTab';
export { ManualQueuePage } from './ManualQueuePage';

export function MatrixPage() {
  const { workspace, user, token, library, busy, mutate, reload, report, navigate } = useProject();
  const [kind, setKind] = useState('requirements');
  const [search, setSearch] = useState('');
  const [volume, setVolume] = useState('all');
  const [status, setStatus] = useState('all');
  const [edit, setEdit] = useState<Requirement | null>(null);
  const [evidenceItem, setEvidenceItem] = useState<Requirement | null>(null);
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [openedEvidence, setOpenedEvidence] = useState<{ revision: number; ids: string[] } | null>(null);
  const [evidenceStale, setEvidenceStale] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [form] = Form.useForm();
  const rows = workspace.requirements.filter(item => item.status !== 'rejected' && (kind === 'requirements' || item.category === 'sla')).filter(item => item.text.includes(search) || item.response.includes(search)).filter(item => volume === 'all' || item.volume === volume).filter(item => status === 'all' || item.status === status);
  const active = workspace.requirements.filter(item => item.status !== 'rejected');
  const responded = active.filter(item => item.response.trim()).length;
  function openEvidence(item: Requirement) {
    setEvidenceItem(item);
    setEvidenceIds(item.evidence_ids.slice());
    setOpenedEvidence({ revision: workspace.revision, ids: item.evidence_ids.slice() });
    setEvidenceStale(false);
  }
  function closeEvidence() { setEvidenceItem(null); setOpenedEvidence(null); setEvidenceStale(false); }
  async function save() { if (!edit?.permissions?.response) return; const values = await form.validateFields(); try { await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${edit.id}`, 'PATCH', { response: values.response || '', ...(edit.permissions.route ? { volume: values.volume, chapter_id: values.chapter_id || null, status: values.status } : {}), reason: values.reason || '' }); setEdit(null); } catch { /* 保留未保存输入 */ } }
  async function saveEvidence() {
    if (!evidenceItem || !openedEvidence) return;
    const current = workspace.requirements.find(item => item.id === evidenceItem.id);
    if (current?.permissions?.response !== true) return;
    if (attachmentStale(openedEvidence.revision, openedEvidence.ids, workspace.revision, current.evidence_ids)) { setEvidenceStale(true); return; }
    try { await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${evidenceItem.id}`, 'PATCH', { evidence_ids: evidenceIds }); closeEvidence(); } catch { /* 证据变动会由后台拒绝，抽屉保留当前勾选 */ }
  }
  async function refreshEvidence() {
    if (!evidenceItem) return;
    const id = evidenceItem.id;
    try {
      const next = await reload();
      if (!next) return;
      const current = next.requirements.find(item => item.id === id);
      if (!current) { closeEvidence(); return; }
      const fresh = applyRefreshedAttachment(current, next.revision);
      setEvidenceItem(current); setEvidenceIds(fresh.ids); setOpenedEvidence(fresh.opened); setEvidenceStale(false);
    } catch { /* 刷新失败时抽屉保留当前勾选 */ }
  }
  return <><Row gutter={12} className="matrix-statistics">{[{ title: '响应点总数', value: active.length }, { title: '已回应', value: responded, color: '#2B9D5C' }, { title: '未确认条款', value: active.filter(item => item.status === 'pending').length, color: '#D9363E' }, { title: '缺证据', value: active.filter(item => /资质|证书|证明|业绩|授权/.test(item.text) && !item.evidence_ids.length).length, color: '#D9363E' }, { title: '覆盖率', value: `${active.length ? Math.round(responded / active.length * 100) : 0}%`, color: '#1E4DB7' }].map(item => <Col flex="1" key={item.title}><Card><Statistic title={item.title} value={item.value} valueStyle={{ color: item.color }} /></Card></Col>)}</Row>{!workspace.parse_confirmed && <Alert type="warning" showIcon className="page-notice" message="解析结果尚未完整确认" description="先在解析结果处理冲突和待确认条款，避免未经核对的数据进入写作方案。" />}<div className="matrix-switch"><Radio.Group value={kind} optionType="button" buttonStyle="solid" onChange={e => setKind(e.target.value)} options={[{ value: 'requirements', label: '要求矩阵' }, { value: 'sla', label: '服务响应承诺（SLA）' }]} />{kind === 'sla' && <span className="muted">招标要求、我方承诺与公司能力逐项对照。</span>}</div>{kind === 'sla' ? <SlaMatrixPage onLocate={setSource} /> : <Card className="matrix-card" bodyStyle={{ padding: 0 }}><div className="table-toolbar"><Input prefix={<SearchOutlined />} aria-label="搜索要求原文或响应" placeholder="搜索要求原文 / 响应要点" value={search} onChange={e => setSearch(e.target.value)} style={{ width: 280 }} /><Select aria-label="矩阵状态" value={status} onChange={setStatus} options={[{ value: 'all', label: '全部状态' }, { value: 'confirmed', label: '已确认' }, { value: 'pending', label: '待确认' }]} /><Select aria-label="矩阵分册" value={volume} onChange={setVolume} options={[{ value: 'all', label: '全部分册' }, { value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /><Tooltip title="批量匹配、Excel 和指派尚未接通"><Button disabled>智能匹配证据</Button></Tooltip></div><Table rowKey="id" size="small" pagination={{ pageSize: 10 }} scroll={{ x: 1040 }} dataSource={rows} rowClassName={item => [item.status === 'pending' || !item.response.trim() ? 'risk-row' : '', item.evidence_ids.some(id => evidenceInvalid(library.find(value => value.id === id), workspace.project.deadline)) ? 'evidence-invalid-row' : ''].filter(Boolean).join(' ')} columns={[{ title: '#', width: 40, render: (_, __, index) => index + 1 }, { title: '要求原文', dataIndex: 'text', width: 270, render: (value: string, item: Requirement) => <><div>{value}</div><SourceLink source={item.source} onClick={setSource} /></> }, { title: '类别 / 性质', width: 105, render: (_, item) => <Tag color={['qualification', 'star', 'disqualification'].includes(item.category) ? 'purple' : 'blue'}>{categoryName(item.category)}</Tag> }, { title: '归属分册', dataIndex: 'volume', width: 90, render: volumeName }, { title: '响应要点', dataIndex: 'response', width: 220, render: (value: string) => value || <span className="orange">未填写</span> }, { title: '对应章节', width: 150, render: (_, item) => workspace.chapters.find(chapter => chapter.id === item.chapter_id)?.title ?? <span className="orange">未分配</span> }, { title: '证据', width: 220, render: (_, item) => <>{item.evidence_ids.length ? item.evidence_ids.map(id => { const evidence = library.find(value => value.id === id); const invalid = evidenceInvalid(evidence, workspace.project.deadline); return <p className={invalid ? 'red' : ''} key={id}>{evidence?.name ?? '资料已不可见'}{evidence ? ` · v${evidence.revision ?? '—'}` : ''}{invalid && <Tag color="red">证据失效</Tag>}</p>; }) : <span className="muted">尚未挂接</span>}<Button type="link" size="small" disabled={!item.permissions?.response || busy} onClick={() => openEvidence(item)}>挂证据</Button></> }, { title: '状态 / 操作', width: 130, render: (_, item) => <><Tag color={statusColor(item.status)}>{statusName(item.status)}</Tag><p><Button type="link" size="small" disabled={busy || !item.permissions?.response} onClick={() => { setEdit(item); form.setFieldsValue(item); }}>编辑响应</Button></p></> }]} /></Card>}<EvidenceDrawer open={!!evidenceItem} requirement={evidenceItem} library={library} deadline={workspace.project.deadline} selectedIds={evidenceIds} openedIds={openedEvidence?.ids ?? []} canWrite={workspace.requirements.find(item => item.id === evidenceItem?.id)?.permissions?.response === true} busy={busy} stale={evidenceStale} onClose={closeEvidence} onSelected={setEvidenceIds} onSave={() => { void saveEvidence(); }} onRefresh={() => { void refreshEvidence(); }} onSupplement={() => navigate('/library')} /><Drawer title="要求来源 · 招标原文" open={!!source} onClose={() => setSource(null)} width={760}><OriginalPreview source={source} /></Drawer><Modal title="编辑响应与分册分流" open={!!edit} onCancel={() => setEdit(null)} onOk={save} cancelText="取消" confirmLoading={busy} okText="保存" okButtonProps={{ disabled: !edit?.permissions?.response }}><Alert type="info" message={edit?.text} /><Form form={form} layout="vertical" disabled={busy || !edit?.permissions?.response} style={{ marginTop: 16 }}><Form.Item name="response" label="我方响应要点"><Input.TextArea rows={4} placeholder="根据实际能力、证据和招标要求写清回应" /></Form.Item><Form.Item name="volume" label="归属分册"><Select disabled={!edit?.permissions?.route} options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /></Form.Item><Form.Item name="chapter_id" label="对应章节"><Select disabled={!edit?.permissions?.route} allowClear options={workspace.chapters.map(item => ({ value: item.id, label: `${volumeName(item.volume)} · ${item.title}` }))} /></Form.Item><Form.Item name="status" label="人工确认"><Select disabled={!edit?.permissions?.route} options={[{ value: 'pending', label: '待确认' }, { value: 'confirmed', label: '已确认' }]} /></Form.Item><Form.Item name="reason" label="说明"><Input.TextArea rows={2} /></Form.Item></Form></Modal></>;
}

export { FactsPage } from './FactsTab';

export function ChecksPage() {
  const { workspace, busy, user, mutate, navigate } = useProject();
  const [volume, setVolume] = useState<Volume | 'all'>(projectCan(workspace, 'check_all') ? 'all' : workspace.permissions?.check_volumes[0] ?? 'all');
  const [severity, setSeverity] = useState('all');
  const [selectedId, setSelectedId] = useState('');
  const [source, setSource] = useState<Source | null>(null);
  const check = workspace.checks.find(item => item.id === selectedId) ?? workspace.checks.slice().reverse().find(item => item.volume === volume) ?? workspace.checks[workspace.checks.length - 1];
  const issues = check?.issues.filter(item => severity === 'all' || (severity === 'blocker' ? isBlocker(item.severity) : item.severity === severity)) ?? [];
  const blockerSummary = deriveBlockerSummary(check, workspace.chapters);

  async function run() {
    if (!volumeOperationAllowed(workspace, 'check', volume) || busy) return;
    try {
      const value = await mutate(`/api/v1/projects/${workspace.project.id}/checks`, 'POST', { volume }) as { check: Check };
      setSelectedId(value.check.id);
    } catch {
      /* 显示实际检查失败 */
    }
  }

  function locate(item: CheckIssue) {
    const requirement = workspace.requirements.find(value => value.id === item.requirement_id);
    if (requirement) setSource(requirement.source);
    else navigate(item.chapter_id ? 'editor' : item.evidence_id ? 'matrix' : 'parse');
  }

  return (
    <>
      <div className="checks-toolbar">
        <Radio.Group
          value={volume}
          onChange={e => { setVolume(e.target.value); setSelectedId(''); }}
          optionType="button"
          options={[
            { value: 'technical', label: '技术分册检查' },
            { value: 'business', label: '商务分册检查' },
            { value: 'all', label: '全文检查' },
          ]}
        />
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={run}
          loading={busy}
          disabled={!volumeOperationAllowed(workspace, 'check', volume)}
        >
          运行{volumeName(volume)}检查
        </Button>
      </div>

      {blockerSummary.hasBlockers && (
        <Alert
          className="blocker-alert-banner"
          data-testid="blocker-alert-banner"
          type="error"
          showIcon
          icon={<StopOutlined />}
          style={{ marginBottom: 16 }}
          message={
            <div style={{ fontWeight: 600 }}>
              合规检查红线阻断（共 {blockerSummary.totalBlockers} 项）：正式递交版导出已被系统锁定禁止！
            </div>
          }
          description={
            <div>
              <p style={{ margin: '4px 0 8px', fontSize: 13, color: '#4e5969' }}>
                检测到星号条款未覆盖、废标条款无证据支撑或关键事实前后矛盾等阻断性缺陷。根据红线门禁规则，正式递交前必须在正文或矩阵中清零阻断项。
              </p>
              <div data-testid="blocker-chapters-list" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: '#1d2129' }}>受阻章节 / 位置：</span>
                {blockerSummary.blockedChapters.map(ch => (
                  <Tag
                    key={ch.chapterId}
                    color="error"
                    style={{ cursor: ch.chapterId !== 'global_non_chapter' ? 'pointer' : 'default', padding: '2px 8px' }}
                    onClick={() => {
                      if (ch.chapterId && ch.chapterId !== 'global_non_chapter') {
                        navigate('editor');
                      }
                    }}
                  >
                    {ch.chapterTitle} ({ch.blockerCount} 项)
                  </Tag>
                ))}
              </div>
            </div>
          }
        />
      )}

      {check ? (
        <Alert
          type={check.status === 'stale' ? 'warning' : check.passed ? 'success' : 'error'}
          showIcon
          className="check-result"
          message={
            check.status === 'stale'
              ? '检查已过期：项目或证据已变化，请重新检查'
              : check.passed
              ? '当前已实现规则通过'
              : `有问题：${check.issues.filter(item => isBlocker(item.severity)).length} 个阻断 · ${check.issues.filter(item => item.severity === 'warning').length} 个警告`
          }
          description={`检查批次 ${check.id.slice(-10)} · ${formatTime(check.created_at)} · 只检查已提交正文，不包含未提交草稿`}
        />
      ) : (
        <Alert className="page-notice" type="info" showIcon message="还没有检查结果，请先提交正文，再运行检查" />
      )}

      <div className="checks-layout">
        <Card className="rule-filter" title="按级别 / 规则" size="small">
          <button className={severity === 'all' ? 'active' : ''} onClick={() => setSeverity('all')}>
            全部问题 <span>{check?.issues.length ?? 0}</span>
          </button>
          {['blocker', 'warning', 'info'].map(value => (
            <button className={severity === value ? 'active' : ''} key={value} onClick={() => setSeverity(value)}>
              <Tag color={value === 'blocker' ? 'red' : value === 'warning' ? 'orange' : 'blue'}>
                {value === 'blocker' ? '阻断' : value === 'warning' ? '警告' : '提示'}
              </Tag>
              <span>{check?.issues.filter(item => (value === 'blocker' ? isBlocker(item.severity) : item.severity === value)).length ?? 0}</span>
            </button>
          ))}
          {check?.coverage && (
            <div className="coverage-box">
              <b>实际规则覆盖</b>
              <p>流程条件已实现 {check.coverage.implemented_rules.length} 项</p>
              <p>待补能力组 {check.coverage.unimplemented_rules.length} 组</p>
              <Tag color="orange">尚非完整业务合规检查</Tag>
            </div>
          )}
        </Card>

        <Card className="issue-card" bodyStyle={{ padding: 0 }}>
          <Tabs
            className="issue-tabs"
            defaultActiveKey="issues"
            items={[
              {
                key: 'issues',
                label: `问题列表 ${check?.issues.length ?? 0}`,
                children: (
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    dataSource={issues}
                    rowClassName={item => (isBlocker(item.severity) ? 'risk-row' : '')}
                    columns={[
                      {
                        title: '级别',
                        width: 75,
                        dataIndex: 'severity',
                        render: value => (
                          <Tag color={isBlocker(value) ? 'red' : value === 'warning' ? 'orange' : 'blue'}>
                            {isBlocker(value) ? '阻断' : value === 'warning' ? '警告' : '提示'}
                          </Tag>
                        ),
                      },
                      { title: '规则', width: 95, dataIndex: 'code' },
                      { title: '问题描述', dataIndex: 'message' },
                      {
                        title: '位置',
                        width: 160,
                        render: (_, item) =>
                          item.chapter_id
                            ? workspace.chapters.find(chapter => chapter.id === item.chapter_id)?.title ?? '章节'
                            : item.requirement_id
                            ? '响应矩阵 / 原文要求'
                            : item.evidence_id
                            ? '企业资料记录'
                            : '项目资料',
                      },
                      {
                        title: '操作',
                        width: 70,
                        render: (_, item) => (
                          <Button type="link" size="small" onClick={() => locate(item)}>
                            定位
                          </Button>
                        ),
                      },
                    ]}
                  />
                ),
              },
              {
                key: 'history',
                label: '检查历史',
                children: (
                  <Table
                    rowKey="id"
                    size="small"
                    dataSource={workspace.checks.slice().reverse()}
                    pagination={false}
                    columns={[
                      { title: '分册', dataIndex: 'volume', render: volumeName },
                      { title: '时间', dataIndex: 'created_at', render: formatTime },
                      {
                        title: '结果',
                        render: (_, item) => (
                          <Tag color={item.status === 'stale' ? 'orange' : item.passed ? 'green' : 'red'}>
                            {item.status === 'stale' ? '已过期' : item.passed ? '通过当前规则' : '有问题'}
                          </Tag>
                        ),
                      },
                      { title: '操作', render: (_, item) => <a onClick={() => setSelectedId(item.id)}>查看结果</a> },
                    ]}
                  />
                ),
              },
              {
                key: 'coverage',
                label: '规则范围',
                children: (
                  <div className="coverage-detail">
                    <Alert type="warning" showIcon message="测试通过与当前检查通过，不能代表整套招标业务规则均已实现" />
                    <Descriptions
                      title="本批次覆盖"
                      column={1}
                      bordered
                      size="small"
                      items={[
                        { key: 'implemented', label: '已实现', children: check?.coverage.implemented_rules.join('、') || '尚未检查' },
                        { key: 'missing', label: '未实现', children: check?.coverage.unimplemented_rules.join('、') || '请先运行检查' },
                      ]}
                    />
                  </div>
                ),
              },
            ]}
          />
        </Card>
      </div>
      <Drawer title="问题依据 · 招标原文" open={!!source} onClose={() => setSource(null)} width={760}>
        <OriginalPreview source={source} />
      </Drawer>
    </>
  );
}

export function ExportPage() {
  const { workspace, token, user, busy, mutate, report, navigate } = useProject();
  const [kind, setKind] = useState('internal');
  const [volume, setVolume] = useState<Volume | 'all'>(projectCan(workspace, 'export_internal') ? 'all' : workspace.permissions?.export_volumes[0] ?? 'all');
  const [checkId, setCheckId] = useState('');
  const { volumes: volumesStatus } = useVolumesStatus(workspace.project.id, token, workspace.revision);
  const allFinalized = areAllVolumesFinalized(volumesStatus);
  const isCurrentVolumeFinalized = volume === 'all'
    ? allFinalized
    : isVolumeFinalized(volumesStatus, volume);
  const validChecks = workspace.checks.filter(item => item.volume === volume && item.passed && item.status !== 'stale');
  const check = validChecks.find(item => item.id === checkId) ?? validChecks[validChecks.length - 1];
  const full = (volume === 'all' ? (['technical', 'business'] as const) : [volume]).every(
    v => workspace.chapters.some(item => item.volume === v && item.content.trim()) && workspace.chapters.filter(item => item.volume === v).every(item => item.content.trim())
  );

  // 计算当前分册最新检查是否有阻断性红线缺陷
  const latestCheckForVolume = workspace.checks.slice().reverse().find(item => item.volume === volume) ?? check;
  const blockerSummary = deriveBlockerSummary(latestCheckForVolume, workspace.chapters);
  const hasBlockers = blockerSummary.hasBlockers;

  const isSubmission = kind === 'submission';
  const submissionCheck = canExportSubmission({
    hasBlockers,
    blockerCount: blockerSummary.totalBlockers,
    fullContent: full,
    hasPassedCheck: !!check && check.passed,
    parseConfirmed: workspace.parse_confirmed,
    userCanExport: volumeOperationAllowed(workspace, 'export', volume),
    isFinalized: isCurrentVolumeFinalized,
  });

  const isButtonDisabled = busy || (isSubmission ? !submissionCheck.allowed : (!volumeOperationAllowed(workspace, 'export', volume) || !full || !workspace.parse_confirmed));
  const buttonTooltip = isSubmission && !submissionCheck.allowed
    ? (submissionCheck.reason || `存在 ${blockerSummary.totalBlockers} 项阻断性合规缺陷，禁止导出递交版`)
    : '';

  async function create() {
    if (isSubmission && !submissionCheck.allowed) return;
    if (!check || !volumeOperationAllowed(workspace, 'export', volume)) return;
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/exports`, 'POST', { check_id: check.id, kind, volume });
    } catch {
      /* 后台再次核对完整分册、角色和检查 */
    }
  }

  const premiseItems = [
    { label: '解析结果已人工确认', ready: workspace.parse_confirmed, tab: 'parse' },
    { label: volume === 'all' ? '技术、商务两册均有完整已提交正文' : `${volumeName(volume)}有完整已提交正文`, ready: full, tab: 'editor' },
    { label: `${volumeName(volume)}有效检查通过当前已实现规则`, ready: !!check && check.passed, tab: 'checks' },
    { label: '合规红线门禁：无阻断性缺陷（Blocker 清零）', ready: !hasBlockers, tab: 'checks' },
    deriveFinalizePremise(volumesStatus, volume),
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h2>导出{volume === 'all' ? '技术、商务两册合订' : volumeName(volume)}</h2>
            {isCurrentVolumeFinalized ? (
              <Tag color="success" data-testid="export-finalized-badge">
                {volume === 'all' ? '分册全部定稿' : `${volumeName(volume)}已定稿`}
              </Tag>
            ) : (
              <Tag color="default" data-testid="export-unfinalized-badge">
                {volume === 'all' ? '分册未全部定稿' : `${volumeName(volume)}未定稿`}
              </Tag>
            )}
          </div>
          <p>项目负责人生成两册，分册负责人生成本册；合标负责人只下载已生成文件。输出取已提交正文，不使用个人草稿。</p>
        </div>
      </div>
      <Row gutter={16}>
        <Col span={15}>
          <Card title="导出前提" className="stack-card">
            <List
              dataSource={premiseItems}
              renderItem={item => (
                <List.Item actions={[<a onClick={() => navigate(item.tab)}>前往查看</a>]}>
                  <Space>
                    {item.ready ? <CheckCircleOutlined className="green" /> : <WarningOutlined className="orange" />}
                    {item.label}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
          <VolumeFinalizePanel volumes={volumesStatus} />
          <Card title="导出选项">
            <Form layout="vertical">
              <Form.Item label="生成范围">
                <Radio.Group
                  aria-label="导出分册范围"
                  data-testid="export-volume-radio"
                  value={volume}
                  onChange={event => {
                    setVolume(event.target.value);
                    setCheckId('');
                  }}
                  options={[
                    { value: 'all', label: '技术、商务两册合订', disabled: !volumeOperationAllowed(workspace, 'export', 'all') },
                    { value: 'technical', label: '技术分册', disabled: !volumeOperationAllowed(workspace, 'export', 'technical') },
                    { value: 'business', label: '商务分册', disabled: !volumeOperationAllowed(workspace, 'export', 'business') },
                  ]}
                />
              </Form.Item>
              <Form.Item label="类型">
                <Radio.Group
                  data-testid="export-kind-radio"
                  value={kind}
                  onChange={e => setKind(e.target.value)}
                >
                  <Radio value="internal">内部评审稿（带水印）</Radio>
                  {projectCan(workspace, 'manage_project') && (
                    <Radio value="submission">正式递交版（盖章版式）</Radio>
                  )}
                </Radio.Group>
              </Form.Item>
              <Form.Item label="检查批次">
                <Select
                  value={check?.id}
                  placeholder="请先运行当前范围的有效检查"
                  onChange={setCheckId}
                  options={validChecks.map(item => ({
                    value: item.id,
                    label: `${formatTime(item.created_at)} · ${volumeName(item.volume)}检查`,
                  }))}
                />
              </Form.Item>
              {hasBlockers && (
                <Alert
                  type="error"
                  showIcon
                  className="export-blocker-warning"
                  data-testid="export-blocker-warning"
                  style={{ marginBottom: 16 }}
                  message={`存在 ${blockerSummary.totalBlockers} 项阻断性合规红线缺陷！正式递交版已锁定`}
                  description={
                    <div>
                      <p style={{ margin: '4px 0', fontSize: 13 }}>
                        受阻章节：{blockerSummary.blockedChapters.map(c => c.chapterTitle).join('、') || '整册合规检查'}
                      </p>
                      <p style={{ margin: 0, fontSize: 12, color: '#8c8c8c' }}>
                        根据红线门禁规范，存在废标条款无证据支撑或星号条款未覆盖时，系统强行锁定递交版导出。仅允许导出「内部评审稿」供团队人工复核。
                      </p>
                    </div>
                  }
                />
              )}
              <Alert
                type={kind === 'submission' ? (hasBlockers ? 'error' : 'warning') : 'info'}
                showIcon
                message={kind === 'submission' ? '正式递交版 · 红线合规盖章版式' : '内部评审稿 · 供人工复核'}
                description={
                  kind === 'submission'
                    ? hasBlockers
                      ? '当前分册存在阻断性合规缺陷，递交版已被锁定禁止导出！请先消除阻断项。'
                      : '导出文件将应用正式盖章与递交格式，不包含内部草稿与演示水印。需项目负责人确认所有合规条款无误。'
                    : '下载文件含内部评审水印与未核验标记。会按当前掩码规则处理高敏数字，但仍需人工复核格式与内容。'
                }
              />
              <Tooltip title={buttonTooltip} placement="top">
                <span style={{ display: 'inline-block', marginTop: 20 }}>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    disabled={isButtonDisabled}
                    loading={busy}
                    onClick={create}
                    data-testid="export-generate-btn"
                    style={{
                      backgroundColor: isSubmission && !isButtonDisabled ? '#52c41a' : undefined,
                      borderColor: isSubmission && !isButtonDisabled ? '#52c41a' : undefined,
                    }}
                  >
                    {isSubmission
                      ? `生成${volume === 'all' ? '两册合订' : volumeName(volume)}正式递交版`
                      : `生成${volume === 'all' ? '两册合订' : volumeName(volume)}内部评审稿`}
                  </Button>
                </span>
              </Tooltip>
            </Form>
          </Card>
        </Col>
        <Col span={9}>
          <Card title="合标核对清单">
            <List
              size="small"
              dataSource={[
                '资格材料是否按本项目要求归册',
                '技术与商务的名称、日期、服务承诺是否一致',
                '证明材料是否有效且覆盖投标截止时间',
                '报价由人在线下处理，确认是否独立提交',
                'Word 文件须人工复核后再使用',
              ]}
              renderItem={item => <List.Item>□ {item}</List.Item>}
            />
            <Tag color="orange" style={{ marginTop: 12 }}>清单目前用于人工核对，不替代正式定稿流程</Tag>
          </Card>
        </Col>
      </Row>
      <Card title="导出历史" className="page-notice" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          size="small"
          data-testid="export-history-table"
          dataSource={workspace.exports.slice().reverse()}
          pagination={false}
          columns={[
            {
              title: '快照编号',
              dataIndex: 'id',
              key: 'id',
              width: 140,
              render: (id: string) => (
                <span data-testid="export-history-id" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                  {id}
                </span>
              ),
            },
            {
              title: '生成时间',
              dataIndex: 'created_at',
              key: 'created_at',
              width: 110,
              render: formatTime,
            },
            {
              title: '操作人',
              key: 'operator',
              width: 90,
              render: (_, item) => (
                <span style={{ fontSize: 12 }}>{item.created_by || item.operator_name || user.name || user.id}</span>
              ),
            },
            {
              title: '分册范围',
              key: 'volume',
              width: 120,
              render: (_, item) => (
                <span style={{ fontSize: 12 }}>
                  {getExportVolumeLabel(item.volume || (item.volumes.length > 1 ? 'all' : item.volumes[0]?.volume || 'all'))}
                </span>
              ),
            },
            {
              title: '类型',
              dataIndex: 'kind',
              key: 'kind',
              width: 110,
              render: (val: string) => {
                const meta = getExportKindMeta(val);
                return <Tag color={meta.tagColor}>{meta.label}</Tag>;
              },
            },
            {
              title: '文件大小',
              key: 'file_size',
              width: 90,
              render: (_, item) => {
                const bytes = item.file_size ?? item.size_bytes ?? item.volumes?.[0]?.file_size ?? item.volumes?.[0]?.size_bytes;
                return <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{formatFileSize(bytes, item.id)}</span>;
              },
            },
            {
              title: '版式指纹 (SHA256)',
              key: 'fingerprint',
              width: 150,
              render: (_, item) => {
                const hash = item.sha256 || item.fingerprint || item.volumes?.[0]?.sha256 || item.volumes?.[0]?.fingerprint;
                const meta = formatSha256Fingerprint(hash, item.id);
                return (
                  <Tooltip title={`完整指纹: ${meta.full}`}>
                    <span
                      data-testid="export-fingerprint"
                      style={{ fontFamily: 'monospace', fontSize: 11, cursor: 'pointer', color: '#1677ff' }}
                    >
                      {meta.short}
                    </span>
                  </Tooltip>
                );
              },
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              width: 110,
              render: (val: string) => (
                <Tag color={val === 'valid' ? 'green' : 'orange'}>
                  {val === 'valid' ? '有效' : '已过期，请重新检查'}
                </Tag>
              ),
            },
            {
              title: '分册下载',
              key: 'downloads',
              render: (_, item) => {
                const tech = item.volumes.find(v => v.volume === 'technical');
                const comm = item.volumes.find(v => v.volume === 'business');
                return (
                  <Space size={8}>
                    {tech ? (
                      <Button
                        size="small"
                        type="link"
                        data-testid="export-download-btn"
                        disabled={item.status !== 'valid'}
                        onClick={() => download(tech.download_url, token, tech.filename).catch(report)}
                      >
                        技术 Word
                      </Button>
                    ) : null}
                    {comm ? (
                      <Button
                        size="small"
                        type="link"
                        data-testid="export-download-btn"
                        disabled={item.status !== 'valid'}
                        onClick={() => download(comm.download_url, token, comm.filename).catch(report)}
                      >
                        商务 Word
                      </Button>
                    ) : null}
                    {!tech && !comm && <span className="muted">未生成分册文件</span>}
                  </Space>
                );
              },
            },
          ]}
        />
      </Card>
    </>
  );
}

export { ProjectHeader } from './ProjectHeader';
export { ProjectListPage } from './ProjectListPage';

