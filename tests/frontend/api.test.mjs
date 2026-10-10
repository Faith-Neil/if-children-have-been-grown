// 为什么有这个文件：验证页面可正确理解新旧后台的错误和项目版本变化。
// 它解决什么问题：解析失败也可能记录新版本，页面需要保留失败信息并重新读取状态。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, request } from '../../frontend/web/src/api.ts';

test('v1解析失败保留详细原因、请求编号和已改变的项目版本', async context => {
  context.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    code: 'INVALID_DOCX', message: '无法读取 DOCX 文件结构。', traceId: 'request-1', details: { revision: 9, job_id: 'job-1' },
  }), { status: 422 }));
  await assert.rejects(request('/api/v1/projects/p/parse', 'synthetic-session', 'POST', {}, 8), error => {
    assert.ok(error instanceof ApiError); assert.equal(error.message, '无法读取 DOCX 文件结构。');
    assert.equal(error.details.revision, 9); assert.equal(error.requestId, 'request-1'); return true;
  });
});

test('旧章节错误仍能显示实际编辑权失败原因', async context => {
  context.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    error: { code: 'LEASE_EXPIRED', message: '编辑权已过期。' }, request_id: 'request-2',
  }), { status: 423 }));
  await assert.rejects(request('/api/chapters/c/draft', 'synthetic-session', 'PUT', {}), error => {
    assert.equal(error.code, 'LEASE_EXPIRED'); assert.equal(error.status, 423);
    assert.equal(error.message, '编辑权已过期。'); assert.equal(error.requestId, 'request-2'); return true;
  });
});

test('移除上传也携带版本、重复请求标记和明确理由', async context => {
  context.mock.method(globalThis, 'fetch', async (path, options) => {
    assert.equal(path, '/api/v1/projects/p/files/f'); assert.equal(options.method, 'DELETE');
    assert.equal(options.headers['If-Match'], '9'); assert.match(options.headers['Idempotency-Key'], /^[0-9a-f-]{36}$/);
    assert.deepEqual(JSON.parse(options.body), { reason: '误传合成损坏文件' });
    return new Response(JSON.stringify({ revision: 10, deleted_file_id: 'f' }));
  });
  assert.equal((await request('/api/v1/projects/p/files/f', 'synthetic-session', 'DELETE', { reason: '误传合成损坏文件' }, 9)).revision, 10);
});
