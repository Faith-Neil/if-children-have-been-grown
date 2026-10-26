// 为什么有这个文件：验证 D3 契约收口任务中的统一错误体与双错误体规范优先解构（落实 2026-10-26 用户拍板 B4）。
// 它解决什么问题：
// 1. 验证 apiFailure 严格优先解构标准业务错误体 {code, message, details, traceId}；
// 2. 验证当同时存在双错误体时（旧 error/request_id 兼容层），标准字段具有绝对优先级；
// 3. 验证当纯旧格式出现时，向后兼容 fallback 正常解析；
// 4. 验证 extractErrorInfo (status-views) 同样具备相同的标准字段严格优先解构规则。

import test from 'node:test';
import assert from 'node:assert/strict';
import { apiFailure, ApiError } from '../../src/shared/api.ts';
import { extractErrorInfo } from '../../src/status/status-views.ts';

test('apiFailure: 纯规范错误体 {code, message, details, traceId} 正常解构', () => {
  const payload = {
    code: 'UNAUTHENTICATED',
    message: '登录令牌已失效，请重新登录。',
    details: { reason: 'token_expired' },
    traceId: 'trace-std-001',
  };
  const err = apiFailure(401, payload, 'header-fallback-id');
  assert.ok(err instanceof ApiError);
  assert.equal(err.status, 401);
  assert.equal(err.code, 'UNAUTHENTICATED');
  assert.equal(err.message, '登录令牌已失效，请重新登录。');
  assert.equal(err.requestId, 'header-fallback-id', 'headerId 优先作为 requestId');
  assert.deepEqual(err.details, { reason: 'token_expired' });
});

test('apiFailure: 双错误体共存时，严格优先解构规范体而非旧 error/request_id', () => {
  // 当双错误体并存时，规范层 code 为 V1_CANONICAL_ERROR，旧兼容层 code 为 LEGACY_ERROR
  const dualPayload = {
    code: 'V1_CANONICAL_ERROR',
    message: '规范中文错误提示',
    details: { canonical: true },
    traceId: 'trace-v1-canonical',
    error: {
      code: 'LEGACY_ERROR',
      message: '旧版兼容错误提示',
      details: { canonical: false },
    },
    request_id: 'legacy-trace-old',
  };
  // 无 headerId 时，检查 body 字段解构
  const err = apiFailure(409, dualPayload);
  assert.equal(err.code, 'V1_CANONICAL_ERROR', '严格优先使用规范体的 code');
  assert.equal(err.message, '规范中文错误提示', '严格优先使用规范体的 message');
  assert.equal(err.requestId, 'trace-v1-canonical', '严格优先使用规范体的 traceId');
  assert.deepEqual(err.details, { canonical: true }, '严格优先使用规范体的 details');
});

test('apiFailure: 纯旧版错误体兼容兜底 {error: {code, message}, request_id}', () => {
  const legacyOnly = {
    error: {
      code: 'OLD_STYLE_ERROR',
      message: '仅旧兼容层提供的内容',
      details: { legacy: true },
    },
    request_id: 'old-req-999',
  };
  const err = apiFailure(502, legacyOnly);
  assert.equal(err.code, 'OLD_STYLE_ERROR');
  assert.equal(err.message, '仅旧兼容层提供的内容');
  assert.equal(err.requestId, 'old-req-999');
  assert.deepEqual(err.details, { legacy: true });
});

test('extractErrorInfo (status-views): 双错误体严格优先解构外层标准规范字段', () => {
  const dualRecord = {
    code: 'CANONICAL_RULE_VIOLATION',
    message: '标准合规阻断提示',
    traceId: 'trace-canonical-888',
    status: 422,
    details: { rule: 'R15' },
    error: {
      code: 'OLD_RULE_FAIL',
      message: '旧错误文案',
      details: { rule: 'OLD' },
    },
    request_id: 'old-req-000',
  };
  const info = extractErrorInfo(dualRecord);
  assert.equal(info.code, 'CANONICAL_RULE_VIOLATION');
  assert.equal(info.message, '标准合规阻断提示');
  assert.equal(info.traceId, 'trace-canonical-888');
  assert.equal(info.status, 422);
  assert.deepEqual(info.details, { rule: 'R15' });
});

test('extractErrorInfo (status-views): 纯旧版结构向后兼容正常解析', () => {
  const legacyRecord = {
    error: {
      code: 'LEGACY_ONLY_CODE',
      message: '纯旧结构说明',
      details: { fallback: true },
    },
    request_id: 'legacy-trace-555',
  };
  const info = extractErrorInfo(legacyRecord);
  assert.equal(info.code, 'LEGACY_ONLY_CODE');
  assert.equal(info.message, '纯旧结构说明');
  assert.equal(info.traceId, 'legacy-trace-555');
  assert.deepEqual(info.details, { fallback: true });
});
