// 为什么有这个文件：保留示例的章节目录、正文和助手三栏编辑流程。
// 它解决什么问题：编辑权、旧草稿、正式版本与建议确认都以后台实际校验为准。
import { useEffect, useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Drawer, Empty, Form, Input, Modal, Radio, Select, Space, Spin, Tabs, Tag, Tooltip } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, HistoryOutlined, LockOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, SendOutlined, UnlockOutlined } from '@ant-design/icons';
import { ApiError, request } from './api';
import { formatTime, useProject, volumeName } from './context';
import type { Candidate, Chapter, Volume, Workspace } from './types';
import { recoveryWrite } from './editor-recovery';
import RecoveryReview, { type RecoveryChoice } from './RecoveryReview';

type Lease = { lease_token: string; expires_at: string; owner_id: string };
type Version = { revision: number; content: string; actor_id: string; created_at: string };

export default function EditorPage({ onDirtyChange }: { onDirtyChange: (dirty: boolean) => void }) {
  const { workspace, user, token, busy: projectBusy, mutate, reload, report } = useProject();
  const { message, modal } = AntApp.useApp();
  const [volume, setVolume] = useState<Volume>('technical');
  const [chapterId, setChapterId] = useState(workspace.chapters.find(item => item.volume === 'technical')?.id ?? workspace.chapters[0]?.id ?? '');
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState('');
  const [lease, setLease] = useState<Lease | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [rightTab, setRightTab] = useState('assistant');
  const [instruction, setInstruction] = useState('写得更具体，按原文和已确认事实说明工作步骤，不能新增未经核实的承诺。');
  const [suggestion, setSuggestion] = useState<Candidate | null>(null);
  const [diff, setDiff] = useState<Candidate | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [savedAt, setSavedAt] = useState('');
  const [notice, setNotice] = useState('');
  const [versions, setVersions] = useState<Version[]>([]);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [recovery, setRecovery] = useState<RecoveryChoice | null>(null);
  const [recoveryReviewed, setRecoveryReviewed] = useState(false);
  const [planForm] = Form.useForm();
  const epoch = useRef(0);
  const currentLease = useRef<Lease | null>(null);
  const currentId = useRef(chapterId);
  const sequence = useRef(0);
  const dirty = chapter ? content !== (chapter.draft?.base_revision === chapter.revision ? chapter.draft.content : chapter.content) : false;
  const modified = chapter ? content !== chapter.content : false;
  const combinedBusy = busy || projectBusy || loading;
  const held = !!lease && Date.parse(lease.expires_at) > Date.now();
  const proposed = suggestion ?? workspace.chapters.find(item => item.id === chapterId)?.candidate ?? null;
  const candidate = proposed?.input_fingerprint && proposed.input_fingerprint === workspace.input_fingerprint ? proposed : null;
  const sources = workspace.requirements.filter(item => item.chapter_id === chapterId || workspace.chapters.find(value => value.id === chapterId)?.requirement_ids?.includes(item.id));

  useEffect(() => { onDirtyChange(dirty); }, [dirty]);
  useEffect(() => {
    function leaving(event: BeforeUnloadEvent) { if (dirty) { event.preventDefault(); event.returnValue = ''; } }
    window.addEventListener('beforeunload', leaving); return () => window.removeEventListener('beforeunload', leaving);
  }, [dirty]);
  useEffect(() => {
    currentId.current = chapterId; const start = ++epoch.current;
    setChapter(null); setContent(''); setLease(null); currentLease.current = null; setSuggestion(null); setDiff(null); setRecovery(null); setSavedAt(''); setNotice(''); onDirtyChange(false);
    if (!chapterId) return;
    setLoading(true);
    request<Chapter>(`/api/chapters/${chapterId}`, token).then(data => {
      if (start !== epoch.current) return;
      setChapter(data); sequence.current = data.draft?.sequence ?? 0;
      if (data.draft && data.draft.base_revision !== data.revision) { setContent(data.content); setNotice('存在基于旧版本的个人草稿。当前先展示新版本正文，旧草稿没有自动覆盖。'); }
      else { setContent(data.draft?.content ?? data.content); if (data.draft) setNotice('已恢复当前版本的个人草稿，提交本节后才进入正式正文和导出。'); }
    }).catch(error => { if (start === epoch.current) report(error); }).finally(() => { if (start === epoch.current) setLoading(false); });
    return () => {
      ++epoch.current;
      const previous = currentLease.current; currentLease.current = null;
      if (previous) void request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: previous.lease_token }).catch(() => undefined);
    };
  }, [chapterId, token]);
  useEffect(() => {
    if (!lease) return;
    const start = epoch.current;
    const timer = window.setInterval(async () => {
      const activeLease = currentLease.current;
      if (!activeLease || start !== epoch.current) return;
      try { const renewed = await request<Lease>(`/api/chapters/${chapterId}/lock/renew`, token, 'POST', { lease_token: activeLease.lease_token }); if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) { currentLease.current = renewed; setLease(renewed); } }
      catch (error) { if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) { currentLease.current = null; setLease(null); setNotice('编辑权续期失败，文字已保留在当前页面。请重新取得编辑权后核对版本再保存。'); report(error); } }
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [lease?.lease_token, chapterId, token]);

  function localError(error: unknown) {
    report(error);
    if (error instanceof ApiError && error.status === 423) { currentLease.current = null; setLease(null); setNotice('编辑权已失效，当前文字仍在页面。请重新取得编辑权，避免覆盖其他人。'); }
    if (error instanceof ApiError && error.status === 409) setNotice('后台正文或草稿已变化，本次写入没有成功。当前文字保留；请查看最新版本后核对，不能继续覆盖。');
  }
  async function run(action: () => Promise<void>) { setBusy(true); try { await action(); } catch (error) { localError(error); } finally { setBusy(false); } }
  async function acquire(reason: string | null = null) {
    await run(async () => {
      const start = epoch.current;
      const result = await request<Lease>(`/api/chapters/${chapterId}/lock`, token, 'POST', { takeover_reason: reason });
      if (start !== epoch.current) return;
      currentLease.current = result; setLease(result);
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      if (chapter && latest.revision !== chapter.revision && modified) { setNotice('取得编辑权时发现新版本。当前文字未被清除，请先查看最新版本，核对后再编辑。'); currentLease.current = null; setLease(null); await request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: result.lease_token }); return; }
      setChapter(latest); sequence.current = latest.draft?.sequence ?? sequence.current;
      if (!modified) setContent(latest.draft?.base_revision === latest.revision ? latest.draft.content : latest.content);
      setNotice('已取得编辑权。其他账号会被后台阻止写入。');
    });
  }
  function takeover() { let reason = ''; modal.confirm({ title: '说明接管编辑的理由', content: <Input.TextArea aria-label="接管理由" placeholder="接管会使原编辑人的凭据失效，原因将留在操作记录中" onChange={e => { reason = e.target.value; }} />, okText: '填写理由并接管', onOk: async () => { if (!reason.trim()) throw new Error('请填写接管理由'); await acquire(reason); } }); }
  async function release() { await run(async () => { if (!lease) return; await request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: lease.lease_token }); currentLease.current = null; setLease(null); setChapter(await request<Chapter>(`/api/chapters/${chapterId}`, token)); }); }
  async function saveDraft() { await run(async () => { if (!chapter || !lease) return; const value = await request<{ sequence: number; content: string; base_revision: number }>(`/api/chapters/${chapterId}/draft`, token, 'PUT', { lease_token: lease.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, content }); setChapter({ ...chapter, draft: value }); setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setNotice('个人草稿已保存；尚未进入正式正文和导出。'); }); }
  async function commit() { await run(async () => { if (!chapter || !lease) return; await request(`/api/chapters/${chapterId}/versions`, token, 'POST', { lease_token: lease.lease_token, base_revision: chapter.revision, content, idempotency_key: crypto.randomUUID() }); const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token); setChapter(updated); setContent(updated.content); setSuggestion(null); sequence.current = updated.draft?.sequence ?? sequence.current; setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setNotice(`已提交正文 v${updated.revision}；之前的检查和导出会失效，需要重新运行。`); await reload(); }); }
  async function suggest() { await run(async () => { const value = await request<Candidate>(`/api/chapters/${chapterId}/suggestions`, token, 'POST', { instruction }); setSuggestion(value); }); }
  async function generate() { try { await mutate(`/api/v1/projects/${workspace.project.id}/generate`, 'POST', { chapter_ids: [chapterId] }); setSuggestion(null); setNotice('已生成候选，尚未改动正式正文。请在右侧比较并确认。'); } catch { /* 统一入口已经显示错误 */ } }
  async function viewVersions() { await run(async () => { const value = await request<{ versions: Version[] }>(`/api/chapters/${chapterId}/versions`, token); setVersions(value.versions.slice().reverse()); setVersionsOpen(true); }); }
  function selectChapter(id: string, nextVolume?: Volume) {
    const action = () => { if (nextVolume) setVolume(nextVolume); setChapterId(id); };
    if (!dirty) action(); else modal.confirm({ title: '当前章节还有未保存文字', content: '先保存草稿或提交本节，才能保证这些文字不丢失。', okText: '离开当前章节', cancelText: '继续编辑', onOk: action });
  }
  function showDiff(value: Candidate) { setReviewed(false); setDiff(value); }
  async function apply() {
    if (!chapter || !lease || !held || !diff || diff.base_revision !== chapter.revision || !reviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      if (!diff.input_fingerprint || diff.input_fingerprint !== latest.input_fingerprint) {
        setDiff(null); setSuggestion(null); await reload();
        throw new Error('条款、事实、证据或正文已变化，这份候选已过期。请重新生成后核对。');
      }
      setContent(diff.content); setDiff(null); setSuggestion(null); setNotice('候选已写入当前编辑内容。请人工修订，再保存草稿或提交本节。');
    });
  }
  function reviewRecovery(choice: RecoveryChoice) { setRecoveryReviewed(false); setRecovery(choice); }
  async function saveRecovery() {
    if (!chapter || !lease || !held || !recovery || !recoveryReviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      const write = recoveryWrite(chapter, latest, recovery.content);
      const draft = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', { ...write, lease_token: lease.lease_token });
      if (start !== epoch.current) return;
      sequence.current = draft.sequence; setChapter({ ...latest, draft }); setContent(draft.content); setRecovery(null);
      setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
      setNotice('恢复内容已保存为新的个人草稿，正式正文未变。请修订后提交本节。');
    });
  }
  function openPlan() { planForm.setFieldsValue({ chapters: workspace.chapters.map(item => ({ id: item.id, title: item.title, volume: item.volume })) }); setPlanOpen(true); }
  async function savePlan() { const value = await planForm.validateFields(); try { await mutate(`/api/v1/projects/${workspace.project.id}/plan`, 'POST', { chapters: value.chapters.map((item: { id?: string; title: string; volume: Volume }) => ({ ...(item.id ? { id: item.id } : {}), title: item.title, volume: item.volume })) }); setPlanOpen(false); } catch { /* 保留大纲供修订 */ } }

  return <><div className="editor-layout"><aside className="chapter-directory"><Radio.Group size="small" optionType="button" buttonStyle="solid" value={volume} onChange={e => { const next = e.target.value as Volume; selectChapter(workspace.chapters.find(item => item.volume === next)?.id ?? '', next); }} options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /><Input size="small" prefix={<FileTextOutlined />} placeholder="搜索章节" aria-label="搜索章节" value={search} onChange={e => setSearch(e.target.value)} /><div className="directory-label">章节目录</div>{workspace.chapters.filter(item => item.volume === volume && item.title.includes(search)).map(item => <button className={`chapter-entry ${chapterId === item.id ? 'active' : ''}`} onClick={() => selectChapter(item.id)} key={item.id}><span className={`chapter-dot ${item.content.trim() ? 'green-dot' : ''}`} /><span><b>{item.title}</b><small>{item.content.trim() ? `已提交 v${item.revision}` : '待编制'}{item.candidate ? ' · 有候选待确认' : ''}</small></span></button>)}<div className="directory-bottom"><Button block size="small" onClick={openPlan} disabled={combinedBusy || user.role === 'viewer' || !workspace.parse_confirmed}>写作方案与大纲确认</Button><p className="muted">{workspace.plan_confirmed ? '大纲已确认' : '先确认解析，再核对大纲'}</p><Tag color="orange">结构化段落编辑仍在后续任务中</Tag></div></aside><section className="editor-center"><div className="editor-toolbar"><Space size={6}><Tooltip title="正文格式与选区工具将在结构化编辑器中实现"><Button size="small" disabled>格式</Button></Tooltip><Button size="small" icon={<HistoryOutlined />} onClick={viewVersions} disabled={combinedBusy || !chapter}>版本</Button><Tooltip title="建议不会直接写入正文"><Button size="small" onClick={generate} disabled={combinedBusy || !workspace.plan_confirmed || user.role === 'viewer' || !chapter}>生成候选</Button></Tooltip></Space><Space size={6}><Tag color={held ? 'green' : chapter?.lock ? 'orange' : 'default'} icon={held ? <LockOutlined /> : <UnlockOutlined />}>{held ? '本人锁定' : chapter?.lock ? '他人 / 其他会话编辑中' : '未取得编辑权'}</Tag>{savedAt && <span className="saved-at">{savedAt} 已保存</span>}<Button type="primary" size="small" onClick={commit} disabled={combinedBusy || !held || !chapter} loading={busy}>提交本节</Button></Space></div><Spin spinning={loading}><div className="editor-scroll">{notice && <Alert className="editor-notice" showIcon type={notice.includes('变化') || notice.includes('失败') || notice.includes('失效') ? 'warning' : 'info'} message={notice} closable onClose={() => setNotice('')} />}{chapter ? <article className="document-paper"><div className="document-heading"><h2>{chapter.title}</h2><Tag>{volumeName(chapter.volume)}</Tag></div><p className="document-subline">正文版本 v{chapter.revision} · {sources.length} 条关联要求 · {held ? '已取得编辑权' : '只读，请先取得编辑权'}</p>{sources.length > 0 && <div className="chapter-source-summary"><span className="source-label">招标原文</span><div>{sources.map(item => <p key={item.id}>{item.text} <Tag>P.{item.source.page}</Tag></p>)}</div></div>}<Input.TextArea className="chapter-editor" aria-label="章节正文" placeholder="根据招标原文、项目事实和可引用证据编制正文。不要把未经核实的承诺直接写入。" autoSize={{ minRows: 18, maxRows: 35 }} value={content} onChange={e => setContent(e.target.value)} readOnly={!held || combinedBusy} /><div className="document-footer"><span className="muted">{content.length} 字 · {modified ? '当前内容未全部提交' : '与已提交正文一致'}</span><Space><Button size="small" icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !held}>保存草稿</Button>{held ? <Button size="small" onClick={release} disabled={combinedBusy}>释放编辑权</Button> : <Button size="small" type="primary" icon={<LockOutlined />} onClick={() => acquire()} disabled={combinedBusy || user.role === 'viewer'}>取得编辑权</Button>}{!held && chapter.lock && user.role === 'manager' && <Button size="small" danger onClick={takeover} disabled={combinedBusy}>填写理由接管</Button>}</Space></div>{chapter.draft && chapter.draft.base_revision !== chapter.revision && <Card size="small" title={`旧草稿（基于 v${chapter.draft.base_revision}，未自动覆盖）`} extra={<Button size="small" disabled={combinedBusy || !held} onClick={() => reviewRecovery({ title: `旧草稿 v${chapter.draft!.base_revision}`, content: chapter.draft!.content })}>核对并恢复</Button>} className="old-draft"><pre>{chapter.draft.content}</pre></Card>}</article> : <Empty description="当前分册没有可编辑章节" />}</div></Spin></section><aside className="editor-right"><Tabs size="small" activeKey={rightTab} onChange={setRightTab} items={[{ key: 'assistant', label: '对话助手' }, { key: 'issues', label: '问题' }, { key: 'sources', label: `来源 ${sources.length}` }]} /><div className="assistant-scroll">{rightTab === 'assistant' && <><div className="model-label"><Tag color="purple">演示建议</Tag><span>人工确认后才写入</span></div>{workspace.project.sensitive && <Alert type="info" message="敏感项目 · 只使用本地服务" />}<Card size="small" className="instruction-card"><span className="muted">当前章节 · {chapter?.title}</span><p>{instruction}</p></Card>{candidate ? <Card size="small" className="suggestion-card" title={<Space><Tag color="purple">建议候选</Tag><span>基于 v{candidate.base_revision}</span></Space>}><p className="suggestion-content">{candidate.content}</p><Alert type={chapter && candidate.base_revision === chapter.revision ? 'info' : 'warning'} showIcon message={candidate.is_real_model ? '模型建议仍须人工核对' : '当前为演示建议，不代表真实模型已接入'} /><p className="muted">先比较当前内容与候选，再决定是否写入草稿。</p><Button type="primary" size="small" disabled={combinedBusy || !held || !chapter || candidate.base_revision !== chapter.revision} onClick={() => showDiff(candidate)}>查看差异并确认写入</Button></Card> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="先生成章节候选，或输入修改要求取得建议" />}</>}{rightTab === 'sources' && <>{sources.map(item => <Card size="small" key={item.id} className="source-card" title={<Space><Tag color="blue">招标原文</Tag><span>P.{item.source.page}</span></Space>}><p>{item.text}</p><blockquote>{item.source.quote}</blockquote>{item.evidence_ids.map(id => { const evidence = workspace ? useEvidencePlaceholder(id) : ''; return <p className="muted" key={id}>已挂证据 {evidence}</p>; })}</Card>)}{sources.length === 0 && <Empty description="暂无关联条款，先在响应矩阵分配章节" />}<Alert type="info" message="当前展示条款和证据关联，正文引用节点尚未实现" /></>}{rightTab === 'issues' && <>{workspace.checks[workspace.checks.length - 1]?.issues.filter(item => item.chapter_id === chapterId).map(item => <Alert key={item.id} className="page-notice" type={item.severity === 'warning' ? 'warning' : 'error'} message={`${item.code} · ${item.message}`} />) ?? <Empty description="请提交正文后运行检查" />}<Alert type="info" message="问题依据当前检查批次；未提交内容尚未检查" /></>}</div>{rightTab === 'assistant' && <div className="assistant-input"><div className="prompt-chips">{['改写', '扩写', '缩写', '按指令修改', '换一种说法'].map(text => <button key={text} onClick={() => setInstruction(`${text}当前章节，依据已核对原文与事实，不新增未经证实的承诺。`)}>{text}</button>)}</div><Input.TextArea aria-label="给助手的修改要求" placeholder="针对当前正文输入修改要求" rows={3} maxLength={2000} value={instruction} onChange={e => setInstruction(e.target.value)} disabled={combinedBusy || user.role === 'viewer'} /><div className="assistant-send"><span className="muted">整章建议 · 选区助手待实现</span><Button size="small" type="primary" icon={<SendOutlined />} disabled={combinedBusy || user.role === 'viewer' || !chapter || !instruction.trim() || modified} onClick={suggest}>发送</Button></div>{modified && <span className="muted">先提交本节，再基于已提交正文请求建议</span>}</div>}</aside></div><Modal title="写入确认 · 建议差异" cancelText="放弃这次写入" width={960} open={!!diff} onCancel={() => setDiff(null)} onOk={apply} okText="确认写入当前草稿" okButtonProps={{ disabled: !held || combinedBusy || !reviewed || !chapter || diff?.base_revision !== chapter.revision || diff?.input_fingerprint !== workspace.input_fingerprint }}><div className="diff-description"><Tag color="purple">{diff?.is_real_model ? '模型建议' : '演示建议'}</Tag>写入不会自动提交正文，提交本节后才用于检查和导出。</div><div className="diff-columns"><div><h4>当前内容</h4><pre className="diff-before">{content || '（空正文）'}</pre></div><div><h4>建议写入</h4><pre className="diff-after">{diff?.content}</pre></div></div><label className="review-checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> 我已逐字核对原文、证据和承诺，并确认修改合理</label></Modal><Drawer title="正式版本记录" open={versionsOpen} onClose={() => setVersionsOpen(false)} width={680}>{versions.length ? versions.map(item => <Card size="small" className="version-card" title={`正文 v${item.revision}`} extra={formatTime(item.created_at)} key={item.revision}><p className="muted">提交账号：{item.actor_id}</p><pre>{item.content}</pre><Button size="small" disabled={combinedBusy || !held || item.revision === chapter?.revision} onClick={() => reviewRecovery({ title: `历史正文 v${item.revision}`, content: item.content })}>核对并恢复为草稿</Button></Card>) : <Empty description="暂无已提交版本" />}<Alert type="info" message="历史版本保留不变。恢复先保存个人草稿，人工修订并提交后才产生新正文版本。" /></Drawer><RecoveryReview choice={recovery} current={content} reviewed={recoveryReviewed} busy={busy} writable={held && !combinedBusy && user.role !== 'viewer'} onReview={setRecoveryReviewed} onCancel={() => setRecovery(null)} onSave={saveRecovery} /><Modal title="写作方案与大纲确认" width={820} open={planOpen} onCancel={() => setPlanOpen(false)} onOk={savePlan} confirmLoading={projectBusy} okText="确认大纲"><Alert showIcon type="info" message="先按回应要点核对章节与分册；已有正文、草稿或编辑权的章节不能静默删除" /><Form form={planForm} layout="vertical" style={{ marginTop: 20 }}><Form.List name="chapters">{(fields, { add, remove }) => <>{fields.map(field => <div className="plan-row" key={field.key}><Form.Item name={[field.name, 'id']} hidden><Input /></Form.Item><Form.Item name={[field.name, 'title']} label={`章节 ${field.name + 1}`} rules={[{ required: true, whitespace: true }]} style={{ flex: 1 }}><Input /></Form.Item><Form.Item name={[field.name, 'volume']} label="分册" rules={[{ required: true }]}><Select style={{ width: 140 }} options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} /></Form.Item><Button style={{ marginTop: 27 }} onClick={() => remove(field.name)} disabled={fields.length <= 2} danger>移除</Button></div>)}<Button icon={<PlusOutlined />} onClick={() => add({ title: '', volume: 'technical' })}>新增章节</Button></>}</Form.List></Form><Alert className="page-notice" showIcon type="warning" message="当前只确认章节大纲；证据计划、字数预算、增值章节与分册责任分配尚未接通" /></Modal></>;
}

// 资料标识只用于追溯；资料的正文和可引用状态在矩阵抽屉核对。
function useEvidencePlaceholder(id: string) { return id; }
