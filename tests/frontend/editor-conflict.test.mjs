// 为什么有这个文件：为 APP-M2-T162 编辑台段落保存、实时字数统计与 OCC 409 冲突合并提供纯逻辑单元测试。
// 它解决什么问题：
// 1. 验证实时字数统计与目标字数区间（偏少 / 符合预期 / 超出上限 / 未设目标）的诊断算法与进度条计算；
// 2. 验证基线对比脏状态（dirty flag）计算准确性；
// 3. 验证 OCC 409 乐观锁冲突识别器对各类 API 错误与响应载荷的准确捕获；
// 4. 验证冲突合并决策策略（保留本地覆盖 vs 放弃本地采纳远程最新）的正确性。

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateWordCount,
  calculateDirtyState,
  isRevisionConflict,
  resolveConflictChoice,
} from '../../frontend/web/src/editor-conflict.ts';
import { ApiError } from '../../frontend/web/src/api.ts';

test('calculateWordCount: 未设目标或非法目标字数', () => {
  const resultNull = calculateWordCount('一段测试文本', null);
  assert.equal(resultNull.charCount, 6);
  assert.equal(resultNull.targetLength, null);
  assert.equal(resultNull.progressPercent, 0);
  assert.equal(resultNull.status, 'no_target');
  assert.equal(resultNull.color, 'default');
  assert.equal(resultNull.label, '6 字');
  assert.match(resultNull.hint, /未设目标字数/);

  const resultZero = calculateWordCount('测试', 0);
  assert.equal(resultZero.status, 'no_target');

  const resultEmpty = calculateWordCount('', null);
  assert.equal(resultEmpty.charCount, 0);
  assert.equal(resultEmpty.status, 'no_target');
  assert.match(resultEmpty.hint, /未填写正文内容/);
});

test('calculateWordCount: 字数偏少 (<80% 目标)', () => {
  // 目标 1000 字，当前 600 字 (60%)
  const content = 'a'.repeat(600);
  const result = calculateWordCount(content, 1000);
  assert.equal(result.charCount, 600);
  assert.equal(result.targetLength, 1000);
  assert.equal(result.progressPercent, 60);
  assert.equal(result.status, 'below_target');
  assert.equal(result.color, 'warning');
  assert.equal(result.label, '600 / 1000 字');
  assert.match(result.hint, /偏少/);
  assert.match(result.hint, /还差约 400 字/);
});

test('calculateWordCount: 字数符合预期 (80% ~ 120% 目标)', () => {
  // 目标 1000 字，当前 950 字 (95%)
  const content950 = 'b'.repeat(950);
  const result950 = calculateWordCount(content950, 1000);
  assert.equal(result950.charCount, 950);
  assert.equal(result950.targetLength, 1000);
  assert.equal(result950.progressPercent, 95);
  assert.equal(result950.status, 'on_target');
  assert.equal(result950.color, 'success');
  assert.match(result950.hint, /符合.*预期/);

  // 边界：刚好 800 字 (80%)
  const content800 = 'b'.repeat(800);
  const result800 = calculateWordCount(content800, 1000);
  assert.equal(result800.status, 'on_target');
  assert.equal(result800.color, 'success');

  // 边界：刚好 1200 字 (120%)
  const content1200 = 'b'.repeat(1200);
  const result1200 = calculateWordCount(content1200, 1000);
  assert.equal(result1200.status, 'on_target');
  assert.equal(result1200.color, 'success');
});

test('calculateWordCount: 字数超出上限 (>120% 目标)', () => {
  // 目标 1000 字，当前 1500 字 (150%)
  const content = 'c'.repeat(1500);
  const result = calculateWordCount(content, 1000);
  assert.equal(result.charCount, 1500);
  assert.equal(result.targetLength, 1000);
  assert.equal(result.progressPercent, 100); // 进度上限封顶 100%
  assert.equal(result.status, 'above_target');
  assert.equal(result.color, 'warning');
  assert.match(result.hint, /超出目标预期约 500 字/);
});

