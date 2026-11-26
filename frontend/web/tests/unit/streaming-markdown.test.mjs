// 为什么有这个文件：流式 Markdown 中间态必须先收敛成安全块，不能把半个符号裸露给用户。
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  parseStreamingInline,
  parseStreamingMarkdown,
  stableInlineChunks,
} from '../../src/editor/streaming-markdown.ts';
import { streamingStageLabel } from '../../src/editor/section-stream.ts';

test('unclosed bold and underline are safely closed without exposing markers', () => {
  assert.deepEqual(parseStreamingInline('普通**加粗一半'), [
    { text: '普通' },
    { text: '加粗一半', bold: true },
  ]);
  assert.deepEqual(parseStreamingInline('普通<u>下划线一半'), [
    { text: '普通' },
    { text: '下划线一半', underline: true },
  ]);
  assert.deepEqual(parseStreamingInline('普通**加粗**恢复'), [
    { text: '普通' },
    { text: '加粗', bold: true },
    { text: '恢复' },
  ]);
});

test('trailing half markers and isolated heading hashes are hidden', () => {
  assert.deepEqual(parseStreamingInline('正文*'), [{ text: '正文' }]);
  assert.deepEqual(parseStreamingInline('正文<u'), [{ text: '正文' }]);
  assert.deepEqual(parseStreamingMarkdown('第一段\n#\n## \n'), [
    { id: 'stream-block-0', type: 'paragraph', nodes: [{ text: '第一段' }] },
    { id: 'stream-block-1', type: 'blank' },
  ]);
});

test('first table row becomes a soft placeholder until the delimiter arrives', () => {
  const partial = parseStreamingMarkdown('| 项目 | 响应 |');
  assert.equal(partial.at(-1).type, 'table-placeholder');
  const partialRule = parseStreamingMarkdown('| 项目 | 响应 |\n| -');
  assert.deepEqual(partialRule.map(block => block.type), ['table-placeholder']);
  const complete = parseStreamingMarkdown('| 项目 | 响应 |\n| --- | --- |\n| 巡检 | 满足 |\n');
  const table = complete.find(block => block.type === 'table');
  assert.deepEqual(table.header, ['项目', '响应']);
  assert.deepEqual(table.rows, [['巡检', '满足']]);
});

test('stable inline chunk keys do not change when the active tail grows', () => {
  const before = stableInlineChunks(parseStreamingInline('abcdefghij'), 'block-1', 4);
  const after = stableInlineChunks(parseStreamingInline('abcdefghijkl'), 'block-1', 4);
  assert.deepEqual(before.map(item => item.key), after.slice(0, before.length).map(item => item.key));
  assert.equal(after.at(-1).text, 'ijkl');
});

test('stage labels use plain user-facing copy', () => {
  assert.equal(streamingStageLabel('retrieve'), '正在检索招标与知识库资料…');
  assert.equal(streamingStageLabel('deviate'), '正在核对偏离要求…');
  assert.equal(streamingStageLabel('write_section'), '正在撰写本节正文…');
});
