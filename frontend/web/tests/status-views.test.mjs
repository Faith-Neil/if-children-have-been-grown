// 为什么有这个文件：执行 StatusViews 组件的真实 AST 结构与属性断言。
// 它解决什么问题：验证六类状态组件完整导出、错误体与 traceId 一键复制、403 上下文保护和 10 秒超时提示均按规范实现。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import * as statusLogic from '../src/status/status-views.ts';

const source = readFileSync(new URL('../src/status/StatusViews.tsx', import.meta.url), 'utf8');
const tree = ts.createSourceFile('StatusViews.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

function findFunctionDeclaration(name) {
  return tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name);
}

function findVariableDeclaration(name) {
  for (const statement of tree.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const decl of statement.declarationList.declarations) {
        if (ts.isIdentifier(decl.name) && decl.name.text === name) {
          return decl;
        }
      }
    }
  }
  return null;
}

test('StatusViews exports all six core status views and their approved aliases', () => {
  // 1. Skeleton 骨架屏
  assert.ok(findFunctionDeclaration('SkeletonView'), 'SkeletonView function is declared');
  assert.ok(findVariableDeclaration('PageSkeleton'), 'PageSkeleton alias is exported');

  // 2. Empty 空态
  assert.ok(findFunctionDeclaration('EmptyState'), 'EmptyState function is declared');
  assert.ok(findVariableDeclaration('EmptyView'), 'EmptyView alias is exported');

  // 3. ErrorView 统一错误体与复制
  assert.ok(findFunctionDeclaration('ErrorView'), 'ErrorView function is declared');
  assert.ok(findVariableDeclaration('ErrorState'), 'ErrorState alias is exported');

  // 4. Forbidden403 无权限
  assert.ok(findFunctionDeclaration('Forbidden403'), 'Forbidden403 function is declared');
  assert.ok(findVariableDeclaration('NoPermission'), 'NoPermission alias is exported');

  // 5. ExpiredWarning 版本过期警告条
  assert.ok(findFunctionDeclaration('ExpiredWarning'), 'ExpiredWarning function is declared');
  assert.ok(findVariableDeclaration('StaleBanner'), 'StaleBanner alias is exported');

  // 6. ReadonlyBanner 只读会话保护横幅
  assert.ok(findFunctionDeclaration('ReadonlyBanner'), 'ReadonlyBanner function is declared');
  assert.ok(findVariableDeclaration('ReadOnlyBanner'), 'ReadOnlyBanner alias is exported');
});

test('ErrorView supports error body code, message, traceId copy button, and retry action', () => {
  const errorFn = findFunctionDeclaration('ErrorView');
  assert.ok(errorFn, 'ErrorView is present in source');
  const fnText = errorFn.getText(tree);

  // 断言提取 code, message, traceId
  assert.match(fnText, /extractErrorInfo\(error\)/);
  assert.match(fnText, /activeCode/);
  assert.match(fnText, /activeMessage/);
  assert.match(fnText, /activeTraceId/);

  // 断言一键复制交互
  assert.match(fnText, /handleCopy/);
  assert.match(fnText, /copyHandler/);
  assert.match(fnText, /onCopyTraceId/);
  assert.match(fnText, /data-testid="copy-trace-button"/);
  assert.match(fnText, /aria-label="复制请求编号"/);
  assert.match(fnText, /已复制/);
  assert.match(fnText, /CopyOutlined/);
  assert.match(fnText, /CheckOutlined/);

  // 断言重试逻辑与标签
  assert.match(fnText, /data-testid="error-retry-button"/);
  assert.match(fnText, /onRetry/);
  assert.match(fnText, /data-testid="error-code-tag"/);

  // 断言布局：page, inline, block
  assert.match(fnText, /layout === 'page'/);
  assert.match(fnText, /layout === 'inline'/);
  assert.match(fnText, /icg-status-error-block/);
});

test('SkeletonView supports table 5 rows, cards 3, detail, and 10s timeout notice', () => {
  const skeletonFn = findFunctionDeclaration('SkeletonView');
  assert.ok(skeletonFn, 'SkeletonView is present in source');
  const fnText = skeletonFn.getText(tree);

  // 默认行数与卡片数
  assert.match(fnText, /rows = 5/);
  assert.match(fnText, /cards = 3/);
  assert.match(fnText, /timeoutSeconds = 10/);

  // 变体支持
  assert.match(fnText, /variant === 'table'/);
  assert.match(fnText, /variant === 'cards'/);
  assert.match(fnText, /variant === 'detail'/);
  assert.match(fnText, /icg-status-skeleton-page/);

  // 超过10秒显示长任务提醒
  assert.match(fnText, /仍在加载，可离开本页，任务在后台继续/);
  assert.match(fnText, /ClockCircleOutlined/);
  assert.match(fnText, /role="status"/);
  assert.match(fnText, /aria-busy="true"/);
});

