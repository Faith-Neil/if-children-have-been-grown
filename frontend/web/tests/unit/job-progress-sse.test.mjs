// 为什么有这个测试：覆盖 APP-M2-T020 JobProgress 的 SSE 订阅、指数退避重试、平滑轮询回退与终态断开机制。
// 它解决什么问题：验证 SSE 消息流解析、3次指数阶梯退避（1s->2s->4s）、降级轮询（2s）触发、降级警告呈现与终态（succeeded/failed/cancelled）资源释放。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  parseSseLine,
  parseSseMessage,
  splitSseBuffer,
  calculateBackoffDelay,
  isJobTerminalStatus,
  jobFromStatus,
  applyJobEvent,
  JobStreamSubscriptionManager,
  TERMINAL_JOB_STATUSES,
} from '../../src/status/job-progress-sse.ts';

test('1. SSE 文本与多行消息解析 (parseSseLine & parseSseMessage)', () => {
  // 单行解析
  assert.equal(parseSseLine(':ping'), null, 'comment line should be ignored');
  assert.equal(parseSseLine('   '), null, 'empty line should be ignored');
  assert.deepEqual(parseSseLine('event: job_progress'), { field: 'event', value: 'job_progress' });
  assert.deepEqual(parseSseLine('data: {"status":"running"}'), {
    field: 'data',
    value: '{"status":"running"}',
  });
  assert.deepEqual(parseSseLine('id: 12345'), { field: 'id', value: '12345' });
  assert.deepEqual(parseSseLine('retry: 3000'), { field: 'retry', value: '3000' });

  // 完整消息包解析
  const rawStream = [
    ': heartbeat comment',
    'event: progress',
    'id: evt-1',
    'data: {"jobId":"job-01","percent":45,"status":"running"}',
    '',
    'event: done',
    'id: evt-2',
    'data: {"jobId":"job-01","percent":100,"status":"completed"}',
    '',
  ].join('\n');

  const events = parseSseMessage(rawStream);
  assert.equal(events.length, 2);

  assert.equal(events[0].event, 'progress');
  assert.equal(events[0].id, 'evt-1');
  assert.equal(events[0].data.percent, 45);
  assert.equal(events[0].data.status, 'running');

  assert.equal(events[1].event, 'done');
  assert.equal(events[1].id, 'evt-2');
  assert.equal(events[1].data.percent, 100);
  assert.equal(events[1].data.status, 'completed');
});

test('2. 指数退避延迟算法计算 (calculateBackoffDelay)', () => {
  // 基础退避基数 1000ms
  // 第 1 次重试: 1000ms (1s)
  assert.equal(calculateBackoffDelay(1, 1000), 1000);
  // 第 2 次重试: 2000ms (2s)
  assert.equal(calculateBackoffDelay(2, 1000), 2000);
  // 第 3 次重试: 4000ms (4s)
  assert.equal(calculateBackoffDelay(3, 1000), 4000);
  // 第 4 次重试 (若未限制): 8000ms
  assert.equal(calculateBackoffDelay(4, 1000), 8000);

  // 上限截断 maxMs 验证
  assert.equal(calculateBackoffDelay(5, 1000, 5000), 5000);

  // 边界保护
  assert.equal(calculateBackoffDelay(0), 0);
  assert.equal(calculateBackoffDelay(-1), 0);
});

test('3. 任务终态判定集合 (isJobTerminalStatus & TERMINAL_JOB_STATUSES)', () => {
  // 终态集合必须包含 completed, succeeded, failed, cancelled
  assert.ok(TERMINAL_JOB_STATUSES.has('completed'));
  assert.ok(TERMINAL_JOB_STATUSES.has('succeeded'));
  assert.ok(TERMINAL_JOB_STATUSES.has('failed'));
  assert.ok(TERMINAL_JOB_STATUSES.has('cancelled'));

  // 正例
  assert.equal(isJobTerminalStatus('completed'), true);
  assert.equal(isJobTerminalStatus('succeeded'), true);
  assert.equal(isJobTerminalStatus('failed'), true);
  assert.equal(isJobTerminalStatus('cancelled'), true);
  assert.equal(isJobTerminalStatus('COMPLETED'), true); // 忽略大小写

  // 运行中间态
  assert.equal(isJobTerminalStatus('pending'), false);
  assert.equal(isJobTerminalStatus('running'), false);
  assert.equal(isJobTerminalStatus(undefined), false);
  assert.equal(isJobTerminalStatus(null), false);
  assert.equal(isJobTerminalStatus(''), false);
});

const frame = (jobId, seq, type, payload) => `id: ${jobId}:${seq}\nevent: ${type}\ndata: ${JSON.stringify({ seq, id: `${jobId}:${seq}`, type, payload })}\n\n`;
const streamResponse = text => ({ ok: true, status: 200, body: null, text: async () => text, json: async () => ({}) });
const jsonResponse = (status, data) => ({ ok: status >= 200 && status < 300, status, body: null, text: async () => JSON.stringify(data), json: async () => data });
const settle = (ms = 30) => new Promise(resolve => setTimeout(resolve, ms));

