import test from 'node:test';
import assert from 'node:assert/strict';
import { docToMarkdown, markdownToDoc, sameMarkdown } from '../../src/editor/paper-markdown.ts';

const SAMPLE = [
  '# 第一章 总体方案',
  '## 1.1 服务体系',
  '本节**重点**说明安排。',
  '- 每月巡检',
  '- 提交报告',
  '1. 到场',
  '2. 复核',
  '| 序号 | 招标条款 |',
  '| --- | --- |',
  '| 1 | **满足** |',
  '',
  '表后正文。',
].join('\n');

test('纸面文档与 Markdown 往返后标题、加粗、列表和表格还在', () => {
  const markdown = docToMarkdown(markdownToDoc(SAMPLE));
  assert.equal(sameMarkdown(markdown, SAMPLE), true);
  assert.match(markdown, /^# 第一章/);
  assert.match(markdown, /\*\*重点\*\*/);
  assert.match(markdown, /^- 每月巡检/m);
  assert.match(markdown, /^1\. 到场/m);
  assert.match(markdown, /^\| 序号 \| 招标条款 \|/m);
});

test('下划线标签能回到编辑文档，序列化后仍是 u 标签', () => {
  const markdown = docToMarkdown(markdownToDoc('现场<u>驻场</u>服务'));
  assert.match(markdown, /<u>驻场<\/u>/);
});
