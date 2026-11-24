// 为什么有这个文件：提取编辑台右侧助手面板组件（EditorAssistantPanel）。
// 它解决什么问题：解耦对话助手、整章候选建议、合规问题提示与写作来源面板，降低 EditorPage 行数。

import React, { useEffect, useState } from 'react';
import { Alert, Button, Input, Select, Space, Tabs, Tag } from 'antd';
import { TECH_CHIPS, takePrefill, type SectionOption } from './technical-assistant.ts';
import { ArrowUpOutlined } from '@ant-design/icons';
import { AiTag } from '../library/BusinessTags.tsx';
import { WritingSources } from './WritingInputPreview.tsx';
import type { Candidate, Chapter, Workspace } from '../shared/types.ts';

export interface EditorAssistantPanelProps {
  rightTab: string;
  setRightTab: (tab: string) => void;
  candidate: Candidate | null;
  candidateIssue: string | null;
  instruction: string;
  setInstruction: (val: string) => void;
  combinedBusy: boolean;
  held: boolean;
  canEdit: boolean;
  canGenerate: boolean;
  chapter: Chapter | null;
  planCurrent: boolean;
  modified: boolean;
  workspace: Workspace;
  chapterId: string;
  onViewInput: () => void;
  onShowDiff: (candidate: Candidate) => void;
  onSuggest: () => void;
  /** 选区改写（对话助手样例），显示在整章建议之上 */
  selectionTools?: React.ReactNode;
  /** 放在右侧栏页签旁的收起按钮 */
  collapseControl?: React.ReactNode;
  /** “问题”页签内容（APP-M2-T166）与待处理问题数 */
  issuesPanel?: React.ReactNode;
  openIssueCount?: number;
  /** 技术分册：初稿完成后才启用写作助手 */
  draftReady?: boolean;
  generating?: boolean;
  /** 标书修改模式：直接改文档前可预览候选 */
  technicalAssistant?: boolean;
  /** 技术分册：确认目录里的小节，问答与修改的作用域 */
  sections?: SectionOption[];
  section?: string;
  setSection?: (value: string) => void;
  onSuggestSection?: () => void;
}

const ASK_CHIPS = ['修改具体表述', '调整责任承诺', '补充客户结合段', '这一节依据是什么'];
const EDIT_CHIPS = ['改写本节', '扩写客户结合', '缩写冗长段', '按指令修改'];

