// 为什么有这个文件：项目设置里新增的设置组界面——项目状态、合作方协议、SLA 取值摘要、规则覆盖、分册格式、递交版完整值
// （PRD v1.8 §5.1.3、§5.1.4；APP-M2-T097～T100）。
// 它解决什么问题：这些设置此前只有占位提示；现在读回后台保存的真实内容，保存失败保留填写，取消后的项目整体只读。

import { useCallback, useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Checkbox, Input, InputNumber, Select, Space, Switch, Table, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { request, userFacingMessage } from '../shared/api';
import { formatTime, volumeName } from '../app/context';
import {
  ACTION_LABELS, FULL_VALUE_LABELS, RESULT_LABELS, availableStatusActions, canConfirmFullValue, fullValuePayload, partnerNeedsAgreement,
  partnersPayload, projectSubPath, ruleOverridesPayload, settingsPath, statusRequest, volumeSettingsPayload,
  type PartnerRow, type ProjectSettingsData, type RuleOverrideRow, type StatusAction, type VolumeSettingRow,
} from './project-settings-core';

type Mutate = (path: string, method: string, body?: unknown) => Promise<unknown>;
type Base = { projectId: string; token: string | null; canEdit: boolean; mutate: Mutate; busy: boolean; settings: ProjectSettingsData | null };

/** 读回后台设置；workspace.revision 变化（任何保存后）自动重读 */
export function useProjectSettings(projectId: string, token: string | null, revision: number) {
  const [settings, setSettings] = useState<ProjectSettingsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try { setSettings(await request<ProjectSettingsData>(settingsPath(projectId), token)); setError(null); }
    catch (cause) { setError(userFacingMessage(cause)); }
  }, [projectId, token]);
  useEffect(() => { void load(); }, [load, revision]);
  return { settings, error, reload: load };
}

function useSave(mutate: Mutate, success: string) {
  const { message } = AntApp.useApp();
  const [saving, setSaving] = useState(false);
  const save = async (path: string, method: string, build: () => unknown) => {
    setSaving(true);
    try { const result = await mutate(path, method, build()) as { warnings?: string[] }; message.success(success); result?.warnings?.forEach(item => message.warning(item)); return true; }
    catch (cause) { message.error(userFacingMessage(cause)); return false; }
    finally { setSaving(false); }
  };
  return { saving, save };
}

export function ProjectStatusCard({ projectId, canEdit, mutate, busy, settings }: Base) {
  const { message, modal } = AntApp.useApp();
  const status = settings?.status;
  const [reason, setReason] = useState('');
  const [result, setResult] = useState<string | undefined>();
  if (!status) return null;
  const actions = canEdit ? availableStatusActions(status.status) : [];
  const run = async (action: StatusAction) => {
    let body;
    try { body = statusRequest(action, reason, result); } catch (cause) { message.error(userFacingMessage(cause)); return; }
    const go = async () => {
      try { await mutate(projectSubPath(projectId, 'status'), 'POST', body); setReason(''); setResult(undefined); message.success(`${ACTION_LABELS[action]}已办理。`); }
      catch (cause) { message.error(userFacingMessage(cause)); }
    };
    if (action === 'cancel') modal.confirm({ title: '确认取消项目', content: '取消后项目只读，不能撤销，已有正文和记录保留。', okText: '确认取消', okButtonProps: { danger: true }, cancelText: '再想想', onOk: go });
    else await go();
  };
  return <div data-testid="project-status-card">
    <Space wrap><b>当前状态：</b><Tag color={status.read_only ? 'default' : 'blue'} data-testid="project-status-tag">{status.label}{status.result_label ? `（${status.result_label}）` : ''}</Tag>
      {!status.registered && <span className="muted">由工作台阶段推出；递交、开标、结果由项目负责人登记</span>}</Space>
    {status.read_only && <Alert style={{ marginTop: 8 }} type="warning" showIcon message="项目已取消，只能查看，不能再修改。" />}
    {status.history.length > 0 && <Table size="small" style={{ marginTop: 8 }} rowKey={(_, index) => String(index)} pagination={false} dataSource={status.history as Array<Record<string, string>>}
      columns={[{ title: '时间', dataIndex: 'at', render: formatTime }, { title: '变更', render: (_, row) => `${row.from} → ${row.to}` }, { title: '原因 / 结果', render: (_, row) => RESULT_LABELS[row.result] ?? row.reason }]} />}
    {actions.length > 0 && <Space wrap style={{ marginTop: 8 }}>
      {(actions.includes('cancel') || actions.includes('result')) && <Input style={{ width: 260 }} placeholder="原因（取消时必填）" value={reason} onChange={event => setReason(event.target.value)} aria-label="状态变更原因" />}
      {actions.includes('result') && <Select style={{ width: 120 }} placeholder="结果" value={result} onChange={setResult} options={Object.entries(RESULT_LABELS).map(([value, label]) => ({ value, label }))} aria-label="登记结果" />}
      {actions.map(action => <Button key={action} danger={action === 'cancel'} disabled={busy} onClick={() => run(action)} data-testid={`status-action-${action}`}>{ACTION_LABELS[action]}</Button>)}
    </Space>}
  </div>;
}

