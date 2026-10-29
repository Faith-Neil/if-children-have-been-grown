// 为什么有这个文件：验证编辑台选区改写的前端计算（APP-M2-T178/T185/T187）。
// 它解决什么问题：选区要能对上已提交正文；写入预览与后端规则一致；差异按字标出增删；后端“位置已变化”能取出新位置。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ApiError } from '../../src/shared/api.ts';
import {
  REWRITE_MODES, diffText, locateSelection, pendingCount, previewWrite, relocation, rewritePath, selectionProblem,
} from '../../src/editor/selection-rewrite-core.ts';

const BODY = '技术正文验收标记：每月安排巡检，报告由负责人复核。\n第二段：故障响应。';

test('selection maps to committed text by offsets, or by a unique match when offsets are unknown', () => {
  const start = BODY.indexOf('每月安排巡检');
  assert.deepEqual(locateSelection(BODY, '每月安排巡检', start, start + 6), { start, end: start + 6, text: '每月安排巡检' });
  assert.deepEqual(locateSelection(BODY, '每月安排巡检'), { start, end: start + 6, text: '每月安排巡检' });
  assert.equal(locateSelection(BODY + '每月安排巡检', '每月安排巡检'), null, 'ambiguous without offsets');
  assert.equal(locateSelection(BODY, '   '), null);
  assert.equal(locateSelection(BODY, 'x'.repeat(2001)), null);
});

test('selection problems: uncommitted edits, empty and ambiguous selections are explained', () => {
  assert.match(selectionProblem(BODY, BODY + '改', '每月安排巡检'), /先提交本节/);
  assert.match(selectionProblem(BODY, BODY, ''), /先在正文中选中/);
  assert.match(selectionProblem(BODY + '每月安排巡检', BODY + '每月安排巡检', '每月安排巡检'), /出现多处/);
  assert.equal(selectionProblem(BODY, BODY, '每月安排巡检'), null);
});

test('write preview mirrors the backend: replace in place, insert inside or as a new paragraph', () => {
  const start = BODY.indexOf('每月安排巡检'), end = start + 6;
  assert.equal(previewWrite(BODY, start, end, '每月开展例行巡检', 'replace'), BODY.replace('每月安排巡检', '每月开展例行巡检'));
  assert.equal(previewWrite(BODY, start, end, '（含夜间）', 'insert_after'), BODY.replace('每月安排巡检', '每月安排巡检（含夜间）'));
  const tail = BODY.indexOf('报告由负责人复核。'), tailEnd = tail + '报告由负责人复核。'.length;
  assert.equal(previewWrite(BODY, tail, tailEnd, '新增一段。', 'insert_after'),
    '技术正文验收标记：每月安排巡检，报告由负责人复核。\n新增一段。\n第二段：故障响应。');
  assert.equal(previewWrite(BODY, start, end, '甲\n乙', 'insert_after').split('\n')[1], '甲');
});

test('character diff marks removed and added text and keeps common parts', () => {
  const parts = diffText('每月安排巡检', '每月开展例行巡检');
  assert.equal(parts.filter(p => p.kind !== 'added').map(p => p.text).join(''), '每月安排巡检');
  assert.equal(parts.filter(p => p.kind !== 'removed').map(p => p.text).join(''), '每月开展例行巡检');
  assert.ok(parts.some(p => p.kind === 'removed') && parts.some(p => p.kind === 'added'));
  assert.deepEqual(diffText('相同', '相同'), [{ kind: 'same', text: '相同' }]);
  const big = diffText('a'.repeat(600) + 'X', 'b'.repeat(600) + 'Y');
  assert.equal(big.filter(p => p.kind === 'removed').map(p => p.text).join(''), 'a'.repeat(600) + 'X');
});