export function EditorAssistantPanel({
  rightTab,
  setRightTab,
  candidate,
  candidateIssue,
  instruction,
  setInstruction,
  combinedBusy,
  held,
  canEdit,
  canGenerate,
  chapter,
  planCurrent,
  modified,
  workspace,
  chapterId,
  onViewInput,
  onShowDiff,
  onSuggest,
  selectionTools,
  collapseControl,
  issuesPanel,
  openIssueCount = 0,
  draftReady = true,
  generating = false,
  technicalAssistant = false,
  sections = [],
  section = '',
  setSection,
  onSuggestSection,
}: EditorAssistantPanelProps) {
  const [composer, setComposer] = useState<'ask' | 'chapter'>('ask');
  const [askDraft, setAskDraft] = useState('');
  const [askNonce, setAskNonce] = useState(0);
  const pendingAsk = React.useRef('');
  const asking = composer === 'ask';
  const draft = asking ? askDraft : instruction;
  const setDraft = asking ? setAskDraft : setInstruction;
  const assistantLocked = technicalAssistant && (generating || !draftReady);
  const sectionMode = technicalAssistant && sections.length > 0;
  useEffect(() => {
    if (!technicalAssistant) return;
    const prefill = takePrefill(workspace.project.id);
    if (!prefill) return;
    setSection?.(prefill.section);
    setInstruction(prefill.instruction);
    setComposer('chapter');
  }, [workspace.project.id, technicalAssistant]);
  const sendDisabled = assistantLocked || (asking
    ? !askDraft.trim()
    : combinedBusy || !canGenerate || !chapter || !instruction.trim() || modified || (technicalAssistant && !held)
      || (sectionMode ? !section : !planCurrent));
  const tools = React.isValidElement(selectionTools)
    ? React.cloneElement(selectionTools as React.ReactElement<{ askDraft?: string; askNonce?: number; askSection?: string }>, { askDraft: pendingAsk.current, askNonce, askSection: sectionMode ? section : undefined })
    : selectionTools;
  function send() {
    if (sendDisabled) return;
    if (asking) {
      const question = askDraft.trim();
      pendingAsk.current = question;
      setAskNonce(value => value + 1);
      setAskDraft('');
    } else if (sectionMode && onSuggestSection) onSuggestSection();
    else onSuggest();
  }
  const chips = sectionMode && !asking ? TECH_CHIPS.map(item => item.label) : asking ? ASK_CHIPS : EDIT_CHIPS;
  return (
    <aside className="editor-right" data-testid="editor-assistant-panel">
      <div className="assistant-tabbar">
      <Tabs
        size="small"
        activeKey={rightTab}
        onChange={setRightTab}
        items={[
          { key: 'assistant', label: technicalAssistant ? '写作助手' : '对话助手' },
          { key: 'issues', label: openIssueCount ? `问题 ${openIssueCount}` : '问题' },
          { key: 'sources', label: '写作来源' },
        ]}
      />
      {collapseControl}
      </div>
      <div className="assistant-scroll">
        {rightTab === 'assistant' && (
          <div className="chat-thread">
            {assistantLocked && (
              <Alert
                type="info"
                showIcon
                data-testid="assistant-wait-draft"
                style={{ marginBottom: 8 }}
                message={generating ? '正文生成中' : '写作助手待启用'}
                description={generating ? '正文生成完成后可使用写作助手。' : '请先「开始生成」完成初稿，再使用写作助手。'}
              />
            )}
            {sectionMode && (
              <Select
                size="small"
                style={{ width: '100%', marginBottom: 8 }}
                placeholder="选择小节"
                aria-label="写作助手作用小节"
                data-testid="assistant-section"
                value={section || undefined}
                onChange={value => setSection?.(value)}
                options={sections.map(item => ({ value: item.key, label: item.label }))}
                disabled={assistantLocked}
              />
            )}
            {tools}
            {workspace.project.sensitive && <p className="chat-note">敏感项目，只使用本地服务。</p>}
            {candidate && (
              <div className="chat-assistant">
                <div className="chat-assistant-meta">
                  <AiTag variant={candidate.is_real_model ? 'model' : 'demo'} />
                  <span>{candidate.section ? `修改 · ${candidate.section}` : technicalAssistant ? '标书修改 · 预览' : `整章 · 基于 v${candidate.base_revision}`}</span>
                </div>
                {candidateIssue && <Alert type="warning" showIcon message={candidateIssue} />}
                {candidate.precheck && candidate.precheck.status !== 'passed' && (
                  <Alert
                    type={candidate.precheck.status === 'failed' ? 'error' : 'warning'}
                    showIcon
                    data-testid="candidate-precheck"
                    message={candidate.precheck.status === 'failed' ? '候选违反废标或硬约束，写入前请修改' : '候选承诺与其他内容不一致，请核对'}
                    description={<ul>{[...candidate.precheck.missing, ...candidate.precheck.conflicts].map(text => <li key={text}>{text}</li>)}</ul>}
                  />
                )}
                <p>{candidate.section_body ?? candidate.content}</p>
                {candidate.sources && (candidate.sources.length ? (
                  <ul className="rewrite-sources">
                    {candidate.sources.map(src => <li key={`${src.dataset_kind}-${src.name}`}><Tag>{src.dataset_kind === 'history' ? '历史标书' : src.dataset_kind === 'materials' || src.dataset_kind === 'material' ? '资料库' : '本标'}</Tag>{src.name}</li>)}
                  </ul>
                ) : <p className="muted">无知识库来源</p>)}
                <Space wrap>
                  <Button size="small" type="link" onClick={onViewInput}>查看来源</Button>
                  <Button size="small" type="primary" disabled={combinedBusy || !held || !chapter || !!candidateIssue} onClick={() => onShowDiff(candidate)}>
                    {technicalAssistant ? '预览后写入' : '写入'}
                  </Button>
                </Space>
              </div>
            )}
          </div>
        )}
        {rightTab === 'sources' && <WritingSources key={chapterId} chapterId={chapterId} candidate={candidate} />}
        {rightTab === 'issues' && issuesPanel}
      </div>
      {rightTab === 'assistant' && (
        <div className="assistant-input">
          <div className="prompt-chips" data-testid="assistant-chips">
            {chips.map(text => (
              <button
                key={text}
                type="button"
                disabled={assistantLocked}
                onClick={() => {
                  const quick = sectionMode ? TECH_CHIPS.find(item => item.label === text) : undefined;
                  if (asking) setAskDraft(text);
                  else setInstruction(quick ? quick.instruction : `${text}：结合本章与双库依据，不新增未经证实的承诺。`);
                }}
              >{text}</button>
            ))}
          </div>
          <Input.TextArea
            aria-label={asking ? '问答写作' : '标书修改要求'}
            placeholder={asking ? '提问（不直接改文档）' : '说明要怎么改正文'}
            autoSize={{ minRows: 1, maxRows: 6 }}
            maxLength={asking ? 1000 : 2000}
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onPressEnter={event => {
              if (event.shiftKey) return;
              event.preventDefault();
              send();
            }}
            disabled={assistantLocked || (asking ? false : combinedBusy || !canEdit)}
          />
          <div className="assistant-send">
            <div className="composer-modes" data-testid="assistant-modes">
              <button type="button" className={composer === 'ask' ? 'active' : ''} disabled={assistantLocked} onClick={() => setComposer('ask')}>{technicalAssistant ? '问答写作' : '提问'}</button>
              <button type="button" className={composer === 'chapter' ? 'active' : ''} disabled={assistantLocked} onClick={() => setComposer('chapter')}>{technicalAssistant ? '标书修改' : '整章'}</button>
            </div>
            <Button
              shape="circle"
              type="primary"
              aria-label="发送"
              icon={<ArrowUpOutlined />}
              data-testid={asking ? 'assistant-ask-btn' : 'assistant-edit-btn'}
              disabled={sendDisabled}
              onClick={send}
            />
          </div>
          {composer === 'chapter' && technicalAssistant && <span className="chat-note">{sectionMode ? '只改所选小节；候选先做废标检查，预览差异后再写入。' : '标书修改会生成可预览候选，确认后再写入。'}</span>}
          {composer === 'chapter' && modified && <span className="chat-note">先提交本节，再请求修改建议。</span>}
          {composer === 'chapter' && !sectionMode && !planCurrent && <span className="chat-note">先确认目录，再请求修改建议。</span>}
        </div>
      )}
    </aside>
  );
}
