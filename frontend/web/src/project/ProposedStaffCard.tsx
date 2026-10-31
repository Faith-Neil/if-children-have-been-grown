// 为什么有这个文件：项目设置里的“拟派人员”（PRD v1.8 §5.1.4 第 4 项；R33 排人时提示，§5.8.4；APP-M2-T241）。
// 它解决什么问题：项目负责人从资料库“人员”资料选人、定角色、A/B 角与关键人员；保存后立即显示 R33 核对结果
// （资格条款不满足阻断、评分条款只提示、人员资料缺项为警告），并标出每个人的资料还缺哪些项。

import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Checkbox, List, Select, Space, Table, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { request, userFacingMessage } from '../shared/api';
import { SEVERITY_LABEL, occupancyMessages, profileGaps, sortedIssues, staffPath, staffPayload, type StaffResult, type StaffRow } from './proposed-staff-core';

type Props = { projectId: string; token: string | null; canEdit: boolean; revision: number; onSaved: () => Promise<unknown> | void };
type Person = { id: string; name: string; type: string; status: string };

export function ProposedStaffCard({ projectId, token, canEdit, revision, onSaved }: Props) {
  const { message } = AntApp.useApp();
  const [result, setResult] = useState<StaffResult | null>(null);
  const [rows, setRows] = useState<StaffRow[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let alive = true;
    request<StaffResult>(staffPath(projectId), token).then(value => { if (alive) { setResult(value); setRows(value.staff); } })
      .catch(error => message.error(userFacingMessage(error)));
    request<{ items: Person[] }>('/api/v1/library', token)
      .then(value => { if (alive) setPeople(value.items.filter(item => item.type === 'personnel' && item.status !== 'rejected')); })
      .catch(() => undefined);
    return () => { alive = false; };
  }, [projectId, token]);  // eslint-disable-line react-hooks/exhaustive-deps

  function update(index: number, patch: Partial<StaffRow>) {
    setRows(current => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  async function save() {
    let body;
    try { body = staffPayload(rows); } catch (error) { message.error(userFacingMessage(error)); return; }
    setSaving(true);
    try {
      const value = await request<StaffResult>(staffPath(projectId), token, 'PUT', body, revision);
      setResult(value); setRows(value.staff);
      message.success('拟派人员已保存，下面是按招标人员条件的核对结果。');
      await onSaved();
    } catch (error) { message.error(userFacingMessage(error)); } finally { setSaving(false); }
  }

  const roles = result?.roles ?? [];
  const issues = sortedIssues(result?.r33.issues ?? []);
  return (
    <div data-testid="proposed-staff-card">
      {occupancyMessages(result?.occupancy).map(text => <Alert key={text} type="warning" showIcon style={{ marginBottom: 8 }} message={text} data-testid="staff-occupancy-hint" />)}
      {people.length === 0 && <Alert type="info" showIcon style={{ marginBottom: 8 }} message="资料库还没有“人员”类资料，请先在资料库录入人员（学历、专业、参加工作时间、证书逐行填写）。" />}
      <Table<StaffRow> size="small" rowKey={(row, index) => row.id ?? `new-${index}`} pagination={false} dataSource={rows}
        locale={{ emptyText: '尚未拟派人员' }}
        columns={[
          { title: '人员', key: 'person', render: (_, row, index) => (
            <Select style={{ width: 160 }} value={row.person_id || undefined} disabled={!canEdit} placeholder="选择人员" showSearch optionFilterProp="label"
              options={people.map(person => ({ value: person.id, label: person.name }))} onChange={value => update(index, { person_id: value, profile: undefined })} />
          ) },
          { title: '项目角色', key: 'role', render: (_, row, index) => (
            <Select style={{ width: 140 }} value={row.role || undefined} disabled={!canEdit} placeholder="角色"
              options={roles.map(role => ({ value: role, label: role }))} onChange={value => update(index, { role: value })} />
          ) },
          { title: 'AB 角', key: 'position', width: 90, render: (_, row, index) => (
            <Select style={{ width: 70 }} allowClear value={row.position ?? undefined} disabled={!canEdit}
              options={[{ value: 'A', label: 'A' }, { value: 'B', label: 'B' }]} onChange={value => update(index, { position: value ?? null })} />
          ) },
          { title: '关键人员', key: 'key', width: 80, render: (_, row, index) => (
            <Checkbox checked={!!row.is_key_person} disabled={!canEdit} onChange={event => update(index, { is_key_person: event.target.checked })} />
          ) },
          { title: '资料缺项', key: 'gaps', render: (_, row) => {
            if (row.profile === undefined) return <span className="muted">保存后读取</span>;
            const gaps = profileGaps(row.profile);
            return gaps.length ? gaps.map(gap => <Tag key={gap} color="orange">缺{gap}</Tag>) : <Tag color="green">齐全</Tag>;
          } },
          { title: '', key: 'remove', width: 60, render: (_, _row, index) => canEdit && (
            <Button type="link" size="small" danger onClick={() => setRows(current => current.filter((_, i) => i !== index))}>移除</Button>
          ) },
        ]} />
      {canEdit && (
        <Space style={{ marginTop: 8 }}>
          <Button icon={<PlusOutlined />} onClick={() => setRows(current => [...current, { person_id: '', role: '' }])}>添加人员</Button>
          <Button type="primary" loading={saving} onClick={save} data-testid="proposed-staff-save">保存拟派人员</Button>
        </Space>
      )}
      {result && (
        <List size="small" style={{ marginTop: 12 }} header={<b>R33 拟派人员条件：{result.r33.finding_summary}</b>} dataSource={issues}
          data-testid="proposed-staff-r33" locale={{ emptyText: '没有需要处理的问题' }}
          renderItem={issue => (
            <List.Item>
              <Space><Tag color={issue.severity === 'blocker' ? 'red' : issue.severity === 'warning' ? 'orange' : 'blue'}>{SEVERITY_LABEL[issue.severity]}</Tag>{issue.message}</Space>
            </List.Item>
          )} />
      )}
    </div>
  );
}