test('pending placeholders are counted and relocation details are read from the 409 error', () => {
  assert.equal(pendingCount('配备【待补：数值来源】名工程师，【待补】'), 2);
  const moved = new ApiError(409, 'REVISION_CONFLICT', 'moved', undefined, { relocated: true, start: 8, end: 14, revision: 5 });
  assert.deepEqual(relocation(moved), { relocated: true, start: 8, end: 14 });
  assert.deepEqual(relocation(new ApiError(409, 'REVISION_CONFLICT', 'gone', undefined, { relocated: false })), { relocated: false });
  assert.equal(relocation(new ApiError(409, 'VERSION_CONFLICT', 'x')), null);
  assert.equal(rewritePath('p1', 'c1'), '/api/v1/projects/p1/chapters/c1/selection-rewrites');
  assert.equal(rewritePath('p1', 'c1', 'b1'), '/api/v1/projects/p1/chapters/c1/selection-rewrites/b1/apply');
  assert.deepEqual(REWRITE_MODES.map(m => m.label), ['改写', '扩写', '缩写', '按指令修改', '换一种说法']);
});

test('the editor wires the bubble to the selection rewrite panel instead of a whole-chapter instruction', () => {
  const page = readFileSync(new URL('../../src/editor/EditorPage.tsx', import.meta.url), 'utf8');
  const bubble = readFileSync(new URL('../../src/editor/SelectionBubble.tsx', import.meta.url), 'utf8');
  const panel = readFileSync(new URL('../../src/editor/EditorAssistantPanel.tsx', import.meta.url), 'utf8');
  assert.match(page, /<SelectionRewritePanel/);
  assert.doesNotMatch(page, /进行AI润色/);
  assert.match(bubble, /问对话助手/);
  assert.doesNotMatch(panel, /选区助手待实现/);
});

test('knowledge-base switch defaults follow company policy and connection state', async () => {
  const { defaultKnowledgeBase, knowledgeBaseNote, modelLabel } = await import('../../src/editor/selection-rewrite-core.ts');
  const base = { enabled: true, kb_default: true, allow_kb_off: true, count: 3, model: 'qwen-local', is_real_model: true, is_local_model: true, sensitive_project: false, knowledge_base_connected: true };
  assert.equal(defaultKnowledgeBase(base), true);
  assert.equal(defaultKnowledgeBase({ ...base, knowledge_base_connected: false }), false, 'unconnected and may turn off → off');
  assert.equal(defaultKnowledgeBase({ ...base, knowledge_base_connected: false, allow_kb_off: false }), true, 'company forbids turning off');
  assert.equal(defaultKnowledgeBase({ ...base, kb_default: false }), false);
  assert.equal(defaultKnowledgeBase(null), false);
  assert.match(knowledgeBaseNote({ ...base, allow_kb_off: false }, true), /不能关闭/);
  assert.match(knowledgeBaseNote(base, false), /无知识库来源/);
  assert.match(knowledgeBaseNote({ ...base, knowledge_base_connected: false }, true), /尚未连接/);
  assert.equal(modelLabel(base), 'qwen-local · 本地模型');
  assert.equal(modelLabel({ ...base, is_real_model: false }), '尚未接入真实模型');
});

test('stream events accumulate samples and drops in arrival order', async () => {
  const { EMPTY_STREAM, reduceStream, assistantPaths } = await import('../../src/editor/selection-rewrite-core.ts');
  let state = reduceStream(EMPTY_STREAM, { event: 'started', styles: ['严谨规范', '简洁精炼'], retrieval: { status: 'off', message: '' } });
  state = reduceStream(state, { event: 'sample', sample: { id: 's2', style_label: '简洁精炼' } });
  state = reduceStream(state, { event: 'dropped', style: '严谨规范', reason: '与原文相同' });
  assert.deepEqual(state.styles, ['严谨规范', '简洁精炼']);
  assert.deepEqual(state.samples.map(s => s.id), ['s2']);
  assert.deepEqual(state.dropped, [{ style: '严谨规范', reason: '与原文相同' }]);
  assert.equal(reduceStream(state, { event: 'done' }), state);
  const paths = assistantPaths('p', 'c');
  assert.equal(paths.stream, '/api/v1/projects/p/chapters/c/selection-rewrites/stream');
  assert.equal(paths.session('s1'), '/api/v1/projects/p/assistant-sessions/s1');
});