test('4. 后台任务状态与事件换成页面进度数据', () => {
  const job = jobFromStatus({ id: 'job-1', type: 'parse', status: 'queued', progress: 0, message: '已排队', error: null, allowedActions: ['cancel'] });
  assert.deepEqual([job.jobId, job.jobType, job.status, job.percent, job.description, job.allowedActions], ['job-1', 'parse', 'pending', 0, '已排队', ['cancel']]);
  const running = applyJobEvent(job, { seq: 1, id: 'job-1:1', type: 'job.status_changed', payload: { from: 'queued', to: 'running' } });
  assert.equal(running.status, 'running');
  const progress = applyJobEvent(running, { seq: 2, id: 'job-1:2', type: 'job.progress', payload: { progress: 40, message: 'RAGFlow 正在识别' } });
  assert.deepEqual([progress.percent, progress.description], [40, 'RAGFlow 正在识别']);
  const failed = applyJobEvent(progress, { seq: 3, id: 'job-1:3', type: 'job.failed', payload: { status: 'failed', completed_at: 't', error: 'PARSER_UNAVAILABLE' } });
  assert.deepEqual([failed.status, failed.errorCode, failed.allowedActions], ['failed', 'PARSER_UNAVAILABLE', ['retry']]);
  const failedStatus = jobFromStatus({ id: 'job-2', type: 'parse', status: 'failed', progress: 100, message: 'x', error: { code: 'INTERNAL_ERROR', message: '中断' } });
  assert.deepEqual([failedStatus.errorCode, failedStatus.errorMessage], ['INTERNAL_ERROR', '中断']);
  assert.deepEqual(splitSseBuffer('id: a\ndata: 1\n\nid: b\nda'), { complete: 'id: a\ndata: 1\n\n', rest: 'id: b\nda' });
});

test('5. 事件流带令牌与 Last-Event-ID；后台到时关闭后续连，任务结束即停止', async () => {
  const calls = [];
  const replies = [
    streamResponse(frame('job-5', 1, 'job.status_changed', { from: 'queued', to: 'running' }) + frame('job-5', 2, 'job.progress', { progress: 30, message: '识别中' })),
    streamResponse(': keep-alive\n\n' + frame('job-5', 3, 'job.completed', { status: 'completed', completed_at: 't', error: null })),
  ];
  const updates = [];
  let terminal = null;
  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-5', token: 'tok', reconnectDelayMs: 1,
    fetchFn: async (url, init) => { calls.push({ url, headers: init.headers }); return replies.shift(); },
    onJobUpdate: job => updates.push(job), onTerminal: job => { terminal = job; },
  });
  manager.connect();
  await settle();
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, '/api/v1/jobs/job-5/events');
  assert.equal(calls[0].headers.Authorization, 'Bearer tok');
  assert.equal(calls[0].headers['Last-Event-ID'], undefined);
  assert.equal(calls[1].headers['Last-Event-ID'], 'job-5:2');
  assert.deepEqual(updates.map(u => [u.status, u.percent]), [['running', undefined], ['running', 30], ['completed', 100]]);
  assert.equal(terminal.status, 'completed');
  assert.equal(manager.getStatus(), 'closed');
});

test('6. 出错 3 次退避后改为带令牌轮询，轮询中再试实时流成功即恢复', async () => {
  const calls = [];
  let streamAttempts = 0;
  const statuses = [];
  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-6', token: 'tok', maxRetries: 3, baseBackoffMs: 1, pollingIntervalMs: 1, resumeEveryPolls: 2, reconnectDelayMs: 1,
    fetchFn: async (url, init) => {
      calls.push({ url, auth: init.headers.Authorization });
      if (url.endsWith('/events')) {
        streamAttempts += 1;
        if (streamAttempts <= 4) throw new TypeError('network down');
        return streamResponse(frame('job-6', 9, 'job.completed', { status: 'completed', completed_at: 't', error: null }));
      }
      return jsonResponse(200, { id: 'job-6', type: 'parse', status: 'running', progress: 60, message: '识别中', error: null, events: [{ seq: 8, id: 'job-6:8', type: 'job.progress' }] });
    },
    onStatusChange: (status, meta) => statuses.push([status, meta.isFallback]),
  });
  manager.connect();
  await settle(80);
  assert.ok(statuses.some(([status, fallback]) => status === 'polling' && fallback), JSON.stringify(statuses));
  assert.ok(calls.filter(c => !c.url.endsWith('/events')).length >= 2);
  assert.ok(calls.every(c => c.auth === 'Bearer tok'));
  assert.ok(statuses.some(([status, fallback]) => status === 'connected' && !fallback), '轮询期间恢复实时流');
  assert.equal(manager.getJob().status, 'completed');
  assert.equal(manager.getStatus(), 'closed');
});

test('7. 401/404 立即停止，不无限重试；断开后不再发请求', async () => {
  for (const status of [401, 404]) {
    let count = 0;
    const statuses = [];
    const manager = new JobStreamSubscriptionManager({
      jobId: 'job-7', token: 'tok', baseBackoffMs: 1,
      fetchFn: async () => { count += 1; return jsonResponse(status, {}); },
      onStatusChange: (value, meta) => statuses.push([value, meta.reason]),
    });
    manager.connect();
    await settle();
    assert.equal(count, 1);
    assert.equal(manager.getStatus(), 'error');
    assert.ok(statuses.at(-1)[1]);
  }
  let count = 0;
  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-8', reconnectDelayMs: 5,
    fetchFn: async () => { count += 1; return streamResponse(''); },
  });
  manager.connect();
  await settle(1);
  manager.disconnect();
  const seen = count;
  await settle(30);
  assert.equal(count, seen);
  assert.equal(manager.getStatus(), 'closed');
  const done = new JobStreamSubscriptionManager({ jobId: 'job-9', initialJob: { jobId: 'job-9', jobType: 'parse', status: 'completed' },
    fetchFn: async () => { throw new Error('must not fetch'); } });
  done.connect();
  assert.equal(done.getStatus(), 'closed');
});
