// 为什么有这个测试：验证任务中心与顶栏任务角标的核心业务逻辑、多维筛选、AI紫色隔离与操作权限。
// 它解决什么问题：
// 1. 确保顶栏角标准确统计“当前公司运行中 + 排队中”的任务数，且严格保障租户数据隔离；
// 2. 覆盖任务中心全部、运行中、已完成、异常失败四分类筛选与准确计数；
// 3. 严格验证 AI 任务专属紫（#722ed1 / purple）与常规业务蓝（#1e4db7 / blue）的色彩隔离底线；
// 4. 验证 allowedActions 权限矩阵：仅失败步骤允许“重试”，仅运行中/排队中允许“取消”；
// 5. 验证异常情况下的容错：空数据、异常字段、非法状态不抛异常且安全归一化。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateActiveTaskCount,
  computeTaskCounts,
  filterTasks,
  normalizeTask,
  canPerformTaskAction,
  isTaskRunning,
  isTaskCompleted,
  isTaskFailed,
  isTaskCancelled,
  formatTaskTime,
  getJobTypeLabel,
  isAiJob,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
} from '../../src/shell/task-center.ts';
import { JOB_PROGRESS_COLORS } from '../../src/status/job-progress.ts';

test('1. 顶栏角标计数 (calculateActiveTaskCount)：统计运行中+排队中任务并保障多租户隔离', () => {
  const mixedTasks = [
    { id: 't1', status: 'running', company_id: 'alpha' },
    { id: 't2', status: 'pending', company_id: 'alpha' },
    { id: 't3', status: 'queued', company_id: 'alpha' },
    { id: 't4', status: 'completed', company_id: 'alpha' },
    { id: 't5', status: 'failed', company_id: 'alpha' },
    { id: 't6', status: 'cancelled', company_id: 'alpha' },
    // 属于 beta 公司的任务，严禁串入 alpha
    { id: 't7', status: 'running', company_id: 'beta' },
    { id: 't8', status: 'pending', company_id: 'beta' },
  ];

  // alpha 公司运行中 + 排队中应该只有 t1, t2, t3（共 3 个）
  const alphaActive = calculateActiveTaskCount(mixedTasks, 'alpha');
  assert.equal(alphaActive, 3);

  // beta 公司运行中 + 排队中应该只有 t7, t8（共 2 个）
  const betaActive = calculateActiveTaskCount(mixedTasks, 'beta');
  assert.equal(betaActive, 2);

  // 全量不带 company 筛选时，应统计所有租户的活跃任务 (3 + 2 = 5)
  const totalActive = calculateActiveTaskCount(mixedTasks);
  assert.equal(totalActive, 5);

  // 边界安全验证：空数组或 null
  assert.equal(calculateActiveTaskCount([]), 0);
  assert.equal(calculateActiveTaskCount(null), 0);
});

test('2. 任务状态谓词判定 (isTaskRunning, isTaskCompleted, isTaskFailed, isTaskCancelled)', () => {
  // 运行中 / 排队中
  assert.equal(isTaskRunning('running'), true);
  assert.equal(isTaskRunning('RUNNING'), true);
  assert.equal(isTaskRunning('pending'), true);
  assert.equal(isTaskRunning('queued'), true);
  assert.equal(isTaskRunning('completed'), false);
  assert.equal(isTaskRunning('failed'), false);

  // 已完成
  assert.equal(isTaskCompleted('completed'), true);
  assert.equal(isTaskCompleted('succeeded'), true);
  assert.equal(isTaskCompleted('running'), false);
  assert.equal(isTaskCompleted('failed'), false);

  // 异常失败
  assert.equal(isTaskFailed('failed'), true);
  assert.equal(isTaskFailed('FAILED'), true);
  assert.equal(isTaskFailed('completed'), false);
  assert.equal(isTaskFailed('running'), false);

  // 已取消
  assert.equal(isTaskCancelled('cancelled'), true);
  assert.equal(isTaskCancelled('completed'), false);
});

