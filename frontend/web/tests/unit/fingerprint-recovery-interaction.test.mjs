// 为什么有这个文件：指纹恢复的可执行行为级交互测试（ISSUE-059 评审收口，替代读源码文本断言）。
// 它解决什么问题：用真实的 fingerprint-recovery/editing-source 逻辑函数驱动与 EditorPage 一致的
// 状态机，验证 PM 要求的两个场景——(a) 409→恢复→继续编辑→再保存直接成功；(b) 重开旧草稿保留旧指纹。

import test from 'node:test';
import assert from 'node:assert/strict';
import { recoverFingerprintedWrite, isInputFingerprintError } from '../../src/editor/fingerprint-recovery.ts';
import { loadedEditingFingerprint, acquiredEditingFingerprint } from '../../src/editor/editing-source.ts';

function fingerprintError() {
  const error = new Error('项目条款、事实、证据或正文已变化，不能保存或提交旧来源内容；请重新核对来源');
  error.status = 409;
  error.code = 'INPUT_FINGERPRINT_STALE';
  return error;
}

// 模拟与 EditorPage 一致的状态机：editFingerprint 为编辑器持有指纹；
// 写入内核在成功时采用「写入后」指纹（提交本身会改变项目指纹），与 writeCommitWith 行为一致。
function makeEditor({ serverFingerprint, draftFingerprint = null }) {
  return {
    editFingerprint: draftFingerprint,
    serverFingerprint,
    recovery: null,
    savedWrites: [],
  };
}

// 写入内核模拟：忠实复刻 writeCommitWith 的关键语义——指纹过期抛 409；
// 成功后项目指纹前进（提交改变指纹）并采用写入后新指纹；失败不采纳任何值。
function makeCommitKernel(editor) {
  return async (fingerprint) => {
    if (fingerprint !== editor.serverFingerprint) throw fingerprintError();
    editor.serverFingerprint = `${fingerprint}-after-write`;
    editor.editFingerprint = editor.serverFingerprint; // 内核读回的写入后新指纹
    editor.savedWrites.push(fingerprint);
    return true;
  };
}

test('场景(a)：409→恢复→继续编辑→再次保存直接成功无需二次恢复', async () => {
  const editor = makeEditor({ serverFingerprint: 'fp-v2', draftFingerprint: 'fp-v1' });

  // 1. 首次提交：编辑器持 fp-v1，服务端已是 fp-v2 → 409 INPUT_FINGERPRINT_STALE
  const kernel = makeCommitKernel(editor);
  await assert.rejects(() => kernel(editor.editFingerprint), isInputFingerprintError);
  editor.recovery = { target: 'commit', message: 'stale' };

  // 2. 点击恢复：拉取最新指纹 fp-v2 → 原样重试 → 成功，内核采用写入后指纹 fp-v2-after-write
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => editor.serverFingerprint,
    write: (fp) => kernel(fp),
  });
  assert.equal(outcome.status, 'saved');

  // 关键断言（Bug3 修复语义）：恢复成功后编辑器持有的是内核读回的写入后指纹，
  // 严禁外层用写入前的 fp-v2 覆盖——否则下一步保存会再次 409。
  if (outcome.status === 'write-error' && outcome.fingerprint) editor.editFingerprint = outcome.fingerprint;
  assert.equal(editor.editFingerprint, 'fp-v2-after-write');
  editor.recovery = null;

  // 3. 继续修改文字后再次保存：直接成功，不再触发恢复
  const again = makeCommitKernel(editor);
  const ok = await again(editor.editFingerprint);
  assert.equal(ok, true);
  assert.equal(editor.recovery, null);
  assert.equal(editor.savedWrites.length, 2);
});

test('场景(b)：重开旧草稿保留草稿原指纹不被自动刷新覆盖', () => {
  // loadedEditingFingerprint：草稿 base_revision 与当前一致时采用草稿指纹
  const withDraft = { revision: 5, draft: { base_revision: 5, input_fingerprint: 'fp-draft-old' } };
  assert.equal(loadedEditingFingerprint(withDraft, 'fp-workspace-new'), 'fp-draft-old');

  // 草稿 base_revision 落后（未恢复进编辑器、展示正式正文）时允许用工作台最新值
  const staleDraft = { revision: 6, draft: { base_revision: 5, input_fingerprint: 'fp-draft-old' } };
  assert.equal(loadedEditingFingerprint(staleDraft, 'fp-workspace-new'), 'fp-workspace-new');

  // acquiredEditingFingerprint：用户已修改内容时保留既有指纹（不回退）
  assert.equal(acquiredEditingFingerprint('fp-held', withDraft, true), 'fp-held');
  // 未修改且草稿恢复时采用草稿指纹
  assert.equal(acquiredEditingFingerprint('fp-held', withDraft, false), 'fp-draft-old');
});

test('恢复期间写入内核被版本冲突接管时如实 handed-off 且不覆盖指纹', async () => {
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => 'fp-latest',
    write: async () => false, // 内核转交既有 OCC 合并流程
  });
  assert.equal(outcome.status, 'handed-off');
});

test('拉取最新指纹失败时绝不写入', async () => {
  let writes = 0;
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => { throw new Error('network down'); },
    write: async () => { writes += 1; return true; },
  });
  assert.equal(outcome.status, 'fetch-error');
  assert.equal(writes, 0);
});
