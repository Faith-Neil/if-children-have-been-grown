// 为什么有这个文件：沿用 ICG 项目设置的左锚点和分组表单，真正保存成员及两册分工。
// 它解决什么问题：把本项目负责人、分册负责人、合标负责人和章节编写人的职责分清，换人不丢正文或个人草稿。
import { useEffect, useState } from 'react';
import { Alert, Anchor, App as AntApp, Button, Card, Checkbox, Col, Empty, Form, Input, Row, Select, Space, Table, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { deadlineForForm, projectBasis, projectFields } from './project-form';
import { formatTime, useProject, volumeName } from '../app/context';
import { eligibleOwners, projectCan, projectRoleName, teamBasis, teamFormValues, teamPayload, type TeamFormValues } from './project-team';
import type { ProjectTeam } from '../shared/types';
import { request } from '../shared/api';
import { ModelConfigModal } from '../admin/ModelConfigModal';
import { modelConfigAccess } from '../admin/model-config-core.ts';
import { projectVolumes, technicalOnly, volumeOptions } from './project-volumes.ts';
import { ProposedStaffCard } from './ProposedStaffCard';
import { ExportNamingCard } from './ExportNamingCard';
import { relatedBidConflict } from './related-bid-core';
import { RelatedBidBanner, askRelatedBidReason } from './RelatedBidPrompt';

const anchors = [ ['basic', '基本信息'], ['members', '成员与分工'], ['partners', '合作方'], ['persons', '拟派人员'], ['sla', 'SLA 取值'], ['rules', '规则覆盖'], ['loops', '生成闭环'], ['volumes', '分册'], ['export', '导出设置'] ];

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
  const canManageProject = projectCan(workspace, 'manage_project');
  const canManageTeam = projectCan(workspace, 'manage_team');
  const members = Form.useWatch('members', teamForm) ?? teamFormValues(team).members;
  const accounts = team?.available_accounts?.length ? team.available_accounts : (team?.members ?? []).map(member => ({ id: member.user_id, name: member.name, role: member.company_role, company_id: user.company_id }));
  const options = (volume?: 'technical' | 'business') => eligibleOwners(members, accounts, volume).map(member => ({ value: member.user_id, label: accounts.find(account => account.id === member.user_id)?.name ?? member.user_id }));
  useEffect(() => {
    basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) });
    setLoadedBasicBasis(projectBasis(workspace.project));
    teamForm.setFieldsValue(teamFormValues(team));
    setLoadedTeamBasis(teamBasis(team));
  }, [workspace.project.id]);
  async function saveBasic() {
    if (!canManageProject || busy) return;
    if (basicChanged) { report(new Error('后台基本信息已更新，当前填写内容已保留。请先核对并载入最新基本信息，再重新保存。')); return; }
    try {
      const values = await basicForm.validateFields();
      const path = `/api/v1/projects/${workspace.project.id}`; const body = projectFields(values);
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
        try { const result = await mutate(`/api/v1/projects/${workspace.project.id}/team`, 'PUT', payload) as { team?: ProjectTeam }; if (result.team) { teamForm.setFieldsValue(teamFormValues(result.team)); setLoadedTeamBasis(teamBasis(result.team)); } else teamForm.setFieldValue('reason', ''); message.success('成员与分册分工已保存，请到编辑台逐章指定编写人。'); }
        catch (error) { throw error; } finally { setSavingTeam(false); }
      },
    });
  }
  return <>
    <div className="page-heading"><div><h2>项目设置</h2><p>项目角色决定本项目职责，公司角色另行限制账号可以办理的事情。</p></div><Tag>{projectRoleName(team?.members.find(member => member.user_id === user.id)?.project_role ?? 'readonly')}</Tag></div>
    {!canManageTeam && <Alert className="page-notice" showIcon type="info" message="当前账号可以查看设置；人员、分工和基本信息由本项目负责人维护。" />}
    {basicChanged && <Alert className="page-notice" showIcon type="warning" message="后台基本信息已变化，当前表单仍保留你的填写" action={<Button onClick={() => modal.confirm({ title: '核对并载入最新基本信息', content: <><p>当前项目：{workspace.project.name}；编号：{workspace.project.tender_number || '未填写'}；截止：{deadlineForForm(workspace.project.deadline) || '未填写'}；{workspace.project.sensitive ? '敏感项目' : '普通项目'}。</p><p>载入会替换当前未保存的基本信息表单，后台记录不变。</p></>, okText: '已核对，载入最新信息', cancelText: '保留当前填写', onOk: () => { basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) }); setLoadedBasicBasis(projectBasis(workspace.project)); } })}>核对并载入最新基本信息</Button>} />}
    {teamChanged && <Alert className="page-notice" showIcon type="warning" message="后台分工已变化，当前表单仍保留你的填写" description="保存已暂停，不能用旧表单覆盖其他协作者的新安排。先核对当前成员与负责人，再决定是否载入最新分工。" action={<Button onClick={() => modal.confirm({ title: '核对并载入后台最新分工', content: <><p>最新成员：{team?.members.map(member => `${member.name}（${projectRoleName(member.project_role)}；参与：${member.volumes.map(volumeName).join('、') || '暂未指定'}）`).join('、')}</p><p>最新负责人：{team?.volumes.map(volume => `${volumeName(volume.volume)}：${volume.owner_name ?? '未指定'}`).join('；')}</p><p>最新合标负责人：{team?.members.find(member => member.user_id === team.assembly_owner_id)?.name ?? '未指定'}</p><p>载入会替换当前未保存的人员表单，后台记录不变。先保留需要重新填写的内容。</p></>, okText: '已核对，载入最新分工', cancelText: '保留当前填写', onOk: () => { teamForm.setFieldsValue(teamFormValues(team)); setLoadedTeamBasis(teamBasis(team)); } })}>核对并载入最新分工</Button>} />}
    <RelatedBidBanner projectId={workspace.project.id} token={token} revision={workspace.revision} canConfirm={canManageProject} modal={modal} onConfirmed={() => reload()} report={report} />
    <div className="settings-layout settings-members-layout">
      <Card className="settings-anchor" size="small"><Anchor offsetTop={80} items={anchors.map(([id, title]) => ({ key: id, href: `#project-setting-${id}`, title }))} /></Card>
      <div className="settings-groups">
        <Card id="project-setting-basic" title="基本信息" className="settings-form stack-card">
          <Form form={basicForm} layout="vertical" disabled={busy || !canManageProject}>
            <Form.Item name="name" label="项目名称" rules={[{ required: true, whitespace: true }, { max: 200 }]}><Input /></Form.Item>
            <Form.Item name="tender_number" label="招标编号"><Input /></Form.Item>
            <Row gutter={16}><Col span={16}><Form.Item name="deadline" label="投标截止时间"><Input placeholder="2026-12-31 17:00（北京时间）" /></Form.Item></Col><Col span={8}><Form.Item name="sensitive" label="敏感标记"><Select options={[{ value: false, label: '普通项目' }, { value: true, label: '敏感 · 强制本地' }]} /></Form.Item></Col></Row>
            <Button type="primary" onClick={saveBasic} loading={busy} disabled={!canManageProject}>保存基本信息</Button>
          </Form>
        </Card>
        <Form form={teamForm} layout="vertical" disabled={busy || savingTeam || !canManageTeam}>
          <Card id="project-setting-members" title="成员与分工" className="stack-card" extra={<span className="muted">当前 {team?.members.length ?? 0} 位项目成员</span>}>
            <Alert type="info" showIcon message="项目负责人管全项目；分册负责人管本册；本节编写人管分配给自己的章节；只读成员不能写入。" description="至少保留一位项目负责人。同公司未加入项目的账号不能进入项目；项目成员可以阅读本项目资料，写入按实际分工校验。" />
            <Form.List name="members">{(fields, { add, remove }) => <>
              {fields.map(field => <div className="project-member-row" key={field.key}>
                <Form.Item name={[field.name, 'user_id']} label={`成员 ${field.name + 1}`} rules={[{ required: true, message: '请选择项目成员' }]}><Select aria-label={`项目成员 ${field.name + 1}`} optionFilterProp="label" showSearch options={accounts.map(account => ({ value: account.id, label: `${account.name}${account.role === 'viewer' ? '（公司只读账号）' : ''}`, disabled: members.some((member, index) => index !== field.name && member.user_id === account.id) }))} /></Form.Item>
                <Form.Item name={[field.name, 'project_role']} label="本项目角色" rules={[{ required: true }]}><Select aria-label={`成员 ${field.name + 1} 的项目角色`} options={[{ value: 'lead', label: '项目负责人', disabled: accounts.find(account => account.id === members[field.name]?.user_id)?.role !== 'manager' }, { value: 'writer', label: '投标编写人', disabled: accounts.find(account => account.id === members[field.name]?.user_id)?.role === 'viewer' }, { value: 'readonly', label: '只读成员' }]} onChange={role => { if (role === 'lead') teamForm.setFieldValue(['members', field.name, 'volumes'], projectVolumes(workspace)); }} /></Form.Item>
                <Form.Item name={[field.name, 'volumes']} label="参与分册（可选）" extra="留空可先加入项目；分配本册负责人或章节时必须选择相应分册。"><Checkbox.Group disabled={members[field.name]?.project_role === 'lead' || busy || !canManageTeam} options={projectVolumes(workspace).map(value => ({ value, label: value === 'technical' ? '技术' : '商务' }))} /></Form.Item>
                <Button danger size="small" disabled={!canManageTeam || busy} onClick={() => remove(field.name)}>移出项目</Button>
              </div>)}
              <Button icon={<PlusOutlined />} disabled={!canManageTeam || busy || fields.length >= accounts.length} onClick={() => add({ user_id: undefined, project_role: 'writer', volumes: projectVolumes(workspace) })}>加入项目成员</Button>
            </>}</Form.List>
          </Card>
          <Card id="project-setting-volumes" title={technicalOnly(workspace) ? '分册分工（只写技术标，不合标）' : '分册与合标分工'} className="stack-card">
            <Row gutter={16}><Col span={12}><Form.Item name="technical_owner_id" label="技术分册负责人" extra="负责人需参与技术册，未指定时本册不能确认写作方案。"><Select aria-label="技术分册负责人" allowClear placeholder="请选择技术分册负责人" options={options('technical')} /></Form.Item></Col>{!technicalOnly(workspace) && <Col span={12}><Form.Item name="business_owner_id" label="商务分册负责人" extra="负责人需参与商务册，未指定时本册不能确认写作方案。"><Select aria-label="商务分册负责人" allowClear placeholder="请选择商务分册负责人" options={options('business')} /></Form.Item></Col>}</Row>
            {!technicalOnly(workspace) && <Form.Item name="assembly_owner_id" label="合标负责人" extra="负责下载两册并人工核对合标；不会因此获得项目设置权，也不能生成正式递交版。"><Select aria-label="合标负责人" allowClear placeholder="请选择合标负责人" options={options()} /></Form.Item>}
            <Form.Item name="reason" label="本次调整原因与交接安排" rules={[{ required: true, whitespace: true, message: '请说明这次人员调整和交接安排' }]}><Input.TextArea aria-label="人员分工调整原因" rows={3} maxLength={2000} placeholder="例如：张工接手技术分册；原正文保留，由两人核对后继续编写；个人草稿由原账号自己处理。" /></Form.Item>
            <Button type="primary" onClick={saveTeam} disabled={!canManageTeam || busy} loading={savingTeam}>保存成员与分工</Button>
          </Card>
        </Form>
        <Card title="人员交接记录" className="stack-card">
          {team?.handoffs.length ? <Table size="small" rowKey="id" pagination={false} dataSource={team.handoffs.slice().reverse()} columns={[{ title: '时间', dataIndex: 'at', render: formatTime }, { title: '交接依据', dataIndex: 'reason' }, { title: '涉及章节', render: (_, handoff) => handoff.chapter_ids.map(id => workspace.chapters.find(chapter => chapter.id === id)?.title ?? id).join('、') || '成员或分册调整' }, { title: '保护处理', render: (_, handoff) => <>撤销旧编辑权 {handoff.revoked_lock_count} 份<br />保留个人草稿 {handoff.preserved_draft_count} 份</> }]} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无人员交接记录" />}
        </Card>
        {anchors.filter(([id]) => !['basic', 'members', 'volumes'].includes(id)).map(([id, title]) => <Card id={`project-setting-${id}`} key={id} title={title} className="stack-card">
          {id === 'loops' ? (
            <div data-testid="project-model-config-panel">
              <p style={{ marginBottom: 12 }}>
                管理本项目在分节生成与提示词推理时绑定的大模型服务配置。涉密项目受策略保护，仅允许选用本地部署模型。
              </p>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: '#F8FAFC', borderRadius: 6, border: '1px solid #E2E8F0' }}>
                <Space direction="vertical" size={4}>
                  <Space>
                    <span style={{ fontWeight: 600 }}>生效模型：</span>
                    <span data-testid="project-current-model-name">{projectModel ? `${projectModel.name} (${projectModel.model})` : '默认全局模型 (qwen2.5-72b-instruct)'}</span>
                    {projectModel?.is_local ? (
                      <Tag color="cyan">本地模型</Tag>
                    ) : (
                      <Tag color="blue">公网模型</Tag>
                    )}
                    {workspace.project.sensitive && (
                      <Tag color="orange" data-testid="project-sensitive-badge">涉密项目门控</Tag>
                    )}
                  </Space>
                  <span style={{ fontSize: 12, color: '#64748B' }}>
                    {workspace.project.sensitive ? '当前项目标记为涉密，严禁绑定非本地或未经许可的外部模型服务。' : '普通项目，支持按需配置内网本地模型或外部安全推理服务。'}
                  </span>
                </Space>
                <Button
                  data-testid="open-model-config-btn"
                  type="primary"
                  ghost
                  onClick={() => setModelModalOpen(true)}
                >
                  配置项目模型
                </Button>
              </div>
              <ModelConfigModal
                open={modelModalOpen}
                onClose={() => setModelModalOpen(false)}
                token={token}
                projectId={workspace.project.id}
                projectSensitive={Boolean(workspace.project.sensitive)}
                {...modelConfigAccess(user?.role, canManageProject)}
                onBound={() => {
                  loadProjectModel();
                }}
              />
            </div>
          ) : id === 'persons' ? (
            <ProposedStaffCard projectId={workspace.project.id} token={token} canEdit={canManageProject}
              revision={workspace.revision} onSaved={reload} />
          ) : id === 'export' ? (
            <ExportNamingCard projectId={workspace.project.id} projectName={workspace.project.name} tenderNumber={workspace.project.tender_number}
              token={token} canEdit={canManageProject} revision={workspace.revision} onSaved={reload} />
          ) : id === 'sla' ? <><p>服务承诺（SLA）是公司能承诺的响应、恢复等标准。实际取值已在响应矩阵逐项核对。</p><Button onClick={() => navigate('matrix')}>前往服务承诺矩阵</Button></> : <Alert type="info" message="该组完整设置仍待实现" description={ `${title}的原始业务范围继续按任务实施，这里没有可保存的配置。`} showIcon />}
        </Card>)}
      </div>
    </div>
    <div className="settings-save-bar"><span className="muted">两个保存入口分别处理基本信息与人员分工；失败时保留填写内容。</span><Space><Button disabled={!canManageProject || busy} onClick={saveBasic}>保存基本信息</Button><Button type="primary" disabled={!canManageTeam || busy} loading={savingTeam} onClick={saveTeam}>保存成员与分工</Button></Space></div>
  </>;
}
