// 为什么有这个文件：项目设置只常显项目与人员，其余收在「更多」里，保存仍走原接口。
// 它解决什么问题：设置页不再用锚点平铺成说明书；换人交接和基本信息的保存行为保持不变。
import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Checkbox, Col, Collapse, Form, Input, Row, Select, Space, Table, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { basicInfoFields, deadlineForForm, projectBasis, projectFields } from './project-form';
import { formatTime, useProject, volumeName } from '../app/context';
import { eligibleOwners, projectCan, projectRoleName, teamBasis, teamFormValues, teamPayload, type TeamFormValues } from './project-team';
import type { ProjectTeam } from '../shared/types';
import { request } from '../shared/api';
import { ModelConfigModal } from '../admin/ModelConfigModal';
import { modelConfigAccess } from '../admin/model-config-core.ts';
import { projectVolumes, technicalOnly } from './project-volumes.ts';
import { ProposedStaffCard } from './ProposedStaffCard';
import { ExportNamingCard } from './ExportNamingCard';
import { relatedBidConflict } from './related-bid-core';
import { RelatedBidBanner, askRelatedBidReason } from './RelatedBidPrompt';
import { FullValueCard, PartnersCard, ProjectStatusCard, RuleOverridesCard, SlaSummaryCard, VolumeFormatCard, useProjectSettings } from './ProjectSettingsGroups';
import { BASIC_FIELD_LABELS, manualEditNote } from './project-settings-core';

