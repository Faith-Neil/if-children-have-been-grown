// 为什么有这个文件：验证编辑台来源指纹死锁的根治逻辑（ISSUE-059 组2e，追踪号 056a411dff69418f92eafbed9649791b）。
// 它解决什么问题：
// 1. INPUT_FINGERPRINT_REQUIRED/STALE 必须被识别为「来源过期」而非版本冲突（不进 OCC 合并流程）；
// 2. 恢复重试编排：先拉最新项目指纹再原样重试，拉取失败绝不写入，章节冲突转交既有流程；
// 3. EditorPage 组件契约：恢复按钮文案、指纹自动同步时机、草稿内容永不静默丢弃。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ApiError } from '../../src/shared/api.ts';
import { isInputFingerprintError, recoverFingerprintedWrite } from '../../src/editor/fingerprint-recovery.ts';
import { isRevisionConflict } from '../../src/editor/editor-conflict.ts';

test('isInputFingerprintError recognizes both stale and required rejections', () => {
  assert.equal(isInputFingerprintError(new ApiError(409, 'INPUT_FINGERPRINT_STALE', '项目条款、事实、证据或正文已变化')), true);
  assert.equal(isInputFingerprintError(new ApiError(409, 'INPUT_FINGERPRINT_REQUIRED', '请先核对项目来源')), true);
  // 普通对象形态（防御性）也识别
  assert.equal(isInputFingerprintError({ code: 'INPUT_FINGERPRINT_STALE' }), true);
  // 版本冲突、序号冲突与其他错误一律不是指纹错误
  assert.equal(isInputFingerprintError(new ApiError(409, 'REVISION_CONFLICT', '章节已更新')), false);
  assert.equal(isInputFingerprintError(new ApiError(409, 'DRAFT_SEQUENCE_CONFLICT', '草稿已更新')), false);
  assert.equal(isInputFingerprintError(new ApiError(423, 'LOCK_LOST', '编辑权已失效')), false);
  assert.equal(isInputFingerprintError(null), false);
  assert.equal(isInputFingerprintError(new Error('network')), false);
});

test('fingerprint errors are never classified as revision conflicts (merge flow stays for real OCC only)', () => {
  assert.equal(isRevisionConflict(new ApiError(409, 'INPUT_FINGERPRINT_STALE', 'x')), false);
  assert.equal(isRevisionConflict(new ApiError(409, 'INPUT_FINGERPRINT_REQUIRED', 'x')), false);
  assert.equal(isRevisionConflict(new ApiError(409, 'REVISION_CONFLICT', 'x')), true);
});

test('recoverFingerprintedWrite retries the write with the freshly fetched fingerprint', async () => {
  const seen = [];
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => 'fresh-fp-2',
    write: async fingerprint => { seen.push(fingerprint); return true; },
  });
  assert.deepEqual(seen, ['fresh-fp-2'], 'write must use the fresh fingerprint, never the stale one');
  assert.deepEqual(outcome, { status: 'saved', fingerprint: 'fresh-fp-2' });
});

test('recoverFingerprintedWrite passes a null fingerprint through honestly when the project has none', async () => {
  const seen = [];
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => null,
    write: async fingerprint => { seen.push(fingerprint); return true; },
  });
  assert.deepEqual(seen, [null]);
  assert.equal(outcome.status, 'saved');
  assert.equal(outcome.fingerprint, null);
});

test('recoverFingerprintedWrite reports handed-off when the write was taken over by conflict merge or chapter switch', async () => {
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => 'fresh-fp',
    write: async () => false,
  });
  assert.deepEqual(outcome, { status: 'handed-off', fingerprint: 'fresh-fp' });
});

test('recoverFingerprintedWrite surfaces write errors with the fingerprint still adopted', async () => {
  const staleAgain = new ApiError(409, 'INPUT_FINGERPRINT_STALE', '来源恰好又变化');
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => 'fresh-fp',
    write: async () => { throw staleAgain; },
  });
  assert.equal(outcome.status, 'write-error');
  assert.equal(outcome.error, staleAgain);
  assert.equal(outcome.fingerprint, 'fresh-fp', 'even on failure the fresher fingerprint is returned for adoption');
});

test('recoverFingerprintedWrite never writes when the fresh fingerprint cannot be fetched', async () => {
  let writes = 0;
  const outage = new Error('network down');
  const outcome = await recoverFingerprintedWrite({
    fetchFingerprint: async () => { throw outage; },
    write: async () => { writes += 1; return true; },
  });
  assert.equal(writes, 0, 'no write may happen without a known-current fingerprint');
  assert.deepEqual(outcome, { status: 'fetch-error', error: outage });
});

function editorPageSource() {
  return readFileSync(new URL('../../src/editor/EditorPage.tsx', import.meta.url), 'utf8');
}

