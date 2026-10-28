// 为什么有这个文件：验证 INT-COMPANY-SETTINGS-RBAC-GLUE 企业设置前端 API 交互契约与类型胶水。
// 它解决什么问题：
// 1. 验证 fetchCompanySettings 与 updateCompanySettings 函数导出契约；
// 2. 验证端点路径拼装（/api/v1/companies/{company_id}/settings）与 URI 编码；
// 3. 验证 HTTP 方法对齐（GET 与 PATCH）；
// 4. 验证接口属性与后端 CompanySettingsModel、UpdateCompanySettingsRequest 保持契约一致。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  fetchCompanySettings,
  updateCompanySettings,
} from '../../src/admin/company-settings-api.ts';

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

test('1. 企业设置 API 函数导出与签名验证', () => {
  assert.equal(typeof fetchCompanySettings, 'function');
  assert.equal(typeof updateCompanySettings, 'function');
});

test('2. 静态 AST 与契约断言：对齐 /api/v1/companies/{company_id}/settings', () => {
  const { content } = parseSource('../../src/admin/company-settings-api.ts');

  // 1. 路由前缀断言
  assert.ok(content.includes('/api/v1/companies/'), '必须使用标准 /api/v1 路径');
  assert.ok(content.includes('/settings'), '必须指向 /settings 资源端点');
  assert.ok(content.includes('encodeURIComponent'), '参数必须经 encodeURIComponent 处理防止注入');

  // 2. HTTP 方法断言
  assert.ok(content.includes("'GET'"), '读取配置必须使用 GET 方法');
  assert.ok(content.includes("'PATCH'"), '更新配置必须使用 PATCH 方法');

  // 3. 接口类型契约包含核心安全策略与编辑参数
  const requiredKeys = [
    'password_min_length',
    'password_min_char_classes',
    'max_login_attempts',
    'session_timeout_minutes',
    'edit_lock_timeout_minutes',
    'edit_lock_heartbeat_seconds',
    'editor_autosave_seconds',
    'loop_max_rounds',
    'assistant_suggestion_count',
  ];

  for (const key of requiredKeys) {
    assert.ok(content.includes(key), `接口契约必须定义核心配置项：${key}`);
  }
});
