// 为什么有这个文件：验证编辑台自动保存与心跳的计算（PRD v1.8 §5.11.9；APP-M2-T172）。
// 它解决什么问题：间隔取公司设置并按后台范围夹紧；只有持锁、有改动、未暂停时才自动保存；心跳只在有操作后发送；
// 释放前 5 分钟提示（假时钟）。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { IDLE_SAVE_MS, WARN_BEFORE_MS, editorTimings, expiryWarning, lockHolderLabel, shouldAutosave, shouldHeartbeat } from '../../src/editor/autosave-core.ts';

test('timings come from company settings and are clamped to platform ranges', () => {
  assert.deepEqual(editorTimings(null), { autosaveMs: 10_000, heartbeatMs: 60_000, timeoutMs: 30 * 60_000 });
  assert.deepEqual(editorTimings({ editor_autosave_seconds: 20, edit_lock_heartbeat_seconds: 90, edit_lock_timeout_minutes: 45 }),
    { autosaveMs: 20_000, heartbeatMs: 90_000, timeoutMs: 45 * 60_000 });
  assert.deepEqual(editorTimings({ editor_autosave_seconds: 1, edit_lock_heartbeat_seconds: 999, edit_lock_timeout_minutes: 1 }),
    { autosaveMs: 5_000, heartbeatMs: 120_000, timeoutMs: 6 * 60_000 });
  assert.equal(IDLE_SAVE_MS, 2000);
});

test('autosave only for a held, dirty, unpaused editor that is not already saving', () => {
  const base = { held: true, dirty: true, saving: false, paused: false, busy: false };
  assert.equal(shouldAutosave(base), true);
  for (const key of ['held', 'dirty']) assert.equal(shouldAutosave({ ...base, [key]: false }), false);
  for (const key of ['saving', 'paused', 'busy']) assert.equal(shouldAutosave({ ...base, [key]: true }), false);
});

test('heartbeat only after activity; warning in the last five minutes (fake clock)', () => {
  assert.equal(shouldHeartbeat(1000, 500), true);
  assert.equal(shouldHeartbeat(500, 1000), false);
  const now = Date.parse('2026-10-29T10:00:00Z');
  assert.equal(expiryWarning('2026-10-29T10:10:00Z', now), null);
  assert.equal(expiryWarning('2026-10-29T10:04:10Z', now), 5);
  assert.equal(expiryWarning('2026-10-29T10:00:20Z', now), 1);
  assert.equal(expiryWarning('2026-10-29T09:59:00Z', now), null);
  assert.equal(expiryWarning(null, now), null);
  assert.equal(WARN_BEFORE_MS, 300_000);
});

test('the editor saves before switching chapters and the lock heartbeat is activity based', () => {
  const page = readFileSync(new URL('../../src/editor/EditorPage.tsx', import.meta.url), 'utf8');
  const lock = readFileSync(new URL('../../src/editor/useEditorLock.ts', import.meta.url), 'utf8');
  assert.match(page, /autoSaveRef\.current\(\)\.then/);
  assert.match(page, /onKeyDown=\{lock\.markActivity\}/);
  assert.match(lock, /shouldHeartbeat\(lastActivity\.current, lastHeartbeat\.current\)/);
  assert.doesNotMatch(lock, /30_000\);/);
});

test('lock badge names the holder and says the chapter is read-only for others', () => {
  const lock = { owner_id: 'u2', owner_name: '李编写', expires_at: '2026-10-28T08:30:00Z' };
  assert.match(lockHolderLabel(lock, 'u1'), /^李编写 编辑中，本节只读，锁至 \d{2}:\d{2}$/);
  assert.match(lockHolderLabel(lock, 'u2'), /^本人在其他会话编辑中/);
  assert.equal(lockHolderLabel({ owner_id: 'u3', expires_at: 'bad' }, 'u1'), '其他成员 编辑中，本节只读');
});