export default function ProjectSettingsPage() {
  const { workspace, token, user, busy, mutate, reload, report, navigate } = useProject();
  const [projectModel, setProjectModel] = useState<{ id: string; name: string; model: string; is_local: boolean; allow_sensitive: boolean } | null>(null);
  const [modelModalOpen, setModelModalOpen] = useState(false);

  const loadProjectModel = async () => {
    try {
      const data = await request<{ id: string; name: string; model: string; is_local: boolean; allow_sensitive: boolean }>(
        `/api/v1/projects/${workspace.project.id}/model-config`,
        token
      );
      setProjectModel(data);
    } catch {
      // 默认全局或未单独绑定
    }
  };

  useEffect(() => {
    if (workspace.project.id) {
      loadProjectModel();
    }
  }, [workspace.project.id, token]);
  const { modal, message } = AntApp.useApp();
  const [basicForm] = Form.useForm();
  const [teamForm] = Form.useForm<TeamFormValues>();
  const [savingTeam, setSavingTeam] = useState(false);
  const team = workspace.team;
  const [loadedBasicBasis, setLoadedBasicBasis] = useState(projectBasis(workspace.project));
  const basicChanged = loadedBasicBasis !== projectBasis(workspace.project);
  const [loadedTeamBasis, setLoadedTeamBasis] = useState(teamBasis(team));
  const teamChanged = loadedTeamBasis !== teamBasis(team);
  const readOnly = workspace.project_status?.read_only === true;  // 项目取消后只读（PRD 5.1.3）
  const leadCan = projectCan(workspace, 'manage_project');
  const canManageProject = leadCan && !readOnly;
  const canManageTeam = projectCan(workspace, 'manage_team') && !readOnly;
  const { settings } = useProjectSettings(workspace.project.id, token, workspace.revision);
  const nameOf = (id: string) => team?.members.find(member => member.user_id === id)?.name ?? id;
  const editNote = (field: string) => { const note = manualEditNote(settings?.manual_edits, field, nameOf); return note ? <Tag color="gold" data-testid={`manual-edit-${field}`}>{note}</Tag> : undefined; };
  const groupProps = { projectId: workspace.project.id, token, canEdit: canManageProject, mutate, busy, settings };
  const members = Form.useWatch('members', teamForm) ?? teamFormValues(team).members;
  const accounts = team?.available_accounts?.length ? team.available_accounts : (team?.members ?? []).map(member => ({ id: member.user_id, name: member.name, role: member.company_role, company_id: user.company_id }));
  const options = (volume?: 'technical' | 'business') => eligibleOwners(members, accounts, volume).map(member => ({ value: member.user_id, label: accounts.find(account => account.id === member.user_id)?.name ?? member.user_id }));
  useEffect(() => {
    basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) });
    setLoadedBasicBasis(projectBasis(workspace.project));
    teamForm.setFieldsValue(teamFormValues(team));
    setLoadedTeamBasis(teamBasis(team));
  }, [workspace.project.id]);
  useEffect(() => {
    // 后台带出的扩展基本信息：只在表单未被改动时载入，避免覆盖未保存的填写
    if (settings && !basicForm.isFieldsTouched()) basicForm.setFieldsValue(settings.basic_info);
  }, [settings?.revision]);  // eslint-disable-line react-hooks/exhaustive-deps
  async function saveBasic() {
    if (!canManageProject || busy) return;
    if (basicChanged) { report(new Error('后台基本信息已更新，当前填写内容已保留。请先核对并载入最新基本信息，再重新保存。')); return; }
    try {
      const values = await basicForm.validateFields();
      const path = `/api/v1/projects/${workspace.project.id}`; const body = { ...projectFields(values), basic_info: basicInfoFields(values) };
      let result: { project?: typeof workspace.project };
      try { result = await mutate(path, 'PATCH', body) as typeof result; }
      catch (error) {
        // R19 关联投标冲突（APP-M2-T096）：写明无关联关系才能保存；取消则保留表单不保存
        const conflict = relatedBidConflict(error); if (!conflict) throw error;
        const reason = await askRelatedBidReason(modal, conflict); if (!reason) return;
        result = await mutate(path, 'PATCH', { ...body, related_bid_reason: reason }) as typeof result;
      }
      if (result.project) { basicForm.setFieldsValue({ ...result.project, deadline: deadlineForForm(result.project.deadline) }); setLoadedBasicBasis(projectBasis(result.project)); }
      message.success('基本信息已保存，旧检查与输出需按当前资料重新核对。');
    } catch (error) { if (!(error instanceof Error && 'status' in error)) report(error); }
  }
  async function saveTeam() {
    if (!canManageTeam || busy || savingTeam) return;
    if (teamChanged) { report(new Error('后台分工已更新，当前填写内容已保留。请先核对并载入最新分工，再重新安排和保存。')); return; }
    let payload;
    try { payload = teamPayload(await teamForm.validateFields(), accounts, projectVolumes(workspace)); } catch (error) { if (error instanceof Error) report(error); return; }
    const oldIds = team?.members.map(member => member.user_id) ?? [];
    const removed = oldIds.filter(id => !payload.members.some(member => member.user_id === id));
    const changeRole = team?.members.some(member => payload.members.some(next => next.user_id === member.user_id && (next.project_role !== member.project_role || JSON.stringify(next.volumes) !== JSON.stringify(member.volumes))));
    const changeOwner = team?.volumes.some(volume => payload.volumes.find(next => next.volume === volume.volume)?.owner_id !== volume.owner_id);
    modal.confirm({
      title: removed.length || changeRole || changeOwner ? '确认人员交接与分工调整' : '确认保存项目成员与分工',
      content: <><p>本次依据：{payload.reason}</p><p>后台会重新核对每位成员和负责人。换人或退出会撤销旧编辑权；相关章节需重新确认。正式正文、历史版本和原账号个人草稿保留，草稿不会自动交给接手人。</p>{removed.includes(user.id) && <Alert type="warning" showIcon message="你将退出这个项目，保存成功后不能继续读取或编辑；先留好自己的未保存文字。" />}</>,
      okText: '按上述交接安排保存', cancelText: '继续核对',
      onOk: async () => {
        setSavingTeam(true);
        try { const result = await mutate(`/api/v1/projects/${workspace.project.id}/team`, 'PUT', payload) as { team?: ProjectTeam }; if (result.team) { teamForm.setFieldsValue(teamFormValues(result.team)); setLoadedTeamBasis(teamBasis(result.team)); } else teamForm.setFieldValue('reason', ''); message.success('成员与方案分工已保存，请到编辑台逐章指定编写人。'); }
        catch (error) { throw error; } finally { setSavingTeam(false); }
      },
    });
  }
  return <>
    <div className="page-heading"><h2>项目设置</h2><Tag>{projectRoleName(team?.members.find(member => member.user_id === user.id)?.project_role ?? 'readonly')}</Tag></div>
    {readOnly && <Alert className="page-notice" showIcon type="warning" message="项目已取消，所有设置只读。" />}
    {basicChanged && <Alert className="page-notice" showIcon type="warning" message="后台基本信息已变化，当前表单仍保留你的填写" action={<Button onClick={() => modal.confirm({ title: '核对并载入最新基本信息', content: <><p>当前项目：{workspace.project.name}；编号：{workspace.project.tender_number || '未填写'}；截止：{deadlineForForm(workspace.project.deadline) || '未填写'}；{workspace.project.sensitive ? '敏感项目' : '普通项目'}。</p><p>载入会替换当前未保存的基本信息表单，后台记录不变。</p></>, okText: '已核对，载入最新信息', cancelText: '保留当前填写', onOk: () => { basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) }); setLoadedBasicBasis(projectBasis(workspace.project)); } })}>核对并载入最新基本信息</Button>} />}
    {teamChanged && <Alert className="page-notice" showIcon type="warning" message="后台分工已变化，当前表单仍保留你的填写" description="保存已暂停，不能用旧表单覆盖其他协作者的新安排。先核对当前成员与负责人，再决定是否载入最新分工。" action={<Button onClick={() => modal.confirm({ title: '核对并载入后台最新分工', content: <><p>最新成员：{team?.members.map(member => `${member.name}（${projectRoleName(member.project_role)}；参与：${member.volumes.map(volumeName).join('、') || '暂未指定'}）`).join('、')}</p><p>最新负责人：{team?.volumes.map(volume => `${volumeName(volume.volume)}：${volume.owner_name ?? '未指定'}`).join('；')}</p><p>最新合标负责人：{team?.members.find(member => member.user_id === team.assembly_owner_id)?.name ?? '未指定'}</p><p>载入会替换当前未保存的人员表单，后台记录不变。先保留需要重新填写的内容。</p></>, okText: '已核对，载入最新分工', cancelText: '保留当前填写', onOk: () => { teamForm.setFieldsValue(teamFormValues(team)); setLoadedTeamBasis(teamBasis(team)); } })}>核对并载入最新分工</Button>} />}
    <RelatedBidBanner projectId={workspace.project.id} token={token} revision={workspace.revision} canConfirm={canManageProject} modal={modal} onConfirmed={async () => { await reload(); }} report={report} />
    <div className="settings-layout settings-members-layout">
      <div className="settings-groups">
        <Card title="项目" className="stack-card">
          {!technicalOnly(workspace) && <ProjectStatusCard {...groupProps} canEdit={leadCan} />}
        <Card id="project-setting-basic" title="基本信息" className="settings-form stack-card">
          <Form form={basicForm} layout="vertical" disabled={busy || !canManageProject}>
            <Form.Item name="name" label="项目名称" extra={editNote('name')} rules={[{ required: true, whitespace: true }, { max: 200 }]}><Input /></Form.Item>
            <Form.Item name="tender_number" label="招标编号" extra={editNote('tender_number')}><Input /></Form.Item>
            <Row gutter={16}><Col span={16}><Form.Item name="deadline" label="投标截止时间" extra={editNote('deadline')}><Input placeholder="2026-12-31 17:00（北京时间）" /></Form.Item></Col><Col span={8}><Form.Item name="sensitive" label="敏感标记"><Select options={[{ value: false, label: '普通项目' }, { value: true, label: '敏感 · 强制本地' }]} /></Form.Item></Col></Row>
            {!technicalOnly(workspace) && <Row gutter={16}>{(['tenderee_name', 'agency_name', 'lot_name', 'client_address', 'open_at', 'service_period', 'project_location'] as const).map(field => <Col span={12} key={field}><Form.Item name={field} label={BASIC_FIELD_LABELS[field]} extra={editNote(field)}><Input maxLength={200} /></Form.Item></Col>)}</Row>}
            <Button type="primary" onClick={saveBasic} loading={busy} disabled={!canManageProject}>保存基本信息</Button>
          </Form>
        </Card>
          <div data-testid="project-model-config-panel" className="project-model-row">
            <Space>
              <span data-testid="project-current-model-name">{projectModel ? `${projectModel.name} (${projectModel.model})` : '默认全局模型'}</span>
              {projectModel?.is_local ? <Tag color="cyan">本地模型</Tag> : <Tag>未单独绑定</Tag>}
              {workspace.project.sensitive && <Tag color="orange" data-testid="project-sensitive-badge">涉密</Tag>}
            </Space>
            <Button data-testid="open-model-config-btn" onClick={() => setModelModalOpen(true)}>配置项目模型</Button>
            <ModelConfigModal
              open={modelModalOpen}
              onClose={() => setModelModalOpen(false)}
              token={token}
              projectId={workspace.project.id}
              projectSensitive={Boolean(workspace.project.sensitive)}
              {...modelConfigAccess(user?.role, canManageProject)}
              onBound={() => { loadProjectModel(); }}
            />
          </div>
        </Card>
        <Card id="project-setting-members" title="人员" className="stack-card" extra={<span className="muted">{team?.members.length ?? 0} 人</span>}>
        <Form form={teamForm} layout="vertical" disabled={busy || savingTeam || !canManageTeam}>
            <Form.List name="members">{(fields, { add, remove }) => <>
              {fields.map(field => <div className="project-member-row" key={field.key}>
                <Form.Item name={[field.name, 'user_id']} label={`成员 ${field.name + 1}`} rules={[{ required: true, message: '请选择项目成员' }]}><Select aria-label={`项目成员 ${field.name + 1}`} optionFilterProp="label" showSearch options={accounts.map(account => ({ value: account.id, label: `${account.name}${account.role === 'viewer' ? '（公司只读账号）' : ''}`, disabled: members.some((member, index) => index !== field.name && member.user_id === account.id) }))} /></Form.Item>
                <Form.Item name={[field.name, 'project_role']} label="本项目角色" rules={[{ required: true }]}><Select aria-label={`成员 ${field.name + 1} 的项目角色`} options={[{ value: 'lead', label: '项目负责人', disabled: accounts.find(account => account.id === members[field.name]?.user_id)?.role !== 'manager' }, { value: 'writer', label: '投标编写人', disabled: accounts.find(account => account.id === members[field.name]?.user_id)?.role === 'viewer' }, { value: 'readonly', label: '只读成员' }]} onChange={role => { if (role === 'lead') teamForm.setFieldValue(['members', field.name, 'volumes'], projectVolumes(workspace)); }} /></Form.Item>
                {!technicalOnly(workspace) && <Form.Item name={[field.name, 'volumes']} label="参与方案（可选）" extra="留空可先加入项目；分配方案负责人或章节时必须选择相应方案。"><Checkbox.Group disabled={members[field.name]?.project_role === 'lead' || busy || !canManageTeam} options={projectVolumes(workspace).map(value => ({ value, label: value === 'technical' ? '技术' : '商务' }))} /></Form.Item>}
                <Button danger size="small" disabled={!canManageTeam || busy} onClick={() => remove(field.name)}>移出项目</Button>
              </div>)}
              <Button icon={<PlusOutlined />} disabled={!canManageTeam || busy || fields.length >= accounts.length} onClick={() => add({ user_id: undefined, project_role: 'writer', volumes: projectVolumes(workspace) })}>加入项目成员</Button>
            </>}</Form.List>
            <Row gutter={16}><Col span={12}><Form.Item name="technical_owner_id" label="技术方案负责人"><Select aria-label="技术方案负责人" allowClear placeholder="请选择技术方案负责人" options={options('technical')} /></Form.Item></Col>{!technicalOnly(workspace) && <Col span={12}><Form.Item name="business_owner_id" label="商务方案负责人"><Select aria-label="商务方案负责人" allowClear placeholder="请选择商务方案负责人" options={options('business')} /></Form.Item></Col>}</Row>
            {!technicalOnly(workspace) && <Form.Item name="assembly_owner_id" label="合标负责人"><Select aria-label="合标负责人" allowClear placeholder="请选择合标负责人" options={options()} /></Form.Item>}
            <Form.Item name="reason" label="调整原因" rules={[{ required: true, whitespace: true, message: '请说明这次人员调整和交接安排' }]}><Input.TextArea aria-label="人员分工调整原因" rows={3} maxLength={2000} /></Form.Item>
            <Button type="primary" onClick={saveTeam} disabled={!canManageTeam || busy} loading={savingTeam}>保存成员与分工</Button>
        </Form>
        {!technicalOnly(workspace) && <ProposedStaffCard projectId={workspace.project.id} token={token} canEdit={canManageProject} revision={workspace.revision} onSaved={reload} />}
        {!technicalOnly(workspace) && team?.handoffs.length ? <Table size="small" rowKey="id" pagination={false} dataSource={team.handoffs.slice().reverse()} columns={[{ title: '时间', dataIndex: 'at', render: formatTime }, { title: '交接依据', dataIndex: 'reason' }, { title: '涉及章节', render: (_, handoff) => handoff.chapter_ids.map(id => workspace.chapters.find(chapter => chapter.id === id)?.title ?? id).join('、') || '成员或方案调整' }, { title: '保护处理', render: (_, handoff) => <>撤销编辑权 {handoff.revoked_lock_count} · 保留草稿 {handoff.preserved_draft_count}</> }]} /> : null}
        </Card>
        {!technicalOnly(workspace) && <Collapse items={[{
          key: 'more',
          label: '更多',
          children: (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <PartnersCard {...groupProps} />
              <SlaSummaryCard settings={settings} onOpen={() => navigate('analyze')} />
              <RuleOverridesCard {...groupProps} requirements={workspace.requirements.map(item => ({ id: item.id, text: item.text }))} />
              <VolumeFormatCard {...groupProps} writerNames={(team?.members ?? []).map(member => member.name)} />
              <ExportNamingCard projectId={workspace.project.id} projectName={workspace.project.name} tenderNumber={workspace.project.tender_number} token={token} canEdit={canManageProject} revision={workspace.revision} onSaved={reload} />
              <FullValueCard {...groupProps} requirements={workspace.requirements.map(item => ({ id: item.id, text: item.text }))} />
            </Space>
          ),
        }]} />}
      </div>
    </div>
    <div className="settings-save-bar"><Space><Button disabled={!canManageProject || busy} onClick={saveBasic}>保存基本信息</Button><Button type="primary" disabled={!canManageTeam || busy} loading={savingTeam} onClick={saveTeam}>保存成员与分工</Button></Space></div>
  </>;
}
