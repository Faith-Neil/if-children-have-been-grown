// 为什么有这个文件：验证模型配置的界面权限（2026-10-29 安全修复）。
// 它解决什么问题：模型地址决定标书正文发往哪里；普通成员不能新建、修改、测试连接，项目绑定只给负责人和公司管理员。后端同样核对。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { modelConfigAccess } from '../../src/admin/model-config-core.ts';

test('only company and platform admins manage model configs; project leads may also bind', () => {
  assert.deepEqual(modelConfigAccess('company_admin', false), { canManage: true, canBind: true });
  assert.deepEqual(modelConfigAccess('platform_admin', false), { canManage: true, canBind: true });
  assert.deepEqual(modelConfigAccess('manager', true), { canManage: false, canBind: true });
  assert.deepEqual(modelConfigAccess('manager', false), { canManage: false, canBind: false });
  assert.deepEqual(modelConfigAccess('editor', false), { canManage: false, canBind: false });
  assert.deepEqual(modelConfigAccess(undefined, false), { canManage: false, canBind: false });
});

test('the modal hides write actions unless allowed and defaults to read-only', () => {
  const modal = readFileSync(new URL('../../src/admin/ModelConfigModal.tsx', import.meta.url), 'utf8');
  assert.match(modal, /canManage = false/);
  assert.match(modal, /canBind = false/);
  assert.match(modal, /\{canManage && !isCreatingNew && activeConfig && \(\s*<Button\s*data-testid="test-connection-btn"/);
  assert.match(modal, /\{canBind && projectId/);
  assert.match(modal, /disabled=\{!canManage\}/);
});