export function PartnersCard({ projectId, canEdit, mutate, busy, settings }: Base) {
  const { saving, save } = useSave(mutate, '合作方已保存。');
  const [rows, setRows] = useState<PartnerRow[]>([]);
  useEffect(() => { if (settings) setRows(settings.partners); }, [settings?.revision]);  // eslint-disable-line react-hooks/exhaustive-deps
  const update = (index: number, patch: Partial<PartnerRow>) => setRows(current => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  const missing = partnerNeedsAgreement(rows.map(row => ({ ...row, agreement_ok: !!row.agreement_attachment_id?.trim() })));
  return <div data-testid="partners-card">
    <p className="muted">联合体成员或分包方必须上传联合体协议或分包协议，其资料才能被章节引用；缺协议的合作方可先登记，资料会显示“缺协议”且不可选。</p>
    {missing.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} message={`${missing.length} 个合作方缺协议：${missing.map(item => item.partner_entity_id).join('、')}`} />}
    <Table<PartnerRow> size="small" rowKey={(_, index) => String(index)} pagination={false} dataSource={rows} locale={{ emptyText: '没有联合体成员或分包方' }}
      columns={[
        { title: '合作方主体', render: (_, row, index) => <Input value={row.partner_entity_id} disabled={!canEdit} aria-label={`合作方 ${index + 1}`} onChange={event => update(index, { partner_entity_id: event.target.value })} /> },
        { title: '关系', width: 130, render: (_, row, index) => <Select style={{ width: 110 }} allowClear disabled={!canEdit} value={row.relation_type ?? undefined} onChange={value => update(index, { relation_type: value ?? null })} options={[{ value: 'consortium', label: '联合体成员' }, { value: 'subcontract', label: '分包方' }]} /> },
        { title: '协议附件编号', render: (_, row, index) => <Input value={row.agreement_attachment_id ?? ''} disabled={!canEdit} onChange={event => update(index, { agreement_attachment_id: event.target.value })} /> },
        { title: '协议', width: 90, render: (_, row) => row.agreement_attachment_id?.trim() ? <Tag color="green">已上传</Tag> : <Tag color="orange">缺协议</Tag> },
        { title: '', width: 60, render: (_, _row, index) => canEdit && <Button type="link" danger size="small" onClick={() => setRows(current => current.filter((_, i) => i !== index))}>移除</Button> },
      ]} />
    {canEdit && <Space style={{ marginTop: 8 }}>
      <Button icon={<PlusOutlined />} onClick={() => setRows(current => [...current, { partner_entity_id: '', agreement_attachment_id: null, agreement_ok: false }])}>添加合作方</Button>
      <Button type="primary" loading={saving} disabled={busy} onClick={() => save(`/api/v1/projects/${encodeURIComponent(projectId)}`, 'PATCH', () => ({ project_partners: partnersPayload(rows) }))}>保存合作方</Button>
    </Space>}
  </div>;
}

export function SlaSummaryCard({ settings, onOpen }: { settings: ProjectSettingsData | null; onOpen: () => void }) {
  const sla = settings?.sla;
  return <div data-testid="sla-summary">
    {sla ? <Space direction="vertical">
      <span>使用模板：<b>{sla.template_name}</b>{sla.template_stale && <Tag color="orange" style={{ marginLeft: 8 }}>模板已变化</Tag>}</span>
      <span>项目取值 {sla.row_count} 项；超出能力 <Tag color={sla.exceeds_capability_count ? 'red' : 'green'}>{sla.exceeds_capability_count}</Tag> 项；待重新核对 <Tag color={sla.needs_review_count ? 'orange' : 'green'}>{sla.needs_review_count}</Tag> 项</span>
    </Space> : <span className="muted">本项目尚未选定服务承诺模板。</span>}
    <p className="muted" style={{ marginTop: 8 }}>在项目内改写取值只存在本项目，不回写资料库；逐项核对在响应矩阵的服务承诺矩阵进行。</p>
    <Button onClick={onOpen}>前往服务承诺矩阵</Button>
  </div>;
}

