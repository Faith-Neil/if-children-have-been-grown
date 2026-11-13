// 为什么有这个文件：提取编辑台右侧助手面板组件（EditorAssistantPanel）。
// 它解决什么问题：解耦对话助手、整章候选建议、合规问题提示与写作来源面板，降低 EditorPage 行数。

import React, { useState } from 'react';
import { Alert, Button, Input, Space, Tabs, Tag } from 'antd';
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
}: EditorAssistantPanelProps) {
  const [composer, setComposer] = useState<'ask' | 'chapter'>('ask');
  const [askDraft, setAskDraft] = useState('');
  const [askNonce, setAskNonce] = useState(0);
  const [askLog, setAskLog] = useState<Array<{ q: string; a: string }>>([]);
  const pendingAsk = React.useRef('');
  const asking = composer === 'ask';
  const draft = asking ? askDraft : instruction;
  const setDraft = asking ? setAskDraft : setInstruction;
  const assistantLocked = technicalAssistant && (generating || !draftReady);
  const sendDisabled = assistantLocked || (asking
    ? !askDraft.trim()
    : combinedBusy || !canGenerate || !chapter || !planCurrent || !instruction.trim() || modified || (technicalAssistant && !held));
  const tools = React.isValidElement(selectionTools)
    ? React.cloneElement(selectionTools as React.ReactElement<{ askDraft?: string; askNonce?: number }>, { askDraft: pendingAsk.current, askNonce })
    : selectionTools;
  function send() {
    if (sendDisabled) return;
    if (asking) {
      const question = askDraft.trim();
      pendingAsk.current = question;
      setAskNonce(value => value + 1);
      setAskDraft('');
      if (technicalAssistant) {
        setAskLog(prev => [...prev, {
          q: question,
          a: '问答写作仅给出建议，不会直接改文档。请结合本章与双库依据人工采纳。',
        }].slice(-8));
      }
    } else onSuggest();
  }
  const chips = asking ? ASK_CHIPS : EDIT_CHIPS;
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
            {tools}
            {workspace.project.sensitive && <p className="chat-note">敏感项目，只使用本地服务。</p>}
            {technicalAssistant && askLog.map((item, index) => (
              <div key={`${item.q}-${index}`} className="chat-assistant" data-testid="ask-log-item">
                <div className="chat-assistant-meta"><span>问答写作</span></div>
                <p><strong>问：</strong>{item.q}</p>
                <p>{item.a}</p>
              </div>
            ))}
            {candidate && (
              <div className="chat-assistant">
                <div className="chat-assistant-meta">
                  <AiTag variant={candidate.is_real_model ? 'model' : 'demo'} />
                  <span>{technicalAssistant ? '标书修改 · 预览' : `整章 · 基于 v${candidate.base_revision}`}</span>
                  {technicalAssistant && <Tag color="purple">内测</Tag>}
                </div>
                {candidateIssue && <Alert type="warning" showIcon message={candidateIssue} />}
                <p>{candidate.content}</p>
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
                  if (asking) setAskDraft(text);
                  else setInstruction(`${text}：结合本章与双库依据，不新增未经证实的承诺。`);
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
          {composer === 'chapter' && technicalAssistant && <span className="chat-note">标书修改会生成可预览候选，确认后再写入；改后节可标「已助手修订」。</span>}
          {composer === 'chapter' && modified && <span className="chat-note">先提交本节，再请求修改建议。</span>}
          {composer === 'chapter' && !planCurrent && <span className="chat-note">先确认目录，再请求修改建议。</span>}
        </div>
      )}
    </aside>
  );
}
