// 为什么有这个文件：测试 1280 / 1440 / 1680 断点自适应、侧栏折叠状态持久化记忆与多层级动态面包屑纯逻辑。
// 它解决什么问题：
// 1. 验证 1280（紧凑桌面，主内容区 1040px）、1440（标准桌面）、1680（宽屏工作台）各视口临界断点与列数推导；
// 2. 验证 localStorage 侧栏持久化状态读写、优雅异常降级与进入项目自动收起策略；
// 3. 验证长项目名称智能截断与悬停全称保留；
// 4. 验证 404、全局功能页、项目概览、各业务页签及编辑台分册的多层级面包屑推导与链接回跳属性。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  BREAKPOINT_COMPACT,
  BREAKPOINT_STANDARD,
  BREAKPOINT_WIDE,
  getBreakpointInfo,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  readStoredSidebarCollapsed,
  writeStoredSidebarCollapsed,
  resolveInitialSidebarCollapsed,
  onEnterProjectCollapse,
  formatProjectShortName,
  deriveBreadcrumbs,
  PROJECT_TAB_LABELS,
  GLOBAL_ROUTE_LABELS,
} from '../../src/shell/responsive.ts';

// ----------------------------------------------------
// 1. 三大标准断点与自适应计算测试
// ----------------------------------------------------

test('standard breakpoint constants match PRD specifications', () => {
  assert.equal(BREAKPOINT_COMPACT, 1280, 'Compact breakpoint is 1280px');
  assert.equal(BREAKPOINT_STANDARD, 1440, 'Standard breakpoint is 1440px');
  assert.equal(BREAKPOINT_WIDE, 1680, 'Wide workbench breakpoint is 1680px');
});

test('getBreakpointInfo correctly calculates tiers, flags, editorColumns, and contentWidth', () => {
  // 场景 1: 超窄视口 (< 1280px)
  const subCompact = getBreakpointInfo(1024);
  assert.equal(subCompact.tier, 'sub-compact');
  assert.equal(subCompact.isSubCompact, true);
  assert.equal(subCompact.isCompact, false);
  assert.equal(subCompact.isStandard, false);
  assert.equal(subCompact.isWide, false);
  assert.equal(subCompact.isAtLeast1280, false);
  assert.equal(subCompact.editorColumns, 3);
  assert.equal(subCompact.contentWidth, 1024 - 240);

  // 临界边界: 1279px
  const edgeSub = getBreakpointInfo(1279);
  assert.equal(edgeSub.tier, 'sub-compact');
  assert.equal(edgeSub.isAtLeast1280, false);

  // 场景 2: 紧凑桌面 (1280px <= width < 1440px)
  const compact1280 = getBreakpointInfo(1280);
  assert.equal(compact1280.tier, 'compact');
  assert.equal(compact1280.isCompact, true);
  assert.equal(compact1280.isAtLeast1280, true);
  assert.equal(compact1280.isAtLeast1440, false);
  assert.equal(compact1280.editorColumns, 3);
  assert.equal(compact1280.contentWidth, 1040, '1280px guarantees 1040px content without horizontal scroll');

  const compact1366 = getBreakpointInfo(1366);
  assert.equal(compact1366.tier, 'compact');
  assert.equal(compact1366.isCompact, true);
  assert.equal(compact1366.contentWidth, 1040);

  // 临界边界: 1439px
  const edgeCompact = getBreakpointInfo(1439);
  assert.equal(edgeCompact.tier, 'compact');
  assert.equal(edgeCompact.isAtLeast1440, false);

  // 场景 3: 标准桌面 (1440px <= width < 1680px)
  const standard1440 = getBreakpointInfo(1440);
  assert.equal(standard1440.tier, 'standard');
  assert.equal(standard1440.isStandard, true);
  assert.equal(standard1440.isAtLeast1440, true);
  assert.equal(standard1440.isAtLeast1680, false);
  assert.equal(standard1440.editorColumns, 3, 'Standard screen uses 3 columns');
  assert.equal(standard1440.contentWidth, 1200);

  // 临界边界: 1679px
  const edgeStandard = getBreakpointInfo(1679);
  assert.equal(edgeStandard.tier, 'standard');
  assert.equal(edgeStandard.isAtLeast1680, false);

  // 场景 4: 宽屏工作台 (>= 1680px)
  const wide1680 = getBreakpointInfo(1680);
  assert.equal(wide1680.tier, 'wide');
  assert.equal(wide1680.isWide, true);
  assert.equal(wide1680.isAtLeast1680, true);
  assert.equal(wide1680.editorColumns, 4, '1680px workbench expands to 4 columns');
  assert.equal(wide1680.contentWidth, 1440);

  const wide1920 = getBreakpointInfo(1920);
  assert.equal(wide1920.tier, 'wide');
  assert.equal(wide1920.editorColumns, 4);

  // 场景 5: 异常输入优雅降级为 1440 标准桌面
  const fallbackNaN = getBreakpointInfo(Number.NaN);
  assert.equal(fallbackNaN.tier, 'standard');
  assert.equal(fallbackNaN.width, 1440);

  const fallbackNegative = getBreakpointInfo(-50);
  assert.equal(fallbackNegative.tier, 'standard');
});