function functionBlock(source, name) {
  const start = source.indexOf(`function ${name}`);
  assert.notEqual(start, -1, `${name} must exist`);
  const rest = source.slice(start);
  const next = rest.slice(10).search(/\n  (async )?function \w/);
  return next === -1 ? rest : rest.slice(0, next + 10);
}

test('EditorPage shows the recovery entry with the exact required label', () => {
  const source = editorPageSource();
  assert.ok(source.includes('data-testid="fingerprint-recovery-alert"'), 'recovery alert must be rendered');
  assert.ok(source.includes('data-testid="fingerprint-recovery-btn"'), 'recovery button must be identifiable');
  assert.ok(source.includes('刷新最新来源并保留当前草稿重试'), 'exact recovery button label required by ISSUE-059 AC-05');
  assert.ok(source.includes('onClick={() => void recoverFingerprintWrite()}'), 'button must trigger the recovery flow');
});

test('EditorPage no longer tells users to blindly save again on fingerprint rejection', () => {
  const source = editorPageSource();
  assert.equal(source.includes('这次没有写入。页面上的文字还在，请再保存一次。'), false,
    'the old message was a deadlock lie: retrying with the same stale fingerprint can never succeed');
  assert.ok(source.includes("setFingerprintRecovery(prev => prev ?? { target: 'draft'"),
    'fingerprint errors must arm the recovery entry (draft fallback target)');
});

test('EditorPage recovery retries with the original target and never rewrites editor content', () => {
  const source = editorPageSource();
  const block = functionBlock(source, 'recoverFingerprintWrite');
  assert.ok(block.includes("recovery.target === 'commit' ? writeCommitWith(fingerprint) : writeDraftWith(fingerprint)"),
    'commit intent must retry as commit, draft as draft');
  assert.equal(block.includes('setContent('), false, 'recovery must never touch the editor draft content');
  assert.equal(block.includes('setChapter('), false, 'recovery must not replace the chapter behind the user');
  assert.ok(block.includes('setEditFingerprint(outcome.fingerprint)'), 'fresh fingerprint adopted after recovery');
});

test('EditorPage write kernels clear the recovery entry and unpause autosave on success', () => {
  const source = editorPageSource();
  const draft = functionBlock(source, 'writeDraftWith');
  const commit = functionBlock(source, 'writeCommitWith');
  for (const [name, block] of [['writeDraftWith', draft], ['writeCommitWith', commit]]) {
    assert.ok(block.includes('setFingerprintRecovery(null)'), `${name} success must close the recovery entry`);
    assert.ok(block.includes('setAutosavePaused(false)'), `${name} success must resume autosave`);
  }
  // 写入内核把版本冲突留在既有合并流程
  assert.ok(draft.includes("handleRevisionConflict(error, 'draft')"), 'draft kernel keeps revision-conflict merge flow');
  assert.ok(commit.includes("handleRevisionConflict(error, 'commit')"), 'commit kernel keeps revision-conflict merge flow');
});

test('EditorPage commit rejection arms the recovery entry with commit target', () => {
  const source = editorPageSource();
  const block = functionBlock(source, 'commit');
  assert.ok(block.includes("setFingerprintRecovery({ target: 'commit'"), 'commit-intent recovery must retry as commit');
});

test('EditorPage auto-refreshes the fingerprint at the safe sync moments', () => {
  const source = editorPageSource();
  // 1. 切换章节后：后台重新拉取 workspace 采用最新指纹
  assert.ok(source.includes('refreshEditFingerprint(start);'), 'chapter switch must background-refresh the fingerprint');
  assert.ok(source.includes('function refreshEditFingerprint(startEpoch: number)'), 'refresh helper must exist');
  // 2. 流式生成完成：采用重读后的最新 workspace 指纹，不得用闭包里的旧指纹
  assert.ok(source.includes('const fresh = await reload().catch(() => undefined);'), 'stream completion must reload before adopting');
  assert.ok(source.includes('setEditFingerprint(fresh?.input_fingerprint ?? workspace.input_fingerprint)'),
    'stream completion and outline refresh must adopt the freshly reloaded fingerprint');
  // 3. 生成完成后绝不能再使用生成前闭包指纹
  assert.equal(source.includes('setEditFingerprint(loadedEditingFingerprint(updated, workspace.input_fingerprint))'), false,
    'post-write content must not reuse the pre-write closure fingerprint');
});

test('EditorPage resets the recovery entry when switching chapters', () => {
  const source = editorPageSource();
  const effect = source.slice(source.indexOf('setFingerprintRecovery(null);') - 400, source.indexOf('setFingerprintRecovery(null);') + 40);
  assert.ok(effect.includes('setAutosavePaused(false)'), 'chapter switch reset block must include the recovery reset');
});
