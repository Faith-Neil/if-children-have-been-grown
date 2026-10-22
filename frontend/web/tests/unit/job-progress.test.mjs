// 为什么有这个测试：验证后台长任务 JobProgress 的核心状态机、AI任务判定、进度推导与色彩隔离纯逻辑。
// 它解决什么问题：确保 5 类任务状态流转正确，AI 任务严格使用专属紫色且非 AI 业务严禁使用紫色，步骤加权进度计算无误差。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  JOB_PROGRESS_COLORS,
  AI_JOB_TYPES,
  isAiJob,
  resolveProgressStrokeColor,
  deriveJobProgress,
  resolveJobStatusMeta,
  formatDuration,
  getJobTypeLabel,
} from '../../src/status/job-progress.ts';

test('1. 状态机与状态元信息映射 (resolveJobStatusMeta)', () => {
  const pending = resolveJobStatusMeta('pending');
  assert.equal(pending.text, '等待中');
  assert.equal(pending.badgeStatus, 'warning');
  assert.equal(pending.progressStatus, 'normal');

  const running = resolveJobStatusMeta('running');
  assert.equal(running.text, '执行中');
  assert.equal(running.badgeStatus, 'processing');
  assert.equal(running.progressStatus, 'active');

  const completed = resolveJobStatusMeta('completed');
  assert.equal(completed.text, '已完成');
  assert.equal(completed.badgeStatus, 'success');
  assert.equal(completed.progressStatus, 'success');

  const failed = resolveJobStatusMeta('failed');
  assert.equal(failed.text, '执行失败');
  assert.equal(failed.badgeStatus, 'error');
  assert.equal(failed.progressStatus, 'exception');

  const cancelled = resolveJobStatusMeta('cancelled');
  assert.equal(cancelled.text, '已取消');
  assert.equal(cancelled.badgeStatus, 'default');
  assert.equal(cancelled.progressStatus, 'normal');
});

test('2. AI 任务类型判定规则 (isAiJob)', () => {
  // 内置 AI 类型正例
  assert.equal(isAiJob('generate_chapter'), true);
  assert.equal(isAiJob('generate_outline'), true);
  assert.equal(isAiJob('chapter_summary'), true);
  assert.equal(isAiJob('model_review'), true);
  assert.equal(isAiJob('model_review_batch'), true);
  assert.equal(isAiJob('assistant_qa'), true);
  assert.equal(isAiJob('assistant_suggest'), true);
  assert.equal(isAiJob('ragflow_retrieval'), true);
  assert.equal(isAiJob('evidence_matching'), true);
  assert.equal(isAiJob('matrix_match'), true);
  assert.equal(isAiJob('attachment_recognize'), true);
  assert.equal(isAiJob('generation'), true);
  assert.equal(isAiJob('loop'), true);

  // 前缀适配与大小写宽容
  assert.equal(isAiJob('GENERATE_CHAPTER'), true);
  assert.equal(isAiJob('ai_text_polishing'), true);
  assert.equal(isAiJob('model_evaluation'), true);

  // 普通业务任务反例（严禁识别为 AI 任务）
  assert.equal(isAiJob('export'), false);
  assert.equal(isAiJob('bid_export'), false);
  assert.equal(isAiJob('compliance'), false);
  assert.equal(isAiJob('compliance_check'), false);
  assert.equal(isAiJob('incremental_check'), false);
  assert.equal(isAiJob('dup_check'), false);
  assert.equal(isAiJob('kb_import'), false);
  assert.equal(isAiJob('kb_rebuild'), false);
  assert.equal(isAiJob('lock_sweep'), false);
  assert.equal(isAiJob('cleanup'), false);
  assert.equal(isAiJob('audit_anchor'), false);
  assert.equal(isAiJob(undefined), false);

  // 显式 isAi 标志优先级最高
  assert.equal(isAiJob('export', true), true); // 显式强制为 AI
  assert.equal(isAiJob('generate_chapter', false), false); // 显式覆盖为非 AI
});

