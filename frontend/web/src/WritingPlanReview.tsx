// 为什么有这个文件：让本节编写人、分册负责人和项目负责人按各自范围保存及确认写作方案。
// 它解决什么问题：已确认的一章可以单独生成，另一册尚未确认不会挡住本章；调整人员和大纲都有明确边界。
import { useEffect, useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { formatTime, useProject, volumeName } from './context';
import { displaySlaValue } from './sla-form';
import { advancePlanReviewRow, capturePlanReviewBasis, chapterPlanChanged, chapterPlanPayload, chapterStructureChanged, planReviewRowProblem, planReviewScopeProblem, writingPlanPayload, writingPlanRowBasis, writingPlanRows, type WritingPlanReviewBasis, type WritingPlanRow } from './writing-input';
import type { Chapter } from './types';
import { assignmentCandidates, chapterCan, planScopes, type PlanScope } from './project-team';

export default function WritingPlanReview({ open, onClose, chapterId }: { open: boolean; onClose: () => void; chapterId?: string }) {
  const { workspace, user, library, slaTemplates, busy, mutate, report } = useProject();
  const { modal, message } = AntApp.useApp();
  const [form] = Form.useForm<{ chapters: WritingPlanRow[]; reason?: string }>();
  const [scope, setScope] = useState<PlanScope | 'chapter'>('chapter');
  const [reviewBasis, setReviewBasis] = useState<WritingPlanReviewBasis | null>(null);
  const latest = useRef({ workspace, library, slaTemplates });
  latest.current = { workspace, library, slaTemplates };
  const scopes = planScopes(workspace, user.id);
  const rows = Form.useWatch('chapters', form) ?? [];
  const canStructure = scope !== 'chapter' && scopes.includes(scope);
  const scopeProblem = reviewBasis ? planReviewScopeProblem(reviewBasis, workspace, { library, slaTemplates }) : null;
  const requiredFacts = workspace.facts.filter(fact => fact.required);
  const optionalFacts = workspace.facts.filter(fact => !fact.required);
  function resetRows(next: PlanScope | 'chapter') {
    setScope(next);
    const all = writingPlanRows(workspace);
    form.resetFields();
    form.setFieldsValue({ chapters: all.filter(row => next === 'all' || (next === 'chapter' ? row.id === chapterId : row.volume === next)) });
    setReviewBasis(capturePlanReviewBasis(workspace, next, chapterId, { library, slaTemplates }));
  }
  useEffect(() => { if (open) resetRows(scopes[0] ?? 'chapter'); }, [open, chapterId]);
  function changeScope(next: PlanScope | 'chapter') {
    if (form.isFieldsTouched()) modal.confirm({ title: '先处理当前未保存的方案', content: '切换范围会重新读取已保存方案，当前表单里未保存的输入将丢失。请先保存本节，或确认放弃这次表单修改。', okText: '放弃表单修改并切换', cancelText: '继续核对', onOk: () => resetRows(next) });
    else resetRows(next);
  }
  async function saveOne(index: number) {
    const row = form.getFieldValue(['chapters', index]) as WritingPlanRow;
    const chapter = workspace.chapters.find(item => item.id === row.id);
    if (!chapter || !chapterCan(chapter, 'confirm_plan') || busy) return;
    try {
      await form.validateFields([['chapters', index, 'target_length']]);
      const snapshot = latest.current;
      const problem = planReviewRowProblem(reviewBasis, chapter.id, snapshot.workspace, snapshot);
      if (problem) { report(new Error(problem)); return; }
      const result = await mutate(`/api/v1/projects/${workspace.project.id}/chapters/${chapter.id}/plan`, 'PATCH', chapterPlanPayload(row)) as { chapter?: Chapter };
      if (result.chapter) setReviewBasis(previous => previous ? advancePlanReviewRow(previous, snapshot.workspace, result.chapter!, snapshot) : previous);
      message.success('本节方案已保存为待确认，正文和其他章节未替换。');
    } catch (error) { if (!(error instanceof Error && 'status' in error)) report(error); }
  }
  async function confirmOne(index: number) {
    const row = form.getFieldValue(['chapters', index]) as WritingPlanRow;
    const chapter = workspace.chapters.find(item => item.id === row.id);
    if (!chapter || !chapterCan(chapter, 'confirm_plan') || busy) return;
    const snapshot = latest.current;
    const problem = planReviewRowProblem(reviewBasis, chapter.id, snapshot.workspace, snapshot);
    if (problem) { report(new Error(problem)); return; }
    if (chapterPlanChanged(row, chapter.writing_input)) { report(new Error('本节表单还有未保存的修改，请先保存本节方案，再确认。')); return; }
    if (chapterStructureChanged(row, chapter)) { report(new Error('章节名称、分册或编写人还有未保存的修改。请先保存人员交接，或由选定范围负责人保存大纲，再确认本节。')); return; }
    try { const result = await mutate(`/api/v1/projects/${workspace.project.id}/chapters/${chapter.id}/plan/confirm`, 'POST', {}) as { chapter?: Chapter }; if (result.chapter) setReviewBasis(previous => previous ? advancePlanReviewRow(previous, snapshot.workspace, result.chapter!, snapshot) : previous); message.success('本节方案已确认，可以单独生成；其他章节维持各自状态。'); }
    catch { /* 保留当前输入和后台给出的待办原因。 */ }
  }
  async function saveAssignee(index: number) {
    const row = form.getFieldValue(['chapters', index]) as WritingPlanRow;
    const chapter = workspace.chapters.find(item => item.id === row.id);
    if (!chapter || !chapterCan(chapter, 'assign') || busy || (row.assignee_id ?? null) === (chapter.assignee_id ?? null)) return;
    const problem = planReviewRowProblem(reviewBasis, chapter.id, latest.current.workspace, latest.current);
    if (problem) { report(new Error(problem)); return; }
    let reason = '';
    modal.confirm({ title: `交接本节编写人：${chapter.title}`, content: <><p>换人会撤销旧编辑权，保留正式正文、历史和原账号个人草稿；本节方案须重新确认。草稿不会自动交给接手人。</p><Input.TextArea aria-label="章节交接理由" rows={3} placeholder="说明换人原因，以及正文与个人草稿怎样核对交接" onChange={event => { reason = event.target.value; }} /></>, okText: '按交接理由保存编写人', cancelText: '取消', onOk: async () => {
      if (!reason.trim()) throw new Error('请填写本次章节交接理由。');
      const snapshot = latest.current;
      const currentProblem = planReviewRowProblem(reviewBasis, chapter.id, snapshot.workspace, snapshot);
      if (currentProblem) throw new Error(currentProblem);
      const result = await mutate(`/api/v1/projects/${workspace.project.id}/chapters/${chapter.id}/assignment`, 'PATCH', { assignee_id: row.assignee_id || null, reason: reason.trim() }) as { chapter?: Chapter };
      if (result.chapter) setReviewBasis(previous => previous ? advancePlanReviewRow(previous, snapshot.workspace, result.chapter!, snapshot) : previous);
      message.success('本节编写人已更新，请重新确认本节方案。');
    } });
  }
  async function confirmScope() {
    if (!canStructure || busy || !workspace.parse_confirmed) return;
    try {
      const values = await form.validateFields();
      const problem = planReviewScopeProblem(reviewBasis, latest.current.workspace, latest.current);
      if (problem) { report(new Error(problem)); return; }
      await mutate(`/api/v1/projects/${workspace.project.id}/plan`, 'POST', { scope, chapters: writingPlanPayload(values.chapters), reason: values.reason?.trim() || '' });
      message.success(scope === 'all' ? '项目范围的章节方案已确认。' : `${volumeName(scope)}范围的章节方案已确认，另一册保持原状态。`);
      onClose();
    } catch (error) { if (!(error instanceof Error && 'status' in error)) report(error); }
  }
  function describeRow(row: WritingPlanRow, snapshot = workspace) {
    return [`章节：${row.title}`, `分册：${volumeName(row.volume)}`, `编写人：${snapshot.team?.members.find(member => member.user_id === row.assignee_id)?.name ?? row.assignee_id ?? '未指定'}`, `可选事实：${row.fact_ids.map(id => { const fact = snapshot.facts.find(item => item.id === id); return fact ? `${fact.key}=${displaySlaValue(fact.value, fact.unit)}` : `${id}（已不可见）`; }).join('；') || '未选择'}`, `字数目标：${row.target_length ?? '不设目标'}`, `写作要点：${row.writing_points || '未填写'}`].join('\n');
  }
  function reviewScope() {
    if (busy) return;
    const snapshot = latest.current;
    const proposed = capturePlanReviewBasis(snapshot.workspace, scope, chapterId, snapshot);
    const actualRows = writingPlanRows(snapshot.workspace).filter(row => proposed.order.includes(row.id ?? ''));
    const localRows = form.getFieldValue('chapters') as WritingPlanRow[];
    modal.confirm({ title: '核对并载入最新范围方案', width: 900,
      content: <><p>后台最新章节顺序：{actualRows.map(row => row.title).join(' → ') || '本范围已无章节'}。</p><div className="diff-columns"><div><h4>当前表单（可先复制保留）</h4><pre className="diff-before">{localRows.map(row => describeRow(row)).join('\n\n')}</pre></div><div><h4>后台最新已保存方案</h4><pre className="diff-after">{actualRows.map(row => describeRow(row, snapshot.workspace)).join('\n\n')}</pre></div></div><p>载入将替换当前范围内未保存的输入与本地增删章节；后台正文、草稿和方案不变。取消会保留当前表单。</p></>,
      okText: '已核对，载入最新范围方案', cancelText: '保留当前填写',
      onOk: () => {
        const problem = planReviewScopeProblem(proposed, latest.current.workspace, latest.current);
        if (problem) { report(new Error('核对期间后台方案又有变化，当前表单未替换。请重新打开核对窗口。')); throw new Error(problem); }
        form.resetFields(); form.setFieldsValue({ chapters: actualRows }); setReviewBasis(proposed);
      },
    });
  }
  function reviewRow(index: number) {
    if (busy) return;
    const row = form.getFieldValue(['chapters', index]) as WritingPlanRow;
    const snapshot = latest.current;
    const savedChapter = snapshot.workspace.chapters.find(chapter => chapter.id === row.id);
    if (!savedChapter || (scope !== 'all' && scope !== 'chapter' && savedChapter.volume !== scope)) { reviewScope(); return; }
    const actualRow = writingPlanRows(snapshot.workspace).find(chapter => chapter.id === row.id);
    if (!actualRow) return;
    const proposedBasis = writingPlanRowBasis(snapshot.workspace, savedChapter, snapshot);
    modal.confirm({ title: `核对并载入最新本节方案：${savedChapter.title}`, width: 850,
      content: <><div className="diff-columns"><div><h4>当前未保存的填写（可先复制保留）</h4><pre className="diff-before">{describeRow(row)}</pre></div><div><h4>后台最新已保存方案</h4><pre className="diff-after">{describeRow(actualRow, snapshot.workspace)}</pre></div></div><p>当前来源要求：{snapshot.workspace.requirements.filter(requirement => requirement.chapter_id === row.id).map(requirement => requirement.text).join('；') || '本节未映射条款'}。</p><p>请同时核对上方必备事实。载入只替换本节表单，其他行保留原输入和各自核对依据；后台记录不变。取消保留当前文字。</p></>,
      okText: '已核对，载入最新本节方案', cancelText: '保留当前填写',
      onOk: () => {
        const current = latest.current.workspace.chapters.find(chapter => chapter.id === row.id);
        if (!current || writingPlanRowBasis(latest.current.workspace, current, latest.current) !== proposedBasis) { report(new Error('核对期间本节又有变化，当前填写未替换。请重新打开核对窗口。')); throw new Error('本节方案再次变化。'); }
        const indexNow = (form.getFieldValue('chapters') as WritingPlanRow[]).findIndex(chapter => chapter.id === row.id);
        if (indexNow < 0) throw new Error('当前表单章节已经变化，请重新核对范围方案。');
        form.setFieldValue(['chapters', indexNow], actualRow);
        setReviewBasis(previous => previous ? advancePlanReviewRow(previous, snapshot.workspace, savedChapter, snapshot) : previous);
      },
    });
  }
  return <Modal title="写作方案与大纲确认" width={940} open={open} onCancel={onClose} styles={{ body: { maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' } }} footer={<Space wrap><Button onClick={onClose}>返回编辑台</Button>{canStructure && <Button type="primary" loading={busy} disabled={!workspace.parse_confirmed || !!scopeProblem} onClick={confirmScope}>{scope === 'all' ? '确认项目范围方案与大纲' : `确认${volumeName(scope)}方案与大纲`}</Button>}</Space>}>
    <Space wrap className="plan-scope-toolbar"><b>操作范围</b><Select aria-label="写作方案操作范围" value={scope} onChange={changeScope} style={{ minWidth: 180 }} options={[...(chapterId ? [{ value: 'chapter', label: '当前本节' }] : []), ...scopes.map(value => ({ value, label: value === 'all' ? '全部项目章节' : volumeName(value) }))]} /><span className="muted">本节保存与确认分开；批量确认只作用于选定范围。</span></Space>
    <Alert showIcon type="info" message="本节编写人确认本节，分册负责人确认本册，项目负责人确认全项目" description="每册必须指定负责人。未保存的表单修改不算确认，其他章节尚未确认不会挡住已确认的本节。大纲删章受正文、编辑权和个人草稿保护。" />
    {scopeProblem && <Alert className="page-notice" type="warning" showIcon message="后台方案发生变化，当前填写仍保留" description={scopeProblem} action={<Button disabled={busy} onClick={reviewScope}>核对并载入最新范围方案</Button>} />}
    <Card size="small" title={`全部章节必备事实 · ${requiredFacts.length} 项`} className="writing-required-facts">
      {requiredFacts.length ? requiredFacts.map(fact => <div className="writing-required-fact" key={fact.id}><Space wrap><Tag color={fact.status === 'confirmed' ? 'green' : 'orange'}>{fact.status === 'confirmed' ? '已确认' : '待核对'}</Tag><b>{fact.source_type === 'sla' ? workspace.sla?.rows.find(row => row.var_key === fact.sla_var_key)?.label ?? fact.key : fact.key}</b><span>{displaySlaValue(fact.value, fact.unit)}</span><Tag>自动加入 · 不能取消</Tag></Space>{fact.source && <small className="muted">原文第 {fact.source.page} 页：{fact.source.quote}</small>}</div>) : <p className="muted">当前项目没有标记为必备的事实，仍会核对已选择事实与本章条款。</p>}
    </Card>
    <Form form={form} layout="vertical" className="writing-plan-form">
      {canStructure && <Form.Item name="reason" label="本次大纲 / 人员调整的交接依据" extra="涉及已有个人草稿或编辑权的换人、删改时必填；正文与历史保留，草稿不会转交。"><Input.TextArea rows={2} maxLength={2000} placeholder="说明为什么调整结构或人员，以及怎样交接已写内容" /></Form.Item>}
      <Form.List name="chapters">{(fields, { add, remove }) => <>
        {fields.map(field => {
          const row = rows[field.name];
          const chapter = workspace.chapters.find(item => item.id === row?.id);
          const rowProblem = row?.id ? planReviewRowProblem(reviewBasis, row.id, workspace, { library, slaTemplates }) : null;
          const editable = chapter ? chapterCan(chapter, 'confirm_plan') : !row?.id && canStructure;
          const assignable = chapter ? chapterCan(chapter, 'assign') : !row?.id && canStructure;
          const current = chapter?.writing_input?.is_current === true;
          const structurePending = !!row && !!chapter && chapterStructureChanged(row, chapter);
          let pending = true;
          try { pending = !!row && chapterPlanChanged(row, chapter?.writing_input); } catch { /* 非法字数待用户修正，确认保持禁用。 */ }
          return <Card size="small" className="writing-chapter-plan" key={field.key} title={<Space wrap><span>{row?.title || `新章节 ${field.name + 1}`}</span><Tag color={current ? 'green' : 'orange'}>{current ? '本节已确认' : '本节待确认'}</Tag></Space>} extra={<Button size="small" danger onClick={() => remove(field.name)} disabled={!canStructure || busy}>移除章节</Button>}>
            {rowProblem && <Alert className="page-notice" type="warning" showIcon message="本节后台内容已变化，当前输入保留" description={rowProblem} action={<Button disabled={busy} onClick={() => reviewRow(field.name)}>核对并载入最新本节方案</Button>} />}
            <Form.Item name={[field.name, 'id']} hidden><Input /></Form.Item>
            <div className="plan-row"><Form.Item name={[field.name, 'title']} label="章节名称" rules={[{ required: true, whitespace: true, message: '请填写章节名称' }]} style={{ flex: 1 }}><Input disabled={!canStructure || busy} maxLength={200} /></Form.Item><Form.Item name={[field.name, 'volume']} label="分册" rules={[{ required: true }]}><Select disabled={!canStructure || busy || scope !== 'all'} style={{ width: 140 }} options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /></Form.Item></div>
            <div className="plan-row"><Form.Item name={[field.name, 'assignee_id']} label="本节编写人" style={{ flex: 1 }} extra={chapter?.assignee_name ? `当前已保存：${chapter.assignee_name}` : '未指定本节编写人'}><Select aria-label={`章节 ${field.name + 1} 的编写人`} disabled={!assignable || busy} allowClear placeholder="选择参与本册的编写人" options={assignmentCandidates(workspace.team?.members ?? [], row?.volume ?? 'technical').map(member => ({ value: member.user_id, label: member.name }))} /></Form.Item>{chapter && <Button style={{ marginTop: 30 }} disabled={!assignable || busy || !!rowProblem || (row?.assignee_id ?? null) === (chapter.assignee_id ?? null)} onClick={() => saveAssignee(field.name)}>说明交接并保存编写人</Button>}</div>
            <Form.Item name={[field.name, 'fact_ids']} label="本章可选事实" extra="只采用本章选中且已确认的事实；必备事实已自动加入。"><Select disabled={!editable || busy} mode="multiple" allowClear placeholder="选择本章需要引用的项目事实" optionFilterProp="label" options={optionalFacts.map(fact => ({ value: fact.id, label: `${fact.key} · ${displaySlaValue(fact.value, fact.unit)}${fact.status === 'confirmed' ? '' : '（待核对）'}`, disabled: fact.status !== 'confirmed' }))} /></Form.Item>
            <Form.Item name={[field.name, 'writing_points']} label="写作要点" extra="说明怎样回应要求，不能在这里修改已确认事实或服务承诺。"><Input.TextArea disabled={!editable || busy} rows={3} maxLength={5000} placeholder="例如：先说明工作步骤，再列出质量核对方式和交付清单" /></Form.Item>
            <Form.Item name={[field.name, 'target_length']} label="字数目标" rules={[{ type: 'integer', min: 1, max: 100000, message: '填写 1 至 100000 的整数，或留空' }]} extra="留空不设目标，不能用字数代替质量验收。"><InputNumber disabled={!editable || busy} min={1} max={100000} precision={0} style={{ width: 180 }} placeholder="不设目标" addonAfter="字" /></Form.Item>
            {chapter?.writing_input?.confirmed_at && <p className="muted">上次本节确认：{chapter.writing_input.confirmed_by_name ?? chapter.writing_input.confirmed_by} · {formatTime(chapter.writing_input.confirmed_at)}{current ? '' : ' · 已需重新核对'}</p>}
            {chapter ? <Space wrap><Button disabled={!editable || busy || !!rowProblem || !workspace.parse_confirmed} onClick={() => saveOne(field.name)}>保存本节方案</Button><Button type="primary" disabled={!editable || busy || !!rowProblem || pending || structurePending || !workspace.parse_confirmed} onClick={() => confirmOne(field.name)}>确认本节方案</Button>{pending && <span className="muted">本节事实、要点或字数有修改，请先保存再确认。</span>}{structurePending && <span className="muted">名称、分册或编写人尚未保存；请保存大纲或人员交接后再确认。</span>}{!editable && <span className="muted">当前账号可查看，本节由指定编写人或负责人办理。</span>}</Space> : <span className="muted">{row?.id ? '本节已不在当前后台章节中，先核对并载入最新范围方案。' : '新章节由选定范围负责人统一保存并确认。'}</span>}
          </Card>;
        })}
        {canStructure && <Button icon={<PlusOutlined />} disabled={busy} onClick={() => add({ title: '', volume: scope === 'business' ? 'business' : 'technical', assignee_id: null, fact_ids: [], writing_points: '', target_length: null })}>新增章节</Button>}
      </>}</Form.List>
    </Form>
    <Alert className="page-notice" showIcon type="warning" message="已保存正文和原账号个人草稿不随换人清除；整章输入仍不是逐段来源证明" description="完整知识片段、结构化编辑、选区助手和生成闭环继续实施。若删章因个人草稿被拒绝，由原账号明确处理自己的草稿后再操作。" />
  </Modal>;
}
