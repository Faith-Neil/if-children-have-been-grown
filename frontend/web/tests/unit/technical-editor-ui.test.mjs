// 为什么有这个文件：核对技术分册目录节状态与选区包装。
import assert from 'node:assert/strict';
import test from 'node:test';
import { sectionBody, sectionStatus, wrapTextareaSelection } from '../../src/editor/technical-editor-ui.ts';

const content = `1 总体\n\n1.1 巡检\n待补\n1.2 主机\n完整段落需要核对\n`;

test('derives section statuses', () => {
  assert.equal(sectionStatus({ content, number: '1.1', title: '巡检', requirementId: 'r1' }), '待补');
  assert.equal(sectionStatus({ content, number: '1.2', title: '主机', requirementId: 'r2', reviewTitles: ['主机'] }), '需核对');
  assert.equal(sectionStatus({ content: '', number: '1.1', title: '巡检', requirementId: 'r1' }), '未生成');
  assert.equal(sectionStatus({ content, number: '1.2', title: '主机', requirementId: 'r2', generating: true }), '生成中');
});

test('reads section body and wraps selection', () => {
  assert.equal(sectionBody(content, '1.1', '巡检'), '待补');
  const next = wrapTextareaSelection('ab', 0, 2, '**', '**');
  assert.equal(next.value, '**ab**');
});
