// 为什么有这个文件：提取编辑台右侧助手面板组件（EditorAssistantPanel）。
// 它解决什么问题：解耦对话助手、整章候选建议、合规问题提示与写作来源面板，降低 EditorPage 行数。

import React from 'react';
import { Alert, Button, Card, Empty, Input, Space, Tabs } from 'antd';
import { SendOutlined } from '@ant-design/icons';
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
}: EditorAssistantPanelProps) {
  return (
    <aside className="editor-right">
      <Tabs
        size="small"
        activeKey={rightTab}
        onChange={setRightTab}
        items={[
          { key: 'assistant', label: '对话助手' },
          { key: 'issues', label: '问题' },
          { key: 'sources', label: '写作来源' },
        ]}
      />
      <div className="assistant-scroll">
        {rightTab === 'assistant' && (
          <>
            <div className="model-label">
              <AiTag variant={candidate?.is_real_model ? 'model' : 'demo'} />
              <span>整章候选 · 人工确认后才写入</span>
            </div>
            {workspace.project.sensitive && <Alert type="info" message="敏感项目 · 只使用本地服务" />}
            <Card size="small" className="instruction-card">
              <span className="muted">当前章节 · {chapter?.title}</span>
              <p>{instruction}</p>
            </Card>
            {candidate ? (
              <Card
                size="small"
                className="suggestion-card"
                title={
                  <Space wrap>
                    <AiTag variant="candidate" />
                    <span>基于 v{candidate.base_revision}</span>
                  </Space>
                }
              >
                {candidateIssue && (
                  <Alert
                    type="warning"
                    showIcon
                    message="候选已失效，暂不能写入"
                    description={candidateIssue}
                    className="page-notice"
                  />
                )}
                <p className="suggestion-content">{candidate.content}</p>
                <Alert
                  type="info"
                  showIcon
                  message={candidate.is_real_model ? '模型建议仍须人工核对' : '当前为演示建议，不代表真实模型已接入'}
                />
                <p className="muted">先核对当次输入，再比较整章内容；写入后仍需提交本节。</p>
                <p className="muted">已校验输入状态、变量和单位；完整事实语义、段落来源和选区预检仍待完成。</p>
                <Space wrap>
                  <Button size="small" onClick={onViewInput}>
                    查看当次输入来源
                  </Button>
                  <Button
                    type="primary"
                    size="small"
                    disabled={combinedBusy || !held || !chapter || !!candidateIssue}
                    onClick={() => onShowDiff(candidate)}
                  >
                    查看差异并确认写入
                  </Button>
                </Space>
              </Card>
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="先确认写作方案，生成整章候选或取得整章修改建议"
              />
            )}
          </>
        )}
        {rightTab === 'sources' && <WritingSources key={chapterId} chapterId={chapterId} candidate={candidate} />}
        {rightTab === 'issues' && (
          <>
            {workspace.checks[workspace.checks.length - 1]?.issues
              .filter(item => item.chapter_id === chapterId)
              .map(item => (
                <Alert
                  key={item.id}
                  className="page-notice"
                  type={item.severity === 'warning' ? 'warning' : 'error'}
                  message={`${item.code} · ${item.message}`}
                />
              )) ?? <Empty description="请提交正文后运行检查" />}
            <Alert type="info" message="问题依据当前检查批次；未提交内容尚未检查" />
          </>
        )}
      </div>
      {rightTab === 'assistant' && (
        <div className="assistant-input">
          <div className="prompt-chips">
            {['改写', '扩写', '缩写', '按指令修改', '换一种说法'].map(text => (
              <button
                key={text}
                onClick={() =>
                  setInstruction(`${text}当前章节，依据已核对原文与事实，不新增未经证实的承诺。`)
                }
              >
                {text}
              </button>
            ))}
          </div>
          <Input.TextArea
            aria-label="给助手的修改要求"
            placeholder="针对已提交正文输入整章修改要求"
            rows={3}
            maxLength={2000}
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            disabled={combinedBusy || !canEdit}
          />
          <div className="assistant-send">
            <span className="muted">整章建议 · 选区助手待实现</span>
            <Button
              size="small"
              type="primary"
              icon={<SendOutlined />}
              disabled={combinedBusy || !canGenerate || !chapter || !planCurrent || !instruction.trim() || modified}
              onClick={onSuggest}
            >
              发送
            </Button>
          </div>
          {modified && <span className="muted">先提交本节，再基于已提交正文请求建议</span>}
          {!planCurrent && <span className="muted">先由本节编写人或负责人确认本节方案，再请求整章建议</span>}
        </div>
      )}
    </aside>
  );
}
