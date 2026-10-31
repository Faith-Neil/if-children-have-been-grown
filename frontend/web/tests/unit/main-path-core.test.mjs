// 为什么有这个文件：验证 Wave 11 人工处理队列、分册交叉复核与疑似遗漏的前端纯逻辑和接线。
// 它解决什么问题：按钮出现条件、默认处理方式、合并同段问题、定稿前提提示与页面接线不回退到占位壳。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  daysUntil, defaultHitCategory, defaultResolveMethod, loopLine, needsMaterial, paragraphEditPayload, paragraphEditProblem, queuePaths, reviewTag,
  reviewerCandidates, sameParagraphIssues, severityTag, volumeActions,
} from '../../src/project/main-path-core.ts';

const issue = (over = {}) => ({
  id: 'i1', number: '1-001', chapter_id: 'c1', volume: 'technical', code: 'PLACEHOLDER_RESIDUAL', rule: 'R15',
  source: 'rule', level: 'blocker', severity: 'high', status: 'pending_human', route: 'direct_human',
  human_reason: 'MISSING_EVIDENCE', human_reason_label: '缺证据的【待补】', paragraph_index: 2, quote: 'q', message: 'm',
  suggestion: 's', fix_count: 0, loop_no: 1, permissions: { resolve: true, reject: false }, ...over,
});

test('resolve defaults and material entry follow the human reason', () => {
  assert.equal(defaultResolveMethod(issue()), 'keep_placeholder');
  assert.equal(defaultResolveMethod(issue({ code: 'NEGATIVE_DEVIATION_DETECTED', human_reason: 'BUSINESS_DEVIATION' })), 'edited');
  assert.equal(needsMaterial(issue()), true);
  assert.equal(needsMaterial(issue({ human_reason: 'BUSINESS_DEVIATION' })), false);
  assert.deepEqual(severityTag(issue()), { color: 'red', label: '阻断' });
});

test('same paragraph issues can be merged only when resolvable', () => {
  const group = { issues: [issue(), issue({ id: 'i2', number: '1-002' }), issue({ id: 'i3', paragraph_index: 5 }),
    issue({ id: 'i4', permissions: { resolve: false, reject: false } })] };
  assert.deepEqual(sameParagraphIssues(group, group.issues[0]).map(item => item.id), ['i2']);
});

test('loop line shows loop count, stop reason, rollback and stale content', () => {
  assert.equal(loopLine({ loop: null }), '尚未运行章节循环');
  const line = loopLine({ loop: { loop_count: 2, stop_reason_label: '剩余问题需人工处理', rolled_back: true, stale: true } });
  assert.equal(line, '第 2 次循环 · 剩余问题需人工处理 · 已回退 · 之后正文有改动');
});

test('deadline countdown tolerates missing values', () => {
  assert.equal(daysUntil('', 0), null);
  assert.equal(daysUntil('not a date', 0), null);
  assert.equal(daysUntil('1970-01-03T00:00:00Z', 0), 2);
});

const workspace = {
  permissions: { manage_project: false },
  team: {
    members: [
      { user_id: 'lead', name: '经理', project_role: 'lead' },
      { user_id: 'owner', name: '技术负责人', project_role: 'writer' },
      { user_id: 'writer', name: '编写人', project_role: 'writer' },
      { user_id: 'viewer', name: '只读', project_role: 'readonly' },
    ],
    volumes: [{ volume: 'technical', owner_id: 'owner' }, { volume: 'business', owner_id: 'lead' }],
  },
};

test('reviewer candidates exclude readonly members and the volume owner', () => {
  assert.deepEqual(reviewerCandidates(workspace.team, 'technical').map(item => item.value), ['lead', 'writer']);
  assert.deepEqual(reviewerCandidates(undefined, 'technical'), []);
});