test('3. 进度条色彩与规范隔离 (resolveProgressStrokeColor)', () => {
  // AI 运行态与等待态必须使用 AI 紫色
  assert.equal(resolveProgressStrokeColor('running', true), JOB_PROGRESS_COLORS.aiProgress);
  assert.equal(resolveProgressStrokeColor('pending', true), JOB_PROGRESS_COLORS.aiProgress);
  assert.equal(JOB_PROGRESS_COLORS.aiProgress, '#722ed1');

  // 普通业务任务严禁使用紫色，必须使用默认业务蓝色
  assert.equal(resolveProgressStrokeColor('running', false), JOB_PROGRESS_COLORS.defaultProgress);
  assert.equal(resolveProgressStrokeColor('pending', false), JOB_PROGRESS_COLORS.defaultProgress);
  assert.equal(JOB_PROGRESS_COLORS.defaultProgress, '#1e4db7');
  assert.notEqual(resolveProgressStrokeColor('running', false), '#722ed1');

  // 终态色彩一致性
  assert.equal(resolveProgressStrokeColor('completed', true), JOB_PROGRESS_COLORS.success);
  assert.equal(resolveProgressStrokeColor('completed', false), JOB_PROGRESS_COLORS.success);
  assert.equal(resolveProgressStrokeColor('failed', true), JOB_PROGRESS_COLORS.error);
  assert.equal(resolveProgressStrokeColor('failed', false), JOB_PROGRESS_COLORS.error);
  assert.equal(resolveProgressStrokeColor('cancelled', true), JOB_PROGRESS_COLORS.cancelled);
  assert.equal(resolveProgressStrokeColor('cancelled', false), JOB_PROGRESS_COLORS.cancelled);
});

test('4. 总体进度推导算法 (deriveJobProgress)', () => {
  // 已完成状态强制为 100
  assert.equal(deriveJobProgress({ status: 'completed' }), 100);
  assert.equal(deriveJobProgress({ status: 'completed', explicitPercent: 45 }), 100);

  // 显式 percent 优先，并确保 0-100 整数截断
  assert.equal(deriveJobProgress({ status: 'running', explicitPercent: 67.4 }), 67);
  assert.equal(deriveJobProgress({ status: 'running', explicitPercent: 120 }), 100);
  assert.equal(deriveJobProgress({ status: 'running', explicitPercent: -10 }), 0);

  // 无步骤默认值
  assert.equal(deriveJobProgress({ status: 'pending' }), 0);
  assert.equal(deriveJobProgress({ status: 'running' }), 0);

  // 基于子步骤自动推导
  const steps = [
    { key: 'step1', title: '提取需求', status: 'completed' }, // 100
    { key: 'step2', title: '检索依据', status: 'completed' }, // 100
    { key: 'step3', title: '模型生成', status: 'running', percent: 60 }, // 60
    { key: 'step4', title: '格式校验', status: 'pending' }, // 0
  ];
  // 平均： (100 + 100 + 60 + 0) / 4 = 65
  assert.equal(deriveJobProgress({ status: 'running', steps }), 65);

  // 包含未设 percent 的 running 步骤默认折算 50%
  const stepsWithDefaultRunning = [
    { key: 'step1', title: '提取需求', status: 'completed' }, // 100
    { key: 'step2', title: '模型生成', status: 'running' }, // 默认 50
  ];
  assert.equal(deriveJobProgress({ status: 'running', steps: stepsWithDefaultRunning }), 75);
});

test('5. 耗时格式化函数 (formatDuration)', () => {
  assert.equal(formatDuration(undefined), '-');
  assert.equal(formatDuration(-10), '-');
  assert.equal(formatDuration(0), '0ms');
  assert.equal(formatDuration(450), '450ms');
  assert.equal(formatDuration(1500), '1.5s');
  assert.equal(formatDuration(12400), '12.4s');
  assert.equal(formatDuration(65000), '1m 5s');
  assert.equal(formatDuration(125000), '2m 5s');
});

test('6. 任务类型中文名称与标签 (getJobTypeLabel)', () => {
  assert.equal(getJobTypeLabel('generate_chapter'), '章节生成');
  assert.equal(getJobTypeLabel('compliance_check'), '标书合规审查');
  assert.equal(getJobTypeLabel('export'), '文档导出');
  assert.equal(getJobTypeLabel('matrix_match'), '响应矩阵匹配');
  assert.equal(getJobTypeLabel('unknown_custom_job'), 'unknown_custom_job');
  assert.equal(getJobTypeLabel(''), '后台任务');
});
