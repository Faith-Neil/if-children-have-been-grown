// 为什么有这个文件：验证 APP-M2-T023 StatusTag 状态注册表与标签组件的规格完整性、WCAG 对比度与安全性。
// 它解决什么问题：
// 1. 验证 6 大核心业务状态码表（项目、章节、长任务、合规检查、导出交付、编辑租约）的完整双向映射；
// 2. 验证未知代码、大小写容错与历史别名回退机制，确保系统永不崩溃；
// 3. 严格核算所有状态色彩令牌的 WCAG AA 4.5:1 文本对比度；
// 4. 验证 AI 紫色强隔离红线（AI 紫色仅用于生成中状态，严禁混入其他业务状态）；
// 5. 验证 StatusTag.tsx 导出的组件契约、无障碍属性与派生快捷组件。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  STATUS_DOMAINS,
  STATUS_DOMAIN_LABELS,
  STATUS_REGISTRY,
  STATUS_COLOR_TOKENS,
  resolveStatus,
  resolveProjectStatus,
  resolveChapterStatus,
  resolveJobStatus,
  resolveCheckStatus,
  resolveExportStatus,
  resolveLockStatus,
  getAllStatusesForDomain,
  isStatusTerminal,
  luminance,
  contrastRatio,
} from '../../src/shared/status-registry.ts';

// 辅助：加载并解析源码 AST
function parseSource(relPath) {
  const fullPath = path.resolve(import.meta.dirname, relPath);
  const content = fs.readFileSync(fullPath, 'utf8');
  const tree = ts.createSourceFile(
    fullPath,
    content,
    ts.ScriptTarget.Latest,
    true
  );
  return { content, tree };
}

test('1. 6 大核心业务状态码表正向映射与元信息完整性', () => {
  // 1.1 业务域收口
  assert.equal(STATUS_DOMAINS.length, 6, 'must contain exactly 6 business status domains');
  assert.deepEqual(STATUS_DOMAINS, ['project', 'chapter', 'job', 'check', 'export', 'lock']);

  // 1.2 ProjectStatus 码表 (PRD §5.10.3)
  const projectDraft = resolveProjectStatus('draft');
  assert.equal(projectDraft.label, '筹备中');
  assert.equal(projectDraft.domain, 'project');
  assert.equal(projectDraft.badgeStatus, 'default');

  const projectInProgress = resolveProjectStatus('in_progress');
  assert.equal(projectInProgress.label, '编写中');
  assert.equal(projectInProgress.badgeStatus, 'processing');

  const projectReview = resolveProjectStatus('review');
  assert.equal(projectReview.label, '审核中');
  assert.equal(projectReview.badgeStatus, 'warning');

  const projectCompleted = resolveProjectStatus('completed');
  assert.equal(projectCompleted.label, '已完成');
  assert.equal(projectCompleted.badgeStatus, 'success');

  const projectArchived = resolveProjectStatus('archived');
  assert.equal(projectArchived.label, '已归档');
  assert.equal(projectArchived.badgeStatus, 'default');

  // 1.3 ChapterStatus 码表
  const chNotStarted = resolveChapterStatus('not_started');
  assert.equal(chNotStarted.label, '未开始');
  const chGenerating = resolveChapterStatus('generating');
  assert.equal(chGenerating.label, '生成中');
  assert.equal(chGenerating.solidBg, STATUS_COLOR_TOKENS.ai.solidBg, 'generating must use AI purple');
  const chDraft = resolveChapterStatus('draft');
  assert.equal(chDraft.label, '草稿');
  const chReviewed = resolveChapterStatus('reviewed');
  assert.equal(chReviewed.label, '已复核');
  const chApproved = resolveChapterStatus('approved');
  assert.equal(chApproved.label, '已定稿');

  // 1.4 JobStatus 码表
  const jobQueued = resolveJobStatus('queued');
  assert.equal(jobQueued.label, '排队中');
  const jobRunning = resolveJobStatus('running');
  assert.equal(jobRunning.label, '进行中');
  const jobCompleted = resolveJobStatus('completed');
  assert.equal(jobCompleted.label, '已完成');
  const jobFailed = resolveJobStatus('failed');
  assert.equal(jobFailed.label, '异常失败');
  const jobCancelled = resolveJobStatus('cancelled');
  assert.equal(jobCancelled.label, '已取消');

  // 1.5 CheckStatus 码表
  const checkPassed = resolveCheckStatus('passed');
  assert.equal(checkPassed.label, '合规通过');
  assert.equal(checkPassed.badgeStatus, 'success');
  const checkWarning = resolveCheckStatus('warning');
  assert.equal(checkWarning.label, '合规提醒');
  assert.equal(checkWarning.badgeStatus, 'warning');
  const checkBlocker = resolveCheckStatus('blocker');
  assert.equal(checkBlocker.label, '废标阻断');
  assert.equal(checkBlocker.badgeStatus, 'error');

  // 1.6 ExportStatus 码表
  const expIdle = resolveExportStatus('idle');
  assert.equal(expIdle.label, '待导出');
  const expProc = resolveExportStatus('processing');
  assert.equal(expProc.label, '排版中');
  const expComp = resolveExportStatus('completed');
  assert.equal(expComp.label, '已生成');
  const expFail = resolveExportStatus('failed');
  assert.equal(expFail.label, '导出失败');

  // 1.7 LockStatus 码表
  const lockUnlocked = resolveLockStatus('unlocked');
  assert.equal(lockUnlocked.label, '空闲可编辑');
  const lockSelf = resolveLockStatus('locked_self');
  assert.equal(lockSelf.label, '本人编辑中');
  const lockOther = resolveLockStatus('locked_other');
  assert.equal(lockOther.label, '他人占用');
  const lockExpired = resolveLockStatus('expired');
  assert.equal(lockExpired.label, '租约过期');

  // 1.8 校验所有注册元数据字段完整性
  for (const domain of STATUS_DOMAINS) {
    const list = getAllStatusesForDomain(domain);
    assert.ok(list.length >= 3, `${domain} must have at least 3 statuses`);
    for (const item of list) {
      assert.ok(item.code, 'must have code');
      assert.ok(item.label, 'must have label');
      assert.equal(item.domain, domain, 'domain must match');
      assert.ok(item.subtleBg, 'must have subtleBg');
      assert.ok(item.subtleText, 'must have subtleText');
      assert.ok(item.solidBg, 'must have solidBg');
      assert.ok(item.solidText, 'must have solidText');
      assert.ok(item.outlineBorder, 'must have outlineBorder');
      assert.ok(item.outlineText, 'must have outlineText');
      assert.ok(item.iconName, 'must have iconName');
      assert.ok(item.description, 'must have description');
      assert.ok(item.ariaLabel, 'must have ariaLabel');
    }
  }
});

