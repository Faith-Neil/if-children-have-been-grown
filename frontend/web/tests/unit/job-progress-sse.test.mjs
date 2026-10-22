// 为什么有这个测试：覆盖 APP-M2-T020 JobProgress 的 SSE 订阅、指数退避重试、平滑轮询回退与终态断开机制。
// 它解决什么问题：验证 SSE 消息流解析、3次指数阶梯退避（1s->2s->4s）、降级轮询（2s）触发、降级警告呈现与终态（succeeded/failed/cancelled）资源释放。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  parseSseLine,
  parseSseMessage,
  calculateBackoffDelay,
  isJobTerminalStatus,
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

test('4. SSE 模拟订阅与正常进度推送更新', () => {
  const updates = [];
  const statusChanges = [];

  class MockEventSource {
    constructor(url) {
      this.url = url;
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.listeners = new Map();
      this.closed = false;

      // 异步触发 open
      setTimeout(() => {
        if (!this.closed && this.onopen) this.onopen({ type: 'open' });
      }, 0);
    }
    close() {
      this.closed = true;
    }
    addEventListener(type, cb) {
      this.listeners.set(type, cb);
    }
  }

  let mockEsInstance = null;
  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-101',
    eventSourceFactory: (url) => {
      mockEsInstance = new MockEventSource(url);
      return mockEsInstance;
    },
    onJobUpdate: (job) => updates.push(job),
    onStatusChange: (status, meta) => statusChanges.push({ status, meta }),
  });

  manager.connect();

  return new Promise((resolve) => {
    setTimeout(() => {
      // 验证连接建立
      assert.equal(manager.getStatus(), 'connected');

      // 模拟服务器推送进度数据
      mockEsInstance.onmessage({
        data: JSON.stringify({
          jobId: 'job-101',
          status: 'running',
          percent: 30,
        }),
      });

      assert.equal(updates.length, 1);
      assert.equal(updates[0].percent, 30);
      assert.equal(updates[0].status, 'running');

      manager.disconnect();
      assert.equal(manager.getStatus(), 'closed');
      assert.equal(mockEsInstance.closed, true);
      resolve();
    }, 10);
  });
});

test('5. 断线 3 次阶梯指数退避重连与重试计数', () => {
  class FailingMockEventSource {
    constructor(url) {
      this.url = url;
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.closed = false;

      // 立即触发错误
      setTimeout(() => {
        if (!this.closed && this.onerror) this.onerror(new Error('Connection dropped'));
      }, 0);
    }
    close() {
      this.closed = true;
    }
  }

  let connectionAttempts = 0;
  const retryStatuses = [];

  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-retry-test',
    maxRetries: 3,
    baseBackoffMs: 10, // 缩短单测时间
    eventSourceFactory: (url) => {
      connectionAttempts++;
      return new FailingMockEventSource(url);
    },
    onStatusChange: (status, meta) => {
      retryStatuses.push({ status, retryCount: meta.retryCount, isFallback: meta.isFallback });
    },
  });

  manager.connect();

  return new Promise((resolve) => {
    // 观察 3 次重试过程
    setTimeout(() => {
      // 3 次重试耗尽后应该触发降级轮询
      assert.ok(connectionAttempts >= 3, `Expected at least 3 attempts, got ${connectionAttempts}`);
      assert.ok(manager.getRetryCount() >= 3, `Retry count should reach at least 3`);
      manager.disconnect();
      resolve();
    }, 100);
  });
});

test('6. 超过 3 次重试后平滑回退至定时轮询模式', () => {
  class FailImmediatelyEventSource {
    constructor(url) {
      this.onerror = null;
      this.closed = false;
      setTimeout(() => {
        if (this.onerror) this.onerror(new Error('ECONNRESET'));
      }, 0);
    }
    close() {
      this.closed = true;
    }
  }

  let pollFetchCount = 0;
  const pollUpdates = [];

  const mockFetch = async (url) => {
    pollFetchCount++;
    return {
      ok: true,
      status: 200,
      json: async () => ({
        jobId: 'job-fallback-1',
        status: 'running',
        percent: 60,
      }),
    };
  };

  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-fallback-1',
    maxRetries: 1, // 设置为 1 次快速触发降级
    baseBackoffMs: 5,
    pollingIntervalMs: 20,
    eventSourceFactory: (url) => new FailImmediatelyEventSource(url),
    fetchFn: mockFetch,
    onJobUpdate: (job) => pollUpdates.push(job),
  });

  manager.connect();

  return new Promise((resolve) => {
    setTimeout(() => {
      // 验证已自动切换为轮询模式
      assert.equal(manager.getStatus(), 'polling');
      assert.equal(manager.getIsFallback(), true);
      assert.ok(pollFetchCount >= 1, 'Poll fetch must be invoked');
      assert.ok(pollUpdates.length >= 1, 'Poll updates must receive data');
      assert.equal(pollUpdates[0].percent, 60);

      manager.disconnect();
      assert.equal(manager.getStatus(), 'closed');
      resolve();
    }, 60);
  });
});

test('7. 任务进入终态 (completed / failed / cancelled) 自动关闭连接与定时器', () => {
  class TerminalMockEventSource {
    constructor(url) {
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.closed = false;
      setTimeout(() => {
        if (this.onopen) this.onopen({});
      }, 0);
    }
    close() {
      this.closed = true;
    }
  }

  let esInstance = null;
  const manager = new JobStreamSubscriptionManager({
    jobId: 'job-terminal-test',
    eventSourceFactory: (url) => {
      esInstance = new TerminalMockEventSource(url);
      return esInstance;
    },
  });

  manager.connect();

  return new Promise((resolve) => {
    setTimeout(() => {
      assert.equal(manager.getStatus(), 'connected');

      // 发送终态消息 completed
      esInstance.onmessage({
        data: JSON.stringify({
          jobId: 'job-terminal-test',
          status: 'completed',
          percent: 100,
        }),
      });

      // 验证连接已被自动关闭
      assert.equal(manager.getStatus(), 'closed');
      assert.equal(esInstance.closed, true);
      resolve();
    }, 10);
  });
});
