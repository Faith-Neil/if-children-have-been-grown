// 为什么有这个测试：验证大纲排序、章节类型、增值理由与星号/废标禁止不适用的核心门禁纯逻辑。
// 它解决什么问题：确保大纲树的排序算法、多级编号归一化、增值理由校验以及 PRD v1.8 §5.7.2/5.7.8 的合规红线门禁得到 100% 独立验证。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canMarkNotApplicable,
  validateChapterTypeChange,
  reorderNodes,
  normalizeChapterNumbers,
  validateValueAddedReason,
  getChapterTypeMeta,
  CHAPTER_TYPES_CONFIG,
} from '../../frontend/web/src/outline-tree.ts';

test('1. 章节类型元信息与配置定义 (getChapterTypeMeta)', () => {
  const specialized = getChapterTypeMeta('specialized');
  assert.equal(specialized.label, '专项方案');
  assert.equal(specialized.color, '#1e4db7');
  assert.equal(specialized.isAiRelevant, true);

  const general = getChapterTypeMeta('general');
  assert.equal(general.label, '通用方案');

  const systemGen = getChapterTypeMeta('system_generated');
  assert.equal(systemGen.label, '系统生成');
  assert.equal(systemGen.color, '#722ed1'); // 专属 AI 紫色

  const cover = getChapterTypeMeta('cover_and_catalog');
  assert.equal(cover.label, '封面目录');

  const notApplicable = getChapterTypeMeta('not_applicable');
  assert.equal(notApplicable.label, '不适用');
});

test('2. 【核心门禁红线】星号条款章节绝对禁止标记为“不适用” (canMarkNotApplicable)', () => {
  const starredNode = {
    title: '系统架构安全设计',
    isStarred: true,
    isBlocker: false,
  };

  const check = canMarkNotApplicable(starredNode);
  assert.equal(check.allowed, false);
  assert.ok(check.reason?.includes('星号(★)关键条款'));
  assert.ok(check.reason?.includes('禁止'));

  // 变更校验前置拦截
  const validation = validateChapterTypeChange(starredNode, 'not_applicable');
  assert.equal(validation.valid, false);
  assert.ok(validation.error?.includes('星号'));

  // 允许变更为其他类型
  assert.equal(validateChapterTypeChange(starredNode, 'specialized').valid, true);
  assert.equal(validateChapterTypeChange(starredNode, 'general').valid, true);
});

test('3. 【核心门禁红线】废标条款章节绝对禁止标记为“不适用” (canMarkNotApplicable)', () => {
  const blockerNode = {
    title: '服务可用性承诺函',
    isStarred: false,
    isBlocker: true,
  };

  const check = canMarkNotApplicable(blockerNode);
  assert.equal(check.allowed, false);
  assert.ok(check.reason?.includes('废标关键条款'));
  assert.ok(check.reason?.includes('禁止'));

  const validation = validateChapterTypeChange(blockerNode, 'not_applicable');
  assert.equal(validation.valid, false);
  assert.ok(validation.error?.includes('废标'));
});

test('4. 普通章节允许正常标记为“不适用”', () => {
  const normalNode = {
    title: '可选增值服务说明',
    isStarred: false,
    isBlocker: false,
  };

  const check = canMarkNotApplicable(normalNode);
  assert.equal(check.allowed, true);
  assert.equal(check.reason, undefined);

  const validation = validateChapterTypeChange(normalNode, 'not_applicable');
  assert.equal(validation.valid, true);
});

test('5. 章节同级顺序调整算法 (reorderNodes)', () => {
  const initialNodes = [
    { id: 'c1', title: '第1章', volume: 'technical', chapterType: 'specialized', orderIndex: 1 },
    { id: 'c2', title: '第2章', volume: 'technical', chapterType: 'general', orderIndex: 2 },
    { id: 'c3', title: '第3章', volume: 'technical', chapterType: 'specialized', orderIndex: 3 },
  ];

  // 1. 第一项不可上移
  const upFirst = reorderNodes(initialNodes, 'c1', 'up');
  assert.deepEqual(upFirst.map(n => n.id), ['c1', 'c2', 'c3']);

  // 2. 最后一项不可下移
  const downLast = reorderNodes(initialNodes, 'c3', 'down');
  assert.deepEqual(downLast.map(n => n.id), ['c1', 'c2', 'c3']);

  // 3. 中间项下移：c2 与 c3 互换
  const downMiddle = reorderNodes(initialNodes, 'c2', 'down');
  assert.deepEqual(downMiddle.map(n => n.id), ['c1', 'c3', 'c2']);
  assert.equal(downMiddle[0].orderIndex, 1);
  assert.equal(downMiddle[1].orderIndex, 2);
  assert.equal(downMiddle[2].orderIndex, 3);

  // 4. 末尾项上移：c3 上移到首位之后
  const upThird = reorderNodes(initialNodes, 'c3', 'up');
  assert.deepEqual(upThird.map(n => n.id), ['c1', 'c3', 'c2']);
});

test('6. 多层级编号归一化 (normalizeChapterNumbers)', () => {
  const hierarchicalNodes = [
    {
      id: 'c1',
      title: '总体方案',
      volume: 'technical',
      chapterType: 'specialized',
      orderIndex: 1,
      children: [
        { id: 'c1-1', title: '架构设计', volume: 'technical', chapterType: 'specialized', orderIndex: 1 },
        { id: 'c1-2', title: '部署方案', volume: 'technical', chapterType: 'general', orderIndex: 2 },
      ],
    },
    {
      id: 'c2',
      title: '运维保障',
      volume: 'technical',
      chapterType: 'general',
      orderIndex: 2,
    },
  ];

  const normalized = normalizeChapterNumbers(hierarchicalNodes);
  assert.equal(normalized[0].chapterNumber, '1');
  assert.equal(normalized[0].children[0].chapterNumber, '1.1');
  assert.equal(normalized[0].children[1].chapterNumber, '1.2');
  assert.equal(normalized[1].chapterNumber, '2');
});

test('7. 增值理由校验 (validateValueAddedReason)', () => {
  // 正常字符放行
  assert.equal(validateValueAddedReason('提供额外 20% 性能提升').valid, true);
  assert.equal(validateValueAddedReason('', 'specialized').valid, true);

  // 超长字符（> 500）拦截
  const overlyLong = 'a'.repeat(501);
  const result = validateValueAddedReason(overlyLong);
  assert.equal(result.valid, false);
  assert.ok(result.error?.includes('500'));
});
