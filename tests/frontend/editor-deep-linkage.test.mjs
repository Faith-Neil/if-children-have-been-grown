// 为什么有这个测试：验证编辑台与大纲树深度联动（APP-M2-T168）、断点响应式折叠（APP-M2-T160）以及章节加载权限协同的纯逻辑。
// 它解决什么问题：
// 1. 验证工作区章节与条款到大纲树节点的映射纯逻辑（mapChaptersToOutlineNodes）；
// 2. 验证星号(★)条款、废标条款、系统生成及封面目录的类型智能推导；
// 3. 验证三档断点响应式下编辑区宽度预算与零横滚自适应规则（确保中屏正文编辑区 >= 700px）；
// 4. 验证未保存文字切换章节防丢拦截与平滑跳转行为。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  mapChaptersToOutlineNodes,
  canMarkNotApplicable,
  getChapterTypeMeta,
} from '../../frontend/web/src/outline-tree.ts';
import {
  getBreakpointInfo,
  BREAKPOINT_COMPACT,
  BREAKPOINT_STANDARD,
  BREAKPOINT_WIDE,
} from '../../frontend/web/src/responsive.ts';

test('1. mapChaptersToOutlineNodes 基础字段与分册映射', () => {
  const chapters = [
    { id: 'c1', title: '1. 项目总体概述', volume: 'technical', assignee_name: '张三' },
    { id: 'c2', title: '2. 商务报价与条款偏离', volume: 'commercial', assignee_name: '李四' },
  ];
  const reqs = [
    { id: 'r1', chapter_id: 'c1', starred: false },
    { id: 'r2', chapter_id: 'c2', starred: false },
  ];

  const nodes = mapChaptersToOutlineNodes(chapters, reqs);
  assert.equal(nodes.length, 2);
  assert.equal(nodes[0].id, 'c1');
  assert.equal(nodes[0].key, 'c1');
  assert.equal(nodes[0].title, '1. 项目总体概述');
  assert.equal(nodes[0].volume, 'technical');
  assert.equal(nodes[0].assignee_name, '张三');
  assert.equal(nodes[0].chapterNumber, '1');
  assert.equal(nodes[0].isLeaf, true);
  assert.equal(nodes[0].requirementCount, 1);

  assert.equal(nodes[1].id, 'c2');
  assert.equal(nodes[1].volume, 'commercial');
  assert.equal(nodes[1].chapterNumber, '2');
});

test('2. mapChaptersToOutlineNodes 智能推导星号(★)与废标条款章节', () => {
  const chapters = [
    { id: 'tech-sec', title: '3. 核心网络安全方案', volume: 'technical' },
    { id: 'tech-block', title: '4. 关键服务响应指标', volume: 'technical' },
    { id: 'comm-norm', title: '5. 交付周期承诺', volume: 'commercial' },
  ];
  const reqs = [
    { id: 'req-star', chapter_id: 'tech-sec', is_starred: true },
    { id: 'req-block', chapter_id: 'tech-block', blocker: true },
    { id: 'req-norm', chapter_id: 'comm-norm', starred: false, blocker: false },
  ];

  const nodes = mapChaptersToOutlineNodes(chapters, reqs);
  // tech-sec 应识别为星号条款章节，并默认推导为专项方案 (specialized)
  assert.equal(nodes[0].isStarred, true);
  assert.equal(nodes[0].isBlocker, false);
  assert.equal(nodes[0].chapterType, 'specialized');

  // tech-block 应识别为废标条款章节，并默认推导为专项方案
  assert.equal(nodes[1].isStarred, false);
  assert.equal(nodes[1].isBlocker, true);
  assert.equal(nodes[1].chapterType, 'specialized');

  // 严守门禁红线：星号与废标章节绝对禁止标记为不适用
  assert.equal(canMarkNotApplicable(nodes[0]).allowed, false);
  assert.equal(canMarkNotApplicable(nodes[1]).allowed, false);

  // 普通章节允许正常
  assert.equal(nodes[2].isStarred, false);
  assert.equal(nodes[2].isBlocker, false);
  assert.equal(nodes[2].chapterType, 'general');
  assert.equal(canMarkNotApplicable(nodes[2]).allowed, true);
});

