// 为什么有这个文件：展示后台实际送入本章写作的条款、证据版本和事实取值。
// 它解决什么问题：区分生成时的历史输入与当前输入，防止把资料编号或猜测当作已核实来源。
import { useEffect, useState } from 'react';
import { Alert, Button, Card, Collapse, Empty, Radio, Space, Spin, Tag } from 'antd';
import { request } from './api';
import { formatTime, paginationName, useProject, volumeName } from './context';
import { displaySlaValue } from './sla-form';
import type { Candidate, Source, WritingInputPreview, WritingInputSnapshot } from './types';

function CapturedSource({ source }: { source: Source | null }) {
  return source ? <div className="writing-captured-source"><p className="muted">{source.filename ?? '招标原文'} · 第 {source.page} 页{source.pagination ? ` · ${paginationName(source.pagination)}` : ''}</p><blockquote>{source.quote || '没有摘录文字；需要结合原文人工核对。'}</blockquote></div> : <p className="muted">项目人工确认或服务承诺派生，无招标页码。</p>;
}

export default function WritingInputPreviewContent({ snapshot, historical }: { snapshot: WritingInputSnapshot | null | undefined; historical: boolean }) {
  if (!snapshot) return <Alert showIcon type="warning" message="这份候选没有保存输入快照，不能据此认定来源已经追溯" description="重新确认方案并生成整章候选后，可以核对当次条款、证据和事实。" />;
  return <div className="writing-input-preview">
    <Alert showIcon type="info" message={historical ? '生成时的输入快照 · 整章候选' : '当前准备送入的输入 · 整章'}
      description={historical ? '以下取值、证据版本和原文摘录来自当次后台快照，不会替换为现在的资料。尚未实现逐段来源绑定。' : '以下由后台读取当前项目；真正生成时仍会重新校验，输入变动会使旧候选失效。'} />
    <p className="muted">{snapshot.project.name} · {snapshot.chapter.title} · {volumeName(snapshot.chapter.volume)} · 正文 v{snapshot.chapter.base_revision} · {formatTime(snapshot.created_at)}</p>
    <Card size="small" title="本章写作方案" className="source-card"><p>写作要点：{snapshot.plan.writing_points || '未额外填写'}</p><p>字数目标：{snapshot.plan.target_length ? `${snapshot.plan.target_length} 字（需人工复核）` : '未设置'}</p><p className="muted">{snapshot.plan.confirmed_at ? `负责人确认时间：${formatTime(snapshot.plan.confirmed_at)}` : '方案尚未确认'}</p></Card>
    <Collapse defaultActiveKey={['requirements', 'facts']} items={[
      { key: 'requirements', label: `响应矩阵 · ${snapshot.requirements.length} 条`, children: snapshot.requirements.length ? snapshot.requirements.map(item => <Card size="small" key={item.id} className="source-card" title={<Space><Tag color="blue">已确认要求</Tag><span>本章条款</span></Space>}><p>{item.text}</p><p><b>响应：</b>{item.response || '尚未填写响应'}</p><CapturedSource source={item.source} /><p className="muted">采用证据：{item.evidence_ids.map(id => snapshot.evidence.find(evidence => evidence.id === id)?.name ?? '未采用，见输入核对结果').join('、') || '无'}</p></Card>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本章没有已确认的关联条款" /> },
      { key: 'facts', label: `项目事实 · ${snapshot.facts.length} 项`, children: snapshot.facts.length ? snapshot.facts.map(item => <Card size="small" key={item.id} className="source-card" title={<Space wrap><b>{item.label ?? item.key}</b><Tag color={item.required ? 'blue' : 'default'}>{item.required ? '全部章节必备' : '本章选中'}</Tag></Space>}><p><b>{displaySlaValue(item.value, item.unit)}</b></p><p className="muted">正文变量：<code>{item.variable}</code></p><CapturedSource source={item.source} /></Card>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本次没有采用项目事实" /> },
      { key: 'evidence', label: `可引用证据 · ${snapshot.evidence.length} 份`, children: snapshot.evidence.length ? snapshot.evidence.map(item => <Card size="small" key={item.id} className="source-card" title={<Space wrap><Tag color="green">已确认</Tag><b>{item.name}</b><span>资料版本 v{item.revision}</span></Space>}><p className="muted">有效期：{item.valid_until || '未设置'}</p><pre className="writing-evidence-content">{item.content}</pre></Card>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本次没有采用公司证据" /> },
      { key: 'omitted', label: `未采用输入 · ${snapshot.omitted_inputs.length} 项`, children: snapshot.omitted_inputs.length ? snapshot.omitted_inputs.map((item, index) => <div className="writing-omitted-item" key={`${item.kind}-${item.id}-${index}`}><b>{item.label}</b><p>{item.reason}</p></div>) : <p className="muted">没有省略项。</p> },
      { key: 'official', label: '本次已提交正文', children: <pre className="writing-evidence-content">{snapshot.official_content || '（尚未提交正文）'}</pre> },
    ]} />
  </div>;
}

export function WritingSources({ chapterId, candidate }: { chapterId: string; candidate: Candidate | null }) {
  const { workspace, token, report } = useProject();
  const [mode, setMode] = useState<'current' | 'candidate'>('current');
  const [preview, setPreview] = useState<WritingInputPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (mode !== 'current' || !chapterId) return;
    let cancelled = false;
    setPreview(null); setLoading(true);
    request<WritingInputPreview>(`/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/writing-input`, token)
      .then(data => { if (!cancelled) setPreview(data); })
      .catch(error => { if (!cancelled) report(error); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [mode, chapterId, workspace.project.id, workspace.input_fingerprint, token, retry]);
  return <><Space wrap className="writing-source-controls"><Radio.Group size="small" value={mode} onChange={event => setMode(event.target.value)} options={[{ value: 'current', label: '当前写作输入' }, { value: 'candidate', label: '候选历史输入', disabled: !candidate }]} optionType="button" />{mode === 'current' && <Button size="small" onClick={() => setRetry(value => value + 1)} disabled={loading}>重新读取</Button>}</Space>
    {mode === 'candidate' ? <WritingInputPreviewContent snapshot={candidate?.input_snapshot} historical /> : <Spin spinning={loading}>{preview && <>{!preview.ready && <Alert type="warning" showIcon className="page-notice" message="当前输入尚不能生成" description={preview.issues.map(issue => issue.message).join('；')} />}<WritingInputPreviewContent snapshot={preview.input_snapshot} historical={false} /></>}{!preview && !loading && <Empty description="尚未读取到当前输入，可重新读取后核对" />}</Spin>}
  </>;
}
