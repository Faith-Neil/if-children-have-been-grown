// 为什么有这个文件：提取编辑台右侧助手面板组件（EditorAssistantPanel）。
// 它解决什么问题：解耦对话助手、整章候选建议、合规问题提示与写作来源面板，降低 EditorPage 行数。

import React, { useState } from 'react';
import { Alert, Button, Input, Space, Tabs } from 'antd';
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
}

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
}: EditorAssistantPanelProps) {
  const [composer, setComposer] = useState<'ask' | 'chapter'>('ask');
  const [askDraft, setAskDraft] = useState('');
  const [askNonce, setAskNonce] = useState(0);
  const pendingAsk = React.useRef('');
  const asking = composer === 'ask';
  const draft = asking ? askDraft : instruction;
  const setDraft = asking ? setAskDraft : setInstruction;
  const sendDisabled = asking
    ? !askDraft.trim()
    : combinedBusy || !canGenerate || !chapter || !planCurrent || !instruction.trim() || modified;
  const tools = React.isValidElement(selectionTools)
    ? React.cloneElement(selectionTools as React.ReactElement<{ askDraft?: string; askNonce?: number }>, { askDraft: pendingAsk.current, askNonce })
    : selectionTools;
  function send() {
    if (sendDisabled) return;
    if (asking) { pendingAsk.current = askDraft; setAskNonce(value => value + 1); setAskDraft(''); }
    else onSuggest();
  }
  return (
    <aside className="editor-right">
      <div className="assistant-tabbar">
      <Tabs
        size="small"
        activeKey={rightTab}
        onChange={setRightTab}
        items={[
          { key: 'assistant', label: '对话助手' },
          { key: 'issues', label: openIssueCount ? `问题 ${openIssueCount}` : '问题' },
          { key: 'sources', label: '写作来源' },
        ]}
      />
      {collapseControl}
      </div>
      <div className="assistant-scroll">
        {rightTab === 'assistant' && (
          <div className="chat-thread">
            {tools}
            {workspace.project.sensitive && <p className="chat-note">敏感项目，只使用本地服务。</p>}
            {candidate && (
              <div className="chat-assistant">
                <div className="chat-assistant-meta">
                  <AiTag variant={candidate.is_real_model ? 'model' : 'demo'} />
                  <span>整章 · 基于 v{candidate.base_revision}</span>
                </div>
                {candidateIssue && <Alert type="warning" showIcon message={candidateIssue} />}
                <p>{candidate.content}</p>
                <Space wrap>
                  <Button size="small" type="link" onClick={onViewInput}>查看来源</Button>
                  <Button size="small" type="primary" disabled={combinedBusy || !held || !chapter || !!candidateIssue} onClick={() => onShowDiff(candidate)}>写入</Button>
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
          {composer === 'chapter' && (
            <div className="prompt-chips">
              {['改写', '扩写', '缩写', '按指令修改', '换一种说法'].map(text => (
                <button key={text} type="button" onClick={() => setInstruction(`${text}当前章节，依据已核对原文与事实，不新增未经证实的承诺。`)}>{text}</button>
              ))}
            </div>
          )}
          <Input.TextArea
            aria-label={asking ? '向对话助手提问' : '给助手的修改要求'}
            placeholder={asking ? '提问' : '说明整章要怎么改'}
            autoSize={{ minRows: 1, maxRows: 6 }}
            maxLength={asking ? 1000 : 2000}
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onPressEnter={event => {
              if (event.shiftKey) return;
              event.preventDefault();
              send();
            }}
            disabled={asking ? false : combinedBusy || !canEdit}
          />
          <div className="assistant-send">
            <div className="composer-modes">
              <button type="button" className={composer === 'ask' ? 'active' : ''} onClick={() => setComposer('ask')}>提问</button>
              <button type="button" className={composer === 'chapter' ? 'active' : ''} onClick={() => setComposer('chapter')}>整章</button>
            </div>
            <Button
              shape="circle"
              type="primary"
              aria-label="发送"
              icon={<ArrowUpOutlined />}
              data-testid={asking ? 'assistant-ask-btn' : undefined}
              disabled={sendDisabled}
              onClick={send}
            />
          </div>
          {composer === 'chapter' && modified && <span className="chat-note">先提交本节，再请求整章建议。</span>}
          {composer === 'chapter' && !planCurrent && <span className="chat-note">先确认本节方案，再请求整章建议。</span>}
        </div>
      )}
    </aside>
  );
}
