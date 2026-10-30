// 为什么有这个文件：APP-M2-T166 问题标注与侧栏联动的前端规则测试。
// 它解决什么问题：筛选（状态、处理路径、规则、所选段落）、段落标记取最重等级、行号换字符区间、
// 编辑中的文字与已提交正文不同时不按行号选中；检查页“定位”带着问题进入编辑台只取一次。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import * as core from '../../src/editor/chapter-issues-core.ts';
import { requestIssueFocus, takeIssueFocus } from '../../src/editor/issue-focus.ts';

const read = rel => fs.readFileSync(path.resolve(import.meta.dirname, rel), 'utf8');
const issue = over => ({
  id: 'x', origin: 'loop', origin_label: '章节循环', rule_id: 'R15', code: 'PLACEHOLDER_RESIDUAL', severity: 'warning',
  message: 'm', quote: 'q', route: 'direct_human', route_label: '直接转人工', status: 'pending_human', status_label: '待人工处理',
  open: true, stale: false, paragraph_key: 'pk-1', line_start: 2, line_end: 2, located_by: 'key', locate_note: '', ...over,
});

test('1. 筛选：默认只看待处理，可按处理路径、规则与所选段落', () => {
  const items = [
    issue({ id: 'a' }),
    issue({ id: 'b', open: false, status: 'resolved' }),
    issue({ id: 'c', route: 'must_fix', rule_id: 'R30', paragraph_key: 'pk-2' }),
    issue({ id: 'd', rule_id: '', code: 'PENDING_CONTENT', paragraph_key: null }),
  ];
  assert.deepEqual(core.filterIssues(items, core.DEFAULT_FILTER).map(i => i.id), ['a', 'c', 'd']);
  assert.deepEqual(core.filterIssues(items, { ...core.DEFAULT_FILTER, status: 'all' }).map(i => i.id), ['a', 'b', 'c', 'd']);
  assert.deepEqual(core.filterIssues(items, { ...core.DEFAULT_FILTER, route: 'must_fix' }).map(i => i.id), ['c']);
  assert.deepEqual(core.filterIssues(items, { ...core.DEFAULT_FILTER, rule: 'PENDING_CONTENT' }).map(i => i.id), ['d']);
  assert.deepEqual(core.filterIssues(items, { ...core.DEFAULT_FILTER, paragraphKey: 'pk-2' }).map(i => i.id), ['c']);
  const options = core.issueOptions(items);
  assert.deepEqual(options.routes.map(o => o.value).sort(), ['direct_human', 'must_fix']);
  assert.deepEqual(options.rules.map(o => o.value), ['PENDING_CONTENT', 'R15', 'R30']);
});

test('2. 段落标记：只数待处理且已定位的问题，等级取最重', () => {
  const markers = core.paragraphMarkers([
    issue({ id: 'a', severity: 'info' }),
    issue({ id: 'b', severity: 'blocker' }),
    issue({ id: 'c', severity: 'warning', paragraph_key: 'pk-2' }),
    issue({ id: 'd', open: false, paragraph_key: 'pk-3' }),
    issue({ id: 'e', paragraph_key: null }),
  ]);
  assert.deepEqual(Object.fromEntries(markers), { 'pk-1': { count: 2, severity: 'blocker' }, 'pk-2': { count: 1, severity: 'warning' } });
});

test('3. 行号区间换成字符区间', () => {
  const content = '第一行\n\n第三行\n第四行';
  assert.deepEqual(core.lineRangeOffsets(content, 2, 2), { start: 5, end: 8 });
  assert.equal(content.slice(5, 8), '第三行');
  assert.deepEqual(core.lineRangeOffsets(content, 2, 3), { start: 5, end: 12 });
  assert.equal(core.lineRangeOffsets(content, 3, 9), null);
  assert.equal(core.canSelectInEditor(issue({}), 'a', 'a'), true);
  assert.equal(core.canSelectInEditor(issue({}), 'a 改过', 'a'), false);
  assert.equal(core.canSelectInEditor(issue({ line_start: null }), 'a', 'a'), false);
});

test('4. 检查页带来的定位只对目标章节生效一次', () => {
  requestIssueFocus('c-1', 'issue-9');
  assert.equal(takeIssueFocus('c-2'), null);
  assert.equal(takeIssueFocus('c-1'), 'issue-9');
  assert.equal(takeIssueFocus('c-1'), null);
});

test('5. 页面接线：问题页签用新清单，正文段落带标记，检查页定位进入章节', async () => {
  const calls = [];
  await core.fetchChapterIssues('p 1', 'c/2', 'tok', async (p, t) => { calls.push([p, t]); return {}; });
  assert.deepEqual(calls, [['/api/v1/projects/p%201/chapters/c%2F2/issues', 'tok']]);
  const panel = read('../../src/editor/EditorAssistantPanel.tsx');
  assert.ok(panel.includes("{rightTab === 'issues' && issuesPanel}"));
  assert.ok(!panel.includes('workspace.checks[workspace.checks.length - 1]'));
  const page = read('../../src/editor/EditorPage.tsx');
  assert.equal((page.match(/issueMarkers=\{issues\.markers\}/g) ?? []).length, 2);
  assert.ok(page.includes('ref={textareaRef}'));
  const renderer = read('../../src/editor/CiteCapsule.tsx');
  assert.ok(renderer.includes('data-testid="paragraph-issue-marker"') && renderer.includes("'paragraph-focused'"));
  const checks = read('../../src/project/ProjectPages.tsx');
  assert.ok(checks.includes('requestIssueFocus(item.chapter_id, item.id)'));
  assert.ok(checks.includes('navigate(editorChapterPath(workspace.project.id, item.chapter_id))'));
});