test('3. 数据归一化 (normalizeTask)：双结构兼容、字段派生与百分比钳位', () => {
  // 3.1 兼容后端 Job 简单结构
  const simpleJob = {
    id: 'job-101',
    project_id: 'proj-001',
    type: 'generate_chapter',
    status: 'running',
    progress: 45,
    message: '正在生成商务标第三章',
    created_at: '2026-10-26T10:00:00Z',
    completed_at: '',
    error: null,
    recoverable: true,
  };

  const normalized = normalizeTask(simpleJob);
  assert.equal(normalized.id, 'job-101');
  assert.equal(normalized.projectId, 'proj-001');
  assert.equal(normalized.type, 'generate_chapter');
  assert.equal(normalized.title, '章节生成');
  assert.equal(normalized.status, 'running');
  assert.equal(normalized.progress, 45);
  assert.equal(normalized.isAi, true); // AI 任务自动识别
  assert.deepEqual(normalized.allowedActions, ['cancel']); // 运行中默认允许取消

  // 3.2 兼容富状态 JobProgressData 结构
  const richJob = {
    jobId: 'job-102',
    jobType: 'bid_export',
    status: 'failed',
    percent: 80,
    steps: [
      { key: 'step-1', title: '格式校验', status: 'completed' },
      { key: 'step-2', title: '两卷组装', status: 'failed', errorMessage: '模板损坏' },
    ],
    currentStepKey: 'step-2',
    errorCode: 'TEMPLATE_INVALID',
    errorMessage: '模板格式解析错误',
    traceId: 'req-trace-999',
    durationMs: 12500,
  };

  const normalizedRich = normalizeTask(richJob);
  assert.equal(normalizedRich.id, 'job-102');
  assert.equal(normalizedRich.type, 'bid_export');
  assert.equal(normalizedRich.title, '标书整本导出');
  assert.equal(normalizedRich.status, 'failed');
  assert.equal(normalizedRich.isAi, false); // 导出非 AI 任务
  assert.equal(normalizedRich.currentStepTitle, '两卷组装'); // 正确解析失败步骤名
  assert.equal(normalizedRich.errorCode, 'TEMPLATE_INVALID');
  assert.equal(normalizedRich.traceId, 'req-trace-999');
  assert.equal(normalizedRich.durationMs, 12500);
  assert.deepEqual(normalizedRich.allowedActions, ['retry']); // 失败默认允许重试

  // 3.3 完成态自动推导 100% 进度
  const completedTask = normalizeTask({ id: 'c1', status: 'completed', progress: 50 });
  assert.equal(completedTask.progress, 100);

  // 3.4 异常越界进度钳位在 0-100
  const clamped1 = normalizeTask({ id: 'cl1', status: 'running', progress: 150 });
  assert.equal(clamped1.progress, 100);
  const clamped2 = normalizeTask({ id: 'cl2', status: 'running', progress: -20 });
  assert.equal(clamped2.progress, 0);
});

test('4. 四分类筛选与统计 (computeTaskCounts & filterTasks)', () => {
  const tasks = [
    normalizeTask({ id: '1', title: 'AI生成1', type: 'generate_chapter', status: 'running', company_id: 'alpha' }),
    normalizeTask({ id: '2', title: 'AI大纲2', type: 'generate_outline', status: 'pending', company_id: 'alpha' }),
    normalizeTask({ id: '3', title: '排队任务3', type: 'export', status: 'queued', company_id: 'alpha' }),
    normalizeTask({ id: '4', title: '成功导出4', type: 'bid_export', status: 'completed', company_id: 'alpha' }),
    normalizeTask({ id: '5', title: '成功检查5', type: 'compliance', status: 'succeeded', company_id: 'alpha' }),
    normalizeTask({ id: '6', title: '失败重试6', type: 'model_review', status: 'failed', company_id: 'alpha' }),
    normalizeTask({ id: '7', title: '已取消7', type: 'export', status: 'cancelled', company_id: 'alpha' }),
  ];

  // 统计四个分类数量
  const counts = computeTaskCounts(tasks, 'alpha');
  assert.equal(counts.all, 7);
  assert.equal(counts.running, 3); // running(1) + pending(2) + queued(3)
  assert.equal(counts.completed, 2); // completed(4) + succeeded(5)
  assert.equal(counts.failed, 1); // failed(6)

  // 按分类过滤
  const allList = filterTasks(tasks, 'all');
  assert.equal(allList.length, 7);

  const runningList = filterTasks(tasks, 'running');
  assert.equal(runningList.length, 3);
  assert.deepEqual(runningList.map(t => t.id), ['1', '2', '3']);

  const completedList = filterTasks(tasks, 'completed');
  assert.equal(completedList.length, 2);
  assert.deepEqual(completedList.map(t => t.id), ['4', '5']);

  const failedList = filterTasks(tasks, 'failed');
  assert.equal(failedList.length, 1);
  assert.equal(failedList[0].id, '6');

  // 关键词检索
  const searchResult = filterTasks(tasks, 'all', { searchQuery: '大纲' });
  assert.equal(searchResult.length, 1);
  assert.equal(searchResult[0].id, '2');
});

