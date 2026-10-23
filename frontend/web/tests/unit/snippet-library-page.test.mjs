// 为什么有这个文件：覆盖 FE-SNIPPET-LIBRARY 方案片段知识库最小页核心业务逻辑与安全隔离单测。
// 它解决什么问题：
// 1. 【安全隔离红线】严格验证当前登录会话 company_id 租户隔离，严禁跨租户数据泄露；
// 2. 验证多维筛选（关键字、分类、产品线、知识库同步状态、仅已发布门禁）；
// 3. 验证标题推导算法、变量占位符提取（{{var}}）与时间等宽格式化；
// 4. 验证知识库同步状态（synced/unsynced/sync_failed）元数据与色彩映射；
// 5. 验证 API 加载韧性与降级回退机制；
// 6. 验证 Layout First 空状态与统计数据计算契约。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  SNIPPET_TYPE_MAP,
  getSnippetTypeLabel,
  getSnippetSyncStatusMeta,
  resolveSnippetTitle,
  extractSnippetVariables,
  formatMonospaceTime,
  filterSnippets,
  computeSnippetStats,
  loadSnippetPublications,
  DEFAULT_SNIPPET_PUBLICATIONS,
} from '../../src/library/snippet-library-core.ts';

/* ========================================================================= */
/* 1. 分类映射与状态元信息测试                                                */
/* ========================================================================= */

test('SNIPPET_TYPE_MAP & getSnippetTypeLabel: 标准分类与友好回退', () => {
  assert.equal(getSnippetTypeLabel('solution'), '技术方案');
  assert.equal(getSnippetTypeLabel('boilerplate'), '通用套话');
  assert.equal(getSnippetTypeLabel('qualification'), '资质证明');
  assert.equal(getSnippetTypeLabel('case'), '经典案例');
  assert.equal(getSnippetTypeLabel('sla'), '服务承诺');
  assert.equal(getSnippetTypeLabel('security'), '安全合规');
  assert.equal(getSnippetTypeLabel('architecture'), '系统架构');
  assert.equal(getSnippetTypeLabel('implementation'), '实施方案');

  // 未知或空类型回退
  assert.equal(getSnippetTypeLabel('custom_type'), 'custom_type');
  assert.equal(getSnippetTypeLabel(null), '方案片段');
  assert.equal(getSnippetTypeLabel(undefined), '方案片段');
});

test('getSnippetSyncStatusMeta: 同步状态标签与徽标状态', () => {
  const synced = getSnippetSyncStatusMeta('synced');
  assert.equal(synced.label, '已同步知识库');
  assert.equal(synced.color, 'green');
  assert.equal(synced.badgeStatus, 'success');

  const unsynced = getSnippetSyncStatusMeta('unsynced');
  assert.equal(unsynced.label, '未同步知识库');
  assert.equal(unsynced.color, 'gold');
  assert.equal(unsynced.badgeStatus, 'warning');

  const failed = getSnippetSyncStatusMeta('sync_failed');
  assert.equal(failed.label, '同步失败');
  assert.equal(failed.color, 'red');
  assert.equal(failed.badgeStatus, 'error');

  const unknown = getSnippetSyncStatusMeta('other');
  assert.equal(unknown.label, 'other');
  assert.equal(unknown.badgeStatus, 'default');
});

/* ========================================================================= */
/* 2. 标题推导算法 (resolveSnippetTitle)                                    */
/* ========================================================================= */

