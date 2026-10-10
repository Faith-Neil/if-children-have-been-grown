// 为什么有这个文件：验证正文写入和恢复使用文字原来的来源依据。
// 它解决什么问题：来源发生变化时不能靠刷新或取得编辑权升级旧候选，重新核对也不能遗漏期间的新变化。
import test from 'node:test';
import assert from 'node:assert/strict';
import { acquiredEditingFingerprint, editingContentWrite, loadedEditingFingerprint, recoveryEditingFingerprint, reviewedEditingFingerprint } from '../src/editing-source.ts';
import { recoveryWrite } from '../src/editor-recovery.ts';

test('load and reacquire preserve a saved draft source instead of the live workspace source', () => {
  const chapter = { revision: 4, draft: { base_revision: 4, input_fingerprint: 'draft-original' } };
  assert.equal(loadedEditingFingerprint(chapter, 'workspace-new'), 'draft-original');
  assert.equal(acquiredEditingFingerprint('candidate-original', chapter, true), 'candidate-original');
  assert.equal(acquiredEditingFingerprint('previous', chapter, false), 'draft-original');
  assert.equal(acquiredEditingFingerprint('manual-original', { revision: 5, draft: null }, false), 'manual-original');
  assert.equal(loadedEditingFingerprint({ revision: 4, draft: { base_revision: 4 } }, 'workspace-new'), null);
  assert.equal(acquiredEditingFingerprint('previous', { revision: 4, draft: { base_revision: 4 } }, false), null);
  assert.equal(loadedEditingFingerprint({ revision: 4, draft: { base_revision: 3, input_fingerprint: 'old-draft' } }, 'workspace-new'), 'workspace-new');
});

test('draft and version payloads carry the original basis including missing legacy basis', () => {
  assert.deepEqual(editingContentWrite('采用候选后人工修改', 'candidate-original'), { content: '采用候选后人工修改', input_fingerprint: 'candidate-original' });
  assert.deepEqual(editingContentWrite('旧草稿', null), { content: '旧草稿', input_fingerprint: null });
});

test('restoring an old draft does not silently use the current sources; explicit review is separate', () => {
  const oldDraft = { source_kind: 'draft', input_fingerprint: 'draft-original' };
  assert.equal(recoveryEditingFingerprint(oldDraft, 'workspace-new'), 'draft-original');
  assert.equal(recoveryEditingFingerprint({ ...oldDraft, input_fingerprint: null }, 'workspace-new'), null);
  assert.equal(recoveryEditingFingerprint({ ...oldDraft, reviewed_input_fingerprint: 'reviewed-new' }, 'reviewed-new'), 'reviewed-new');
  assert.equal(oldDraft.input_fingerprint, 'draft-original');
  assert.throws(() => recoveryEditingFingerprint({ source_kind: 'history', input_fingerprint: 'review-opened' }, 'changed-during-review'), /又变化/);
  assert.equal(recoveryEditingFingerprint({ source_kind: 'history', input_fingerprint: 'review-opened' }, 'review-opened'), 'review-opened');
});

test('human source confirmation refuses changes during review or a new official chapter version', () => {
  const workspace = { input_fingerprint: 'review-opened', chapters: [{ id: 'chapter-a', revision: 4 }] };
  assert.equal(reviewedEditingFingerprint('review-opened', workspace, 'chapter-a', 4), 'review-opened');
  assert.throws(() => reviewedEditingFingerprint('review-opened', { ...workspace, input_fingerprint: 'new-source' }, 'chapter-a', 4), /来源又变化/);
  assert.throws(() => reviewedEditingFingerprint('review-opened', workspace, 'chapter-a', 3), /正文版本变化/);
  assert.throws(() => reviewedEditingFingerprint('review-opened', workspace, 'other-chapter', 4), /正文版本变化/);
});

test('recovery rejects a draft whose saved basis changed while the text was being reviewed', () => {
  const chapter = { id: 'chapter-a', revision: 4, draft: { base_revision: 4, sequence: 6, content: '旧文字', input_fingerprint: 'draft-original' } };
  assert.throws(() => recoveryWrite(chapter, { ...chapter, draft: { ...chapter.draft, input_fingerprint: 'new-basis' } }, '核对后的文字'), /草稿已变化/);
});