test('2. 容错性与别名兼容：大小写不敏感、历史别名映射与安全兜底', () => {
  // 2.1 大小写与空白字符容错
  assert.equal(resolveProjectStatus(' DRAFT ').label, '筹备中');
  assert.equal(resolveProjectStatus('IN_PROGRESS').label, '编写中');
  assert.equal(resolveJobStatus('RUNNING').label, '进行中');
  assert.equal(resolveCheckStatus('BLOCKER').label, '废标阻断');

  // 2.2 别名兼容映射
  assert.equal(resolveJobStatus('pending').code, 'queued', 'pending aliases to queued');
  assert.equal(resolveJobStatus('succeeded').code, 'completed', 'succeeded aliases to completed');
  assert.equal(resolveJobStatus('canceled').code, 'cancelled', 'canceled aliases to cancelled');

  assert.equal(resolveProjectStatus('drafting').code, 'in_progress', 'drafting aliases to in_progress');
  assert.equal(resolveProjectStatus('submitted').code, 'completed', 'submitted aliases to completed');
  assert.equal(resolveProjectStatus('closed').code, 'archived', 'closed aliases to archived');

  assert.equal(resolveCheckStatus('hint').code, 'warning', 'hint aliases to warning');
  assert.equal(resolveCheckStatus('disqualification').code, 'blocker', 'disqualification aliases to blocker');
  assert.equal(resolveCheckStatus('fail').code, 'blocker', 'fail aliases to blocker');

  assert.equal(resolveLockStatus('free').code, 'unlocked', 'free aliases to unlocked');
  assert.equal(resolveLockStatus('held').code, 'locked_self', 'held aliases to locked_self');
  assert.equal(resolveLockStatus('busy').code, 'locked_other', 'busy aliases to locked_other');

  // 2.3 未知与非法代码安全兜底（永不抛异常）
  const fallbackNull = resolveStatus('project', null);
  assert.equal(fallbackNull.domain, 'project');
  assert.equal(fallbackNull.badgeStatus, 'default');
  assert.ok(fallbackNull.label.includes('未知') || fallbackNull.label === 'unknown');

  const fallbackUndefined = resolveStatus('chapter', undefined);
  assert.equal(fallbackUndefined.domain, 'chapter');

  const fallbackUnknownCode = resolveStatus('check', 'NON_EXISTENT_STATUS');
  assert.equal(fallbackUnknownCode.code, 'NON_EXISTENT_STATUS');
  assert.equal(fallbackUnknownCode.badgeStatus, 'default');
  assert.ok(fallbackUnknownCode.description.includes('未知状态'));
});