test('finalize actions require review on current content and no pending human issues', () => {
  const pending = { volume_id: 'technical', is_finalized: false, pending_human_issues: 2, cross_review: { status: 'pending', stale: false, reviewer_id: 'writer' } };
  const owner = volumeActions(pending, workspace, 'owner', 'technical');
  assert.equal(owner.canAssign, true);
  assert.equal(owner.canFinalize, false);
  assert.deepEqual(owner.finalizeBlockers, ['人工处理队列还有 2 个问题', '尚未完成交叉复核']);
  assert.equal(volumeActions(pending, workspace, 'writer', 'technical').canConfirm, true);
  assert.equal(volumeActions(pending, workspace, 'writer', 'technical').canAssign, false);

  const stale = { ...pending, pending_human_issues: 0, cross_review: { status: 'approved', stale: true } };
  assert.deepEqual(volumeActions(stale, workspace, 'owner', 'technical').finalizeBlockers, ['复核后正文有改动，须重新复核']);
  assert.equal(reviewTag(stale.cross_review).label, '复核后正文有改动');

  const ready = { ...stale, cross_review: { status: 'approved', stale: false } };
  assert.equal(volumeActions(ready, workspace, 'owner', 'technical').canFinalize, true);
  assert.equal(volumeActions(ready, workspace, 'writer', 'technical').canFinalize, false);

  const finalized = { ...ready, is_finalized: true };
  const lead = volumeActions(finalized, { ...workspace, permissions: { manage_project: true } }, 'lead', 'technical');
  assert.equal(lead.canUnlock, true);
  assert.equal(lead.canAssign, false);
});

test('scan hit default category and API paths', () => {
  assert.equal(defaultHitCategory({ terms: ['★'] }), 'star');
  assert.equal(defaultHitCategory({ terms: ['否决投标'] }), 'disqualification');
  assert.equal(queuePaths.excludeHit('p 1', 'h1'), '/api/v1/projects/p%201/parse/omissions/h1/exclude');
  assert.equal(queuePaths.recheck('p', 'c'), '/api/v1/projects/p/chapters/c/loop/recheck');
});

test('main path pages are wired instead of placeholders', () => {
  const workspaceContent = readFileSync(new URL('../../src/app/ProjectWorkspaceContent.tsx', import.meta.url), 'utf8');
  assert.ok(workspaceContent.includes("{tab === 'manual' && <ManualQueuePage />}"));
  assert.ok(!workspaceContent.includes('PendingPage'));
  const parse = readFileSync(new URL('../../src/project/ParseTab.tsx', import.meta.url), 'utf8');
  assert.ok(!parse.includes('待实现'));
  assert.ok(parse.includes('omissions > 0'));
  const drawer = readFileSync(new URL('../../src/project/OmissionsDrawer.tsx', import.meta.url), 'utf8')
    .split('\n').filter(line => !line.trim().startsWith('//')).join('\n');
  assert.ok(!/批量|全部排除|全部新增/.test(drawer), '疑似遗漏不提供批量处理');
  const exportPage = readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8');
  assert.ok(exportPage.includes('<VolumeFinalizePanel volumes={volumesStatus} />'));
});

test('single paragraph edit pre-check and payload follow the backend contract', () => {
  assert.equal(paragraphEditProblem('原段落。', '  '), '改写后的段落不能为空');
  assert.equal(paragraphEditProblem('原段落。', '第一行\n第二行'), '这里只能改写一个段落，不能换行');
  assert.equal(paragraphEditProblem('原段落。', '原段落。 '), '内容与原段落相同');
  assert.match(paragraphEditProblem('原段落。', 'x'.repeat(5001)), /不能超过 5000 字/);
  assert.equal(paragraphEditProblem('原段落。', '新的一段。'), null);
  assert.deepEqual(paragraphEditPayload({ chapter_revision: 7 }, ' 新的一段。 ', ' 按合同改 '),
    { chapter_revision: 7, new_text: '新的一段。', note: '按合同改' });
  assert.equal(queuePaths.edit('p 1', 'i/1'), '/api/v1/projects/p%201/human-queue/issues/i%2F1/edit');
});

test('queue page wires the edit button to backend permission and the edit endpoint', () => {
  const page = readFileSync(new URL('../../src/project/ManualQueuePage.tsx', import.meta.url), 'utf8');
  assert.ok(page.includes('issue.permissions.edit &&'), '按钮是否出现只看后台 permissions.edit');
  assert.ok(page.includes('queuePaths.edit(projectId, issue.id)'));
  assert.ok(page.includes('paragraphEditPayload(pending.group'));
});
