// 为什么有这个文件：顶栏与编辑台从任务列表里认出进行中的技术卷生成会话。
import assert from 'node:assert/strict';
import test from 'node:test';
import { activeVolumeSession, volumeSessionLabel } from '../../src/status/generation-session.ts';

function job(id, extra = {}) {
  return {
    id, project_id: 'p1', type: 'technical_volume', status: 'running', progress: 40,
    message: '已完成 2/5 节', created_at: '2026-11-18T10:00:00Z', completed_at: '', error: null, recoverable: true,
    ...extra,
  };
}

test('picks the newest unfinished technical volume session', () => {
  const jobs = [
    job('old', { created_at: '2026-11-18T09:00:00Z' }),
    job('done', { status: 'completed', created_at: '2026-11-18T11:00:00Z' }),
    job('parse', { type: 'parse', created_at: '2026-11-18T12:00:00Z' }),
    job('new', { status: 'queued', created_at: '2026-11-18T10:30:00Z' }),
  ];
  assert.equal(activeVolumeSession(jobs)?.id, 'new');
});

test('no session when every technical volume job has ended or belongs elsewhere', () => {
  assert.equal(activeVolumeSession([job('a', { status: 'cancelled' }), job('b', { status: 'failed' })]), null);
  assert.equal(activeVolumeSession([job('c', { project_id: 'p2' })], 'p1'), null);
  assert.equal(activeVolumeSession(undefined), null);
});

test('label shows the server progress text', () => {
  assert.equal(volumeSessionLabel('已完成 2/5 节'), '技术卷生成中 · 已完成 2/5 节');
  assert.equal(volumeSessionLabel(''), '技术卷生成中');
});