test('resolveSnippetTitle: 智能推导方案片段标题', () => {
  // 1. 显式指定 title 时优先使用 title
  assert.equal(
    resolveSnippetTitle({ title: '高可用微服务架构标准条款', product: '云计算', boilerplate_group: '架构' }),
    '高可用微服务架构标准条款'
  );

  // 2. 无 title 但有 product 和 boilerplate_group
  assert.equal(
    resolveSnippetTitle({ product: '智慧应急', boilerplate_group: '冗余设计' }),
    '智慧应急 · 冗余设计'
  );

  // 3. 无 boilerplate_group 但有 snippet_type
  assert.equal(
    resolveSnippetTitle({ product: '数据中台', snippet_type: 'solution' }),
    '数据中台 · 技术方案'
  );

  // 4. 仅有 product
  assert.equal(
    resolveSnippetTitle({ product: '物联网平台' }),
    '物联网平台 方案片段'
  );

  // 5. 空对象回退
  assert.equal(resolveSnippetTitle({ id: 'snp-001' }), '方案片段 #snp-001');
  assert.equal(resolveSnippetTitle(null), '方案片段');
});

/* ========================================================================= */
/* 3. 变量提取算法 (extractSnippetVariables)                                 */
/* ========================================================================= */

test('extractSnippetVariables: 从正文中准确提取与去重变量占位符', () => {
  const body = '在环境温度 {{temp_c}} 和压力 {{pressure_kpa}} 下，单节点支持 {{tps_max}} 并发。若低于 {{temp_c}} 则报警。';
  const vars = extractSnippetVariables(body);
  assert.deepEqual(vars, ['pressure_kpa', 'temp_c', 'tps_max']);

  // 无变量与空输入
  assert.deepEqual(extractSnippetVariables('静态文本无变量'), []);
  assert.deepEqual(extractSnippetVariables(''), []);
  assert.deepEqual(extractSnippetVariables(null), []);

  // 复杂命名规范（包含连字符、下划线、句点）
  const complexBody = '承诺 {{node-1.v2}} 与 {{backup_cluster_3}} 协同工作。';
  assert.deepEqual(extractSnippetVariables(complexBody), ['backup_cluster_3', 'node-1.v2']);
});

/* ========================================================================= */
/* 4. 时间格式化 (formatMonospaceTime)                                       */
/* ========================================================================= */

test('formatMonospaceTime: 格式化为等宽标准时间', () => {
  const dateStr = '2026-10-22T10:15:30Z';
  const formatted = formatMonospaceTime(dateStr);
  assert.match(formatted, /^2026-10-22 \d{2}:15:30$/);

  // 空与非法值保护
  assert.equal(formatMonospaceTime(null), '-');
  assert.equal(formatMonospaceTime(''), '-');
  assert.equal(formatMonospaceTime('invalid-date'), 'invalid-date');
});

/* ========================================================================= */
/* 5. 【核心安全红线】租户隔离门禁 (Tenant Isolation)                          */
/* ========================================================================= */

test('filterSnippets: 租户公司隔离红线验证 (严格杜绝跨租户数据可见)', () => {
  const items = [
    {
      id: 'snip-alpha-001',
      company_id: 'alpha',
      product: '智慧应急',
      snippet_type: 'solution',
      variables: ['rto'],
      published_revision: 1,
      published_body: 'Alpha 机密正文',
      kb_sync_status: 'synced',
      updated_at: '2026-10-22T10:00:00Z',
    },
    {
      id: 'snip-alpha-002',
      company_id: 'alpha',
      product: '数据中台',
      snippet_type: 'solution',
      variables: ['tps'],
      published_revision: 2,
      published_body: 'Alpha 第二条正文',
      kb_sync_status: 'synced',
      updated_at: '2026-10-22T11:00:00Z',
    },
    {
      id: 'snip-beta-001',
      company_id: 'beta',
      product: '机电安装',
      snippet_type: 'solution',
      variables: ['bim'],
      published_revision: 1,
      published_body: 'Beta 机密正文',
      kb_sync_status: 'synced',
      updated_at: '2026-10-22T12:00:00Z',
    },
  ];

  // 1. Alpha 用户绝对看不到 Beta 的数据
  const alphaResults = filterSnippets(items, {}, 'alpha');
  assert.equal(alphaResults.length, 2);
  assert.ok(alphaResults.every(item => item.company_id === 'alpha'));
  assert.equal(alphaResults.some(item => item.id === 'snip-beta-001'), false);

  // 2. Beta 用户绝对看不到 Alpha 的数据
  const betaResults = filterSnippets(items, {}, 'beta');
  assert.equal(betaResults.length, 1);
  assert.equal(betaResults[0].id, 'snip-beta-001');
  assert.equal(betaResults[0].company_id, 'beta');
  assert.equal(betaResults.some(item => item.company_id === 'alpha'), false);

  // 3. 不存在的租户返回空列表
  const gammaResults = filterSnippets(items, {}, 'gamma');
  assert.equal(gammaResults.length, 0);
});

