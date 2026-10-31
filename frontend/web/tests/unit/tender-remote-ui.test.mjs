// 为什么有这个文件：确认招标上传页接受扫描件/.doc/Excel/图片，并把“RAGFlow 解析中”如实显示出来（AI-TENDER-DEEPDOC-PARSE）。
// 它解决什么问题：后台已能经 RAGFlow 识别这些格式，页面若仍只收 .docx/.pdf 或把解析中显示成“已上传”，用户会误判。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('tender upload accepts remote-parsed formats and shows the pending state', () => {
  const page = readFileSync(new URL('../../src/project/TenderTab.tsx', import.meta.url), 'utf8');
  assert.match(page, /accept="\.txt,\.md,\.docx,\.doc,\.pdf,\.xls,\.xlsx,\.png,\.jpg,\.jpeg"/);
  assert.match(page, /RAGFlow 解析中/);
  assert.match(page, /\['uploaded', 'failed', 'parsing_remote'\]\.includes\(item\.status\)/);
  const context = readFileSync(new URL('../../src/app/context.tsx', import.meta.url), 'utf8');
  assert.match(context, /ragflow_deepdoc_positions: '按 RAGFlow 版面识别/);
});
