// 为什么有这个文件：核对一次写入动作的重复请求标记，以及哪些失败可以自动再试。
// 它解决什么问题：避免每次重试换一把新键，或把冲突和校验失败再发给后台。
import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, download, request, userFacingMessage, isRequestFailureCurrent } from '../src/api.ts';

const noWait = async () => {};
const v1 = '/api/v1/projects/p-one/files';
const legacy = '/api/chapters/c-one/versions';

test('a permanent secret-key 503 stops GET, keyed write and download on the first response', async context => {
  for (const mode of ['GET', 'POST', 'download']) {
    let calls = 0;
    context.mock.method(globalThis, 'fetch', async () => {
      calls++;
      return jsonResponse(503, { code: 'SECRET_KEY_UNAVAILABLE', message: '密钥服务未就绪。', traceId: 'secret-review' });
    });
    const error = await (mode === 'download'
      ? download('/api/v1/synthetic/file', 'synthetic-token', 'synthetic.docx', noWait)
      : request(v1, 'synthetic-token', mode, mode === 'POST' ? {} : undefined, 1, noWait)).catch(value => value);
    assert.ok(error instanceof ApiError);
    assert.equal(error.code, 'SECRET_KEY_UNAVAILABLE');
    assert.equal(error.requestId, 'secret-review');
    assert.equal(calls, 1, mode);
  }
});

test('transport failures keep private origin identity without putting a token on the error', async context => {
  context.mock.method(globalThis, 'fetch', async () => jsonResponse(401, { code: 'UNAUTHENTICATED', message: '重新登录。' }));
  const error = await request('/api/v1/session', 'old-synthetic-token', 'GET', undefined, undefined, noWait).catch(value => value);
  assert.equal(isRequestFailureCurrent(error, 'new-synthetic-token'), false);
  assert.equal(isRequestFailureCurrent(error, 'old-synthetic-token'), true);
  assert.equal(isRequestFailureCurrent(error, null), false);
  assert.equal(JSON.stringify(error).includes('old-synthetic-token'), false);
  const unowned = new ApiError(401, 'SESSION_REQUIRED', '请登录。');
  assert.equal(isRequestFailureCurrent(unowned, 'new-synthetic-token'), true);
  const downloadError = await download('/api/v1/synthetic/file', 'download-old-token', 'synthetic.docx', noWait).catch(value => value);
  assert.equal(isRequestFailureCurrent(downloadError, 'new-synthetic-token'), false);
});

function jsonResponse(status, body, headerId) {
  const headers = headerId ? { 'X-Request-ID': headerId, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
  return new Response(JSON.stringify(body), { status, headers });
}

function gateway502() {
  return new Response('Bad Gateway', { status: 502, headers: { 'Content-Type': 'text/html' } });
}

test('v1 and legacy error bodies both keep the trace id shown to the user', async context => {
  context.mock.method(globalThis, 'fetch', async () => jsonResponse(422, {
    code: 'FIELD_INVALID', message: '名称不能为空。', details: { fields: ['body.name'] }, traceId: 'abc123',
  }, 'abc123'));
  const v1Error = await request(v1, 'token', 'POST', { name: '' }, 4, noWait).catch(error => error);
  assert.ok(v1Error instanceof ApiError);
  assert.equal(v1Error.status, 422);
  assert.equal(v1Error.code, 'FIELD_INVALID');
  assert.equal(v1Error.requestId, 'abc123');
  assert.deepEqual(v1Error.details, { fields: ['body.name'] });
  assert.equal(userFacingMessage(v1Error), '名称不能为空。（追踪号 abc123）');

  context.mock.method(globalThis, 'fetch', async () => jsonResponse(409, {
    error: { code: 'REVISION_CONFLICT', message: '正文已变化。' }, request_id: 'legacy-id',
  }));
  const legacyError = await request(legacy, 'token', 'POST', { idempotency_key: 'body-key' }, undefined, noWait).catch(error => error);
  assert.equal(legacyError.code, 'REVISION_CONFLICT');
  assert.equal(legacyError.requestId, 'legacy-id');
  assert.equal(userFacingMessage(legacyError), '正文已变化。（追踪号 legacy-id）');
});

test('the response header is the trace id when it is present', async context => {
  context.mock.method(globalThis, 'fetch', async () => jsonResponse(403, {
    code: 'ACCESS_DENIED', message: '没有权限。', traceId: 'body-id',
  }, 'header-id'));
  const error = await request('/api/v1/session', 'token', 'GET', undefined, undefined, noWait).catch(error => error);
  assert.equal(error.requestId, 'header-id');
});

test('a bare gateway 502 retries with the same idempotency key', async context => {
  const keys = [];
  const waits = [];
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    keys.push(init.headers['Idempotency-Key']);
    calls += 1;
    if (calls < 3) return gateway502();
    return jsonResponse(200, { ok: true });
  });
  const result = await request(v1, 'token', 'POST', { name: '合成项目' }, 9, async ms => { waits.push(ms); });
  assert.deepEqual(result, { ok: true });
  assert.equal(calls, 3);
  assert.equal(keys[0], keys[1]);
  assert.equal(keys[0], keys[2]);
  assert.match(keys[0], /^[A-Za-z0-9_-]{8,120}$/);
  assert.deepEqual(waits, [200, 400]);
});

