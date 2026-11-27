// 为什么有这个文件：验证平台安全策略保存不再用前端默认值或整份本地对象覆盖服务端已存策略项（ISSUE-059 组1c / AC-03）。
// 它解决什么问题：PATCH 是合并语义，前端只上行相对服务端快照真正改动的字段；
// GET 未成功读回快照前禁止保存；刷新不静默丢弃未保存编辑。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  SECURITY_SETTINGS_KEYS,
  canSaveSecuritySettings,
  changedSecurityFields,
  hasSecurityChanges,
} from '../../src/admin/platform-security-core.ts';

const baseline = { password_min_length: 8, password_min_char_classes: 3, max_login_attempts: 5, session_timeout_minutes: 120 };

test('changedSecurityFields only returns fields the user actually edited', () => {
  assert.deepEqual(changedSecurityFields(baseline, baseline), {});
  assert.deepEqual(changedSecurityFields(baseline, { ...baseline, password_min_length: 12 }), { password_min_length: 12 });
  assert.deepEqual(
    changedSecurityFields(baseline, { ...baseline, password_min_length: 12, session_timeout_minutes: 240 }),
    { password_min_length: 12, session_timeout_minutes: 240 },
  );
  // 未编辑字段绝不上行：服务端并发修改的同名字段不被覆盖
  const partial = changedSecurityFields(baseline, { ...baseline, max_login_attempts: 3 });
  assert.equal(Object.keys(partial).length, 1);
  assert.equal('password_min_length' in partial, false);
});

test('changedSecurityFields never invents keys outside the modeled policy set', () => {
  const draft = { ...baseline, password_min_length: 10 };
  const changed = changedSecurityFields(baseline, draft);
  for (const key of Object.keys(changed)) assert.ok(SECURITY_SETTINGS_KEYS.includes(key), `unexpected key ${key}`);
});

test('hasSecurityChanges tracks dirty state exactly', () => {
  assert.equal(hasSecurityChanges(baseline, baseline), false);
  assert.equal(hasSecurityChanges(baseline, { ...baseline, session_timeout_minutes: 121 }), true);
  assert.equal(hasSecurityChanges(baseline, { ...baseline, session_timeout_minutes: 121, password_min_length: 8 }), true);
});

test('canSaveSecuritySettings requires a loaded server snapshot and real edits', () => {
  const dirty = { ...baseline, password_min_length: 12 };
  // GET 未完成/失败（无快照）：严禁保存——此时表单只是前端默认值
  assert.equal(canSaveSecuritySettings({ baseline: null, draft: dirty, loading: false, saving: false }), false);
  assert.equal(canSaveSecuritySettings({ baseline: null, draft: baseline, loading: true, saving: false }), false);
  // 加载中或保存中禁止重复提交
  assert.equal(canSaveSecuritySettings({ baseline, draft: dirty, loading: true, saving: false }), false);
  assert.equal(canSaveSecuritySettings({ baseline, draft: dirty, loading: false, saving: true }), false);
  // 无改动不发空写（避免无意义更新 updated_at/updated_by）
  assert.equal(canSaveSecuritySettings({ baseline, draft: baseline, loading: false, saving: false }), false);
  // 有快照 + 有改动：允许保存
  assert.equal(canSaveSecuritySettings({ baseline, draft: dirty, loading: false, saving: false }), true);
});

test('PlatformSecurityPage submits only the changed-fields diff, never the whole local object', () => {
  const source = readFileSync(new URL('../../src/admin/PlatformSecurityPage.tsx', import.meta.url), 'utf8');
  assert.ok(source.includes('changedSecurityFields(baseline, draft)'), 'PATCH body must be the diff against the server snapshot');
  assert.doesNotMatch(source, /PATCH['"]?,\s*(settings|draft)\)/, 'must not submit the whole local settings object');
  assert.ok(source.includes('if (!baseline || !saveable) return'), 'save must bail out without a server snapshot');
  assert.ok(source.includes('disabled={!saveable}'), 'save button disabled without snapshot or edits');
});

test('PlatformSecurityPage disables inputs and warns when the server snapshot never loaded', () => {
  const source = readFileSync(new URL('../../src/admin/PlatformSecurityPage.tsx', import.meta.url), 'utf8');
  assert.ok(source.includes('!baseline || loading'), 'form inputs disabled until a snapshot exists');
  assert.ok(source.includes('未读回服务端快照前不能保存'), 'load failure must explain saving is blocked');
});

test('PlatformSecurityPage refresh preserves unsaved user edits instead of discarding them', () => {
  const source = readFileSync(new URL('../../src/admin/PlatformSecurityPage.tsx', import.meta.url), 'utf8');
  assert.ok(source.includes('prev[key] !== baseline[key]'), 'refresh keeps fields the user edited');
  assert.ok(source.includes('const merged = { ...data }'), 'untouched fields adopt the fresh server values');
});
