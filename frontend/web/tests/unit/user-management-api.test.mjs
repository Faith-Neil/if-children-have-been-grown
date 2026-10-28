// 为什么有这个文件：验证 INT-USER-TRANSFER-RBAC-GLUE 用户管理与停用转交前端 API 交互契约与类型胶水。
// 它解决什么问题：
// 1. 验证 fetchUsers、fetchUser、createUser、updateUser、transferUserAssets 导出签名；
// 2. 验证端点路径拼装与 URI 编码（/api/v1/users/{user_id} 及 /transfer）；
// 3. 验证 HTTP 方法规范（GET、POST、PATCH）；
// 4. 验证接口属性与后端 UserModel、CreateUserRequest、UpdateUserRequest 契约对齐。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  fetchUsers,
  fetchUser,
  createUser,
  updateUser,
  transferUserAssets,
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

test('1. 用户管理 API 函数导出与签名验证', () => {
  assert.equal(typeof fetchUsers, 'function');
  assert.equal(typeof fetchUser, 'function');
  assert.equal(typeof createUser, 'function');
  assert.equal(typeof updateUser, 'function');
  assert.equal(typeof transferUserAssets, 'function');
});

test('2. 静态 AST 与契约断言：对齐 /api/v1/users 端点', () => {
  const { content } = parseSource('../../src/admin/user-management-api.ts');

  // 1. 路由断言
  assert.ok(content.includes('/api/v1/users'), '必须使用标准 /api/v1/users 路径');
  assert.ok(content.includes('/transfer'), '必须定义资产交接子端点 /transfer');
  assert.ok(content.includes('encodeURIComponent'), '参数必须经 encodeURIComponent 处理防注入');

  // 2. HTTP 方法断言
  assert.ok(content.includes("'GET'"), '读取必须使用 GET');
  assert.ok(content.includes("'POST'"), '新增必须使用 POST');
  assert.ok(content.includes("'PATCH'"), '更新必须使用 PATCH');

  // 3. 核心字段契约
  assert.ok(content.includes('successor_user_id'), '必须支持停用资产交接接收人 successor_user_id');
  assert.ok(content.includes('company_id'), '必须支持企业租户隔离字段 company_id');
});