test('a 502 MODEL_UNAVAILABLE sends one request and shows the trace id', async context => {
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async () => {
    calls += 1;
    return jsonResponse(502, {
      code: 'MODEL_UNAVAILABLE', message: '模型暂不可用。', details: { model: 'demo' }, traceId: 'trace-model',
    }, 'trace-model');
  });
  const error = await request(v1, 'token', 'POST', { name: '合成项目' }, 9, noWait).catch(error => error);
  assert.equal(calls, 1);
  assert.ok(error instanceof ApiError);
  assert.equal(error.status, 502);
  assert.equal(error.code, 'MODEL_UNAVAILABLE');
  assert.equal(error.requestId, 'trace-model');
  assert.equal(userFacingMessage(error), '模型暂不可用。（追踪号 trace-model）');
});

test('a later user action receives a new idempotency key', async context => {
  const keys = [];
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    keys.push(init.headers['Idempotency-Key']);
    return jsonResponse(200, { ok: true });
  });
  await request(v1, 'token', 'POST', { name: '第一次' }, undefined, noWait);
  await request(v1, 'token', 'POST', { name: '第二次' }, undefined, noWait);
  assert.equal(keys.length, 2);
  assert.notEqual(keys[0], keys[1]);
});

test('network errors and 503 retry with the same key, then stop after three attempts', async context => {
  const keys = [];
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    keys.push(init.headers['Idempotency-Key']);
    calls += 1;
    if (calls === 1) throw new TypeError('Failed to fetch');
    return jsonResponse(503, { code: 'UI_NOT_READY', message: '页面还没准备好。', traceId: 'trace-503' }, 'trace-503');
  });
  const error = await request(v1, 'token', 'PATCH', { name: '合成' }, undefined, noWait).catch(error => error);
  assert.equal(calls, 3);
  assert.equal(keys[0], keys[1]);
  assert.equal(keys[0], keys[2]);
  assert.equal(error.status, 503);
  assert.equal(error.requestId, 'trace-503');
});

test('409, 422, 423 and 428 are not retried', async context => {
  for (const status of [409, 422, 423, 428]) {
    let calls = 0;
    context.mock.method(globalThis, 'fetch', async () => {
      calls += 1;
      return jsonResponse(status, { code: 'STOP', message: '停止。', traceId: `id-${status}` }, `id-${status}`);
    });
    const error = await request(v1, 'token', 'PUT', { value: 1 }, 3, noWait).catch(error => error);
    assert.equal(calls, 1, `status ${status}`);
    assert.equal(error.status, status);
  }
});

test('401 and 500 stop on the first response', async context => {
  for (const status of [401, 500]) {
    let calls = 0;
    context.mock.method(globalThis, 'fetch', async () => {
      calls += 1;
      return jsonResponse(status, { code: 'STOP', message: '停止。', traceId: `id-${status}` });
    });
    const error = await request('/api/v1/session', 'token', 'GET', undefined, undefined, noWait).catch(error => error);
    assert.equal(calls, 1, `status ${status}`);
    assert.equal(error.status, status);
  }
});

test('a retried read does not send an idempotency key', async context => {
  const keys = [];
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    keys.push(init.headers['Idempotency-Key']);
    calls += 1;
    if (calls === 1) return gateway502();
    return jsonResponse(200, { items: [] });
  });
  const result = await request('/api/v1/projects', 'token', 'GET', undefined, undefined, noWait);
  assert.deepEqual(result, { items: [] });
  assert.deepEqual(keys, [undefined, undefined]);
});