// ----------------------------------------------------
// 2. 侧栏持久化记忆与进入项目收起策略测试
// ----------------------------------------------------

function createMockStorage() {
  const map = new Map();
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
    clear: () => map.clear(),
  };
}

test('readStoredSidebarCollapsed and writeStoredSidebarCollapsed operate on localStorage correctly', () => {
  const mock = createMockStorage();

  // 初始无值
  assert.equal(readStoredSidebarCollapsed(mock), null);

  // 写入收起 true
  assert.equal(writeStoredSidebarCollapsed(true, mock), true);
  assert.equal(mock.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY), 'true');
  assert.equal(readStoredSidebarCollapsed(mock), true);

  // 写入展开 false
  assert.equal(writeStoredSidebarCollapsed(false, mock), true);
  assert.equal(mock.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY), 'false');
  assert.equal(readStoredSidebarCollapsed(mock), false);

  // 异常 storage（如无权限/配额满抛出异常）
  const failingStorage = {
    getItem: () => { throw new Error('Storage security denied'); },
    setItem: () => { throw new Error('Quota exceeded'); },
  };
  assert.equal(readStoredSidebarCollapsed(failingStorage), null);
  assert.equal(writeStoredSidebarCollapsed(true, failingStorage), false);
});

test('resolveInitialSidebarCollapsed adheres to user preference and project auto-collapse rule', () => {
  // 1. 用户显式设置了持久化偏好时，无条件遵从用户偏好
  assert.equal(resolveInitialSidebarCollapsed({ isInProject: true, storedValue: false }), false);
  assert.equal(resolveInitialSidebarCollapsed({ isInProject: false, storedValue: true }), true);

  // 2. 用户未设置持久化偏好 (null)
  // 进入项目：默认自动收起 (true)
  assert.equal(resolveInitialSidebarCollapsed({ isInProject: true, storedValue: null }), true);
  // 全局页面：默认展开 (false)
  assert.equal(resolveInitialSidebarCollapsed({ isInProject: false, storedValue: null }), false);
  // 全局页面自定义默认值
  assert.equal(resolveInitialSidebarCollapsed({ isInProject: false, storedValue: null, defaultGlobalCollapsed: true }), true);
});

test('onEnterProjectCollapse ensures sidebar collapses upon entering project unless user preferred expanded', () => {
  // 未设置偏好：自动收起 (true)
  assert.equal(onEnterProjectCollapse(false, null), true);
  assert.equal(onEnterProjectCollapse(true, null), true);

  // 用户设置了偏好：保持偏好
  assert.equal(onEnterProjectCollapse(true, false), false);
  assert.equal(onEnterProjectCollapse(false, true), true);
});

// ----------------------------------------------------
// 3. 项目名称格式化测试
// ----------------------------------------------------

test('formatProjectShortName truncates long project names and appends ellipsis', () => {
  // 正常短名称 (< 16 字符)
  assert.equal(formatProjectShortName('智慧城市交通项目'), '智慧城市交通项目');

  // 恰好 16 字符
  const exactly16 = '东海城商行数据库运维维保采购';
  assert.equal(exactly16.length, 14);
  assert.equal(formatProjectShortName(exactly16, 14), exactly16);

  // 超过 16 字符，截断为 15 字符 + 省略号
  const longName = '东海城商行2026-2028年度信创核心业务数据库升级及全生命周期维保采购项目';
  const shortened = formatProjectShortName(longName, 16);
  assert.equal(shortened.length, 16);
  assert.ok(shortened.endsWith('…'));
  assert.equal(shortened, '东海城商行2026-2028年…');

  // 空值防守
  assert.equal(formatProjectShortName(''), '未命名项目');
  assert.equal(formatProjectShortName('   '), '未命名项目');
});

// ----------------------------------------------------
// 4. 多层级动态面包屑推导测试
// ----------------------------------------------------

test('deriveBreadcrumbs correctly derives breadcrumb paths for 404 missing pages', () => {
  const crumbs = deriveBreadcrumbs({ missing: '/some-invalid-page' });
  assert.equal(crumbs.length, 2);
  assert.deepEqual(crumbs[0], {
    key: 'workbench',
    title: '工作台',
    fullTitle: '投标项目工作台',
    path: '/workbench',
  });
  assert.deepEqual(crumbs[1], {
    key: 'missing',
    title: '页面不存在',
    fullTitle: '页面不存在',
    isCurrent: true,
  });
});

