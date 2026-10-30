// 为什么有这个文件：验证粘贴识别提示文字（PRD v1.8 §5.11.7；APP-M2-T188）。
// 它解决什么问题：没有识别结果时不加提示；有结果时写明段落、重合比例和复查问题。
import test from 'node:test';
import assert from 'node:assert/strict';
import { pasteNotice } from '../../src/editor/paste-notice.ts';

test('paste notice', () => {
  assert.equal(pasteNotice(null), '');
  assert.equal(pasteNotice([]), '');
  const text = pasteNotice([{ paragraph_index: 1, match_ratio: 0.93, source_label: '对话助手撰写（粘贴）', text: 'x',
    issues: [{ rule_id: 'R30', severity: 'warning', message: '改动段落含项目事实与本章条款中没有的数值：5 名' }] }]);
  assert.match(text, /第 2 段（重合 93%）/);
  assert.match(text, /复查发现 1 个问题：改动段落含项目事实与本章条款中没有的数值：5 名/);
});
