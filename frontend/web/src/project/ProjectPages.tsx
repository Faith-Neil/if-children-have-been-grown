// 为什么有这个文件：按 ICG 示例实现项目主链路中的业务页签。
// 它解决什么问题：上传与解析、响应和证据、检查与两册导出都调用后台真实结果。
import { editorChapterPath } from '../app/app-route.ts';
import { requestIssueFocus } from '../editor/issue-focus.ts';
import { useEffect, useRef, useState } from 'react';
import { Alert, App as AntApp, Badge, Button, Card, Checkbox, Col, Collapse, Descriptions, Drawer, Empty, Form, Input, List, Modal, Progress, Radio, Row, Select, Space, Statistic, Steps, Table, Tabs, Tag, Tooltip, Upload } from 'antd';
import { DownloadOutlined, ReloadOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons';
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
  exportBatchLabel,
  exportStatusMeta,
  formatFileSize,
  formatSha256Fingerprint,
  getExportKindMeta,
  getExportVolumeLabel,
  canReleaseIssue,
  releasePath,
  unreleasedCount,
  checklistFilename,
  checklistRowTone,
  latestSubmissionWithChecklist,
  responseTracePath,
} from './export-checks-core';
import { useVolumesStatus } from './volume-api';

const statusName = (value: string) => value === 'confirmed' ? '已确认' : value === 'needs_review' ? '需重新核对' : value === 'rejected' ? '已排除' : '待确认';
const statusColor = (value: string) => value === 'confirmed' ? 'green' : value === 'rejected' ? 'default' : 'orange';
const ignoreFailure = () => undefined;

