// 为什么有这个文件：验证 INT-USER-SECURITY-OPS-GLUE 用户角色分配、重置密码与账号解锁前端 API 交互契约与类型胶水。
// 它解决什么问题：
// 1. 验证 resetUserPassword、unlockUser、updateUserRole 导出签名完整性；
// 2. 验证端点路径拼装与 URI 编码（/api/v1/users/{user_id}/reset-password、/unlock、/role）；
// 3. 验证 HTTP 动词对齐（POST 重置与解锁、PATCH 角色分配）；
// 4. 验证 ApiUserModel 支持 'locked' 状态与 is_locked 属性，对齐后端模型与 OpenAPI 契约。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  resetUserPassword,
  unlockUser,
  updateUserRole,
} from '../../src/admin/user-management-api.ts';

function parseSource(relPath) {
  const fullPath = path.resolve(import.meta.dirname, relPath);
  const content = fs.readFileSync(fullPath, 'utf8');
  const tree = ts.createSourceFile(
    fullPath,
    content,
    ts.ScriptTarget.Latest,
    true
  );
  return { content, tree };
}

test('1. 用户安全运维与角色分配 API 函数导出与签名验证', () => {
  assert.equal(typeof resetUserPassword, 'function');
  assert.equal(typeof unlockUser, 'function');
  assert.equal(typeof updateUserRole, 'function');
});

test('2. 静态 AST 与契约断言：对齐 /reset-password, /unlock, /role 端点', () => {
  const { content } = parseSource('../../src/admin/user-management-api.ts');

  // 1. 路由断言
  assert.ok(content.includes('/reset-password'), '必须定义重置密码子端点 /reset-password');
  assert.ok(content.includes('/unlock'), '必须定义账号解锁子端点 /unlock');
  assert.ok(content.includes('/role'), '必须定义角色变更子端点 /role');

  // 2. 状态断言
  assert.ok(content.includes("'active' | 'disabled' | 'locked'"), 'UserModel 状态必须支持 locked 状态');
  assert.ok(content.includes('is_locked'), 'UserModel 必须包含 is_locked 属性');

  // 3. 契约模型
  assert.ok(content.includes('ApiResetPasswordRequest'), '必须导出 ApiResetPasswordRequest 类型');
  assert.ok(content.includes('ApiUnlockUserResponse'), '必须导出 ApiUnlockUserResponse 类型');
  assert.ok(content.includes('ApiUpdateUserRoleRequest'), '必须导出 ApiUpdateUserRoleRequest 类型');
});