test('Forbidden403 preserves context tags, retained notice, and returns to workbench or safe route', () => {
  const forbiddenFn = findFunctionDeclaration('Forbidden403');
  assert.ok(forbiddenFn, 'Forbidden403 is present in source');
  const fnText = forbiddenFn.getText(tree);

  // 默认提示与返回引导
  assert.match(fnText, /没有访问权限/);
  assert.match(fnText, /你没有该页面的权限，请联系公司管理员。/);
  assert.match(fnText, /backText = '返回工作台'/);
  assert.match(fnText, /backPath = '\/workbench'/);

  // 上下文保留与未保存内容保护提醒
  assert.match(fnText, /data-testid="forbidden-context-info"/);
  assert.match(fnText, /当前项目：/);
  assert.match(fnText, /当前身份：/);
  assert.match(fnText, /目标路径：/);
  assert.match(fnText, /当前内容及未保存文字仍保留在下方，写入口已关闭。/);
  assert.match(fnText, /data-testid="retained-notice"/);
  assert.match(fnText, /data-testid="forbidden-back-button"/);
});

test('ExpiredWarning alerts on stale revision with WCAG high contrast warning styling', () => {
  const expiredFn = findFunctionDeclaration('ExpiredWarning');
  assert.ok(expiredFn, 'ExpiredWarning is present in source');
  const fnText = expiredFn.getText(tree);

  // 提示文案与动作
  assert.match(fnText, /内容已修改，结果已过期/);
  assert.match(fnText, /actionText = '重新运行'/);
  assert.match(fnText, /WarningOutlined/);
  assert.match(fnText, /color: '#9a5608'/); // WCAG 4.5:1 锁定高对比度黄色文本

  // 新旧版本对比展示
  assert.match(fnText, /当前已保存版本：/);
  assert.match(fnText, /后台最新版本：/);
  assert.match(fnText, /data-testid="expired-action-button"/);
});

test('ReadonlyBanner provides non-editable session protection and displays scope and role', () => {
  const readonlyFn = findFunctionDeclaration('ReadonlyBanner');
  assert.ok(readonlyFn, 'ReadonlyBanner is present in source');
  const fnText = readonlyFn.getText(tree);

  // 只读提示文案与说明
  assert.match(fnText, /只读：/);
  assert.match(fnText, /只读会话保护/);
  assert.match(fnText, /所有修改、保存与生成入口已关闭，仅供查阅。/);
  assert.match(fnText, /InfoCircleOutlined/);

  // 范围与角色标记
  assert.match(fnText, /范围：/);
  assert.match(fnText, /当前角色：/);
  assert.match(fnText, /data-testid="readonly-banner-alert"/);
});

test('EmptyState supports filtered and search modes with actionable buttons', () => {
  const emptyFn = findFunctionDeclaration('EmptyState');
  assert.ok(emptyFn, 'EmptyState is present in source');
  const fnText = emptyFn.getText(tree);

  // 三种模式
  assert.match(fnText, /mode === 'filtered'/);
  assert.match(fnText, /mode === 'search'/);
  assert.match(fnText, /Empty\.PRESENTED_IMAGE_SIMPLE/);
  assert.match(fnText, /Empty\.PRESENTED_IMAGE_DEFAULT/);
  assert.match(fnText, /role="status"/);
  assert.match(fnText, /onAction/);
});

test('status-views pure logic and contrast constants are intact and verified', () => {
  assert.equal(typeof statusLogic.copyText, 'function');
  assert.equal(typeof statusLogic.extractErrorInfo, 'function');
  assert.equal(typeof statusLogic.contrastRatio, 'function');
  assert.equal(statusLogic.STATUS_CONTRAST_TOKENS.warningText, '#9a5608');
  assert.equal(statusLogic.STATUS_CONTRAST_TOKENS.primary, '#1e4db7');
  assert.equal(statusLogic.STATUS_CONTRAST_TOKENS.error, '#d9363e');
});
