// 为什么有这个文件：验证章节循环进度页与轮次时间线（APP-M2-T130 / T131）的文案与排序逻辑。
// 它解决什么问题：停在哪、谁修了哪段、依据和版本、前章摘要缺失都要如实显示，旧记录没有依据时明说未记录。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  interruptionText, loopStatus, metaLines, progressPercent, relayNotice, retryLabel, roundColor, roundSummary, timelineLoops,
} from '../../src/project/chapter-loop-core.ts';

const loop = (over = {}) => ({
  chapter_id: 'c1', loop_no: 2, kind: 'recheck', status: 'pending_human', status_label: '待人工处理',
  stop_reason: 'NEED_HUMAN', stop_reason_label: '剩余问题需人工处理', max_rounds: 3, rolled_back: false,
  started_at: '2026-10-28T08:00:00Z', stale: false, loop_count: 2, rounds: [], ...over,
});

test('status tag distinguishes not generated, unchecked, stale, completed and pending', () => {
  assert.equal(loopStatus({ loop: null, has_content: false }).label, '未生成');
  assert.equal(loopStatus({ loop: null, has_content: true }).label, '未检查');
  assert.equal(loopStatus({ loop: loop({ stale: true }), has_content: true }).label, '正文已改动，待复查');
  assert.equal(loopStatus({ loop: loop({ status: 'completed' }), has_content: true }).color, 'green');
  assert.equal(loopStatus({ loop: loop(), has_content: true }).label, '待人工处理');
});

test('round summary names who fixed which paragraph', () => {
  const round = { round: 1, found: 3, new: 0, resolved: 0, modified_paragraphs: [0, 2], conclusion: '继续修正',
    fixes: [{ paragraph_index: 0, by: 'model', codes: ['A'] }, { paragraph_index: 2, by: 'rule', codes: ['B'] }] };
  assert.equal(roundSummary(round), '查出 3 项 · 模型修正 1 段、规则修正 1 段（第 1、3 段）');
  assert.equal(roundSummary({ round: 2, found: 1, new: 1, resolved: 2, modified_paragraphs: [], conclusion: '' }), '查出 1 项 · 解决 2 项 · 新出现 1 项');
  assert.equal(roundColor(round, true, { stop_reason: 'FIX_REGRESSION', rolled_back: true }), 'red');
  assert.equal(roundColor(round, true, { stop_reason: 'ALL_RESOLVED', rolled_back: false }), 'green');
  assert.equal(roundColor(round, false, { stop_reason: 'ALL_RESOLVED', rolled_back: false }), 'blue');
});

test('meta lines show task, model, inputs and version; old loops say nothing was recorded', () => {
  const lines = metaLines({ task_label: '章节生成', model: 'openai-compatible', model_name: 'qwen3', is_real_model: true,
    fixer: '模型修正', base_revision: 3, inputs: { requirements: 4, evidence: 2, snippets: 5, facts: 6, critical: true } },
    { checked_revision: 3, result_revision: 4 });
  const byLabel = Object.fromEntries(lines.map(line => [line.label, line.value]));
  assert.equal(byLabel['模型'], 'openai-compatible（qwen3）');
  assert.equal(byLabel['实际输入'], '条款 4 · 已挂证据 2 · 知识库切片 5 · 已确认事实 6 · 含★/废标条款');
  assert.equal(byLabel['版本'], 'v3 → v4');
  assert.equal(metaLines({ task: 'recheck', model: null, base_revision: 5 }, { result_revision: 5 }).find(l => l.label === '版本').value, 'v5（正文未改）');
  assert.match(metaLines(undefined, {})[0].value, /未记录/);
  assert.match(metaLines({ model: 'demo', is_real_model: false }, {}).find(l => l.label === '模型').value, /非真实模型/);
});

test('summary relay: missing previous chapter is a warning, first chapter is info', () => {
  assert.equal(relayNotice({ summary_relay: { status: 'missing', title: '总体方案', message: '前章《总体方案》还没有正文' } }).type, 'warning');
  assert.equal(relayNotice({ summary_relay: { status: 'used', title: '总体方案', summary: '我司驻场' } }).text, '已接力前章《总体方案》摘要：我司驻场');
  assert.equal(relayNotice({ summary_relay: { status: 'not_applicable' } }).type, 'info');
  assert.equal(relayNotice({}), null);
});

test('timeline puts the current loop first, then history newest first', () => {
  const items = timelineLoops({ loop: loop({ loop_no: 3 }), history: [
    { loop_no: 1, kind: 'generation_candidate', stop_reason: 'MAX_ROUNDS', rounds: [], rolled_back: false, started_at: 'a' },
    { loop_no: 2, kind: 'recheck', stop_reason: 'NEED_HUMAN', stop_reason_label: '剩余问题需人工处理', rounds: [], rolled_back: false, started_at: 'b' },
  ] });
  assert.deepEqual(items.map(item => [item.loop_no, item.current]), [[3, true], [2, false], [1, false]]);
  assert.equal(items[2].kind_label, '生成后循环');
  assert.equal(items[2].stop_reason_label, 'MAX_ROUNDS');
  assert.deepEqual(timelineLoops({ loop: null, history: [] }), []);
});

test('progress counts completed and human-handled chapters', () => {
  assert.equal(progressPercent({ chapters: 4, completed: 1, human_handled: 1, pending_human: 1, not_started: 1, stale: 0 }), 50);
  assert.equal(progressPercent(undefined), 0);
});

test('page shows retry on failure, empty states and gates recheck by can_recheck', () => {
  const page = readFileSync(new URL('../../src/project/ChapterLoopPage.tsx', import.meta.url), 'utf8');
  assert.match(page, /重试/);
  assert.match(page, /本节还没有运行过章节循环/);
  assert.match(page, /!row\.can_recheck/);
  const queue = readFileSync(new URL('../../src/project/ManualQueuePage.tsx', import.meta.url), 'utf8');
  assert.match(queue, /章节循环进度/);
});

test('interrupted loop shows red tag, error text and a retry button label', () => {
  const interrupted = loop({ status: 'interrupted', stop_reason: 'INTERRUPTED', stop_reason_label: '异常中断',
    meta: { error: { code: 'LOOP_INTERRUPTED', type: 'RuntimeError', message: 'timeout' }, retry_count: 0 } });
  assert.deepEqual(loopStatus({ loop: interrupted, has_content: true }), { color: 'red', label: '异常中断' });
  assert.equal(retryLabel(interrupted), '重试');
  assert.equal(retryLabel(loop()), '重新检查');
  assert.equal(retryLabel(null), '重新检查');
  assert.match(interruptionText(interrupted), /timeout.*正文未改动.*重试/);
  assert.doesNotMatch(interruptionText(interrupted), /已重试/);
  const again = { ...interrupted, meta: { ...interrupted.meta, retry_count: 2 } };
  assert.match(interruptionText(again), /已重试 2 次/);
  assert.equal(interruptionText(loop()), null);
  const lines = metaLines(interrupted.meta, interrupted);
  assert.ok(lines.some(line => line.label === '中断原因' && line.value === 'RuntimeError：timeout'));
});

test('timeline keeps an interrupted loop entry with its stop label', () => {
  const entry = loop({ loop_no: 3, status: 'interrupted', stop_reason: 'INTERRUPTED', stop_reason_label: '异常中断' });
  const items = timelineLoops({ loop: entry, history: [] });
  assert.equal(items[0].stop_reason, 'INTERRUPTED');
  assert.equal(items[0].stop_reason_label, '异常中断');
});