test('a chapter version write sends the same key in the header and the body, including on retry', async context => {
  const seen = [];
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (path, init) => {
    seen.push({ path, header: init.headers['Idempotency-Key'], body: JSON.parse(init.body) });
    calls += 1;
    if (calls === 1) throw new TypeError('Failed to fetch');
    if (calls === 2) return jsonResponse(503, { error: { code: 'UI_NOT_READY', message: '暂不可用。' }, request_id: 'legacy-503' });
    return jsonResponse(200, { revision: 2 });
  });
  const result = await request('/api/chapters/c%20one/versions?draft=1', 'token', 'POST', {
    lease_token: 'lease', idempotency_key: 'chapter-action',
  }, undefined, noWait);
  assert.deepEqual(result, { revision: 2 });
  assert.equal(calls, 3);
  for (const item of seen) {
    assert.equal(item.path, '/api/chapters/c%20one/versions?draft=1');
    assert.equal(item.header, 'chapter-action');
    assert.equal(item.body.idempotency_key, 'chapter-action');
    assert.equal(item.body.lease_token, 'lease');
  }
});

test('a chapter version write without a body key fills one generated key into both places', async context => {
  const seen = [];
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    seen.push({ header: init.headers['Idempotency-Key'], body: JSON.parse(init.body) });
    return jsonResponse(502, { error: { code: 'MODEL_UNAVAILABLE', message: '模型暂不可用。' }, request_id: 'legacy-502' });
  });
  const error = await request(legacy, 'token', 'POST', { lease_token: 'lease' }, undefined, noWait).catch(error => error);
  assert.equal(seen.length, 1);
  assert.equal(seen[0].header, seen[0].body.idempotency_key);
  assert.match(seen[0].header, /^[A-Za-z0-9_-]{8,120}$/);
  assert.equal(error.status, 502);
  assert.equal(error.code, 'MODEL_UNAVAILABLE');
  assert.equal(userFacingMessage(error), '模型暂不可用。（追踪号 legacy-502）');

  const next = [];
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    next.push(init.headers['Idempotency-Key']);
    return jsonResponse(200, { revision: 3 });
  });
  await request(legacy, 'token', 'POST', { idempotency_key: 'next-click' }, undefined, noWait);
  assert.deepEqual(next, ['next-click']);
  assert.notEqual(next[0], seen[0].header);
});

test('a legacy write without an idempotency key is not retried', async context => {
  const cases = [
    { name: '503', fail: () => jsonResponse(503, { error: { code: 'UI_NOT_READY', message: '暂不可用。' }, request_id: 'lock-503' }) },
    { name: 'gateway', fail: () => gateway502() },
    { name: 'network', fail: () => { throw new TypeError('Failed to fetch'); } },
  ];
  for (const item of cases) {
    let calls = 0;
    let header;
    context.mock.method(globalThis, 'fetch', async (_path, init) => {
      calls += 1;
      header = init.headers['Idempotency-Key'];
      return item.fail();
    });
    const error = await request('/api/chapters/c-one/lock', 'token', 'POST', { lease_token: 'lease' }, undefined, noWait).catch(error => error);
    assert.equal(calls, 1, item.name);
    assert.equal(header, undefined, item.name);
    if (item.name === '503') {
      assert.equal(error.status, 503);
      assert.equal(error.requestId, 'lock-503');
    }
    if (item.name === 'gateway') assert.equal(error.status, 502);
    if (item.name === 'network') assert.ok(error instanceof TypeError);
  }
});

test('a GET 503 retries without an idempotency key', async context => {
  const keys = [];
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    keys.push(init.headers['Idempotency-Key']);
    calls += 1;
    if (calls < 2) return jsonResponse(503, { code: 'UI_NOT_READY', message: '暂不可用。', traceId: 'get-503' });
    return jsonResponse(200, { items: [] });
  });
  const result = await request('/api/v1/projects', 'token', 'GET', undefined, undefined, noWait);
  assert.deepEqual(result, { items: [] });
  assert.equal(calls, 2);
  assert.deepEqual(keys, [undefined, undefined]);
});

test('other legacy writes do not receive an idempotency header', async context => {
  let header;
  let body;
  context.mock.method(globalThis, 'fetch', async (_path, init) => {
    header = init.headers['Idempotency-Key'];
    body = JSON.parse(init.body);
    return jsonResponse(200, { ok: true });
  });
  await request('/api/chapters/c-one/lock/release', 'token', 'POST', { lease_token: 'lease' }, undefined, noWait);
  assert.equal(header, undefined);
  assert.deepEqual(body, { lease_token: 'lease' });
});