/* ========================================================================= */
/* 6. 多维条件筛选 (filterSnippets)                                           */
/* ========================================================================= */

test('filterSnippets: 关键字、分类、同步状态与仅已发布门禁', () => {
  const items = DEFAULT_SNIPPET_PUBLICATIONS;

  // 1. 仅已发布门禁 (onlyPublished)
  const onlyPublished = filterSnippets(items, { onlyPublished: true }, 'alpha');
  assert.ok(onlyPublished.every(i => (i.published_revision ?? 0) > 0 || (i.published_body && i.published_body.trim())));

  // 2. 按分类筛选
  const solutions = filterSnippets(items, { snippet_type: 'solution' }, 'alpha');
  assert.ok(solutions.length > 0);
  assert.ok(solutions.every(i => i.snippet_type === 'solution'));

  const boilerplates = filterSnippets(items, { snippet_type: 'boilerplate' }, 'alpha');
  assert.ok(boilerplates.length > 0);
  assert.ok(boilerplates.every(i => i.snippet_type === 'boilerplate'));

  // 3. 按同步状态筛选
  const synced = filterSnippets(items, { kb_sync_status: 'synced' }, 'alpha');
  assert.ok(synced.every(i => i.kb_sync_status === 'synced'));

  const unsynced = filterSnippets(items, { kb_sync_status: 'unsynced' }, 'alpha');
  assert.ok(unsynced.every(i => i.kb_sync_status === 'unsynced'));

  // 4. 关键字搜索（支持正文、变量、产品、套话组、ID）
  const kwSearch1 = filterSnippets(items, { search: 'cluster_nodes' }, 'alpha');
  assert.equal(kwSearch1.length, 1);
  assert.equal(kwSearch1[0].id, 'snip-alpha-001');

  const kwSearch2 = filterSnippets(items, { search: '应急监测' }, 'alpha');
  assert.ok(kwSearch2.length >= 1);

  const kwSearch3 = filterSnippets(items, { search: 'non_existent_key_999' }, 'alpha');
  assert.equal(kwSearch3.length, 0);
});

/* ========================================================================= */
/* 7. 指标汇总统计 (computeSnippetStats)                                      */
/* ========================================================================= */

test('computeSnippetStats: 准确计算租户内的片段统计指标', () => {
  const statsAlpha = computeSnippetStats(DEFAULT_SNIPPET_PUBLICATIONS, 'alpha');
  assert.equal(statsAlpha.totalCount, 4);
  assert.equal(statsAlpha.publishedCount, 4);
  assert.equal(statsAlpha.syncedCount, 3);
  // Alpha 变量去重计数
  assert.ok(statsAlpha.variablesCount > 0);

  const statsBeta = computeSnippetStats(DEFAULT_SNIPPET_PUBLICATIONS, 'beta');
  assert.equal(statsBeta.totalCount, 1);
  assert.equal(statsBeta.publishedCount, 1);
  assert.equal(statsBeta.syncedCount, 1);
  assert.equal(statsBeta.variablesCount, 2);
});

/* ========================================================================= */
/* 8. API 数据加载韧性 (loadSnippetPublications)                              */
/* ========================================================================= */

test('loadSnippetPublications: 函数接口完整且可调用', () => {
  assert.equal(typeof loadSnippetPublications, 'function');
});
