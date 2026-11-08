// 为什么有这个文件：项目设置页只编辑项目基本信息，人员分工不在这里改。
// 它解决什么问题：基本信息仍走原保存接口；页面由外层内容区滚动，滚轮不会被内层空滚动容器吃掉。
import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Collapse, Form, Input, Row, Select, Space, Tag } from 'antd';
import { basicInfoFields, deadlineForForm, projectBasis, projectFields } from './project-form';
import { useProject } from '../app/context';
import { projectCan, projectRoleName } from './project-team';
import { request } from '../shared/api';
import { ModelConfigModal } from '../admin/ModelConfigModal';
import { modelConfigAccess } from '../admin/model-config-core.ts';
import { technicalOnly } from './project-volumes.ts';
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
  const team = workspace.team;
  const [loadedBasicBasis, setLoadedBasicBasis] = useState(projectBasis(workspace.project));
  const basicChanged = loadedBasicBasis !== projectBasis(workspace.project);
  const readOnly = workspace.project_status?.read_only === true;  // 项目取消后只读（PRD 5.1.3）
  const leadCan = projectCan(workspace, 'manage_project');
  const canManageProject = leadCan && !readOnly;
  const { settings } = useProjectSettings(workspace.project.id, token, workspace.revision);
  const nameOf = (id: string) => team?.members.find(member => member.user_id === id)?.name ?? id;
  const editNote = (field: string) => { const note = manualEditNote(settings?.manual_edits, field, nameOf); return note ? <Tag color="gold" data-testid={`manual-edit-${field}`}>{note}</Tag> : undefined; };
  const groupProps = { projectId: workspace.project.id, token, canEdit: canManageProject, mutate, busy, settings };
  useEffect(() => {
    basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) });
    setLoadedBasicBasis(projectBasis(workspace.project));
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
  return <>
    <div className="page-heading"><h2>项目设置</h2><Tag>{projectRoleName(team?.members.find(member => member.user_id === user.id)?.project_role ?? 'readonly')}</Tag></div>
    {readOnly && <Alert className="page-notice" showIcon type="warning" message="项目已取消，所有设置只读。" />}
    {basicChanged && <Alert className="page-notice" showIcon type="warning" message="后台基本信息已变化，当前表单仍保留你的填写" action={<Button onClick={() => modal.confirm({ title: '核对并载入最新基本信息', content: <><p>当前项目：{workspace.project.name}；编号：{workspace.project.tender_number || '未填写'}；截止：{deadlineForForm(workspace.project.deadline) || '未填写'}；{workspace.project.sensitive ? '敏感项目' : '普通项目'}。</p><p>载入会替换当前未保存的基本信息表单，后台记录不变。</p></>, okText: '已核对，载入最新信息', cancelText: '保留当前填写', onOk: () => { basicForm.setFieldsValue({ ...workspace.project, deadline: deadlineForForm(workspace.project.deadline) }); setLoadedBasicBasis(projectBasis(workspace.project)); } })}>核对并载入最新基本信息</Button>} />}
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
  </>;
}