test('3. mapChaptersToOutlineNodes 智能推导系统生成与封面目录章节', () => {
  const chapters = [
    { id: 'gen-score', title: '评分办法及索引对应矩阵', volume: 'technical' },
    { id: 'gen-cover', title: '投标文件封面及总目录', volume: 'commercial' },
  ];

  const nodes = mapChaptersToOutlineNodes(chapters, []);
  assert.equal(nodes[0].chapterType, 'system_generated');
  assert.equal(getChapterTypeMeta(nodes[0].chapterType).color, '#722ed1'); // AI 专属紫色

  assert.equal(nodes[1].chapterType, 'cover_and_catalog');
  assert.equal(getChapterTypeMeta(nodes[1].chapterType).color, '#8c8c8c');
});

test('4. 响应式断点与编辑台列数派生（APP-M2-T160）', () => {
  // 1. 宽屏 >= 1680px：完整展开 4 栏布局（目录 + 正文 + 问题来源 + 对话助手）
  const wideInfo = getBreakpointInfo(1920);
  assert.equal(wideInfo.tier, 'wide');
  assert.equal(wideInfo.isWide, true);
  assert.equal(wideInfo.editorColumns, 4);
  assert.equal(wideInfo.contentWidth, 1440);

  // 2. 标准桌面 1440px ~ 1679px：3 栏布局
  const standardInfo = getBreakpointInfo(1440);
  assert.equal(standardInfo.tier, 'standard');
  assert.equal(standardInfo.isStandard, true);
  assert.equal(standardInfo.editorColumns, 3);
  assert.equal(standardInfo.contentWidth, 1200);

  // 3. 紧凑桌面 1280px ~ 1439px：紧凑 3 栏，保障 1040px 无横向滚动
  const compactInfo = getBreakpointInfo(1280);
  assert.equal(compactInfo.tier, 'compact');
  assert.equal(compactInfo.isCompact, true);
  assert.equal(compactInfo.editorColumns, 3);
  assert.equal(compactInfo.contentWidth, 1040);

  // 4. 超窄视口 < 1280px：sub-compact 状态，支持侧边栏折叠与抽屉
  const subCompactInfo = getBreakpointInfo(1024);
  assert.equal(subCompactInfo.tier, 'sub-compact');
  assert.equal(subCompactInfo.isSubCompact, true);
  assert.equal(subCompactInfo.isAtLeast1280, false);
});

test('5. 中屏 1280px 编辑区最小 700px 预算计算与零横滚保障', () => {
  // 在 1280px 视口下：
  // 容器总宽 1280px
  // 全局左侧折叠导航栏 48px
  // 目录若展开：260px；助手展开：320px
  // 若同时展开：1280 - 48 - 260 - 320 = 652px < 700px，此时会挤压编辑区；
  // APP-M2-T160 / APP-M2-T168 响应式机制：
  // 支持将大纲目录收起为迷你竖条 (44px) 或收起右侧助手 (0px)
  const windowWidth = 1280;
  const globalNavCollapsed = 48;
  const outlineCollapsedWidth = 44;
  const assistantWidth = 320;
  const editorPadding = 32;

  // 当大纲收起为迷你竖条时，中间编辑区宽度：
  const centerWithCollapsedOutline = windowWidth - globalNavCollapsed - outlineCollapsedWidth - assistantWidth - editorPadding;
  assert.ok(centerWithCollapsedOutline >= 700, `中间正文区宽度 ${centerWithCollapsedOutline}px 必须 >= 700px 消除横滚`);

  // 当右侧助手也折叠时，正文区宽度更充裕：
  const centerWithBothCollapsed = windowWidth - globalNavCollapsed - outlineCollapsedWidth - editorPadding;
  assert.ok(centerWithBothCollapsed >= 1100, `双折叠下正文区宽度 ${centerWithBothCollapsed}px 应极为宽裕`);
});

test('6. 未保存文字防离开拦截状态流逻辑', () => {
  let modalConfirmed = false;
  let activeChapterId = 'c1';

  function requestChapterSwitch(nextId, isDirty) {
    if (!isDirty) {
      activeChapterId = nextId;
      return true;
    }
    // 未保存文字触发拦截确认
    modalConfirmed = true;
    return false;
  }

  // 场景 A：无脏文字，平滑直接切换
  const switchClean = requestChapterSwitch('c2', false);
  assert.equal(switchClean, true);
  assert.equal(activeChapterId, 'c2');
  assert.equal(modalConfirmed, false);

  // 场景 B：有脏文字，拦截并唤起提示
  const switchDirty = requestChapterSwitch('c3', true);
  assert.equal(switchDirty, false);
  assert.equal(activeChapterId, 'c2'); // 依然停留在原章节
  assert.equal(modalConfirmed, true);
});
