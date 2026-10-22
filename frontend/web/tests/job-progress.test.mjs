// 为什么有这个文件：静态 AST 结构断言与 JobProgress 组件与进度条契约测试。
// 它解决什么问题：验证后台长任务进度条、AI 紫色隔离规范、子步骤列表与失败追踪号交互的架构契约。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function parseSource(relativePath) {
  const fileUrl = new URL(relativePath, import.meta.url);
  const content = readFileSync(fileUrl, 'utf8');
  const tree = ts.createSourceFile(
    relativePath,
    content,
    ts.ScriptTarget.Latest,
    true,
    relativePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  return { content, tree };
}

test('1. job-progress.ts exports core logic and status-machine symbols', () => {
  const { tree } = parseSource('../src/job-progress.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exported.add(decl.name.text);
      }
    }
  });

  assert.ok(exported.has('isAiJob'), 'must export isAiJob');
  assert.ok(exported.has('resolveProgressStrokeColor'), 'must export resolveProgressStrokeColor');
  assert.ok(exported.has('deriveJobProgress'), 'must export deriveJobProgress');
  assert.ok(exported.has('resolveJobStatusMeta'), 'must export resolveJobStatusMeta');
  assert.ok(exported.has('formatDuration'), 'must export formatDuration');
  assert.ok(exported.has('getJobTypeLabel'), 'must export getJobTypeLabel');
  assert.ok(exported.has('JOB_PROGRESS_COLORS'), 'must export JOB_PROGRESS_COLORS');
  assert.ok(exported.has('AI_JOB_TYPES'), 'must export AI_JOB_TYPES');
});

test('2. JobProgress.tsx exports JobProgress component and binds essential attributes', () => {
  const { content, tree } = parseSource('../src/JobProgress.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('JobProgress'), 'must export JobProgress component');

  // 测试属性 data-testid 完备性验证
  assert.ok(content.includes('data-testid="job-progress"'), 'must include job-progress root test id');
  assert.ok(content.includes('data-testid="job-main-progress"'), 'must include job-main-progress test id');
  assert.ok(content.includes('data-testid="job-step-item"'), 'must include job-step-item test id');
  assert.ok(content.includes('data-testid="job-error-block"'), 'must include job-error-block test id');
  assert.ok(content.includes('data-testid="copy-trace-btn"'), 'must include copy-trace-btn test id');
  assert.ok(content.includes('data-testid="job-retry-btn"'), 'must include job-retry-btn test id');
  assert.ok(content.includes('data-testid="job-cancel-btn"'), 'must include job-cancel-btn test id');
});

test('3. AI 紫色样式隔离规范断言（严格禁止非 AI 任务出现紫色）', () => {
  const { content: tsxContent } = parseSource('../src/JobProgress.tsx');
  const cssUrl = new URL('../src/styles.css', import.meta.url);
  const cssContent = readFileSync(cssUrl, 'utf8');

  // TSX 必须通过 isAiJob 判定动态挂载 is-ai-progress
  assert.ok(
    tsxContent.includes("isAi ? 'is-ai-progress' : ''"),
    'JobProgress root must conditionally append .is-ai-progress strictly when isAi is true'
  );
  assert.ok(
    tsxContent.includes("data-is-ai={isAi ? 'true' : 'false'}"),
    'JobProgress must export data-is-ai attribute for integration inspection'
  );

  // CSS 样式表中必须定义专属 AI 紫色规则，并使用 #722ed1 / #d3adf7
  assert.ok(
    cssContent.includes('.icg-job-progress.is-ai-progress'),
    'styles.css must declare .icg-job-progress.is-ai-progress class'
  );
  assert.ok(
    cssContent.includes('#722ed1'),
    'styles.css or tokens must include AI purple color token #722ed1'
  );
  assert.ok(
    cssContent.includes('#d3adf7'),
    'styles.css must include AI purple border token #d3adf7'
  );
});

test('4. 失败容错、重试与 Trace ID 交互契约断言', () => {
  const { content } = parseSource('../src/JobProgress.tsx');

  // 验证失败态下对 traceId、errorCode、errorSummary 的渲染
  assert.ok(content.includes('job.traceId'), 'must inspect job.traceId');
  assert.ok(content.includes('copyText(job.traceId)'), 'must trigger copyText on traceId');
  assert.ok(content.includes('handleCopyTraceId'), 'must define copy trace handler');
  assert.ok(content.includes('onRetry'), 'must support onRetry callback');
  assert.ok(content.includes('onCancel'), 'must support onCancel callback');
  assert.ok(content.includes('failedStep'), 'must detect failedStep to support step-level retry');
});

test('5. SSE 流订阅、断线重试与平滑轮询降级契约断言 (APP-M2-T020)', () => {
  const { content, tree } = parseSource('../src/JobProgress.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  // 必须导出支持 SSE 的高阶组件
  assert.ok(exported.has('JobProgressWithSse'), 'must export JobProgressWithSse');

  // 必须绑定降级测试 ID
  assert.ok(content.includes('data-testid="job-stream-fallback-tag"'), 'must include job-stream-fallback-tag testid');
  assert.ok(content.includes('实时流已断开，已切换为定时刷新'), 'must display fallback warning message');

  // 验证 job-progress-sse.ts 导出的核心控制器与 hook
  const { tree: sseTree } = parseSource('../src/job-progress-sse.ts');
  const sseExported = new Set();
  ts.forEachChild(sseTree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) sseExported.add(node.name.text);
    }
    if (ts.isClassDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) sseExported.add(node.name.text);
    }
  });

  assert.ok(sseExported.has('JobStreamSubscriptionManager'), 'job-progress-sse.ts must export JobStreamSubscriptionManager');
  assert.ok(sseExported.has('createJobStreamSubscription'), 'job-progress-sse.ts must export createJobStreamSubscription');
  assert.ok(sseExported.has('useJobProgressSse'), 'job-progress-sse.ts must export useJobProgressSse');
  assert.ok(sseExported.has('calculateBackoffDelay'), 'job-progress-sse.ts must export calculateBackoffDelay');
  assert.ok(sseExported.has('isJobTerminalStatus'), 'job-progress-sse.ts must export isJobTerminalStatus');
});

