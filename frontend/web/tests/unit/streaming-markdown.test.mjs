// 为什么有这个文件：流式 Markdown 中间态必须先收敛成安全块，不能把半个符号裸露给用户。
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  growthFrontierLine,
  parseStreamingInline,
  parseStreamingMarkdown,
  parseStreamingMarkdownTracked,
  blockIndexAtLine,
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

test('single-column tables never expose raw pipes while streaming', () => {
  // 半截单列表头（还没有收尾管道）也不能裸露源码。
  assert.deepEqual(parseStreamingMarkdown('| 响应情况').map(block => block.type), ['table-placeholder']);
  // 完整单列表头在分隔行到达前保持占位。
  assert.deepEqual(parseStreamingMarkdown('| 响应情况 |').map(block => block.type), ['table-placeholder']);
  // 单竖线是表格最开始的第一个字符，同样先占位不裸露。
  assert.deepEqual(parseStreamingMarkdown('|').map(block => block.type), ['table-placeholder']);
  // 单列分隔行到达后展开为正式单列表格，与最终 paper-markdown 口径一致。
  const complete = parseStreamingMarkdown('| 响应情况 |\n| --- |\n| 满足 |\n');
  const table = complete.find(block => block.type === 'table');
  assert.deepEqual(table.header, ['响应情况']);
  assert.deepEqual(table.rows, [['满足']]);
  // 多列表头的半截行 `| 项目 |` 同样不裸露。
  assert.deepEqual(parseStreamingMarkdown('| 项目 |').map(block => block.type), ['table-placeholder']);
});

test('dashes without pipes are not mistaken for a table rule', () => {
  const blocks = parseStreamingMarkdown('---\n');
  assert.equal(blocks[0].type, 'paragraph');
});

test('growth frontier tracks mid-document writing instead of the document end', () => {
  // 靠前章节在中部生长：前沿落在插入文本末尾的行，而不是全篇末尾。
  const before = '1.1 巡检\n正在写第一\n\n1.2 主机\n已有正文\n';
  const after = '1.1 巡检\n正在写第一\n接着第二句\n\n1.2 主机\n已有正文\n';
  assert.equal(growthFrontierLine(before, after), 2);
  // 纯追加到末尾时前沿就是最后一行。
  assert.equal(growthFrontierLine('abc', 'abc新字'), 0);
  // 无变化与纯收缩都不算增长。
  assert.equal(growthFrontierLine('abc', 'abc'), null);
  assert.equal(growthFrontierLine('abcdef', 'abc'), null);
});

test('block lookup maps a source line back to the block that owns it', () => {
  const { blockLines } = parseStreamingMarkdownTracked('标题一\n\n正文段落\n');
  assert.deepEqual(blockLines, [0, 1, 2, 3]);
  assert.equal(blockIndexAtLine(blockLines, 2), 2);
  assert.equal(blockIndexAtLine(blockLines, 1), 1);
  assert.equal(blockIndexAtLine(blockLines, 0), 0);
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

test('table formation never flickers back to placeholder while the rule row grows', () => {
  const target = '| 项目 | 响应 |\n| --- | --- |\n| 巡检 | 满足 |';
  let formed = false;
  for (let size = 1; size <= target.length; size += 1) {
    const blocks = parseStreamingMarkdown(target.slice(0, size));
    const hasTable = blocks.some(block => block.type === 'table');
    if (hasTable) formed = true;
    if (formed) {
      const backToPlaceholder = blocks.some(block => block.type === 'table-placeholder');
      assert.equal(backToPlaceholder, false, `table must not revert to placeholder at length ${size}`);
    }
  }
  assert.equal(formed, true);
});

