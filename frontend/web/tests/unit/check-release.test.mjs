// 为什么有这个文件：验证检查页“警告逐项放行”的判定（PRD §5.8；R29/R30 的警告须项目负责人填理由放行）。
// 它解决什么问题：阻断永远不出放行按钮，非负责人看不到，已放行的不再重复放行；待处理计数与后台“是否通过”口径一致。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { canReleaseIssue, releasePath, unreleasedCount } from '../../src/project/export-checks-core.ts';

test('only the project lead can release unreleased warnings and hints, never blockers', () => {
  assert.equal(canReleaseIssue({ severity: 'warning' }, true), true);
  assert.equal(canReleaseIssue({ severity: 'info' }, true), true);
  assert.equal(canReleaseIssue({ severity: 'blocker' }, true), false);
  assert.equal(canReleaseIssue({ severity: 'blocking' }, true), false);
  assert.equal(canReleaseIssue({ severity: 'warning' }, false), false);
  assert.equal(canReleaseIssue({ severity: 'warning', released: { reason: 'x' } }, true), false);
});

test('pending count matches the backend pass rule', () => {
  const issues = [
    { severity: 'blocker' }, { severity: 'warning' }, { severity: 'warning', released: { reason: '已确认' } },
    { severity: 'info' }, { severity: 'blocking', released: { reason: '不应生效' } },
  ];
  assert.equal(unreleasedCount(issues), 3);
  assert.equal(unreleasedCount([{ severity: 'info' }, { severity: 'warning', released: { reason: 'ok' } }]), 0);
});

test('release path and page wiring require a reason', () => {
  assert.equal(releasePath('p 1', 'chk', 'iss'), '/api/v1/projects/p%201/checks/chk/issues/iss/release');
  const page = readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8');
  assert.match(page, /请填写放行理由/);
  assert.match(page, /canReleaseIssue\(item, isLead\)/);
});