import { SourceLink } from './SourceLink';
import { defaultTemplateChoice, exportRequestBody, templateOptions, templateSourceLabel, wordTemplatePaths, type TemplateChoice, type WordTemplate } from '../admin/word-template-core';
import { MatrixMatchDrawer } from './MatrixMatchDrawer';
import { RISK_COLORS, coverageSummary, fetchMatrix, matrixPaths, needsReason, responseOptions, routingRows, type MatrixData } from './matrix-core';
import { OriginalPreview } from './OriginalPreview';
import { ConflictCards } from './ConflictCards';
import { projectVolumes, technicalOnly, volumeOptions } from './project-volumes';
import { CoverageView } from './CoverageView.tsx';
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
  const [matrixData, setMatrixData] = useState<MatrixData | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [matchIds, setMatchIds] = useState<string[]>([]);
  const editType = Form.useWatch('response_type', form);
  useEffect(() => { fetchMatrix(workspace.project.id, token).then(setMatrixData).catch(() => setMatrixData(null)); }, [workspace.project.id, workspace.revision, token]);
  const matrixById = new Map((matrixData?.items ?? []).map(item => [item.id, item]));
  const isLead = projectCan(workspace, 'manage_project');
  const isTechnicalCoverage = technicalOnly(workspace);
  if (isTechnicalCoverage) return <CoverageView />;
  const coverage = coverageSummary(workspace.requirements, workspace.technical_outline);
  const historyPending = workspace.requirements.filter(item => item.technical_clause && item.response_origin === 'history' && item.status === 'pending' && item.response_type === 'comply');
  async function confirmHistory() {
    if (!historyPending.length || isTechnicalCoverage) return;
    try { await mutate(`/api/v1/projects/${workspace.project.id}/requirements/batch-confirm`, 'POST', { requirement_ids: historyPending.map(item => item.id) }); }
    catch { /* 错误已提示 */ }
  }
  async function confirmRouting(useSuggested: boolean) {
    const items = (matrixData?.items ?? []).filter(item => selected.includes(item.id));
    if (!items.length) return;
    try { await mutate(matrixPaths.routing(workspace.project.id), 'POST', { rows: routingRows(items, useSuggested) }); setSelected([]); } catch { /* 错误已提示 */ }
  }
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
  async function save() { if (!edit?.permissions?.response) return; const values = await form.validateFields(); try { await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${edit.id}`, 'PATCH', { ...(values.response_type ? { response_type: values.response_type, deviation_reason: values.deviation_reason || '' } : {}), ...(values.assignee_id ? { assignee_id: values.assignee_id } : {}), ...(edit.permissions.route ? { volume: values.volume, chapter_id: values.chapter_id || null, status: values.status } : {}), ...(edit.permissions.route && matrixById.get(edit.id)?.is_cross_volume && (values.shared_chapter_id ?? null) !== (edit.shared_chapter_id ?? null) ? { shared_chapter_id: values.shared_chapter_id || null } : {}), reason: values.reason || '' }); setEdit(null); } catch { /* 保留未保存输入 */ } }
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
  const stats = isTechnicalCoverage
    ? [
        { title: '技术条款', value: coverage.total },
        { title: '已有响应', value: coverage.withResponse, color: '#2B9D5C' },
        { title: '目录缺口', value: coverage.gaps, color: coverage.gaps ? '#D9363E' : undefined },
        { title: '正/负偏离', value: coverage.deviate, color: '#1E4DB7' },
        { title: '无检索依据', value: coverage.noEvidence, color: coverage.noEvidence ? '#D9363E' : undefined },
        { title: '响应覆盖率', value: `${coverage.coveragePercent}%`, color: '#1E4DB7' },
      ]
    : [
        { title: '响应点总数', value: active.length },
        { title: '星号/废标未确认', value: matrixData?.stats.critical_unconfirmed ?? 0, color: '#D9363E' },
        { title: '证据失效', value: matrixData?.stats.evidence_invalid ?? 0, color: '#D9363E' },
        { title: '已回应', value: responded, color: '#2B9D5C' },
        { title: '未确认条款', value: active.filter(item => item.status === 'pending').length, color: '#D9363E' },
        { title: '缺证据', value: active.filter(item => /资质|证书|证明|业绩|授权/.test(item.text) && !item.evidence_ids.length).length, color: '#D9363E' },
        { title: '覆盖率', value: `${active.length ? Math.round(responded / active.length * 100) : 0}%`, color: '#1E4DB7' },
      ];
  return <><Row gutter={12} className="matrix-statistics" data-testid={isTechnicalCoverage ? 'coverage-view-stats' : 'matrix-statistics'}>{stats.map(item => <Col key={item.title} xs={24} sm={12} md={8} lg={6} xl={4}><Card><Statistic title={item.title} value={item.value} valueStyle={{ color: item.color }} /></Card></Col>)}</Row>{isTechnicalCoverage ? <Alert type="info" showIcon className="page-notice" data-testid="coverage-view-notice" message="覆盖视图（可选）" description="查看条款与目录映射、偏离与缺口。不挡「开始生成」与导出；可事后改偏离说明。" action={<Button size="small" type="link" onClick={() => navigate('editor')}>回编辑台</Button>} /> : !workspace.parse_confirmed && <Alert type="warning" showIcon className="page-notice" message="解析结果尚未完整确认" description="先在解析结果处理冲突和待确认条款，避免未经核对的数据进入写作方案。" />}<div className="matrix-switch"><Radio.Group value={kind} optionType="button" buttonStyle="solid" onChange={e => setKind(e.target.value)} options={[{ value: 'requirements', label: '要求矩阵' }, { value: 'sla', label: '服务响应承诺（SLA）' }]} />{kind === 'sla' && <span className="muted">招标要求、我方承诺与公司能力逐项对照。</span>}</div>{kind === 'sla' ? <SlaMatrixPage onLocate={setSource} /> : <Card className="matrix-card" bodyStyle={{ padding: 0 }}><div className="table-toolbar"><Input prefix={<SearchOutlined />} aria-label="搜索要求原文或响应" placeholder="搜索要求原文 / 响应要点" value={search} onChange={e => setSearch(e.target.value)} style={{ width: 280 }} /><Select aria-label="矩阵状态" value={status} onChange={setStatus} options={[{ value: 'all', label: '全部状态' }, { value: 'confirmed', label: '已确认' }, { value: 'pending', label: '待确认' }]} /><Select aria-label="矩阵方案" value={volume} onChange={setVolume} options={technicalOnly(workspace) ? [{ value: 'all', label: '全部（含不在范围的商务条款）' }, { value: 'technical', label: '技术方案' }] : [{ value: 'all', label: '全部方案' }, { value: 'technical', label: '技术方案' }, { value: 'business', label: '商务方案' }]} /><Tooltip title={selected.length ? '' : '先勾选要匹配的行'}><Button data-testid="matrix-match-button" disabled={!selected.length || busy} onClick={() => setMatchIds(selected)}>智能匹配证据{selected.length ? `（${selected.length}）` : ''}</Button></Tooltip>{isLead && <Button data-testid="matrix-routing-button" disabled={!selected.length || busy} onClick={() => void confirmRouting(false)}>确认分流</Button>}{isLead && !technicalOnly(workspace) && <Button disabled={!selected.length || busy} onClick={() => void confirmRouting(true)}>按建议分流并确认</Button>}<Button data-testid="matrix-excel-button" icon={<DownloadOutlined />} onClick={() => download(matrixPaths.excel(workspace.project.id), token, `matrix-${workspace.project.id}.xlsx`).catch(report)}>导出 Excel</Button>{!isTechnicalCoverage && technicalOnly(workspace) && <Button data-testid="technical-history-confirm" disabled={!historyPending.length || busy} onClick={() => void confirmHistory()}>确认历史做法</Button>}</div><Table rowKey="id" size="small" pagination={{ pageSize: 10 }} scroll={{ x: 1240 }} dataSource={rows} rowSelection={{ selectedRowKeys: selected, onChange: keys => setSelected(keys as string[]) }} rowClassName={item => [item.status === 'pending' || !item.response.trim() ? 'risk-row' : '', item.evidence_ids.some(id => evidenceInvalid(library.find(value => value.id === id), workspace.project.deadline)) ? 'evidence-invalid-row' : ''].filter(Boolean).join(' ')} columns={[{ title: '#', width: 40, render: (_, __, index) => index + 1 }, { title: '要求原文', dataIndex: 'text', width: 270, render: (value: string, item: Requirement) => <><div>{value}</div><SourceLink source={item.source} onClick={setSource} /></> }, { title: '类别 / 性质', width: 105, render: (_, item) => <Tag color={['qualification', 'star', 'disqualification'].includes(item.category) ? 'purple' : 'blue'}>{categoryName(item.category)}</Tag> }, { title: '归属', dataIndex: 'volume', width: 110, render: (value: string, item: Requirement) => { const m = matrixById.get(item.id); return <>{volumeName(value)}{m && !m.volume_confirmed_at && <div className="muted">建议：{volumeName(m.suggested_volume)} · 待确认</div>}{m?.is_cross_volume && <Tag>跨方案共用</Tag>}</>; } }, { title: '响应方式', width: 110, render: (_, item) => { const m = matrixById.get(item.id); return m?.response_type ? <><Tag color={m.response_type === 'deviate' ? 'red' : m.response_type === 'exceed' ? 'blue' : m.response_type === 'not_applicable' ? 'default' : 'green'}>{m.response_label}</Tag><div className="muted">{m.deviation_label}</div></> : <span className="muted">未选择</span>; } }, { title: '响应要点', dataIndex: 'response', width: 220, render: (value: string, item: Requirement) => <><div>{value || <span className="orange">未填写</span>}</div>{item.response_origin === 'history' && <div className="muted">{item.history_filename}</div>}{(item.material_sources ?? []).map(src => <div className="muted" key={src.filename}>{src.filename}</div>)}{item.response_origin === 'model' && <div className="muted">待逐条确认</div>}{item.response_origin === 'retrieval_failed' && <div className="muted">检索失败</div>}{item.response_origin === 'draft_failed' && <div className="muted">拟写失败</div>}</> }, { title: '对应章节', width: 150, render: (_, item) => workspace.chapters.find(chapter => chapter.id === item.chapter_id)?.title ?? <span className="orange">未分配</span> }, { title: '证据', width: 220, render: (_, item) => <>{item.evidence_ids.length ? item.evidence_ids.map(id => { const evidence = library.find(value => value.id === id); const invalid = evidenceInvalid(evidence, workspace.project.deadline); return <p className={invalid ? 'red' : ''} key={id}>{evidence?.name ?? '资料已不可见'}{evidence ? ` · v${evidence.revision ?? '—'}` : ''}{invalid && <Tag color="red">证据失效</Tag>}</p>; }) : <span className="muted">尚未挂接</span>}<Button type="link" size="small" disabled={!item.permissions?.response || busy} onClick={() => openEvidence(item)}>挂证据</Button></> }, { title: '风险（证据失效见证据列）', width: 150, render: (_, item) => <>{(matrixById.get(item.id)?.risk_flags ?? []).map((flag, index) => flag === 'evidence_invalid' ? null : <Tag key={flag} color={RISK_COLORS[flag]} data-testid="matrix-risk">{matrixById.get(item.id)?.risk_labels[index]}</Tag>)}</> }, { title: '状态 / 操作', width: 130, render: (_, item) => <><Tag color={statusColor(item.status)}>{statusName(item.status)}</Tag>{matrixById.get(item.id)?.assignee_name && <div className="muted">负责人：{matrixById.get(item.id)?.assignee_name}</div>}<p><Button type="link" size="small" disabled={busy || !item.permissions?.response} onClick={() => { setEdit(item); form.setFieldsValue({ ...item, response_type: matrixById.get(item.id)?.response_type ?? undefined, deviation_reason: matrixById.get(item.id)?.deviation_reason ?? '', assignee_id: matrixById.get(item.id)?.assignee_id ?? undefined }); }}>编辑响应</Button></p></> }]} /></Card>}<EvidenceDrawer open={!!evidenceItem} requirement={evidenceItem} library={library} deadline={workspace.project.deadline} selectedIds={evidenceIds} openedIds={openedEvidence?.ids ?? []} canWrite={workspace.requirements.find(item => item.id === evidenceItem?.id)?.permissions?.response === true} busy={busy} stale={evidenceStale} onClose={closeEvidence} onSelected={setEvidenceIds} onSave={() => { void saveEvidence(); }} onRefresh={() => { void refreshEvidence(); }} onSupplement={() => navigate('/library')} /><Drawer title="要求来源 · 招标原文" open={!!source} onClose={() => setSource(null)} width={760}><OriginalPreview source={source} /></Drawer><MatrixMatchDrawer ids={matchIds} onClose={() => setMatchIds([])} /><Modal title="编辑响应与方案分流" open={!!edit} onCancel={() => setEdit(null)} onOk={save} cancelText="取消" confirmLoading={busy} okText="保存" okButtonProps={{ disabled: !edit?.permissions?.response }}><Alert type="info" message={edit?.text} /><Form form={form} layout="vertical" disabled={busy || !edit?.permissions?.response} style={{ marginTop: 16 }}><Form.Item name="response_type" label="响应方式" extra={edit && matrixById.get(edit.id)?.critical ? '星号/废标条款不能选不适用；如实选偏离会阻断导出' : '满足=无偏离，优于=正偏离，偏离=负偏离'}><Select allowClear options={responseOptions(!!(edit && matrixById.get(edit.id)?.critical))} /></Form.Item>{needsReason(editType, !!edit?.technical_clause) && <Form.Item name="deviation_reason" label="偏离 / 不适用说明" rules={[{ required: true, whitespace: true, message: edit?.technical_clause && editType === 'exceed' ? '正偏离必须写明优在哪一项、优多少' : '偏离或不适用必须填写说明' }]}><Input.TextArea rows={2} /></Form.Item>}<Form.Item name="assignee_id" label="本行负责人"><Select allowClear options={(workspace.team?.members ?? []).filter(m => m.project_role !== 'readonly').map(m => ({ value: m.user_id, label: m.name ?? m.user_id }))} /></Form.Item><Form.Item label="检索响应"><Input.TextArea rows={4} value={edit?.response || (edit?.response_origin === 'no_evidence' ? '知识库没有依据，待确认' : '')} readOnly /></Form.Item><Form.Item name="volume" label="归属"><Select disabled={!edit?.permissions?.route} options={volumeOptions(workspace)} /></Form.Item><Form.Item name="chapter_id" label="对应章节"><Select disabled={!edit?.permissions?.route} allowClear options={workspace.chapters.map(item => ({ value: item.id, label: `${volumeName(item.volume)} · ${item.title}` }))} /></Form.Item>{edit && matrixById.get(edit.id)?.is_cross_volume && <Form.Item name="shared_chapter_id" label="另一方案对应章节（跨方案共用）" extra="跨方案共用的行在两个方案的写作方案中都能选到，两处引用同一份项目事实"><Select data-testid="matrix-shared-chapter" disabled={!edit?.permissions?.route} allowClear options={workspace.chapters.filter(item => item.volume !== edit.volume).map(item => ({ value: item.id, label: `${volumeName(item.volume)} · ${item.title}` }))} /></Form.Item>}{!isTechnicalCoverage && <Form.Item name="status" label="人工确认"><Select disabled={!edit?.permissions?.route} options={[{ value: 'pending', label: '待确认' }, { value: 'confirmed', label: '已确认' }]} /></Form.Item>}<Form.Item name="reason" label="说明"><Input.TextArea rows={2} /></Form.Item></Form></Modal></>;
}

export { FactsPage } from './FactsTab';

export function ChecksPage() {
  const { workspace, busy, user, mutate, navigate } = useProject();
  const technical = technicalOnly(workspace);
  const [volume, setVolume] = useState<Volume | 'all'>(technical ? 'technical' : projectCan(workspace, 'check_all') ? 'all' : workspace.permissions?.check_volumes[0] ?? 'all');
  const [severity, setSeverity] = useState('all');
  const [selectedId, setSelectedId] = useState('');
  const [source, setSource] = useState<Source | null>(null);
  const check = workspace.checks.find(item => item.id === selectedId) ?? workspace.checks.slice().reverse().find(item => item.volume === volume) ?? workspace.checks[workspace.checks.length - 1];
  const issues = (check?.issues.filter(item => severity === 'all' || (severity === 'blocker' ? isBlocker(item.severity) : item.severity === severity)) ?? [])
    .slice()
    .sort((a, b) => Number(isBlocker(b.severity)) - Number(isBlocker(a.severity)));
  const blockerSummary = deriveBlockerSummary(check, workspace.chapters);
  const isLead = projectCan(workspace, 'manage_project');
  const [releasing, setReleasing] = useState<CheckIssue | null>(null);
  const [releaseForm] = Form.useForm();

  async function release() {
    if (!check || !releasing) return;
    const values = await releaseForm.validateFields();
    try {
      await mutate(releasePath(workspace.project.id, check.id, releasing.id), 'POST', { reason: values.reason.trim(), decision: values.decision });
      setReleasing(null);
    } catch {
      /* 错误已提示；保留填写内容 */
    }
  }

  async function run() {
    if (!volumeOperationAllowed(workspace, 'check', volume) || busy) return;
    try {
      const value = await mutate(`/api/v1/projects/${workspace.project.id}/checks`, 'POST', { volume }) as { check: Check };
      setSelectedId(value.check.id);
    } catch {
      /* 显示实际检查失败 */
    }
  }

  useEffect(() => {
    const onRun = () => { void run(); };
    window.addEventListener('icg-run-check', onRun);
    return () => window.removeEventListener('icg-run-check', onRun);
  });

  function locate(item: CheckIssue) {
    const requirement = workspace.requirements.find(value => value.id === item.requirement_id);
    if (requirement) setSource(requirement.source);
    else if (item.chapter_id) {
      // 打开问题所在章节，编辑台读到问题清单后定位到段落（APP-M2-T166）
      requestIssueFocus(item.chapter_id, item.id);
      navigate(editorChapterPath(workspace.project.id, item.chapter_id));
    } else navigate(item.evidence_id ? 'matrix' : 'parse');
  }

  return (
    <>
      <section className="check-export-issues">
      {blockerSummary.hasBlockers && (
        <Alert
          className="blocker-alert-banner"
          data-testid="blocker-alert-banner"
          type="error"
          showIcon
          icon={<StopOutlined />}
          style={{ marginBottom: 12 }}
          message={`阻断 ${blockerSummary.totalBlockers} 项，递交版已锁定`}
          description={
            <div data-testid="blocker-chapters-list" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
              {blockerSummary.blockedChapters.map(ch => (
                <Tag
                  key={ch.chapterId}
                  color="error"
                  style={{ cursor: ch.chapterId !== 'global_non_chapter' ? 'pointer' : 'default', padding: '2px 8px' }}
                  onClick={() => {
                    if (ch.chapterId && ch.chapterId !== 'global_non_chapter') {
                      navigate(editorChapterPath(workspace.project.id, ch.chapterId));
                    }
                  }}
                >
                  {ch.chapterTitle} ({ch.blockerCount} 项)
                </Tag>
              ))}
            </div>
          }
        />
      )}

      <div className="check-issue-filters">
        {!technical && (
          <Radio.Group
            size="small"
            optionType="button"
            value={volume}
            onChange={e => { setVolume(e.target.value); setSelectedId(''); }}
            options={[
              { value: 'technical', label: '技术方案' },
              { value: 'business', label: '商务方案' },
              { value: 'all', label: '全文' },
            ]}
          />
        )}
        <Radio.Group
          size="small"
          optionType="button"
          value={severity}
          onChange={e => setSeverity(e.target.value)}
          options={[
            { value: 'all', label: `全部 ${check?.issues.length ?? 0}` },
            { value: 'blocker', label: `阻断 ${check?.issues.filter(item => isBlocker(item.severity)).length ?? 0}` },
            { value: 'warning', label: `警告 ${check?.issues.filter(item => item.severity === 'warning').length ?? 0}` },
            { value: 'info', label: `提示 ${check?.issues.filter(item => item.severity === 'info').length ?? 0}` },
          ]}
        />
        {check && (
          <span className="muted">
            {check.status === 'stale' ? '检查已过期' : check.passed ? '当前规则通过' : `待处理 ${unreleasedCount(check.issues)}`}
            {' · '}{formatTime(check.created_at)}
          </span>
        )}
      </div>

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
                    locale={{ emptyText: '还没有检查结果' }}
                    onRow={item => ({ onClick: () => locate(item), style: { cursor: 'pointer' } })}
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
                      {
                        title: '问题描述',
                        dataIndex: 'message',
                        render: (value: string, item: CheckIssue) => (
                          <div>
                            <div>{value}</div>
                            {!!item.details?.fragments?.length && <div className="muted">重复片段：{item.details.fragments.slice(0, 3).join('；')}</div>}
                            {item.details?.quote && !item.details?.fragments?.length && <div className="muted">原句：{item.details.quote}</div>}
                            {item.released && <Tag color="green" style={{ marginTop: 4 }}>已放行 · {item.released.by_name ?? item.released.by}：{item.released.reason}</Tag>}
                          </div>
                        ),
                      },
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
                        width: 110,
                        render: (_, item) => (
                          <Space size={0}>
                            <Button type="link" size="small" onClick={() => locate(item)}>
                              定位
                            </Button>
                            {canReleaseIssue(item, isLead) && check?.status !== 'stale' && (
                              <Button type="link" size="small" data-testid="check-release-button" disabled={busy}
                                onClick={() => { releaseForm.resetFields(); releaseForm.setFieldsValue({ decision: 'keep', reason: '' }); setReleasing(item); }}>
                                放行
                              </Button>
                            )}
                          </Space>
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
                      { title: '方案', dataIndex: 'volume', render: volumeName },
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
            ].filter(item => !technical || item.key === 'issues')}
          />
        </Card>
      </section>
      <Drawer title="问题依据 · 招标原文" open={!!source} onClose={() => setSource(null)} width={760}>
        <OriginalPreview source={source} />
      </Drawer>
      <Modal
        open={!!releasing}
        title="放行检查警告"
        okText="确认放行"
        cancelText="取消"
        confirmLoading={busy}
        onOk={() => void release()}
        onCancel={() => setReleasing(null)}
        destroyOnClose
      >
        {releasing && (
          <Form form={releaseForm} layout="vertical">
            <Alert type="warning" showIcon style={{ marginBottom: 12 }} message={releasing.message}
              description="放行会记录你的姓名、时间和理由；正文改动后放行失效，需重新确认。阻断级问题不能放行。" />
            <Form.Item name="decision" label="处理方式">
              <Radio.Group options={[
                { value: 'keep', label: releasing.code === 'EXTRA_NUMERIC_COMMITMENT' ? '确认保留该承诺' : '确认保留' },
                { value: 'accept', label: '确认无需修改' },
              ]} />
            </Form.Item>
            <Form.Item name="reason" label="理由" rules={[{ required: true, whitespace: true, message: '请填写放行理由' }, { max: 500 }]}>
              <Input.TextArea rows={3} placeholder="例如：销售确认本项目额外赠送质保；与历史标书重复部分为公司标准服务描述" />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </>
  );
}

// 合标核对清单：取最近一次递交版批次随导出生成的清单（PRD §5.9.2）。只列事实与系统结论，不替代人工核对。
function MergeChecklistCard() {
  const { workspace, token, report } = useProject();
  const latest = latestSubmissionWithChecklist(workspace.exports);
  const checklist = latest?.merge_checklist;
  if (technicalOnly(workspace)) return null;
  if (!latest || !checklist) {
    return (
      <Card title="合标核对清单" data-testid="merge-checklist-card">
        <Alert type="info" showIcon message="导出递交版时会同时生成合标核对清单（Excel）"
          description="清单列出合标时须人工核对的 9 类事项：方案与文件、页码与目录、评审索引表、两本之间的一致性结论、偏离表与点对点应答、密封份数装订、签章、暗标、文件命名。" />
      </Card>
    );
  }
  const stale = latest.status !== 'valid';
  return (
    <Card
      title="合标核对清单"
      data-testid="merge-checklist-card"
      extra={
        <Button size="small" icon={<DownloadOutlined />} onClick={() => download(latest.merge_checklist_url as string, token, checklistFilename(latest.id)).catch(report)}>
          下载 Excel
        </Button>
      }
    >
      {stale && <Alert type="warning" showIcon style={{ marginBottom: 8 }} message="已过期：方案已解锁或正文已改动，清单仅供追溯" />}
      <div className="muted" style={{ marginBottom: 8 }}>批次 {latest.id.slice(-10)} · {formatTime(checklist.generated_at)} · 依据全文检查 {checklist.check_id?.slice(-10)}</div>
      <Collapse
        size="small"
        items={checklist.sections.map(section => ({
          key: String(section.no),
          label: <Space>{section.no}. {section.item}{section.rows.some(r => r.status === 'not_run' || r.status === 'failed') && <Tag color="orange">须人工核对</Tag>}</Space>,
          children: (
            <List
              size="small"
              dataSource={section.rows}
              renderItem={row => (
                <List.Item>
                  <Space direction="vertical" size={0}>
                    <span>{row.status ? <Tag color={checklistRowTone(row.status)}>{row.status === 'not_run' ? '未运行' : row.status === 'manual' ? '人工' : row.status === 'passed' ? '通过' : '未通过'}</Tag> : null}{row.text}</span>
                    {row.source && <span className="muted">原文：{row.source}</span>}
                  </Space>
                </List.Item>
              )}
              footer={<span className="muted">合标时：{section.action}</span>}
            />
          ),
        }))}
      />
    </Card>
  );
}

export function ExportPage() {
  const { workspace, token, user, busy, mutate, report } = useProject();
  const technical = technicalOnly(workspace);
  const [volume, setVolume] = useState<Volume | 'all'>(technical ? 'technical' : projectCan(workspace, 'export_internal') ? 'all' : workspace.permissions?.export_volumes[0] ?? 'all');
  const [checkId, setCheckId] = useState('');
  const [companyTemplate, setCompanyTemplate] = useState<WordTemplate | null>(null);
  const [templateChoice, setTemplateChoice] = useState<TemplateChoice | null>(null);
  const [insertAttachments, setInsertAttachments] = useState(true);
  const [attachmentWatermark, setAttachmentWatermark] = useState('');
  useEffect(() => {
    let alive = true;
    request<{ template: WordTemplate | null }>(wordTemplatePaths.info(workspace.project.company_id), token)
      .then(result => { if (alive) setCompanyTemplate(result.template); })
      .catch(() => { if (alive) setCompanyTemplate(null); });
    return () => { alive = false; };
  }, [workspace.project.company_id, token]);
  const template = templateChoice ?? defaultTemplateChoice(companyTemplate);
  useVolumesStatus(workspace.project.id, token, workspace.revision);
  const validChecks = workspace.checks.filter(item => item.volume === volume && item.passed && item.status !== 'stale');
  const check = validChecks.find(item => item.id === checkId) ?? validChecks[validChecks.length - 1];
  const full = (volume === 'all' ? projectVolumes(workspace) : [volume]).every(
    v => workspace.chapters.some(item => item.volume === v && item.content.trim()) && workspace.chapters.filter(item => item.volume === v).every(item => item.content.trim())
  );
  const latestCheckForVolume = workspace.checks.slice().reverse().find(item => item.volume === volume) ?? check;
  const blockerSummary = deriveBlockerSummary(latestCheckForVolume, workspace.chapters);
  const hasBlockers = blockerSummary.hasBlockers;
  const submissionCheck = canExportSubmission({
    hasBlockers,
    blockerCount: blockerSummary.totalBlockers,
    fullContent: full,
    hasPassedCheck: !!check && check.passed,
    parseConfirmed: workspace.parse_confirmed,
    userCanExport: volumeOperationAllowed(workspace, 'export', technical ? 'technical' : volume),
    isFinalized: true,
  });
  const canSubmit = projectCan(workspace, 'manage_project');
  const internalDisabled = busy || (technical
    ? !volumeOperationAllowed(workspace, 'export', 'technical')
    : (!volumeOperationAllowed(workspace, 'export', volume) || !full || !workspace.parse_confirmed));
  const submissionDisabled = busy || !canSubmit || !submissionCheck.allowed;
  const internalReason = !internalDisabled || busy ? ''
    : (technical || !volumeOperationAllowed(workspace, 'export', volume)) ? '没有导出权限'
    : !workspace.parse_confirmed ? '解析结果未确认'
    : !full ? '正文未齐'
    : '';
  const submissionReason = !submissionDisabled || busy ? ''
    : !canSubmit ? '没有递交版权限'
    : (submissionCheck.reason || `阻断 ${blockerSummary.totalBlockers} 项`);
  const checkVolume: Volume | 'all' = technical ? 'technical' : (projectCan(workspace, 'check_all') ? 'all' : volume);

  async function create(nextKind: 'internal' | 'submission') {
    if (nextKind === 'submission' && !submissionCheck.allowed) return;
    if (technical && nextKind === 'internal') {
      if (!volumeOperationAllowed(workspace, 'export', 'technical')) return;
      try {
        await mutate(`/api/v1/projects/${workspace.project.id}/exports`, 'POST',
          exportRequestBody(check?.id || 'technical-internal', 'internal', 'technical', { template, insertAttachments, watermark: attachmentWatermark }));
      } catch {
        /* 后台再次核对正文和角色 */
      }
      return;
    }
    if (!check || !volumeOperationAllowed(workspace, 'export', volume)) return;
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/exports`, 'POST',
        exportRequestBody(check.id, nextKind, volume, { template, insertAttachments, watermark: attachmentWatermark }));
    } catch {
      /* 后台再次核对完整方案、角色和检查 */
    }
  }

  return (
    <>
      <div className="check-export-toolbar">
        {!technical && (
          <Button
            icon={<ReloadOutlined />}
            loading={busy}
            disabled={!volumeOperationAllowed(workspace, 'check', checkVolume)}
            onClick={() => window.dispatchEvent(new Event('icg-run-check'))}
          >
            运行检查
          </Button>
        )}
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          data-testid="export-generate-btn"
          disabled={internalDisabled}
          loading={busy}
          onClick={() => void create('internal')}
        >
          导出内部稿
        </Button>
        {!technical && (
          <Button
            data-testid="export-submission-btn"
            disabled={submissionDisabled}
            loading={busy}
            onClick={() => void create('submission')}
          >
            导出递交版
          </Button>
        )}
        {!technical && (internalReason || submissionReason) && (
          <span className="muted">{[internalReason && `内部稿：${internalReason}`, submissionReason && `递交版：${submissionReason}`].filter(Boolean).join(' · ')}</span>
        )}
        {technical && internalReason && <span className="muted">内部稿：{internalReason}</span>}
      </div>
      <aside className="check-export-side">
        {technical && workspace.technical_quality && !workspace.technical_quality.passed && (
          <Alert type="warning" showIcon data-testid="technical-quality-export-warning" message={workspace.technical_quality.warning || '质量八条未全部通过'} />
        )}
        {technical && (workspace.technical_needs_review?.length ?? 0) > 0 && (
          <Alert type="warning" showIcon data-testid="technical-needs-review" message={`需要核对：${workspace.technical_needs_review?.join('、')}`} />
        )}
        {technical && workspace.technical_deviation_note && (
          <Alert type="warning" showIcon data-testid="technical-deviation-note" message={workspace.technical_deviation_note} />
        )}
        {!technical && hasBlockers && (
          <Alert
            type="error"
            showIcon
            className="export-blocker-warning"
            data-testid="export-blocker-warning"
            message={`阻断 ${blockerSummary.totalBlockers} 项，递交版已锁定`}
          />
        )}
        <Card
          size="small"
          title="导出记录"
          extra={!technical ? (
            <Button size="small" type="link" icon={<DownloadOutlined />} data-testid="response-trace-btn"
              onClick={() => download(responseTracePath(workspace.project.id, volume), token, `response-trace-${volume}.xlsx`).catch(report)}>
              响应追溯表
            </Button>
          ) : null}
        >
          <div data-testid="export-history-table">
            {workspace.exports.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有导出记录" />}
            {workspace.exports.slice().reverse().map(item => {
              const meta = getExportKindMeta(item.kind);
              const hash = item.volumes?.[0]?.docx_sha256 || item.sha256 || item.volumes?.[0]?.sha256;
              const finger = formatSha256Fingerprint(hash);
              const bytes = item.file_size ?? item.size_bytes ?? item.volumes.reduce((sum, v) => sum + (v.size_bytes ?? v.file_size ?? 0), 0);
              const tech = item.volumes.find(v => v.volume === 'technical');
              const comm = item.volumes.find(v => v.volume === 'business');
              const status = exportStatusMeta(item.status);
              return (
                <div key={item.id} className="export-history-row">
                  <Tooltip title={`导出记录 ${item.id}`}>
                    <span data-testid="export-history-id">{exportBatchLabel(item)}</span>
                  </Tooltip>
                  <Tag color={meta.tagColor}>{meta.label}</Tag>
                  <span className="muted">{formatTime(item.created_at)}</span>
                  <span className="muted">{getExportVolumeLabel(item.volume || (item.volumes.length > 1 ? 'all' : item.volumes[0]?.volume || 'all'))}</span>
                  <span className="muted">{formatFileSize(bytes)}</span>
                  <Tooltip title={item.error_message || `完整指纹: ${finger.full}`}>
                    <Tag color={status.color} data-testid="export-status">{status.label}</Tag>
                  </Tooltip>
                  <Tooltip title={`完整指纹: ${finger.full}`}>
                    <span data-testid="export-fingerprint">{finger.short}</span>
                  </Tooltip>
                  {tech ? (
                    <Button size="small" type="link" data-testid="export-download-btn" onClick={() => download(tech.download_url, token, tech.filename).catch(report)}>
                      下载{item.status === 'stale' ? '（已过期）' : ''}
                    </Button>
                  ) : null}
                  {comm ? (
                    <Button size="small" type="link" data-testid="export-download-btn" onClick={() => download(comm.download_url, token, comm.filename).catch(report)}>
                      商务{item.status === 'stale' ? '（已过期）' : ''}
                    </Button>
                  ) : null}
                  {item.deviation_download_url ? (
                    <Button size="small" type="link" data-testid="export-deviation-btn" onClick={() => download(item.deviation_download_url as string, token, '技术偏离表.docx').catch(report)}>
                      技术偏离表
                    </Button>
                  ) : null}
                  {item.merge_checklist_url ? (
                    <Button size="small" type="link" data-testid="export-checklist-btn" onClick={() => download(item.merge_checklist_url as string, token, checklistFilename(item.id)).catch(report)}>
                      合标清单{item.status !== 'valid' ? '（已过期）' : ''}
                    </Button>
                  ) : null}
                  {!tech && !comm && <span className="muted" data-testid="export-no-files">{item.status === 'failed' ? item.error_message : '未生成方案文件'}</span>}
                  <span className="muted">{item.created_by || item.operator_name || user.name || user.id}</span>
                </div>
              );
            })}
          </div>
        </Card>
        <Collapse
          items={[{
            key: 'options',
            label: '导出选项',
            children: (
              <Form layout="vertical">
                {!technical && (
                  <Form.Item label="生成范围">
                    <Radio.Group
                      aria-label="导出方案范围"
                      data-testid="export-volume-radio"
                      value={volume}
                      onChange={event => { setVolume(event.target.value); setCheckId(''); }}
                      options={[
                        { value: 'all', label: '技术方案与商务方案合订', disabled: !volumeOperationAllowed(workspace, 'export', 'all') },
                        { value: 'technical', label: '技术方案', disabled: !volumeOperationAllowed(workspace, 'export', 'technical') },
                        { value: 'business', label: '商务方案', disabled: !volumeOperationAllowed(workspace, 'export', 'business') },
                      ]}
                    />
                  </Form.Item>
                )}
                <Form.Item label="Word 模板">
                  <Select data-testid="export-template-select" value={template} onChange={setTemplateChoice} options={templateOptions(companyTemplate)} />
                </Form.Item>
                <Form.Item label="附件扫描件">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Checkbox data-testid="export-insert-attachments" checked={insertAttachments} onChange={event => setInsertAttachments(event.target.checked)}>
                      插入条款挂接资料的扫描件
                    </Checkbox>
                    <Input data-testid="export-attachment-watermark" disabled={!insertAttachments} maxLength={60}
                      value={attachmentWatermark} onChange={event => setAttachmentWatermark(event.target.value)}
                      addonBefore="水印" placeholder={`仅用于${workspace.project.name}投标`} />
                  </Space>
                </Form.Item>
                {!technical && (
                  <Form.Item label="检查批次">
                    <Select
                      value={check?.id}
                      placeholder="请先运行当前范围的有效检查"
                      onChange={setCheckId}
                      options={validChecks.map(item => ({ value: item.id, label: `${formatTime(item.created_at)} · ${volumeName(item.volume)}检查` }))}
                    />
                  </Form.Item>
                )}
              </Form>
            ),
          }]}
        />
        <MergeChecklistCard />
      </aside>
    </>
  );
}

export { ProjectHeader } from './ProjectHeader';
export { ProjectListPage } from './ProjectListPage';

