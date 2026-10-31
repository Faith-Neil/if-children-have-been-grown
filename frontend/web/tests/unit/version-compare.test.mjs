// 为什么有这个文件：验证版本逐段对比与修改方式标签（APP-M2-T175）。
// 它解决什么问题：按段落键对上两个版本，改动段落逐字标增删，新增与删除段落各在原位置列出；回退按钮在不该用时说明原因。
import test from 'node:test';
import assert from 'node:assert/strict';
import { changeSummary, compareVersions, rollbackBlocker, versionModeLabel } from '../../src/editor/version-compare.ts';

const p = (key, line) => ({ key, kind: 'para', level: 0, line_start: line, line_end: line, hash: key, source: 'manual', source_label: '人工编写' });
const older = { revision: 2, content: '甲段\n乙段原文\n丙段', actor_id: 'u', created_at: '', paragraphs: [p('a', 0), p('b', 1), p('c', 2)] };
const newer = { revision: 3, content: '甲段\n乙段改后原文\n丁段', actor_id: 'u', created_at: '', paragraphs: [p('a', 0), p('b', 1), p('d', 2)] };

test('paragraphs are matched by key: same, changed with char diff, added, removed', () => {
  const changes = compareVersions(older, newer);
  assert.deepEqual(changes.map(c => `${c.kind}:${c.key}`), ['same:a', 'changed:b', 'added:d', 'removed:c']);
  const changed = changes[1];
  assert.deepEqual(changed.parts.filter(x => x.kind === 'added').map(x => x.text), ['改后']);
  assert.equal(changeSummary(changes), '改动 1 段，新增 1 段，删除 1 段');
  assert.equal(changeSummary(compareVersions(older, older)), '两个版本正文相同');
});

test('removed paragraphs stay at their old place', () => {
  const middleGone = { ...older, revision: 4, content: '甲段\n丙段', paragraphs: [p('a', 0), p('c', 1)] };
  assert.deepEqual(compareVersions(older, middleGone).map(c => `${c.kind}:${c.key}`), ['same:a', 'removed:b', 'same:c']);
});

test('version mode labels and rollback blockers', () => {
  assert.equal(versionModeLabel({ ...older, edit_mode: 'assistant_replace' }), '对话助手替换');
  assert.equal(versionModeLabel({ ...older, edit_mode: 'rollback', rollback_from: 1 }), '版本回退（回到 v1）');
  assert.equal(versionModeLabel({ ...older, source: 'chapter_loop' }), '章节循环修正');
  assert.equal(versionModeLabel(older), '手改');
  assert.equal(rollbackBlocker({ held: true, isCurrent: false, dirty: false, system: false }), null);
  assert.match(rollbackBlocker({ held: false, isCurrent: false, dirty: false, system: false }), /编辑权/);
  assert.match(rollbackBlocker({ held: true, isCurrent: false, dirty: true, system: false }), /未提交/);
  assert.match(rollbackBlocker({ held: true, isCurrent: false, dirty: false, system: true }), /系统生成/);
});
