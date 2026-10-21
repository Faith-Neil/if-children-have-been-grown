// 为什么有这个文件：验证通用状态组件的核心规则、错误体解析与对比度约束。
// 它解决什么问题：确保错误体、追踪号提取、无权限保护与 WCAG 4.5:1 对比度符合规范。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from '../../frontend/web/src/api.ts';
import {
  STATUS_CONTRAST_TOKENS,
  contrastRatio,
  extractErrorInfo,
  copyText,
  resolveEmptyState,
  resolveForbidden,
  resolveExpired,
  resolveReadonly,
} from '../../frontend/web/src/status-views.ts';

test('WCAG 4.5:1 text contrast compliance for all status view colors', () => {
  // 1. 警告文字对比度 (针对黄色/橙色文字在浅底对比度不足的历史痛点)
  const warningTextRatio = contrastRatio(STATUS_CONTRAST_TOKENS.warningText, STATUS_CONTRAST_TOKENS.cardBg);
  assert.ok(warningTextRatio >= 4.5, `warningText contrast on white is ${warningTextRatio.toFixed(2)}, must be >= 4.5`);

  const warningBgRatio = contrastRatio(STATUS_CONTRAST_TOKENS.warningText, STATUS_CONTRAST_TOKENS.warningBg);
  assert.ok(warningBgRatio >= 4.5, `warningText contrast on warningBg is ${warningBgRatio.toFixed(2)}, must be >= 4.5`);

  const warningDescRatio = contrastRatio(STATUS_CONTRAST_TOKENS.warningDesc, STATUS_CONTRAST_TOKENS.warningBg);
  assert.ok(warningDescRatio >= 4.5, `warningDesc contrast on warningBg is ${warningDescRatio.toFixed(2)}, must be >= 4.5`);

  // 2. 主品牌色与正文对比度
  const textRatio = contrastRatio(STATUS_CONTRAST_TOKENS.text, STATUS_CONTRAST_TOKENS.cardBg);
  assert.ok(textRatio >= 7.0, `main text contrast is ${textRatio.toFixed(2)}, exceeds AAA standard`);

  const mutedRatio = contrastRatio(STATUS_CONTRAST_TOKENS.muted, STATUS_CONTRAST_TOKENS.cardBg);
  assert.ok(mutedRatio >= 4.5, `muted text contrast is ${mutedRatio.toFixed(2)}, must be >= 4.5`);

  const primaryRatio = contrastRatio(STATUS_CONTRAST_TOKENS.primary, STATUS_CONTRAST_TOKENS.cardBg);
  assert.ok(primaryRatio >= 4.5, `primary contrast is ${primaryRatio.toFixed(2)}, must be >= 4.5`);

  // 3. 错误红色对比度
  const errorRatio = contrastRatio(STATUS_CONTRAST_TOKENS.error, STATUS_CONTRAST_TOKENS.cardBg);
  assert.ok(errorRatio >= 4.5, `error red contrast is ${errorRatio.toFixed(2)}, must be >= 4.5`);
});

test('extractErrorInfo safely extracts code, message, traceId, status, and details', () => {
  // 1. ApiError 实例提取
  const apiError = new ApiError(409, 'LOCK_CONFLICT', '章节正在被其他编写人编辑。', 'trace-req-001', { lock_owner: 'user-2' });
  const extractedApi = extractErrorInfo(apiError);
  assert.equal(extractedApi.code, 'LOCK_CONFLICT');
  assert.equal(extractedApi.message, '章节正在被其他编写人编辑。');
  assert.equal(extractedApi.traceId, 'trace-req-001');
  assert.equal(extractedApi.status, 409);
  assert.deepEqual(extractedApi.details, { lock_owner: 'user-2' });

  // 2. v1 结构化错误对象提取
  const v1Obj = {
    code: 'MODEL_UNAVAILABLE',
    message: '模型推理服务暂不可用。',
    traceId: 'trace-v1-999',
    details: { provider: 'mock' },
  };
  const extractedV1 = extractErrorInfo(v1Obj);
  assert.equal(extractedV1.code, 'MODEL_UNAVAILABLE');
  assert.equal(extractedV1.message, '模型推理服务暂不可用。');
  assert.equal(extractedV1.traceId, 'trace-v1-999');

  // 3. 旧版嵌套 error 对象提取 (兼容 error.code 与 request_id)
  const legacyObj = {
    error: { code: 'LEASE_EXPIRED', message: '独占编辑锁已失效。' },
    request_id: 'legacy-trace-555',
  };
  const extractedLegacy = extractErrorInfo(legacyObj);
  assert.equal(extractedLegacy.code, 'LEASE_EXPIRED');
  assert.equal(extractedLegacy.message, '独占编辑锁已失效。');
  assert.equal(extractedLegacy.traceId, 'legacy-trace-555');

  // 4. 标准 Error 实例
  const stdError = new Error('网络连接超时，请重试');
  const extractedStd = extractErrorInfo(stdError);
  assert.equal(extractedStd.code, 'REQUEST_FAILED');
  assert.equal(extractedStd.message, '网络连接超时，请重试');

  // 5. 纯字符串错误
  const strError = '系统正在维护中';
  const extractedStr = extractErrorInfo(strError);
  assert.equal(extractedStr.code, 'ERROR');
  assert.equal(extractedStr.message, '系统正在维护中');

  // 6. null / 空值安全降级
  const nullExtracted = extractErrorInfo(null, '默认错误消息');
  assert.equal(nullExtracted.code, 'REQUEST_FAILED');
  assert.equal(nullExtracted.message, '默认错误消息');
});