test('3. WCAG AA 4.5:1 文本对比度标准核验', () => {
  // 校验 STATUS_COLOR_TOKENS 所有调色板变体
  for (const [tokenName, token] of Object.entries(STATUS_COLOR_TOKENS)) {
    const subtleRatio = contrastRatio(token.subtleText, token.subtleBg);
    assert.ok(
      subtleRatio >= 4.5,
      `${tokenName} subtle contrast ${subtleRatio.toFixed(2)} must be >= 4.5:1`
    );

    const solidRatio = contrastRatio(token.solidText, token.solidBg);
    assert.ok(
      solidRatio >= 4.5,
      `${tokenName} solid contrast ${solidRatio.toFixed(2)} must be >= 4.5:1`
    );

    const outlineRatio = contrastRatio(token.outlineText, '#FFFFFF');
    assert.ok(
      outlineRatio >= 4.5,
      `${tokenName} outline contrast ${outlineRatio.toFixed(2)} must be >= 4.5:1`
    );
  }

  // 校验 6 大域所有状态实测颜色
  for (const domain of STATUS_DOMAINS) {
    for (const meta of getAllStatusesForDomain(domain)) {
      const subtleContrast = contrastRatio(meta.subtleText, meta.subtleBg);
      assert.ok(
        subtleContrast >= 4.5,
        `${domain}.${meta.code} subtle contrast ${subtleContrast.toFixed(2)} must be >= 4.5:1`
      );

      const solidContrast = contrastRatio(meta.solidText, meta.solidBg);
      assert.ok(
        solidContrast >= 4.5,
        `${domain}.${meta.code} solid contrast ${solidContrast.toFixed(2)} must be >= 4.5:1`
      );

      const outlineContrast = contrastRatio(meta.outlineText, '#FFFFFF');
      assert.ok(
        outlineContrast >= 4.5,
        `${domain}.${meta.code} outline contrast ${outlineContrast.toFixed(2)} must be >= 4.5:1`
      );
    }
  }
});

test('4. AI 紫色强隔离红线断言', () => {
  const AI_PURPLE_HEX = '#6E4BD8';

  // 1. chapter.generating 明确绑定 AI 紫色
  const generating = resolveChapterStatus('generating');
  assert.equal(generating.solidBg, AI_PURPLE_HEX, 'generating status must use AI purple');

  // 2. 其他非 AI 生成状态绝对禁止混入 AI 紫
  for (const domain of ['project', 'check', 'export', 'lock']) {
    for (const meta of getAllStatusesForDomain(domain)) {
      assert.notEqual(
        meta.solidBg,
        AI_PURPLE_HEX,
        `Domain ${domain} status ${meta.code} must NOT use AI purple`
      );
    }
  }
});

test('5. 终态判定函数 isStatusTerminal 契约断言', () => {
  // job
  assert.equal(isStatusTerminal('job', 'completed'), true);
  assert.equal(isStatusTerminal('job', 'failed'), true);
  assert.equal(isStatusTerminal('job', 'cancelled'), true);
  assert.equal(isStatusTerminal('job', 'running'), false);
  assert.equal(isStatusTerminal('job', 'queued'), false);

  // export
  assert.equal(isStatusTerminal('export', 'completed'), true);
  assert.equal(isStatusTerminal('export', 'failed'), true);
  assert.equal(isStatusTerminal('export', 'processing'), false);
  assert.equal(isStatusTerminal('export', 'idle'), false);

  // project
  assert.equal(isStatusTerminal('project', 'completed'), true);
  assert.equal(isStatusTerminal('project', 'archived'), true);
  assert.equal(isStatusTerminal('project', 'in_progress'), false);

  // chapter
  assert.equal(isStatusTerminal('chapter', 'approved'), true);
  assert.equal(isStatusTerminal('chapter', 'draft'), false);
});

test('6. StatusTag.tsx 组件结构与无障碍契约 AST 断言', () => {
  const { content, tree } = parseSource('../../src/shared/StatusTag.tsx');

  // 导出断言
  const exported = new Set();
  ts.forEachChild(tree, node => {
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (decl.name && ts.isIdentifier(decl.name)) {
          exported.add(decl.name.text);
        }
      }
    }
  });

  // 必须导出主组件与各领域便捷派生组件
  assert.ok(exported.has('StatusTag'), 'must export StatusTag');
  assert.ok(exported.has('ProjectStatusTag'), 'must export ProjectStatusTag');
  assert.ok(exported.has('ChapterStatusTag'), 'must export ChapterStatusTag');
  assert.ok(exported.has('JobStatusTag'), 'must export JobStatusTag');
  assert.ok(exported.has('CheckStatusTag'), 'must export CheckStatusTag');
  assert.ok(exported.has('ExportStatusTag'), 'must export ExportStatusTag');
  assert.ok(exported.has('LockStatusTag'), 'must export LockStatusTag');

  // 必须包含 aria-label, role="status" 与 data-testid 契约
  assert.ok(content.includes('role="status"'), 'StatusTag must declare role="status"');
  assert.ok(content.includes('aria-label={meta.ariaLabel}'), 'StatusTag must set accessible aria-label');
  assert.ok(content.includes('data-testid='), 'StatusTag must provide data-testid');
  assert.ok(content.includes('data-domain='), 'StatusTag must provide data-domain');
  assert.ok(content.includes('data-status='), 'StatusTag must provide data-status');
  assert.ok(content.includes('data-variant='), 'StatusTag must provide data-variant');
  assert.ok(content.includes('data-size='), 'StatusTag must provide data-size');

  // 必须支持 showBadge 与 tooltip 包装
  assert.ok(content.includes('icg-status-tag-badge-dot'), 'StatusTag must support badge dot rendering');
  assert.ok(content.includes('<Tooltip'), 'StatusTag must support Tooltip wrapper');
});
