// 为什么有这个文件：编辑台对话助手的自由提问（PRD v1.8 §5.11.3“未选中正文 → 只回答，不提供写入按钮；知识库打开时回答附引用”；APP-M2-T179）。
// 它解决什么问题：不选中文字时直接提问；问到本项目数据时显示答案卡；否则回答逐字出现，可停止；回答只能复制，不能写入正文；
// 显示引用的资料、改用备用模型或排队等待本地模型的提示。问答记入当前会话。

import { useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Input, Space, Tag } from 'antd';
import { CopyOutlined, SendOutlined } from '@ant-design/icons';
import { ApiError, streamEvents, userFacingMessage } from '../shared/api.ts';
import { isAbort } from './selection-rewrite-core.ts';
import { askPath, reduceAsk, EMPTY_ASK, type AskState } from './assistant-ask-core.ts';

type Props = {
  projectId: string; chapterId: string; token: string; knowledgeBase: boolean; sessionId: string | null; disabled: boolean;
  onAnswered: (sessionId: string | null) => void;
};

export function AssistantAskBox({ projectId, chapterId, token, knowledgeBase, sessionId, disabled, onAnswered }: Props) {
  const { message } = AntApp.useApp();
  const [question, setQuestion] = useState('');
  const [state, setState] = useState<AskState>(EMPTY_ASK);
  const abort = useRef<AbortController | null>(null);

  async function ask() {
    const text = question.trim();
    if (!text) return;
    const controller = new AbortController();
    abort.current = controller;
    setState({ ...EMPTY_ASK, working: true });
    try {
      await streamEvents(askPath(projectId, chapterId), token, {
        question: text, knowledge_base_enabled: knowledgeBase, ...(sessionId ? { session_id: sessionId } : {}),
      }, event => {
        if (event.event === 'error') throw new ApiError(Number(event.status) || 502, String(event.code), String(event.message));
        setState(current => reduceAsk(current, event));
        if (event.event === 'done') onAnswered(((event.answer as { session_id?: string }) ?? {}).session_id ?? null);
      }, controller.signal);
    } catch (error) {
      if (isAbort(error)) setState(current => ({ ...current, stopped: true }));
      else message.error(userFacingMessage(error));
    } finally {
      abort.current = null;
      setState(current => ({ ...current, working: false }));
    }
  }

  const answer = state.answer;
  return (
    <div data-testid="assistant-ask-box">
      <Input.TextArea rows={2} maxLength={1000} value={question} onChange={event => setQuestion(event.target.value)} aria-label="向对话助手提问"
        placeholder="不选中文字时可以直接提问，例如：巡检这一节应该写哪些要点？（回答只供参考，可复制）" disabled={disabled || state.working} />
      <Space style={{ marginTop: 8 }}>
        <Button size="small" type="primary" icon={<SendOutlined />} loading={state.working} disabled={disabled || !question.trim()}
          onClick={() => void ask()} data-testid="assistant-ask-btn">提问</Button>
        {state.working && <Button size="small" danger type="link" onClick={() => abort.current?.abort()} data-testid="assistant-ask-stop">停止</Button>}
      </Space>
      {state.queued && <Alert type="info" showIcon style={{ marginTop: 8 }} message={state.queued} />}
      {state.fallback && <Alert type="warning" showIcon style={{ marginTop: 8 }} message={state.fallback} data-testid="assistant-ask-fallback" />}
      {state.stopped && <Alert type="info" showIcon style={{ marginTop: 8 }} message="已停止，本次回答不保存。" />}
      {state.notice && <Alert type="info" showIcon style={{ marginTop: 8 }} message={state.notice} />}
      {(state.draft || answer?.answer) && (
        <Card size="small" style={{ marginTop: 8 }} data-testid="assistant-answer"
          title={<Space><Tag>只供参考</Tag>{answer?.model && <span className="muted">{answer.model}{answer.is_fallback ? '（备用模型）' : ''}</span>}</Space>}
          extra={answer?.answer && (
            <Button size="small" type="link" icon={<CopyOutlined />}
              onClick={() => void navigator.clipboard.writeText(answer.answer ?? '').then(() => message.success('已复制'))}>复制</Button>
          )}>
          <p className="suggestion-content" style={{ whiteSpace: 'pre-wrap' }}>{answer?.answer ?? state.draft}</p>
          {(answer?.warnings ?? []).map(text => <Alert key={text} type="warning" showIcon message={text} style={{ marginBottom: 6 }} />)}
          {answer && (answer.sources?.length ? (
            <ul className="rewrite-sources">{answer.sources.map(src => <li key={src.cite_tag}><Tag>{src.cite_tag}</Tag>{src.name}（v{src.revision}）</li>)}</ul>
          ) : <p className="muted">无知识库来源</p>)}
        </Card>
      )}
      {answer?.answer_card && (
        <Card size="small" style={{ marginTop: 8 }} title={answer.answer_card.title} data-testid="assistant-answer-card">
          {answer.answer_card.notice && <p className="muted">{answer.answer_card.notice}</p>}
          <ul>{answer.answer_card.records.slice(0, 10).map((record, index) => (
            <li key={index}>{Object.entries(record).filter(([key]) => !key.endsWith('_id') && key !== 'id').slice(0, 4).map(([, value]) => String(value)).join(' · ')}</li>
          ))}</ul>
        </Card>
      )}
    </div>
  );
}
