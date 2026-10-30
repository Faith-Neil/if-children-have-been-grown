// 为什么有这个文件：验证编辑台按行找到段落键与来源（APP-M2-T161）。
// 它解决什么问题：表格等多行块的每一行都归到同一段落键；只有段落首行、且不是人工写的段落才标来源；本地改过正文后不再套用旧行号。
import test from 'node:test';
import assert from 'node:assert/strict';
import { lineParagraphs, paragraphsMatch, showsSource } from '../../src/editor/paragraph-keys.ts';

const paragraphs = [
  { key: 'pk-a', kind: 'heading', level: 1, line_start: 0, line_end: 0, hash: 'h1', source: 'manual', source_label: '人工编写' },
  { key: 'pk-b', kind: 'table', level: 0, line_start: 2, line_end: 4, hash: 'h2', source: 'system', source_label: '系统生成' },
  { key: 'pk-c', kind: 'para', level: 0, line_start: 6, line_end: 6, hash: 'h3', source: 'assistant', source_label: '对话助手写入' },
];

test('every line of a multi-line block maps to one paragraph key', () => {
  const map = lineParagraphs(paragraphs);
  assert.equal(map.get(3).key, 'pk-b');
  assert.equal(map.get(4).first, false);
  assert.equal(map.has(1), false);
});

test('only the first line of non-manual paragraphs shows a source tag', () => {
  const map = lineParagraphs(paragraphs);
  assert.equal(showsSource(map.get(0)), false);
  assert.equal(showsSource(map.get(2)), true);
  assert.equal(showsSource(map.get(3)), false);
  assert.equal(showsSource(map.get(6)), true);
  assert.equal(showsSource(undefined), false);
});

test('keys are used only while the text matches the committed version', () => {
  assert.equal(paragraphsMatch(paragraphs, 'a', 'a'), true);
  assert.equal(paragraphsMatch(paragraphs, 'a（本地改过）', 'a'), false);
  assert.equal(paragraphsMatch([], 'a', 'a'), false);
});