test('calculateDirtyState: 准确判定编辑草稿脏状态', () => {
  assert.equal(calculateDirtyState('任意内容', null).dirty, false);

  const baseChapter = {
    id: 'chap-1',
    project_id: 'p-1',
    volume: 'commercial',
    revision: 3,
    title: '实施方案',
    content: '正式正文内容 v3',
    draft: null,
  };

  // 场景 1：无草稿，当前内容与正式正文相同 -> 不脏，未修改
  const res1 = calculateDirtyState('正式正文内容 v3', baseChapter);
  assert.equal(res1.dirty, false);
  assert.equal(res1.modified, false);

  // 场景 2：无草稿，当前内容发生修改 -> 脏，已修改
  const res2 = calculateDirtyState('新编写的一段文字', baseChapter);
  assert.equal(res2.dirty, true);
  assert.equal(res2.modified, true);

  // 场景 3：有与正文同 revision 的草稿，当前内容与草稿一致 -> 不脏
  const chapterWithMatchingDraft = {
    ...baseChapter,
    draft: {
      base_revision: 3,
      sequence: 1,
      content: '未提交的暂存草稿',
      updated_at: '2026-10-22T10:00:00Z',
    },
  };
  const res3a = calculateDirtyState('未提交的暂存草稿', chapterWithMatchingDraft);
  assert.equal(res3a.dirty, false);
  assert.equal(res3a.modified, true); // 与正式正文相比有不同

  const res3b = calculateDirtyState('继续修改草稿文字', chapterWithMatchingDraft);
  assert.equal(res3b.dirty, true);
  assert.equal(res3b.modified, true);

  // 场景 4：草稿是基于旧 revision (v2) 的，正文已是 v3 -> 基线采用正文 v3 内容
  const chapterWithOldDraft = {
    ...baseChapter,
    draft: {
      base_revision: 2,
      sequence: 1,
      content: '基于旧版本的草稿',
      updated_at: '2026-10-21T10:00:00Z',
    },
  };
  const res4a = calculateDirtyState('正式正文内容 v3', chapterWithOldDraft);
  assert.equal(res4a.dirty, false);

  const res4b = calculateDirtyState('基于旧版本的草稿', chapterWithOldDraft);
  assert.equal(res4b.dirty, true);
});

test('isRevisionConflict: 多形态 409 OCC 乐观锁冲突识别', () => {
  // 1. ApiError 实例且状态码为 409
  const apiErr409 = new ApiError(409, 'REVISION_CONFLICT', '正文已被其他编写人提交');
  assert.equal(isRevisionConflict(apiErr409), true);

  // 2. ApiError code 为 CHAPTER_CONFLICT
  const apiErrChapterConflict = new ApiError(400, 'CHAPTER_CONFLICT', '章节版本冲突');
  assert.equal(isRevisionConflict(apiErrChapterConflict), true);

  // 3. 普通对象结构模拟的 409 响应载荷
  assert.equal(isRevisionConflict({ status: 409 }), true);
  assert.equal(isRevisionConflict({ code: 'REVISION_CONFLICT' }), true);
  assert.equal(isRevisionConflict({ error: { code: 'REVISION_CONFLICT' } }), true);
  assert.equal(isRevisionConflict({ message: '409 revision conflict' }), true);
  assert.equal(isRevisionConflict({ message: '版本冲突，请拉取最新章节' }), true);

  // 4. 非冲突错误应返回 false
  assert.equal(isRevisionConflict(new ApiError(403, 'FORBIDDEN', '无权操作')), false);
  assert.equal(isRevisionConflict(new ApiError(404, 'NOT_FOUND', '章节不存在')), false);
  assert.equal(isRevisionConflict(new ApiError(500, 'SERVER_ERROR', '服务器内部错误')), false);
  assert.equal(isRevisionConflict(null), false);
  assert.equal(isRevisionConflict(undefined), false);
  assert.equal(isRevisionConflict('网络超时'), false);
});

test('resolveConflictChoice: 决策本地覆盖或放弃本地', () => {
  const context = {
    localContent: '本地编写的修改',
    remoteContent: '远程同事提交的新正文',
    remoteRevision: 5,
    baseRevision: 3,
    target: 'draft',
  };

  // 决策 1：保留本地覆盖（推进基线后覆盖保存草稿）
  const overwriteChoice = resolveConflictChoice('overwrite', context);
  assert.equal(overwriteChoice.action, 'overwrite');
  assert.equal(overwriteChoice.nextRevision, 5);
  assert.equal(overwriteChoice.nextBaseRevision, 5);
  assert.equal(overwriteChoice.nextContent, '本地编写的修改');
  assert.match(overwriteChoice.message, /保留本地修改/);
  assert.match(overwriteChoice.message, /v5/);

  // 决策 2：放弃本地修改（采用远程最新正文）
  const discardChoice = resolveConflictChoice('discard', context);
  assert.equal(discardChoice.action, 'discard');
  assert.equal(discardChoice.nextRevision, 5);
  assert.equal(discardChoice.nextBaseRevision, 5);
  assert.equal(discardChoice.nextContent, '远程同事提交的新正文');
  assert.match(discardChoice.message, /放弃本地修改/);
  assert.match(discardChoice.message, /v5/);
});
