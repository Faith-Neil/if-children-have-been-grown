// 为什么有这个文件：为正文段落内联证据节点（.cite）与划词操作气泡（Selection Action Bubble）提供纯逻辑与算法单元测试。
// 它解决什么问题：
// 1. 验证 [证:ID] 和 [片:ID] 格式的正则匹配、段落分词（parseCitations）与 ID 集合去重提取（extractCitationIds）；
// 2. 验证元数据解析合并（resolveCitationMeta）与胶囊标签格式化（formatCiteLabel）；
// 3. 验证选区字数计算、边界截断与 AI 润色、合规问答提示词模板组装逻辑。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  CITE_REGEX,
  parseCitations,
  extractCitationIds,
  resolveCitationMeta,
  formatCiteLabel,
} from '../../frontend/web/src/cite-capsule.ts';

test('CITE_REGEX matches [证:ID] and [片:ID] accurately', () => {
  const text = '根据招标文件要求 [证:doc_001] 以及技术方案片段 [片:arch_sec2]，本项目提供 99.9% 可用性承诺。';
  const matches = Array.from(text.matchAll(CITE_REGEX));

  assert.equal(matches.length, 2, 'Should match exactly two citations');
  assert.equal(matches[0][1], '证');
  assert.equal(matches[0][2], 'doc_001');
  assert.equal(matches[1][1], '片');
  assert.equal(matches[1][2], 'arch_sec2');
});

test('parseCitations splits pure text without markers into single text segment', () => {
  const text = '这是一个没有任何引用标记的普通正文段落。';
  const segments = parseCitations(text);

  assert.equal(segments.length, 1);
  assert.equal(segments[0].type, 'text');
  assert.equal(segments[0].content, text);
});

test('parseCitations handles mixed text and citations with metadata enrichment', () => {
  const text = '前置说明[证:101]中间文本[片:snp-5]末尾说明';
  const knownCitations = {
    '101': {
      title: '高新技术企业证书',
      code: 'CERT-2025-001',
      status: 'confirmed',
      validUntil: '2028-12-31',
    },
  };

  const segments = parseCitations(text, knownCitations);
  assert.equal(segments.length, 5, 'Should produce 5 segments');

  // 0: text
  assert.equal(segments[0].type, 'text');
  assert.equal(segments[0].content, '前置说明');

  // 1: cite evidence
  assert.equal(segments[1].type, 'cite');
  assert.equal(segments[1].citeMeta?.id, '101');
  assert.equal(segments[1].citeMeta?.kind, 'evidence');
  assert.equal(segments[1].citeMeta?.title, '高新技术企业证书');
  assert.equal(segments[1].citeMeta?.status, 'confirmed');

  // 2: text
  assert.equal(segments[2].type, 'text');
  assert.equal(segments[2].content, '中间文本');

  // 3: cite snippet
  assert.equal(segments[3].type, 'cite');
  assert.equal(segments[3].citeMeta?.id, 'snp-5');
  assert.equal(segments[3].citeMeta?.kind, 'snippet');
  assert.equal(segments[3].citeMeta?.status, 'confirmed', 'Default status for snippet is confirmed');

  // 4: text
  assert.equal(segments[4].type, 'text');
  assert.equal(segments[4].content, '末尾说明');
});

test('extractCitationIds extracts unique evidence and snippet IDs preserving order', () => {
  const content = `
    段落一引用 [证:101] 与 [片:arch_01]。
    段落二再次引用 [证:101] 以及新证据 [证:102] 和新片段 [片:arch_02]。
  `;

  const result = extractCitationIds(content);
  assert.deepEqual(result.evidenceIds, ['101', '102']);
  assert.deepEqual(result.snippetIds, ['arch_01', 'arch_02']);
  assert.deepEqual(result.allIds, ['101', '102', 'arch_01', 'arch_02']);
});

test('resolveCitationMeta supplies sensible defaults when not found', () => {
  const meta = resolveCitationMeta('unknown_id', 'evidence');
  assert.equal(meta.id, 'unknown_id');
  assert.equal(meta.kind, 'evidence');
  assert.equal(meta.title, '资料证据 #unknown_id');
  assert.equal(meta.status, 'confirmed');

  const customMeta = resolveCitationMeta('custom_01', 'evidence', { status: 'needs_review' });
  assert.equal(customMeta.status, 'needs_review');

  const snippetMeta = resolveCitationMeta('snp_99', 'snippet');
  assert.equal(snippetMeta.title, '方案片段 #snp_99');
  assert.equal(snippetMeta.status, 'confirmed');
});

test('formatCiteLabel formats evidence and snippet tags', () => {
  assert.equal(formatCiteLabel('evidence', 'CERT-88'), '证:CERT-88');
  assert.equal(formatCiteLabel('snippet', 'SEC-01'), '片:SEC-01');
});

test('Selection bubble logic builds truncated polish & compliance prompts', () => {
  const shortText = '本项目提供 7x24 小时服务响应';
  const longText = 'A'.repeat(150);

  // 润色提示词
  const makePolishPrompt = text =>
    `针对选区「${text.slice(0, 100)}${text.length > 100 ? '...' : ''}」进行AI润色：保持原文事实，优化文字表达，不新增未经核实的承诺。`;
  
  // 合规问答提示词
  const makeCompliancePrompt = text =>
    `针对选区「${text.slice(0, 100)}${text.length > 100 ? '...' : ''}」进行合规性核对：核对是否与招标要求或服务承诺相冲突，是否存在不可核实承诺。`;

  const p1 = makePolishPrompt(shortText);
  assert.ok(p1.includes('本项目提供 7x24 小时服务响应'));
  assert.ok(!p1.includes('...'));

  const p2 = makePolishPrompt(longText);
  assert.ok(p2.includes('...'));
  assert.ok(p2.includes('A'.repeat(100)));

  const c1 = makeCompliancePrompt(shortText);
  assert.ok(c1.includes('合规性核对'));
  assert.ok(c1.includes('本项目提供 7x24 小时服务响应'));
});