test('resolveEmptyState resolves defaults for empty, filtered, and search modes', () => {
  // empty 模式
  const emptyRes = resolveEmptyState({ mode: 'empty' });
  assert.equal(emptyRes.title, '暂无数据');
  assert.equal(emptyRes.actionText, undefined);

  // filtered 模式 (清除筛选引导)
  const filterRes = resolveEmptyState({ mode: 'filtered' });
  assert.equal(filterRes.title, '没有符合条件的记录');
  assert.equal(filterRes.description, '请尝试调整或重置筛选条件');
  assert.equal(filterRes.actionText, '清除筛选');

  // search 模式 (带关键字引导)
  const searchRes = resolveEmptyState({ mode: 'search', searchKeyword: '招标文件' });
  assert.equal(searchRes.title, '未找到匹配结果');
  assert.equal(searchRes.description, '没有找到名称包含“招标文件”的项目或资料');

  // 自定义覆盖
  const customRes = resolveEmptyState({
    mode: 'empty',
    title: '项目列表为空',
    description: '上传第一份招标文件开启智能编标',
    actionText: '上传招标文件',
  });
  assert.equal(customRes.title, '项目列表为空');
  assert.equal(customRes.description, '上传第一份招标文件开启智能编标');
  assert.equal(customRes.actionText, '上传招标文件');
});

test('resolveForbidden resolves context, reassurance notice, and back navigation', () => {
  // 默认值
  const defaultRes = resolveForbidden({});
  assert.equal(defaultRes.title, '没有访问权限');
  assert.equal(defaultRes.reasonText, '你没有该页面的权限，请联系公司管理员。');
  assert.equal(defaultRes.backText, '返回工作台');
  assert.equal(defaultRes.backPath, '/workbench');
  assert.equal(defaultRes.showRetained, false);

  // 指定原因与未保存内容保留提示
  const customRes = resolveForbidden({
    reason: '对象已不存在或你没有查看权限',
    showRetainedNotice: true,
    backText: '返回可访问首页',
    backPath: '/workbench',
  });
  assert.equal(customRes.reasonText, '对象已不存在或你没有查看权限');
  assert.equal(customRes.showRetained, true);
  assert.equal(customRes.backText, '返回可访问首页');
});

test('resolveExpired and resolveReadonly format warning and readonly protection states', () => {
  // ExpiredWarning 状态
  const expiredRes = resolveExpired({
    currentRevision: 3,
    latestRevision: 5,
  });
  assert.equal(expiredRes.message, '内容已修改，结果已过期');
  assert.equal(expiredRes.actionText, '重新运行');
  assert.equal(expiredRes.hasDiff, true);

  // ReadonlyBanner 状态
  const readonlyRes = resolveReadonly({
    reason: '项目已取消',
    scope: '商务分册',
  });
  assert.equal(readonlyRes.message, '只读：项目已取消');
  assert.match(readonlyRes.description, /只读状态/);
  assert.equal(readonlyRes.scope, '商务分册');
});

test('copyText copies to clipboard or returns gracefully in node environment', async () => {
  // 在模拟环境测试 copyText
  let copiedText = '';
  Object.defineProperty(globalThis.navigator, 'clipboard', {
    value: {
      writeText: async text => {
        copiedText = text;
      },
    },
    configurable: true,
  });

  const success = await copyText('test-trace-id-12345');
  assert.equal(success, true);
  assert.equal(copiedText, 'test-trace-id-12345');

  // 当 clipboard 抛异常时的降级
  Object.defineProperty(globalThis.navigator, 'clipboard', {
    value: {
      writeText: async () => {
        throw new Error('Not allowed');
      },
    },
    configurable: true,
  });
  const failResult = await copyText('fail-text');
  assert.equal(failResult, false);
});
