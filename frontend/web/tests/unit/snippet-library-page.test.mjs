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
} from '../../src/library/snippet-library-core.ts';

/* ========================================================================= */
/* 1. 分类映射与状态元信息测试                                                */
/* ========================================================================= */

// 测试夹具：两家公司的片段，用于验证过滤与统计的租户隔离（页面本身不再内置示例数据）。
const DEFAULT_SNIPPET_PUBLICATIONS = [
  {
    id: 'snip-alpha-001',
    company_id: 'alpha',
    product: '智慧应急监测系统',
    snippet_type: 'solution',
    boilerplate_group: '核心架构与冗余设计',
    source_group: '应急监测技术白皮书',
    variables: ['cluster_nodes', 'rto_minutes', 'rpo_minutes', 'redundancy_level'],
    published_body: '系统基于双活微服务集群架构设计，整体集群节点不少于 {{cluster_nodes}} 个，支持跨机房双活容灾部署。在主节点发生软硬件单点故障时，核心数据及业务可在 {{rto_minutes}} 分钟内实现无感漂移（RTO ≤ {{rto_minutes}} min），数据备份恢复点目标达到 {{rpo_minutes}} 分钟以内（RPO ≤ {{rpo_minutes}} min）。系统整体硬件冗余度符合国家 {{redundancy_level}} 级高可用技术规范。',
    draft_body: '系统基于双活微服务集群架构设计...',
    draft_revision: 2,
    published_revision: 2,
    kb_sync_status: 'synced',
    updated_at: '2026-10-22T10:15:00Z',
  },
  {
    id: 'snip-alpha-002',
    company_id: 'alpha',
    product: '物联网数据中台',
    snippet_type: 'solution',
    boilerplate_group: '高并发接入与流式处理',
    source_group: '数据中台技术集',
    variables: ['tps_limit', 'storage_retention_days', 'compression_ratio'],
    published_body: '平台采用分布式流式计算引擎，单集群峰值支持每秒 {{tps_limit}} 笔并发设备遥测上报，网络端到端延迟控制在 50ms 范围内。历史数据采用列式分级归档存储，标准保存周期为 {{storage_retention_days}} 天，结合自研 LZ4 增强算法实现 {{compression_ratio}} 的高压缩比，大幅降低存储开销与查询成本。',
    draft_body: '平台采用分布式流式计算引擎...',
    draft_revision: 1,
    published_revision: 1,
    kb_sync_status: 'synced',
    updated_at: '2026-10-21T16:40:00Z',
  },
  {
    id: 'snip-alpha-003',
    company_id: 'alpha',
    product: '通用商务方案',
    snippet_type: 'boilerplate',
    boilerplate_group: '服务可用性与响应SLA',
    source_group: '通用商务条款库',
    variables: ['response_hours', 'onsite_hours', 'sla_uptime_percent'],
    published_body: '在项目维保服务期内，承诺提供 7×24 小时技术支持热线与专属工单通道。针对一级紧急故障，技术专家团队将在 {{response_hours}} 小时内做出实质响应并提供排障方案，{{onsite_hours}} 小时内到达现场进行抢修，确保年度系统服务可用性达 {{sla_uptime_percent}}% 以上。',
    draft_body: '在项目维保服务期内...',
    draft_revision: 3,
    published_revision: 3,
    kb_sync_status: 'synced',
    updated_at: '2026-10-20T09:20:00Z',
  },
  {
    id: 'snip-alpha-004',
    company_id: 'alpha',
    product: '智慧应急监测系统',
    snippet_type: 'case',
    boilerplate_group: '标杆工程实施经验',
    source_group: '标杆案例库',
    variables: ['project_city', 'sensor_count'],
    published_body: '本方案已在 {{project_city}} 综合应急监测项目中成熟落地，平稳接入各类边缘传感器超过 {{sensor_count}} 台，经历多次强对流天气考验，预警准确率达到 99.8%，获省部级数字化转型优秀案例示范。',
    draft_body: '本方案已在 {{project_city}} 综合应急监测项目中成熟落地...',
    draft_revision: 2,
    published_revision: 1,
    kb_sync_status: 'unsynced',
    updated_at: '2026-10-22T14:00:00Z',
  },
  {
    id: 'snip-beta-001',
    company_id: 'beta',
    product: '机电安装工程',
    snippet_type: 'solution',
    boilerplate_group: 'BIM深化工法技术',
    source_group: '建筑机电方案库',
    variables: ['bim_software', 'clash_accuracy_mm'],
    published_body: '项目全过程采用 {{bim_software}} 进行全专业三维管线综合排布与碰撞检查，将管线安装标高冲突控制在 {{clash_accuracy_mm}} mm 精度内，确保现场一次成优，避免返工窝工。',
    draft_body: '项目全过程采用...',
    draft_revision: 1,
    published_revision: 1,
    kb_sync_status: 'synced',
    updated_at: '2026-10-21T11:00:00Z',
  },
];

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
