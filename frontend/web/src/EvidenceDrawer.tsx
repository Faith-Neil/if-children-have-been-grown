// 为什么有这个文件：在响应矩阵行上打开挂证据抽屉。
// 它解决什么问题：把可挂资料、方案片段和只能参考的历史标书分成三组，不能勾选的不写入本行。
import { useState } from 'react';
import { Alert, Button, Card, Checkbox, Drawer, Empty, Space, Tag } from 'antd';
import type { Evidence, Requirement } from './types';
import { attachedEvidenceLabel, attachmentDiff, evidenceDecision, groupEvidence, toggleSelection } from './evidence-drawer';

const groupTitle = { structured: '结构化资料', snippet: '方案片段', history: '历史标书（参考）' };

function CandidateCard({ item, deadline, checked, canWrite, onToggle, onView }: {
  item: Evidence; deadline?: string | null; checked: boolean; canWrite: boolean;
  onToggle: (id: string, selected: boolean, allowed: boolean) => void;
  onView: (item: Evidence) => void;
}) {
  const decision = evidenceDecision(item, deadline);
  const history = decision.group === 'history';
  return <Card size="small" className={`evidence-card ${decision.selectable ? '' : 'disabled'}`}>
    {history ? <b>{item.name}</b> : <Checkbox disabled={!decision.selectable || !canWrite} checked={checked} onChange={event => onToggle(item.id, event.target.checked, decision.selectable && canWrite)}><b>{item.name}</b></Checkbox>}
    <p className="muted">资料版本 v{item.revision ?? '—'}{item.source?.filename ? ` · 来源 ${item.source.filename}${item.source.page ? ` 第 ${item.source.page} 页` : ''}` : ''}</p>
    <Space wrap>
      <Tag>{item.status === 'confirmed' ? '已确认' : item.status === 'rejected' ? '已排除' : '待确认'}</Tag>
      <Tag color={decision.selectable ? 'green' : 'red'}>{decision.selectable ? '可引用' : decision.reason}</Tag>
      {item.valid_until ? <Tag>有效期 {item.valid_until}</Tag> : <Tag>未登记到期日</Tag>}
    </Space>
    {history && <p><Button type="link" size="small" onClick={() => onView(item)}>查看原文</Button></p>}
  </Card>;
}

export function EvidenceDrawer({ open, requirement, library, deadline, selectedIds, openedIds, canWrite, busy, stale, onClose, onSelected, onSave, onSupplement, onRefresh }: {
  open: boolean;
  requirement: Requirement | null;
  library: Evidence[];
  deadline?: string | null;
  selectedIds: string[];
  openedIds: string[];
  canWrite: boolean;
  busy: boolean;
  stale: boolean;
  onClose: () => void;
  onSelected: (ids: string[]) => void;
  onSave: () => void;
  onSupplement: () => void;
  onRefresh: () => void;
}) {
  const [reading, setReading] = useState<Evidence | null>(null);
  const groups = groupEvidence(library, deadline);
  const diff = attachmentDiff(openedIds, selectedIds);
  const attached = selectedIds.map(id => {
    const item = library.find(value => value.id === id) ?? null;
    return { id, item, label: attachedEvidenceLabel(item, deadline) };
  });
  const expiredAttached = attached.some(row => row.label === '证据失效');
  function toggle(id: string, selected: boolean, allowed: boolean) {
    onSelected(toggleSelection(selectedIds, id, selected, allowed));
  }
  return <Drawer className="evidence-drawer" title="挂证据" open={open} onClose={onClose} width={560} extra={<Button type="primary" disabled={busy || !canWrite || stale} onClick={onSave}>保存挂接</Button>}>
    <Card size="small" title="本行要求原文"><p>{requirement?.text}</p><p className="muted">证明材料要求：{requirement?.proof_requirements || '未单独登记，以上方要求原文为准。'}</p></Card>
    {stale && <Alert className="page-notice" type="warning" showIcon message="本行已被他人修改，请刷新后再保存" description="打开抽屉之后，项目版本或已挂证据变了。当前勾选仍留在这里，不会覆盖新内容。" />}
    {([
      ['structured', groups.structured, '没有结构化资料'],
      ['snippet', groups.snippets, '没有方案片段'],
    ] as const).map(([key, rows, empty]) => <section className="evidence-group" key={key}><h4>{groupTitle[key]}</h4>{rows.length ? rows.map(row => <CandidateCard key={row.item.id} item={row.item} deadline={deadline} checked={selectedIds.includes(row.item.id)} canWrite={canWrite && !busy && !stale} onToggle={toggle} onView={setReading} />) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={empty} />}</section>)}
    {groups.citableEmpty && <Alert type="info" showIcon message="资料库没有可引用的记录" action={<Button size="small" onClick={onSupplement}>去补录</Button>} />}
    <section className="evidence-group"><h4>{groupTitle.history}</h4>{groups.history.length ? groups.history.map(row => <CandidateCard key={row.item.id} item={row.item} deadline={deadline} checked={false} canWrite={false} onToggle={toggle} onView={setReading} />) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有历史标书参考" />}</section>
    {reading && <Alert className="page-notice" type="info" showIcon message={`历史标书原文 · ${reading.name}`} description={<><p>{reading.source?.quote || reading.content}</p><p className="muted">只能查看，不能勾选，也不能由智能匹配挂为证据。</p></>} />}
    <section className="evidence-group"><h4>本行已挂证据</h4>{expiredAttached && <Alert className="page-notice" type="error" showIcon message="证据失效" description="有效期已早于投标截止日。刷新会重新读取资料候选和本行已挂证据。" action={<Button size="small" autoInsertSpace={false} disabled={busy} onClick={onRefresh}>刷新</Button>} />}{attached.length ? attached.map(row => <Card size="small" key={row.id}><b>{row.item?.name ?? '资料已不可见'}</b><p className="muted">资料版本 v{row.item?.revision ?? '—'}</p><Tag color={row.label === '当前合格' ? 'green' : 'red'}>{row.label}</Tag><Button type="link" danger disabled={!canWrite || busy || stale} onClick={() => toggle(row.id, false, canWrite && !busy && !stale)}>移除</Button></Card>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本行还没有挂接证据" />}{(diff.added.length > 0 || diff.removed.length > 0) && <Alert className="page-notice" type="info" message="相对打开时的变动" description={`新增 ${diff.added.length} 条，移除 ${diff.removed.length} 条。保存后本行只保留当前列表。`} />}</section>
  </Drawer>;
}
