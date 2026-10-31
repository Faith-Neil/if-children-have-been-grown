// 为什么有这个文件：验证写作方案核对里条款的显示（PRD v1.8 §5.3.1 验收④⑤）。
// 它解决什么问题：分流未确认的行要标出“确认前不进入写作方案”；跨分册共用行在另一分册也列出。
import test from 'node:test';
import assert from 'node:assert/strict';
import { planRequirementText } from '../../src/editor/writing-input.ts';

test('plan text marks pending routing and shared rows', () => {
  const workspace = {
    chapters: [{ id: 'c-tech', requirement_ids: ['r1', 'r2'] }, { id: 'c-biz', requirement_ids: ['r2'] }],
    requirements: [
      { id: 'r1', text: '每月巡检', chapter_id: 'c-tech', volume_confirmed_at: null },
      { id: 'r2', text: '驻场人员', chapter_id: 'c-tech', volume_confirmed_at: '2026-10-29T00:00:00Z', is_cross_volume: true, shared_chapter_id: 'c-biz' },
    ],
  };
  assert.equal(planRequirementText(workspace, 'c-tech'), '每月巡检（分流待确认，确认前不进入写作方案）；驻场人员');
  assert.equal(planRequirementText(workspace, 'c-biz'), '驻场人员（跨分册共用）');
  assert.equal(planRequirementText({ chapters: [], requirements: [] }, 'x'), '本节未映射条款');
});
