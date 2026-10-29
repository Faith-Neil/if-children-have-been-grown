// 为什么有这个文件：验证站内提醒的前端计算（PRD v1.8 §5.12.2；APP-M2-T029～T032）。
// 它解决什么问题：超过 99 显示 99+；筛选拼参数；只按后端核对过的站内地址跳转；页面里没有站外渠道。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { badgeText, listPath, mergedNote, safeTarget, POLL_MS, DROPDOWN_SIZE } from '../../src/notifications/notifications-core.ts';

test('badge shows the count and caps at 99+', () => {
  assert.equal(badgeText(0), '');
  assert.equal(badgeText(5), '5');
  assert.equal(badgeText(99), '99');
  assert.equal(badgeText(100), '99+');
  assert.equal(POLL_MS, 60000);
  assert.equal(DROPDOWN_SIZE, 7);
});

test('filters become query parameters', () => {
  assert.equal(listPath({ status: 'unread', type: 'job_failed', projectId: 'p1', since: '2026-10-01T00:00:00Z' }, 20),
    '/api/v1/notifications?status=unread&limit=20&offset=0&type=job_failed&project_id=p1&since=2026-10-01T00%3A00%3A00Z');
  assert.equal(listPath({ status: 'all' }), '/api/v1/notifications?status=all&limit=50&offset=0');
});

test('only in-app paths approved by the backend are followed', () => {
  const base = { notification: {}, message: null };
  assert.equal(safeTarget({ ...base, ok: true, path: '/projects/p1/manual' }), '/projects/p1/manual');
  assert.equal(safeTarget({ ...base, ok: true, path: 'https://evil.example' }), null);
  assert.equal(safeTarget({ ...base, ok: true, path: '//evil.example' }), null);
  assert.equal(safeTarget({ ...base, ok: false, path: null, message: '对象已不存在或你没有查看权限' }), null);
  assert.equal(mergedNote({ count: 3 }), '（未读期间合并 3 次）');
  assert.equal(mergedNote({ count: 1 }), '');
});

test('no off-site channel settings appear in the notification UI', () => {
  for (const file of ['../../src/notifications/NotificationBell.tsx', '../../src/notifications/NotificationsPage.tsx']) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /邮件|短信|email|sms/i);
  }
});
