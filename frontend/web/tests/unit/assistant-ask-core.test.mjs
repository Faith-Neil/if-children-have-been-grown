// 为什么有这个文件：验证自由提问事件合并（PRD v1.8 §5.11.3；APP-M2-T179）。
// 它解决什么问题：逐字预览、备用模型提示清空预览、排队提示、最终回答只能复制（can_insert 为 false）。
import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY_ASK, askPath, reduceAsk } from '../../src/editor/assistant-ask-core.ts';

test('ask stream reducer', () => {
  let s = reduceAsk(EMPTY_ASK, { event: 'started', retrieval: { status: 'off', message: '知识库已关闭，未查询本公司资料库。' } });
  assert.equal(s.notice, '知识库已关闭，未查询本公司资料库。');
  s = reduceAsk(s, { event: 'queued', message: '本地模型暂时不可用，5 秒后重试' });
  assert.match(s.queued, /5 秒后重试/);
  s = reduceAsk(s, { event: 'delta', text: '建议' });
  s = reduceAsk(s, { event: 'delta', text: '写明范围' });
  assert.equal(s.draft, '建议写明范围');
  assert.equal(s.queued, '');
  s = reduceAsk(s, { event: 'fallback', model: 'qwen-b', reason: '主模型超时' });
  assert.equal(s.draft, '');
  assert.equal(s.fallback, '已使用备用模型 qwen-b（主模型超时）');
  s = reduceAsk(s, { event: 'done', answer: { id: 'a', route: 'model', answer: '建议写明范围。', can_insert: false } });
  assert.equal(s.answer.answer, '建议写明范围。');
  assert.equal(s.answer.can_insert, false);
  const none = reduceAsk(EMPTY_ASK, { event: 'done', answer: { id: 'b', route: 'no_results', answer: null, message: '没有找到相关内容', can_insert: false } });
  assert.equal(none.notice, '没有找到相关内容');
  assert.equal(askPath('p', 'c'), '/api/v1/projects/p/chapters/c/assistant-questions/stream');
});