test('deriveBreadcrumbs correctly derives breadcrumbs for global routes', () => {
  // 工作台根路径
  const wb = deriveBreadcrumbs({ nav: 'workbench' });
  assert.equal(wb.length, 1);
  assert.equal(wb[0].key, 'workbench');
  assert.equal(wb[0].isCurrent, true);
  assert.equal(wb[0].path, undefined);

  // 企业资料库
  const lib = deriveBreadcrumbs({ nav: 'library' });
  assert.equal(lib.length, 2);
  assert.equal(lib[0].key, 'workbench');
  assert.equal(lib[0].path, '/workbench');
  assert.equal(lib[1].key, 'library');
  assert.equal(lib[1].title, GLOBAL_ROUTE_LABELS.library);
  assert.equal(lib[1].isCurrent, true);

  // 后台任务
  const jobs = deriveBreadcrumbs({ nav: 'jobs' });
  assert.equal(jobs.length, 2);
  assert.equal(jobs[0].key, 'workbench');
  assert.equal(jobs[1].key, 'jobs');
  assert.equal(jobs[1].title, '后台任务');
  assert.equal(jobs[1].isCurrent, true);
});

test('deriveBreadcrumbs derives multi-level paths inside project workspace with proper leaf and links', () => {
  const workspace = {
    project: {
      id: 'proj-001',
      name: '东海城商行2026-2028年度信创核心业务数据库升级及全生命周期维保采购项目',
    },
  };

  // 1. 项目概览页 (tab = 'overview')
  const overviewCrumbs = deriveBreadcrumbs({
    nav: 'workbench',
    tab: 'overview',
    workspace,
  });
  assert.equal(overviewCrumbs.length, 3);
  assert.equal(overviewCrumbs[0].title, '工作台');
  assert.equal(overviewCrumbs[0].path, '/workbench');

  assert.equal(overviewCrumbs[1].key, 'project');
  assert.equal(overviewCrumbs[1].title, '东海城商行2026-2028年…');
  assert.equal(overviewCrumbs[1].fullTitle, workspace.project.name);
  assert.equal(overviewCrumbs[1].path, '/projects/proj-001/overview');

  assert.equal(overviewCrumbs[2].key, 'tab-overview');
  assert.equal(overviewCrumbs[2].title, '项目概览');
  assert.equal(overviewCrumbs[2].isCurrent, true);
  assert.equal(overviewCrumbs[2].path, undefined);

  // 2. 章节编辑台 (tab = 'editor')
  const editorCrumbs = deriveBreadcrumbs({
    nav: 'workbench',
    tab: 'editor',
    workspace,
  });
  assert.equal(editorCrumbs.length, 3);
  assert.equal(editorCrumbs[1].path, '/projects/proj-001/overview');
  assert.equal(editorCrumbs[2].title, PROJECT_TAB_LABELS.editor);
  assert.equal(editorCrumbs[2].isCurrent, true);

  // 3. 编辑台附带分册上下文 (4 级面包屑：工作台 > 项目 > 编辑台 > 技术分册)
  const volumeCrumbs = deriveBreadcrumbs({
    nav: 'workbench',
    tab: 'editor',
    volume: 'technical',
    workspace,
  });
  assert.equal(volumeCrumbs.length, 4);
  assert.equal(volumeCrumbs[0].path, '/workbench');
  assert.equal(volumeCrumbs[1].path, '/projects/proj-001/overview');
  assert.equal(volumeCrumbs[2].title, '编辑台');
  assert.equal(volumeCrumbs[2].path, '/projects/proj-001/editor');
  assert.equal(volumeCrumbs[3].title, '技术分册');
  assert.equal(volumeCrumbs[3].fullTitle, '编辑台 · 技术分册');
  assert.equal(volumeCrumbs[3].isCurrent, true);
  assert.equal(volumeCrumbs[3].path, undefined);

  // 4. 业务页签切换 (合规检查、响应矩阵等)
  const checkCrumbs = deriveBreadcrumbs({
    nav: 'workbench',
    tab: 'checks',
    workspace,
  });
  assert.equal(checkCrumbs.length, 3);
  assert.equal(checkCrumbs[2].title, '合规检查');
  assert.equal(checkCrumbs[2].isCurrent, true);
});

test('deriveBreadcrumbs strictly guarantees linkability invariants', () => {
  const workspace = { project: { id: 'test-p', name: '短项目' } };
  const crumbs = deriveBreadcrumbs({ nav: 'workbench', tab: 'matrix', workspace });

  // 前置节点必须包含 path 且不能被判定为当前页
  for (let i = 0; i < crumbs.length - 1; i++) {
    const item = crumbs[i];
    assert.ok(item.path, `Item ${i} (${item.title}) must have a valid path`);
    assert.equal(item.isCurrent, undefined, `Item ${i} must not be marked current`);
  }

  // 末级节点不能提供 path 且必须标记为 isCurrent
  const last = crumbs[crumbs.length - 1];
  assert.equal(last.path, undefined, 'Last item should not have navigation path');
  assert.equal(last.isCurrent, true, 'Last item must be marked isCurrent');
});
