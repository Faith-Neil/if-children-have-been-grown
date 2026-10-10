// 为什么有这个文件：让负责人逐章确认要点、字数目标和实际使用的项目事实。
// 它解决什么问题：生成有明确依据，必备事实不能被编写人取消，可选事实不会全部塞进每一章。
import { useEffect } from 'react';
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { formatTime, useProject } from './context';
import { displaySlaValue } from './sla-form';
import { writingPlanPayload, writingPlanRows, type WritingPlanRow } from './writing-input';

export default function WritingPlanReview({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { workspace, user, busy, mutate, report } = useProject();
  const [form] = Form.useForm<{ chapters: WritingPlanRow[] }>();
  const writable = user.role === 'manager';
  const requiredFacts = workspace.facts.filter(fact => fact.required);
  const optionalFacts = workspace.facts.filter(fact => !fact.required);
  useEffect(() => { if (open) form.setFieldsValue({ chapters: writingPlanRows(workspace) }); }, [open]);
  async function save() {
    if (!writable || busy || !workspace.parse_confirmed) return;
    const values = await form.validateFields();
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/plan`, 'POST', { chapters: writingPlanPayload(values.chapters) });
      onClose();
    } catch (error) { if (!(error instanceof Error && 'status' in error)) report(error); }
  }
  const plan = workspace.writing_plan;
  return <Modal title="写作方案与大纲确认" width={900} open={open} onCancel={onClose} onOk={save} styles={{ body: { maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' } }}
    confirmLoading={busy} okText="负责人确认方案" cancelText="返回编辑台"
    okButtonProps={{ disabled: !writable || busy || !workspace.parse_confirmed }}>
    <Alert showIcon type="info" message="逐章选择写作依据，必备事实自动用于每一章"
      description="字数是写作目标，需要人工复核；已有正文、草稿或编辑权的章节不能静默删除。确认方案会使旧候选和检查需要重新核对。" />
    {!writable && <Alert className="page-notice" type="warning" showIcon message="当前账号可查看方案；只有项目负责人能修改并确认" />}
    {plan?.confirmed_at && <p className="muted">上次确认：{plan.confirmed_by_name || (plan.confirmed_by === user.id ? user.name : '项目负责人')} · {formatTime(plan.confirmed_at)} · {workspace.plan_confirmed ? '当前有效' : '输入已变化，须重新确认'}</p>}
    <Card size="small" title={`全部章节必备事实 · ${requiredFacts.length} 项`} className="writing-required-facts">
      {requiredFacts.length ? requiredFacts.map(fact => <div className="writing-required-fact" key={fact.id}>
        <Space wrap><Tag color={fact.status === 'confirmed' ? 'green' : 'orange'}>{fact.status === 'confirmed' ? '已确认' : '待核对'}</Tag><b>{fact.source_type === 'sla' ? workspace.sla?.rows.find(row => row.var_key === fact.sla_var_key)?.label ?? fact.key : fact.key}</b><span>{displaySlaValue(fact.value, fact.unit)}</span><Tag>自动加入 · 不能取消</Tag></Space>
        {fact.source && <small className="muted">原文第 {fact.source.page} 页：{fact.source.quote}</small>}
      </div>) : <p className="muted">当前项目没有标记为必备的事实，仍会核对已选择的事实和本章条款。</p>}
    </Card>
    <Form form={form} layout="vertical" disabled={!writable || busy} className="writing-plan-form">
      <Form.List name="chapters">{(fields, { add, remove }) => <>
        {fields.map(field => <Card size="small" className="writing-chapter-plan" key={field.key} title={`章节 ${field.name + 1}`}
          extra={<Button size="small" danger onClick={() => remove(field.name)} disabled={!writable || busy || fields.length <= 2}>移除章节</Button>}>
          <Form.Item name={[field.name, 'id']} hidden><Input /></Form.Item>
          <div className="plan-row"><Form.Item name={[field.name, 'title']} label="章节名称" rules={[{ required: true, whitespace: true, message: '请填写章节名称' }]} style={{ flex: 1 }}><Input maxLength={200} /></Form.Item>
            <Form.Item name={[field.name, 'volume']} label="分册" rules={[{ required: true }]}><Select style={{ width: 140 }} options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /></Form.Item></div>
          <Form.Item name={[field.name, 'fact_ids']} label="本章可选事实" extra="只采用本章选中且已确认的事实；必备事实已在上方固定加入。">
            <Select mode="multiple" allowClear placeholder="选择本章需要引用的项目事实" optionFilterProp="label"
              options={optionalFacts.map(fact => ({ value: fact.id, label: `${fact.key} · ${displaySlaValue(fact.value, fact.unit)}${fact.status === 'confirmed' ? '' : '（待核对）'}`, disabled: fact.status !== 'confirmed' }))} />
          </Form.Item>
          <Form.Item name={[field.name, 'writing_points']} label="写作要点" extra="说明本章要怎样回应要求；不能在这里修改已经确认的项目事实或服务承诺。"><Input.TextArea rows={3} maxLength={5000} placeholder="例如：先说明工作步骤，再列出质量核对方式和交付清单" /></Form.Item>
          <Form.Item name={[field.name, 'target_length']} label="字数目标" rules={[{ type: 'integer', min: 1, max: 100000, message: '填写 1 至 100000 的整数，或留空' }]} extra="留空表示不设目标；这不是自动通过的验收标准。"><InputNumber min={1} max={100000} precision={0} style={{ width: 180 }} placeholder="不设目标" addonAfter="字" /></Form.Item>
        </Card>)}
        <Button icon={<PlusOutlined />} disabled={!writable || busy} onClick={() => add({ title: '', volume: 'technical', fact_ids: [], writing_points: '', target_length: null })}>新增章节</Button>
      </>}</Form.List>
    </Form>
    <Alert className="page-notice" showIcon type="warning" message="当前确认整章输入；完整证据计划、增值章节、分册责任分配和选区助手仍在后续任务中" />
  </Modal>;
}
