// 为什么有这个文件：自由提问事件流的合并规则（PRD v1.8 §5.11.3；APP-M2-T179）。
// 它解决什么问题：delta 逐字拼成预览；fallback 清空预览并提示“已使用备用模型”；queued 提示排队等本地模型；
// done 换成最终回答（或答案卡、无检索结果的提示）。

export type AskSource = { cite_tag: string; name: string; revision: number };
export type AskAnswer = {
  id: string; session_id?: string | null; route: 'model' | 'direct_query' | 'no_results'; answer: string | null;
  answer_card?: { title: string; notice?: string | null; records: Record<string, unknown>[] } | null;
  message?: string; warnings?: string[]; sources?: AskSource[]; model?: string; is_fallback?: boolean; can_insert: false;
};
export type AskState = { working: boolean; draft: string; fallback: string; queued: string; notice: string; stopped: boolean; answer: AskAnswer | null };

export const EMPTY_ASK: AskState = { working: false, draft: '', fallback: '', queued: '', notice: '', stopped: false, answer: null };

export const askPath = (projectId: string, chapterId: string) =>
  `/api/v1/projects/${encodeURIComponent(projectId)}/chapters/${encodeURIComponent(chapterId)}/assistant-questions/stream`;

export function reduceAsk(state: AskState, event: Record<string, unknown>): AskState {
  switch (event.event) {
    case 'started': {
      const retrieval = event.retrieval as { status?: string; message?: string } | undefined;
      return { ...state, notice: retrieval?.status === 'off' ? String(retrieval.message ?? '') : '' };
    }
    case 'delta':
      return { ...state, draft: state.draft + String(event.text ?? ''), queued: '' };
    case 'fallback':
      return { ...state, draft: '', fallback: `已使用备用模型 ${String(event.model)}（${String(event.reason)}）` };
    case 'queued':
      return { ...state, queued: String(event.message ?? '本地模型排队中') };
    case 'done': {
      const answer = event.answer as AskAnswer;
      return { ...state, answer, draft: '', queued: '', notice: answer.route === 'no_results' ? String(answer.message ?? '') : state.notice };
    }
    default:
      return state;
  }
}
