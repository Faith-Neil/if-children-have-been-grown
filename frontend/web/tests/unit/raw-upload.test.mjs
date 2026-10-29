// 为什么有这个文件：验证 100MB 上传上限与二进制直传（招标文件、知识库原件、证书附件三处共用）。
// 它解决什么问题：大扫描件不能先在浏览器里转成 base64；超限在前端先拦，带上 If-Match 与幂等键。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { MAX_UPLOAD_BYTES, rawUploadPath, uploadRaw, uploadTooLarge } from '../../src/shared/api.ts';

test('limit is 100MB and the message states the size', () => {
  assert.equal(MAX_UPLOAD_BYTES, 100 * 1024 * 1024);
  assert.equal(uploadTooLarge({ size: MAX_UPLOAD_BYTES }), null);
  assert.match(uploadTooLarge({ size: MAX_UPLOAD_BYTES + 1 }), /不能超过 100MB/);
  assert.equal(rawUploadPath('/x/raw', { filename: '招标 文件.pdf', content_type: '' }), '/x/raw?filename=%E6%8B%9B%E6%A0%87+%E6%96%87%E4%BB%B6.pdf');
});

test('uploadRaw sends the file itself as the body with revision and idempotency key', async context => {
  let seen;
  context.mock.method(globalThis, 'fetch', async (path, init) => { seen = { path, init }; return new Response(JSON.stringify({ ok: true }), { status: 200 }); });
  const blob = new Blob(['raw-bytes']);
  assert.deepEqual(await uploadRaw('/api/v1/projects/p/files/raw?filename=a.pdf', 'tok', blob, 7), { ok: true });
  assert.equal(seen.init.body, blob);
  assert.equal(seen.init.headers['Content-Type'], 'application/octet-stream');
  assert.equal(seen.init.headers['If-Match'], '7');
  assert.ok(seen.init.headers['Idempotency-Key']);
  context.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ code: 'FILE_SIZE_LIMIT', message: '文件须有内容且不超过 100MB。' }), { status: 413 }));
  await assert.rejects(uploadRaw('/x', 'tok', blob), error => error.status === 413);
});

test('all three upload screens use the raw channel', () => {
  for (const file of ['project/TenderTab.tsx', 'library/KnowledgeBaseAdminPage.tsx', 'library/CertificateImport.tsx']) {
    const source = readFileSync(new URL(`../../src/${file}`, import.meta.url), 'utf8');
    assert.match(source, /uploadRaw/, file);
    assert.doesNotMatch(source, /content_base64/, file);
  }
});