const RULE_PRESETS = [{ value: 'check_service_period', label: '有效期覆盖服务期检查' }, { value: 'require_own_staff', label: '拟派人员须为本单位员工' }, { value: 'social_insurance_months', label: '连续缴纳社保月数' }, { value: 'proof_valid_days.', label: '证明材料有效天数（后接材料类型）' }];

export function RuleOverridesCard({ projectId, canEdit, mutate, busy, settings, requirements }: Base & { requirements: Array<{ id: string; text?: string }> }) {
  const { saving, save } = useSave(mutate, '规则覆盖已保存，之后的合规检查按覆盖值运行。');
  const [rows, setRows] = useState<RuleOverrideRow[]>([]);
  useEffect(() => { if (settings) setRows(settings.rule_overrides); }, [settings?.revision]);  // eslint-disable-line react-hooks/exhaustive-deps
  const update = (index: number, patch: Partial<RuleOverrideRow>) => setRows(current => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  return <div data-testid="rule-overrides-card">
    <Alert type="info" showIcon style={{ marginBottom: 8 }} message="覆盖值已按项目保存并读回；合规检查引擎尚未读取这些覆盖值，检查结果暂不随之变化（见交付说明）。" />
    <Table<RuleOverrideRow> size="small" rowKey={(_, index) => String(index)} pagination={false} dataSource={rows} locale={{ emptyText: '没有项目级覆盖' }}
      columns={[
        { title: '规则', render: (_, row, index) => <Input list="rule-presets" style={{ width: 240 }} value={row.rule_key} disabled={!canEdit} aria-label={`规则 ${index + 1}`} onChange={event => update(index, { rule_key: event.target.value })} /> },
        { title: '取值', render: (_, row, index) => typeof row.value === 'boolean' || row.rule_key === 'check_service_period' || row.rule_key === 'require_own_staff'
          ? <Switch checked={row.value === true} disabled={!canEdit} onChange={checked => update(index, { value: checked })} />
          : <InputNumber value={typeof row.value === 'number' ? row.value : undefined} disabled={!canEdit} onChange={value => update(index, { value: value ?? 0 })} /> },
        { title: '依据的招标要求', render: (_, row, index) => <Select style={{ width: 220 }} allowClear showSearch optionFilterProp="label" disabled={!canEdit} value={row.source_requirement_id ?? undefined}
          options={requirements.map(item => ({ value: item.id, label: (item.text ?? item.id).slice(0, 30) }))} onChange={value => update(index, { source_requirement_id: value ?? null })} /> },
        { title: '', width: 60, render: (_, _row, index) => canEdit && <Button type="link" danger size="small" onClick={() => setRows(current => current.filter((_, i) => i !== index))}>移除</Button> },
      ]} />
    <datalist id="rule-presets">{RULE_PRESETS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</datalist>
    {canEdit && <Space style={{ marginTop: 8 }}>
      <Button icon={<PlusOutlined />} onClick={() => setRows(current => [...current, { rule_key: 'check_service_period', value: true }])}>添加覆盖</Button>
      <Button type="primary" loading={saving} disabled={busy} onClick={() => save(projectSubPath(projectId, 'rule-overrides'), 'PUT', () => ruleOverridesPayload(rows))}>保存规则覆盖</Button>
    </Space>}
  </div>;
}

export function VolumeFormatCard({ projectId, canEdit, mutate, busy, settings, writerNames }: Base & { writerNames: string[] }) {
  const { saving, save } = useSave(mutate, '分册格式已保存。');
  const [rows, setRows] = useState<VolumeSettingRow[]>([]);
  useEffect(() => { if (settings) setRows(settings.volume_settings); }, [settings?.revision]);  // eslint-disable-line react-hooks/exhaustive-deps
  const update = (index: number, patch: Partial<VolumeSettingRow>) => setRows(current => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  return <div data-testid="volume-format-card">
    <p className="muted">内部截止时间晚于项目投标截止时间会给警告；递交文件名不得含编写人变量或姓名，导出递交版时优先使用。</p>
    <Table<VolumeSettingRow> size="small" rowKey="volume" pagination={false} dataSource={rows} scroll={{ x: 900 }}
      columns={[
        { title: '分册', width: 80, render: (_, row) => volumeName(row.volume) },
        { title: '编制方式', width: 130, render: (_, row, index) => <Select style={{ width: 110 }} disabled={!canEdit} value={row.compile_mode} onChange={value => update(index, { compile_mode: value })} options={[{ value: 'system', label: '系统编制' }, { value: 'external', label: '系统外编制' }]} /> },
        { title: '内部截止时间', width: 200, render: (_, row, index) => <Input placeholder="2026-12-30T17:00" disabled={!canEdit} value={row.internal_deadline ?? ''} onChange={event => update(index, { internal_deadline: event.target.value })} /> },
        { title: '单独密封', width: 90, render: (_, row, index) => <Switch disabled={!canEdit} checked={row.separate_seal} onChange={checked => update(index, { separate_seal: checked })} /> },
        { title: '页码', width: 130, render: (_, row, index) => <Select style={{ width: 110 }} disabled={!canEdit} value={row.page_numbering} onChange={value => update(index, { page_numbering: value })} options={[{ value: 'per_volume', label: '每册从 1 起' }, { value: 'continuous', label: '连续页码' }] } /> },
        { title: '暗标', width: 70, render: (_, row, index) => <Switch disabled={!canEdit} checked={row.blind_bid} onChange={checked => update(index, { blind_bid: checked })} /> },
        { title: '封面模板', width: 150, render: (_, row, index) => <Input disabled={!canEdit} value={row.cover_template ?? ''} onChange={event => update(index, { cover_template: event.target.value })} /> },
        { title: '递交文件名', width: 180, render: (_, row, index) => <Input disabled={!canEdit} value={row.submit_file_name ?? ''} onChange={event => update(index, { submit_file_name: event.target.value })} /> },
      ]} />
    {canEdit && <Button style={{ marginTop: 8 }} type="primary" loading={saving} disabled={busy || !rows.length} onClick={() => save(projectSubPath(projectId, 'volume-settings'), 'PUT', () => volumeSettingsPayload(rows, writerNames))}>保存分册格式</Button>}
  </div>;
}

export function FullValueCard({ projectId, canEdit, mutate, busy, settings, requirements }: Base & { requirements: Array<{ id: string; text?: string }> }) {
  const { saving, save } = useSave(mutate, '递交版完整值类别已确认并留痕。');
  const [categories, setCategories] = useState<string[]>([]);
  const [basis, setBasis] = useState<string[]>([]);
  useEffect(() => { if (settings) { setCategories(settings.submit_full_value.categories); setBasis(settings.submit_full_value.basis_requirement_ids); } }, [settings?.revision]);  // eslint-disable-line react-hooks/exhaustive-deps
  const allowed = canEdit && canConfirmFullValue({ manage_project: canEdit });
  const info = settings?.submit_full_value;
  return <div data-testid="full-value-card">
    <p className="muted">招标要求在递交文件中填写完整身份证件号码、手机号等高敏信息时，由项目负责人勾选类别并关联依据；未勾选的类别在递交版中仍掩码。</p>
    <Checkbox.Group disabled={!allowed} value={categories} onChange={values => setCategories(values as string[])} options={Object.entries(FULL_VALUE_LABELS).map(([value, label]) => ({ value, label }))} />
    <div style={{ marginTop: 8 }}><Select mode="multiple" style={{ width: '100%' }} disabled={!allowed} placeholder="依据的招标要求（勾选类别时必填）" optionFilterProp="label" value={basis} onChange={setBasis}
      options={requirements.map(item => ({ value: item.id, label: (item.text ?? item.id).slice(0, 40) }))} /></div>
    {info?.confirmed_at && <p className="muted" style={{ marginTop: 8 }}>确认人 {info.confirmed_by}，{formatTime(info.confirmed_at)}</p>}
    {allowed ? <Button style={{ marginTop: 8 }} type="primary" loading={saving} disabled={busy} onClick={() => save(projectSubPath(projectId, 'submit-full-value'), 'PUT', () => fullValuePayload(categories, basis))}>确认完整值类别</Button>
      : <Alert style={{ marginTop: 8 }} type="info" showIcon message="只有本项目负责人可以勾选完整值类别。" />}
  </div>;
}
