// 为什么有这个文件：APP-M2-T096 R19 关联投标冲突的前端规则测试。
// 它解决什么问题：只认后台 409 RELATED_BID_CONFLICT；说明字数与后台一致；新建项目与项目设置保存招标编号时都接上确认弹窗。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import * as core from '../../src/project/related-bid-core.ts';
import { ApiError } from '../../src/shared/api.ts';

const read = rel => fs.readFileSync(path.resolve(import.meta.dirname, rel), 'utf8');

test('1. 只识别后台的关联投标冲突', () => {
  const error = new ApiError(409, 'RELATED_BID_CONFLICT', '集团内另一家公司已对同一标段立项。', 'trace', {
    match: 'exact', companies: ['乙公司'], message: '集团内另一家公司已对同一标段立项。依据……', statute: '依据……' });
  assert.deepEqual(core.relatedBidConflict(error), { match: 'exact', companies: ['乙公司'], message: '集团内另一家公司已对同一标段立项。依据……', statute: '依据……' });
  assert.equal(core.relatedBidConflict(new ApiError(409, 'VERSION_CONFLICT', 'x')), null);
  assert.equal(core.relatedBidConflict(new Error('x')), null);
  assert.deepEqual(core.relatedBidConflict(new ApiError(409, 'RELATED_BID_CONFLICT', '原文提示')).companies, []);
});

test('2. 说明至少 5 个字；匹配方式文字', () => {
  assert.ok(core.reasonProblem('无'));
  assert.ok(core.reasonProblem('    '));
  assert.equal(core.reasonProblem('与乙公司无控股关系'), null);
  assert.equal(core.matchLabel('exact'), '同一招标编号与标段');
  assert.equal(core.matchLabel('approximate'), '可能是同一项目');
  assert.equal(core.relatedBidPath('p 1', '/ack'), '/api/v1/projects/p%201/related-bids/ack');
});

test('3. 新建项目与项目设置都接上确认，取消不保存', () => {
  const app = read('../../src/app/App.tsx');
  assert.match(app, /relatedBidConflict\(error\); const reason = conflict \? await askRelatedBidReason\(modal, conflict\) : null; if \(!reason\) throw error;/);
  assert.match(app, /related_bid_reason: reason/);
  const settings = read('../../src/project/ProjectSettingsPage.tsx');
  assert.match(settings, /const reason = await askRelatedBidReason\(modal, conflict\); if \(!reason\) return;/);
  assert.match(settings, /<RelatedBidBanner /);
  assert.ok(!settings.includes('当前使用合成演示账号验证多人编标'), '去掉过时的演示账号说明');
  const prompt = read('../../src/project/RelatedBidPrompt.tsx');
  assert.ok(prompt.includes("okText: '确认无上述关系并继续'") && prompt.includes("cancelText: '取消'"));
});