test('5. 操作权限校验防线 (canPerformTaskAction)', () => {
  const failedTask = normalizeTask({
    id: 'f1',
    status: 'failed',
    allowedActions: ['retry'],
  });
  // 失败任务允许 retry，拒绝 cancel
  assert.equal(canPerformTaskAction(failedTask, 'retry'), true);
  assert.equal(canPerformTaskAction(failedTask, 'cancel'), false);

  const runningTask = normalizeTask({
    id: 'r1',
    status: 'running',
    allowedActions: ['cancel'],
  });
  // 运行中任务允许 cancel，拒绝 retry
  assert.equal(canPerformTaskAction(runningTask, 'cancel'), true);
  assert.equal(canPerformTaskAction(runningTask, 'retry'), false);

  const completedTask = normalizeTask({
    id: 'c1',
    status: 'completed',
    allowedActions: [],
  });
  // 已完成任务两者皆不允许
  assert.equal(canPerformTaskAction(completedTask, 'retry'), false);
  assert.equal(canPerformTaskAction(completedTask, 'cancel'), false);

  // 即使声明了 retry，但如果状态是 running，严格防御拒绝
  const malformed = normalizeTask({
    id: 'm1',
    status: 'running',
    allowedActions: ['retry'],
  });
  assert.equal(canPerformTaskAction(malformed, 'retry'), false);
});

test('6. AI 任务色彩隔离红线验证 (resolveProgressStrokeColor & isAiJob)', () => {
  // 6.1 验证 AI 任务使用专属 AI 紫色 (#722ed1)
  assert.equal(isAiJob('generate_chapter'), true);
  assert.equal(isAiJob('generate_outline'), true);
  assert.equal(isAiJob('assistant_qa'), true);
  assert.equal(isAiJob('model_review'), true);

  const aiStrokeRunning = resolveProgressStrokeColor('running', true);
  assert.equal(aiStrokeRunning, JOB_PROGRESS_COLORS.aiProgress);
  assert.equal(aiStrokeRunning, '#722ed1');

  // 6.2 验证非 AI 业务严禁使用紫色，必须使用企业主蓝色 (#1e4db7)
  assert.equal(isAiJob('export'), false);
  assert.equal(isAiJob('bid_export'), false);
  assert.equal(isAiJob('compliance'), false);
  assert.equal(isAiJob('compliance_check'), false);
  assert.equal(isAiJob('kb_import'), false);

  const businessStrokeRunning = resolveProgressStrokeColor('running', false);
  assert.equal(businessStrokeRunning, JOB_PROGRESS_COLORS.defaultProgress);
  assert.equal(businessStrokeRunning, '#1e4db7');
  assert.notEqual(businessStrokeRunning, '#722ed1');

  // 6.3 失败与成功颜色不受 AI 影响，保持统一绿/红
  assert.equal(resolveProgressStrokeColor('completed', true), JOB_PROGRESS_COLORS.success);
  assert.equal(resolveProgressStrokeColor('completed', false), JOB_PROGRESS_COLORS.success);
  assert.equal(resolveProgressStrokeColor('failed', true), JOB_PROGRESS_COLORS.error);
  assert.equal(resolveProgressStrokeColor('failed', false), JOB_PROGRESS_COLORS.error);
});

test('7. 时间与耗时格式化友好渲染 (formatTaskTime & resolveJobStatusMeta)', () => {
  const timeStr = '2026-10-26T14:30:00Z';
  const formatted = formatTaskTime(timeStr);
  assert.match(formatted, /\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}/);

  // 非法时间优雅回退
  assert.equal(formatTaskTime(''), '-');
  assert.equal(formatTaskTime(undefined), '-');

  // 状态元信息
  const runningMeta = resolveJobStatusMeta('running');
  assert.equal(runningMeta.badgeStatus, 'processing');
  assert.equal(runningMeta.text, '执行中');

  const failedMeta = resolveJobStatusMeta('failed');
  assert.equal(failedMeta.badgeStatus, 'error');
  assert.equal(failedMeta.text, '执行失败');
});
