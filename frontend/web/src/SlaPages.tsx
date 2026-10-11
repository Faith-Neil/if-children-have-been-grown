// 为什么有这个文件：把公司实际可承诺的服务标准与每个项目的招标要求放在一起核对。
// 它解决什么问题：负责人能维护模板、比较承诺、说明风险，并下载真实内部承诺函。
import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Descriptions, Empty, Form, Input, Modal, Row, Select, Space, Table, Tag } from 'antd';
import { DownloadOutlined, FileTextOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { download } from './api';
import { projectCan } from './project-team';
import { formatTime, useProject } from './context';
import { displaySlaValue, slaScalar, slaVariablePayload, slaUnits, slaGroups } from './sla-form';
import type { Account, SlaRow, SlaTemplate, SlaVariable, Source } from './types';

const directions = [{ value: 'lower_better', label: '越小越好（例如响应时间）' }, { value: 'higher_better', label: '越大越好（例如培训次数）' }, { value: 'exact', label: '须完全相同（例如服务范围）' }];
const editions = [{ value: 'standard', label: '通用版' }, { value: 'finance', label: '金融行业版' }, { value: 'government', label: '政企版' }];
const serviceHours = [{ value: 'h5x8', label: '每周5天、每天8小时' }, { value: 'h5x8_holiday', label: '每周5天、每天8小时，含节假日安排' }, { value: 'h7x24', label: '每周7天、每天24小时' }];
const variableTypes = [{ value: 'integer', label: '整数' }, { value: 'decimal', label: '小数' }, { value: 'text', label: '文字' }];
const blankVariable = (): SlaVariable => ({ var_key: '', label: '', group: 'response', value_type: 'integer', default_value: null, unit: 'minute', compare_direction: 'lower_better', best_committable_value: null });
const judgmentColors: Record<SlaRow['judgment'], string> = { satisfied: 'green', not_satisfied: 'red', exceeds_capability: 'orange', missing: 'default', manual: 'purple', not_required: 'blue', unquantified: 'gold' };
const factLabel = (status: string) => status === 'confirmed' ? '已逐项确认' : status === 'needs_review' ? '需重新核对' : '尚未确认';

type TemplateProps = { items: SlaTemplate[]; user: Account; busy: boolean; mutate: (path: string, method: string, body: unknown) => Promise<unknown>; report: (error: unknown) => void };

export function SlaTemplatesPage({ items, user, busy, mutate, report }: TemplateProps) {
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<SlaTemplate | null>(null);
  const [form] = Form.useForm();
  const canWrite = user.role === 'manager';
  function editing(item: SlaTemplate | null) {
    setEdit(item); form.resetFields();
    form.setFieldsValue(item ? { ...item, reason: '', variables: item.variables.map(value => ({ ...value })) } : { name: '', version_no: '1.0', edition: 'standard', service_hours: 'h5x8', status: 'pending', body_text: '', reason: '', variables: [blankVariable()] });
    setOpen(true);
  }
  async function save() {
    if (!canWrite || busy) return;
    let values;
    try { values = await form.validateFields(); } catch { return; }
    let variables;
    try {
      variables = values.variables.map(slaVariablePayload);
      if (new Set(variables.map((item: SlaVariable) => item.var_key)).size !== variables.length) throw new Error('同一模板的指标标识不能重复，请逐行核对。');
      if (values.status === 'confirmed' && !values.reason?.trim()) throw new Error('确认模板前，请填写本次核对依据。');
    } catch (error) { report(error); return; }
    try { await mutate(edit ? `/api/v1/sla/templates/${edit.id}` : '/api/v1/sla/templates', edit ? 'PATCH' : 'POST', { name: values.name, version_no: values.version_no, edition: values.edition, service_hours: values.service_hours, body_text: values.body_text || '', status: values.status, reason: values.reason || '', variables }); setOpen(false); }
    catch { /* 统一入口报告错误，当前模板填写内容保留。 */ }
  }
  return <>
    <div className="sla-template-heading"><div><h3>服务承诺模板</h3><p className="muted">服务承诺（SLA）说明多快响应、多久恢复等标准；公司能力与项目承诺分别保存。</p></div><Button type="primary" icon={<PlusOutlined />} disabled={busy || !canWrite} onClick={() => editing(null)}>新增合成模板</Button></div>
    <Alert className="page-notice" type="info" showIcon message={canWrite ? '由公司模板维护账号确认可承诺的标准' : '当前账号可查看，模板维护需要公司经理账号'} description="这里没有预置真实公司能力。能力极限留空表示未提供依据；项目不能把它当作已验证能力。修改模板后，引用它的项目需要刷新并重新核对。" />
    <Table rowKey="id" size="small" dataSource={items} pagination={false} columns={[
      { title: '模板名称', dataIndex: 'name', render: (value, item) => <a onClick={() => editing(item)}>{value}</a> },
      { title: '业务版本', dataIndex: 'version_no' },
      { title: '行业 / 服务时段', render: (_, item) => <>{editions.find(value => value.value === item.edition)?.label || item.edition}<p className="muted">{serviceHours.find(value => value.value === item.service_hours)?.label || item.service_hours}</p></> },
      { title: '指标数', render: (_, item) => item.variables.length },
      { title: '核对状态', dataIndex: 'status', render: value => <Tag color={value === 'confirmed' ? 'green' : 'orange'}>{value === 'confirmed' ? '已确认' : value === 'rejected' ? '已退回' : '待确认'}</Tag> },
      { title: '操作', render: (_, item) => <Button type="link" disabled={busy} onClick={() => editing(item)}>{canWrite ? '查看 / 修改' : '查看详情'}</Button> },
    ]} />
    <Modal title={edit ? '服务承诺模板详情' : '新增合成服务承诺模板'} width={1040} open={open} onCancel={() => { if (!busy) setOpen(false); }} onOk={save} confirmLoading={busy} okText="保存模板" cancelText="关闭" okButtonProps={{ disabled: !canWrite || busy }}>
      <Form form={form} layout="vertical" disabled={busy || !canWrite}>
        <Row gutter={16}><Col span={16}><Form.Item name="name" label="模板名称" rules={[{ required: true, whitespace: true, message: '请填写模板名称' }]}><Input placeholder="例如：合成测试响应标准" /></Form.Item></Col><Col span={8}><Form.Item name="version_no" label="业务版本（便于人工识别）" rules={[{ required: true, whitespace: true }]}><Input placeholder="例如1.0" /></Form.Item></Col></Row>
        <Row gutter={16}><Col span={12}><Form.Item name="edition" label="适用行业"><Select options={editions} /></Form.Item></Col><Col span={12}><Form.Item name="service_hours" label="服务时段"><Select options={serviceHours} /></Form.Item></Col></Row>
        <Alert type="info" showIcon message="指标标识用来连接矩阵与正文。例如P1.response是一级故障响应时限的内部名称。" description="数值填写时不带单位；响应时限越小越好，培训次数越大越好。工作日、自然日和月不能随意互换。" />
        <Form.List name="variables" rules={[{ validator: async (_, values) => { if (!values?.length) throw new Error('至少添加一个服务指标'); } }]}>{(fields, { add, remove }, { errors }) => <>
          {fields.map(field => <Card size="small" key={field.key} className="sla-variable-card" title={`指标 ${field.name + 1}`} extra={<Button size="small" danger disabled={!canWrite || busy || fields.length <= 1} onClick={() => remove(field.name)}>移除指标</Button>}>
            <Row gutter={12}><Col span={8}><Form.Item name={[field.name, 'var_key']} label="指标标识" rules={[{ required: true, whitespace: true }]}><Input placeholder="P1.response" /></Form.Item></Col><Col span={10}><Form.Item name={[field.name, 'label']} label="指标名称" rules={[{ required: true, whitespace: true }]}><Input placeholder="一级故障响应时限" /></Form.Item></Col><Col span={6}><Form.Item name={[field.name, 'group']} label="所属组" rules={[{ required: true }]}><Select options={slaGroups} /></Form.Item></Col></Row>
            <Row gutter={12}><Col span={6}><Form.Item name={[field.name, 'value_type']} label="取值类型" rules={[{ required: true }]}><Select options={variableTypes} /></Form.Item></Col><Col span={6}><Form.Item name={[field.name, 'default_value']} label="通常承诺值" rules={[{ required: true, message: '请登记模板默认值' }]}><Input placeholder="模板默认值；项目可另外核对修改" /></Form.Item></Col><Col span={5}><Form.Item name={[field.name, 'unit']} label="单位"><Select options={slaUnits} /></Form.Item></Col><Col span={7}><Form.Item name={[field.name, 'best_committable_value']} label="公司能力极限"><Input placeholder="留空表示未提供依据" /></Form.Item></Col></Row>
            <Form.Item name={[field.name, 'compare_direction']} label="怎样算更严格" rules={[{ required: true }]}><Select options={directions} /></Form.Item>
          </Card>)}<Form.ErrorList errors={errors} /><Button icon={<PlusOutlined />} disabled={!canWrite || busy} onClick={() => add(blankVariable())}>新增服务指标</Button>
        </>}</Form.List>
        <Form.Item name="body_text" label="承诺函正文" rules={[{ required: true, whitespace: true, message: '请填写承诺函正文' }]} style={{ marginTop: 20 }}><Input.TextArea rows={4} placeholder="可使用模板变量，例如：一级故障响应时限为{{P1.response}}分钟。只使用已定义的指标标识。" /></Form.Item>
        <Row gutter={16}><Col span={8}><Form.Item name="status" label="核对状态"><Select options={[{ value: 'pending', label: '待确认' }, { value: 'confirmed', label: '已逐项核对并确认' }]} /></Form.Item></Col><Col span={16}><Form.Item name="reason" label="本次修改 / 核对依据"><Input.TextArea rows={2} placeholder="确认模板时必填，说明这些承诺及能力值的依据" /></Form.Item></Col></Row>
      </Form>
      <Alert type="warning" showIcon message="请使用合成资料验证，不填写未经核实的真实公司能力。完整故障等级与服务时段覆盖检查仍待补齐。" />
    </Modal>
  </>;
}

export function SlaMatrixPage({ onLocate }: { onLocate: (source: Source) => void }) {
  const { workspace, user, token, slaTemplates, busy, mutate, report, navigate } = useProject();
  const { modal, message } = AntApp.useApp();
  const sla = workspace.sla ?? null;
  const canWrite = projectCan(workspace, 'manage_sla');
  const [templateId, setTemplateId] = useState(sla?.template_id || '');
  const [templateOpen, setTemplateOpen] = useState(false);
  const [templateForm] = Form.useForm();
  const [edit, setEdit] = useState<SlaRow | null>(null);
  const [valueForm] = Form.useForm();
  const [review, setReview] = useState<SlaRow | null>(null);
  const [reviewForm] = Form.useForm();
  const selectedRequirementId = Form.useWatch('requirement_id', valueForm);
  const selectedRequirement = workspace.requirements.find(item => item.id === selectedRequirementId);
  const selectedTemplate = slaTemplates.find(item => item.id === templateId);
  const projectPath = `/api/v1/projects/${workspace.project.id}/sla`;
  useEffect(() => { setTemplateId(sla?.template_id || ''); }, [workspace.project.id, sla?.template_id]);
  function chooseTemplate() { if (!selectedTemplate || busy || !canWrite) return; templateForm.resetFields(); setTemplateOpen(true); }
  async function applyTemplate() {
    if (!selectedTemplate || busy || !canWrite) return;
    let values; try { values = await templateForm.validateFields(); } catch { return; }
    try { await mutate(`${projectPath}/template`, 'POST', { template_id: templateId, reason: values.reason || '' }); setTemplateOpen(false); message.success('项目模板已更新，请核对每个服务承诺和对应事实。'); } catch { /* 保留确认说明。 */ }
  }
  function editRow(row: SlaRow) { valueForm.resetFields(); valueForm.setFieldsValue({ project_value: row.project_value, project_unit: row.project_unit || row.unit, requirement_id: row.requirement_id, tender_required_value: row.tender_required_value, tender_unit: row.tender_unit || row.unit, reason: '' }); setEdit(row); }
  async function saveValue() {
    if (!edit || busy || !canWrite) return;
    let values; try { values = await valueForm.validateFields(); } catch { return; }
    let payload;
    try { payload = { project_value: slaScalar(values.project_value, edit.value_type, '我方承诺'), project_unit: values.project_unit || '', requirement_id: values.requirement_id || null, tender_required_value: slaScalar(values.tender_required_value, edit.value_type, '招标要求'), tender_unit: values.tender_unit || '', reason: values.reason || '' }; } catch (error) { report(error); return; }
    try { await mutate(`${projectPath}/values/${encodeURIComponent(edit.var_key)}`, 'PATCH', payload); setEdit(null); } catch { /* 失败或版本冲突时保留表单。 */ }
  }
  function applyTender() {
    if (!canWrite || busy) return;
    modal.confirm({ title: '按已登记的招标要求取值', content: '可比较的指标会采用招标值。若招标值超出公司能力，后台保留公司能力极限并标为不满足；未量化或需人工判断的项仍需单独核对。本操作不代替事实确认或风险批准。', okText: '按招标要求取值', cancelText: '取消', onOk: async () => { await mutate(`${projectPath}/apply-tender`, 'POST', {}); } });
  }
  function reviewRow(row: SlaRow) { reviewForm.resetFields(); setReview(row); }
  async function saveReview() {
    if (!review || busy || !canWrite) return;
    let values; try { values = await reviewForm.validateFields(); } catch { return; }
    try { await mutate(`${projectPath}/values/${encodeURIComponent(review.var_key)}/review`, 'POST', { reason: values.reason }); setReview(null); } catch { /* 不满足招标的项不能批准，错误由后台说明。 */ }
  }
  async function commitment() {
    if (!canWrite || busy) return;
    try { const result = await mutate(`${projectPath}/commitment`, 'POST', {}) as { commitment: { filename: string; download_url: string } }; await download(result.commitment.download_url, token, result.commitment.filename); } catch (error) { if (!(error instanceof Error && 'status' in error)) report(error); }
  }
  return <>
    <div className="sla-toolbar"><Space wrap><Select aria-label="选用服务承诺模板" placeholder="选择当前公司已确认的服务模板" value={templateId || undefined} onChange={setTemplateId} style={{ width: 290 }} options={slaTemplates.map(item => ({ value: item.id, label: `${item.name} · ${item.version_no}${item.status !== 'confirmed' ? '（待确认）' : ''}`, disabled: item.status !== 'confirmed' }))} /><Button icon={sla?.template_id === templateId ? <ReloadOutlined /> : undefined} disabled={busy || !canWrite || !selectedTemplate || selectedTemplate.status !== 'confirmed'} onClick={chooseTemplate}>{sla?.template_id === templateId ? '刷新模板与能力' : '选用模板'}</Button><Button disabled={busy || !canWrite || !sla || sla.template_stale} onClick={applyTender}>按招标要求取值</Button></Space><Button icon={<DownloadOutlined />} disabled={busy || !canWrite || !sla || sla.template_stale} onClick={commitment}>导出内部承诺函</Button></div>
    {!canWrite && <Alert className="page-notice" type="info" showIcon message="服务承诺由项目负责人维护；当前角色仅查看" />}
    {sla?.template_stale && <Alert className="page-notice" type="warning" showIcon message="公司模板已变化，本项目的能力依据需要刷新" description="同一模板刷新会保留项目承诺与招标来源，并要求重新核对；尚未核对的值不能进入导出。" />}
    {!sla ? <Card><Empty description={slaTemplates.some(item => item.status === 'confirmed') ? '尚未选用服务模板，请由负责人在上方选用' : '还没有已确认的模板，请先到企业资料库维护服务承诺模板'} /></Card> : <>
      <Alert className="page-notice" type="info" showIcon message={`当前模板：${sla.template_name}`} description="比较方向、单位与判定来自后台。没有招标要求或要求未量化会单独显示；工作日和自然日等不能强行换算。数字改变后，须到事实表逐项重新确认。" />
      <Table rowKey="var_key" size="small" scroll={{ x: 1240 }} pagination={false} dataSource={sla.rows} rowClassName={row => ['not_satisfied', 'missing'].includes(row.judgment) || row.source_stale ? 'risk-row' : ''} columns={[
        { title: '指标 / 比较方式', width: 185, render: (_, row) => <><b>{row.label}</b><p className="muted">{slaGroups.find(item => item.value === row.group)?.label || row.group} · {directions.find(item => item.value === row.compare_direction)?.label}</p><small className="muted">{row.var_key}</small></> },
        { title: '招标要求值 / 来源', width: 215, render: (_, row) => <>{displaySlaValue(row.tender_required_value, row.tender_unit, row.requirement_id ? '原文未量化' : '未登记招标要求')}{row.source ? <p><a onClick={() => onLocate(row.source!)}><FileTextOutlined /> 第{row.source.page}页</a></p> : <p className="muted">未绑定原文</p>}{row.source_stale && <Tag color="red">原文已变化，需重新核对</Tag>}</> },
        { title: '我方承诺值', width: 150, render: (_, row) => <>{displaySlaValue(row.project_value, row.project_unit)}<p><Button type="link" size="small" disabled={busy || !canWrite || sla.template_stale} onClick={() => editRow(row)}>核对 / 修改</Button></p></> },
        { title: '公司能力极限', width: 150, render: (_, row) => <>{displaySlaValue(row.best_committable_value, row.unit, '未提供依据')}<p className="muted">取自公司模板</p></> },
        { title: '后台判定 / 负责人核对', width: 290, render: (_, row) => <><Tag color={judgmentColors[row.judgment]}>{row.judgment_label}</Tag><p>{row.message}</p>{row.review ? <p className="muted">已留痕：{row.review.reason}<br />{formatTime(row.review.at)}</p> : ['exceeds_capability', 'manual', 'unquantified', 'not_required'].includes(row.judgment) ? <Button type="link" size="small" disabled={busy || !canWrite || sla.template_stale || row.source_stale} onClick={() => reviewRow(row)}>说明依据并核对风险</Button> : null}</> },
        { title: '事实确认 / 正文变量', width: 225, render: (_, row) => <><Tag color={row.fact_status === 'confirmed' ? 'green' : 'orange'}>{factLabel(row.fact_status)}</Tag><p><Button type="link" size="small" onClick={() => navigate('facts')}>去事实表逐项确认</Button></p><code>{row.variable_token}</code></> },
      ]} />
    </>}
    <Modal title={sla?.template_id === templateId ? '刷新当前服务模板' : '选用服务模板'} open={templateOpen} onCancel={() => { if (!busy) setTemplateOpen(false); }} onOk={applyTemplate} confirmLoading={busy} okText="确认选用" cancelText="取消">
      <Alert showIcon type={sla && sla.template_id !== templateId ? 'warning' : 'info'} message={sla && sla.template_id !== templateId ? '更换为不同模板会重置当前项目承诺及原文绑定' : sla ? '刷新会保留承诺与来源，并重新核对公司能力' : '首次选用后需登记招标要求，并逐项确认服务事实'} description={selectedTemplate?.name} />
      <Form form={templateForm} layout="vertical" disabled={busy} style={{ marginTop: 16 }}><Form.Item name="reason" label="选用 / 更新依据" rules={sla && sla.template_id !== templateId ? [{ required: true, whitespace: true, message: '更换模板请填写依据' }] : []}><Input.TextArea rows={3} placeholder="说明为何适用于当前项目" /></Form.Item></Form>
    </Modal>
    <Modal title={`核对服务指标：${edit?.label || ''}`} width={740} open={!!edit} onCancel={() => { if (!busy) setEdit(null); }} onOk={saveValue} confirmLoading={busy} okText="保存并重新计算" cancelText="取消" okButtonProps={{ disabled: !canWrite }}>
      <Form form={valueForm} layout="vertical" disabled={busy || !canWrite}>
        <Form.Item name="requirement_id" label="对应招标原要求"><Select allowClear placeholder="选择原文条款；无要求时留空" onChange={() => valueForm.setFieldsValue({ tender_required_value: null })} options={workspace.requirements.filter(item => item.status === 'confirmed').map(item => ({ value: item.id, label: `第${item.source.page}页 · ${item.text}` }))} /></Form.Item>
        {selectedRequirement ? <Card size="small" className="stack-card"><p>{selectedRequirement.text}</p><blockquote>{selectedRequirement.source.quote}</blockquote><a onClick={() => onLocate(selectedRequirement.source)}>查看第{selectedRequirement.source.page}页原文</a></Card> : <Alert className="page-notice" type="info" showIcon message="未绑定招标要求会显示“招标未要求”，不会被当成满足招标。" />}
        <Row gutter={16}><Col span={16}><Form.Item name="tender_required_value" label="从原文核对的要求值"><Input disabled={!selectedRequirement || busy} placeholder="原文只有定性要求时留空；数字不带单位" /></Form.Item></Col><Col span={8}><Form.Item name="tender_unit" label="招标单位"><Select disabled={!selectedRequirement || busy} options={slaUnits} /></Form.Item></Col></Row>
        <Row gutter={16}><Col span={16}><Form.Item name="project_value" label="我方承诺值"><Input placeholder="按真实承诺填写，留空则标为未填写" /></Form.Item></Col><Col span={8}><Form.Item name="project_unit" label="我方单位"><Select options={slaUnits} /></Form.Item></Col></Row>
        <Descriptions size="small" column={1} items={[{ key: 'direction', label: '比较规则', children: directions.find(item => item.value === edit?.compare_direction)?.label }, { key: 'capability', label: '公司能力（本页不可更改）', children: displaySlaValue(edit?.best_committable_value, edit?.unit, '未提供依据') }]} />
        <Form.Item name="reason" label="本次原文核对 / 修改依据" rules={[{ required: true, whitespace: true, message: '请说明取值依据' }]} style={{ marginTop: 16 }}><Input.TextArea rows={3} placeholder="说明数值来自哪段原文，或为何没有量化要求" /></Form.Item>
      </Form>
      <Alert type="warning" showIcon message="服务指标与事实表共用一个取值；保存后，原有风险批准和事实确认需要重新核对。" />
    </Modal>
    <Modal title="负责人说明服务承诺风险" open={!!review} onCancel={() => { if (!busy) setReview(null); }} onOk={saveReview} confirmLoading={busy} okText="保存核对依据" cancelText="取消" okButtonProps={{ disabled: !canWrite }}>
      <Alert type="warning" showIcon message={review?.message} description="这次核对只对当前模板、数值及来源有效；修改后会失效。不满足招标要求的承诺不能通过批准变成满足。" /><Form form={reviewForm} layout="vertical" disabled={busy || !canWrite} style={{ marginTop: 16 }}><Form.Item name="reason" label="人工判断 / 风险处理依据" rules={[{ required: true, whitespace: true, message: '请填写核对依据' }]}><Input.TextArea rows={4} /></Form.Item></Form>
    </Modal>
  </>;
}
