// 为什么有这个文件：验证五类系统生成章节的识别与编辑台只读接线（APP-M2-T191～T195）。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SOURCE_TAB, systemChapterKind, systemPaths } from '../../src/project/system-chapter-core.ts';

test('system chapter titles map to kinds; ordinary chapters do not', () => {
  assert.equal(systemChapterKind('第六章 偏离表').kind, 'deviation');
  assert.equal(systemChapterKind('评审索引表').kind, 'review_index');
  assert.equal(systemChapterKind('2026 年度服务计划表').kind, 'service_plan');
  assert.equal(systemChapterKind('技术方案'), null);
  assert.equal(SOURCE_TAB.service_plan, 'facts');
  assert.equal(systemPaths.generate('p', 'c'), '/api/v1/projects/p/chapters/c/system/generate');
});

test('editor turns system chapters read-only and shows the generate panel', () => {
  const page = readFileSync(new URL('../../src/editor/EditorPage.tsx', import.meta.url), 'utf8');
  assert.match(page, /&& !systemKind;/);
  assert.match(page, /<SystemChapterPanel/);
});
