// 为什么有这个文件：验证恢复历史文字时不会覆盖核对期间发生的新修改。
// 它解决什么问题：恢复旧草稿要转成当前正文版本的新草稿，并保持递增保存顺序。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { recoveryWrite } from '../../frontend/web/src/editor-recovery.ts';

test('旧草稿核对后变成新正文版本的个人草稿，不改正式正文', () => {
  const snapshot = { id: 'chapter-a', revision: 4, draft: { base_revision: 2, sequence: 6, content: '旧文字' } };
  assert.deepEqual(recoveryWrite(snapshot, structuredClone(snapshot), '人工核对的旧文字'), {
    base_revision: 4, sequence: 7, content: '人工核对的旧文字',
  });
  assert.equal(snapshot.revision, 4);
  assert.equal(snapshot.draft.base_revision, 2);
});

test('新正文、不同章节或其他新草稿出现时拒绝恢复', () => {
  const snapshot = { id: 'chapter-a', revision: 4, draft: { base_revision: 2, sequence: 6, content: '旧文字' } };
  for (const latest of [
    { ...snapshot, revision: 5 }, { ...snapshot, id: 'chapter-b' },
    { ...snapshot, draft: { ...snapshot.draft, sequence: 7 } },
    { ...snapshot, draft: { ...snapshot.draft, content: '别人更新的草稿' } },
    { ...snapshot, draft: null },
  ]) assert.throws(() => recoveryWrite(snapshot, latest, '旧文字'), /已变化/);
});

test('历史版本可从没有草稿的当前版本开始保存', () => {
  const snapshot = { id: 'chapter-a', revision: 3, draft: null };
  assert.deepEqual(recoveryWrite(snapshot, snapshot, '历史正文'), { base_revision: 3, sequence: 1, content: '历史正文' });
});
