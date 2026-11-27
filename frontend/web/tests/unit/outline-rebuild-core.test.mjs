// 为什么有这个测试：目录模型编排失败上浮与「重新生成目录」是 ISSUE-060/TV-M0-T32 的前端验收第 2 条。
// 它解决什么问题：
// 1. 失败可见——rule_fallback/tree_model_failed 必须判为失败态且原因可读出，模型目录不误判；
// 2. 按钮触发——重跑编排调用与后端 rebuild-model 契约一致的实际端点，顺序是先重跑后刷新；
// 3. 成功后刷新/状态变化——HTTP 200 仍可能失败，只有 ok 且无失败标记才算恢复，失败原因驻留不丢。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  OUTLINE_MODEL_FAILED_GENERIC,
  canRebuildOutlineModel,
  outlineFailureState,
  rebuildOutcome,
  rebuildOutlineModelPath,
  runOutlineRebuild,
} from '../../src/project/outline-rebuild-core.ts';

/* ---------- 1. 失败可见 ---------- */

test('rule_fallback 顶层来源判为失败态，原因直接可读', () => {
  const state = outlineFailureState({
    outline_source: 'rule_fallback',
    tree_model_failed: true,
    outline_reason: '模型拟目录失败（超时），已用规则目录。',
  });
  assert.equal(state.failed, true);
  assert.equal(state.source, 'rule_fallback');
  assert.equal(state.reason, '模型拟目录失败（超时），已用规则目录。');
});

test('technical_outline 内嵌失败标记同样判失败（顶层缺失时）', () => {
  const state = outlineFailureState({
    technical_outline: {
      outline_source: 'rule_fallback',
      tree_model_failed: true,
      outline_reason: '模型拟目录失败，已用规则目录。',
    },
  });
  assert.equal(state.failed, true);
  assert.equal(state.reason, '模型拟目录失败，已用规则目录。');
});

test('tree_model_failed 为真时即使来源字段缺失也判失败', () => {
  const state = outlineFailureState({ tree_model_failed: true });
  assert.equal(state.failed, true);
  assert.equal(state.reason, OUTLINE_MODEL_FAILED_GENERIC);
});

test('模型编排成功目录不判失败，不显示重跑入口', () => {
  const state = outlineFailureState({ outline_source: 'model', tree_model_failed: false });
  assert.equal(state.failed, false);
  assert.equal(state.reason, '');
});

test('「模型正在编排目录」过渡态不算失败，不给重跑按钮', () => {
  const state = outlineFailureState({
    outline_source: 'rule',
    technical_outline: { outline_source: 'rule', outline_reason: '模型正在编排目录，当前是规则草稿。' },
  });
  assert.equal(state.failed, false);
});

test('未调用模型的规则目录（无失败标记）不算编排失败', () => {
  const state = outlineFailureState({
    outline_source: 'rule',
    outline_reason: '未调用模型编排目录（没有可用的本地写作模型），目录按规则编排。',
  });
  assert.equal(state.failed, false);
});

test('失败但后端原因为空时给出明确兜底原因，绝不空白', () => {
  const state = outlineFailureState({ outline_source: 'rule_fallback', tree_model_failed: true, outline_reason: '' });
  assert.equal(state.failed, true);
  assert.equal(state.reason, OUTLINE_MODEL_FAILED_GENERIC);
});

/* ---------- 2. 重跑权限与后端一致 ---------- */

test('平台管理员可以重跑任意公司项目的模型目录', () => {
  assert.equal(canRebuildOutlineModel({ role: 'platform_admin', company_id: 'c-other' }, 'c-1'), true);
});

test('本公司管理员可以重跑，外公司管理员与成员不行', () => {
  assert.equal(canRebuildOutlineModel({ role: 'company_admin', company_id: 'c-1' }, 'c-1'), true);
  assert.equal(canRebuildOutlineModel({ role: 'company_admin', company_id: 'c-2' }, 'c-1'), false);
  assert.equal(canRebuildOutlineModel({ role: 'member', company_id: 'c-1' }, 'c-1'), false);
});

test('历史别名角色归一后为成员，不能重跑；空用户不行', () => {
  assert.equal(canRebuildOutlineModel({ role: 'manager', company_id: 'c-1' }, 'c-1'), false);
  assert.equal(canRebuildOutlineModel(null, 'c-1'), false);
  assert.equal(canRebuildOutlineModel(undefined, 'c-1'), false);
});

/* ---------- 3. 端点契约 ---------- */

test('重跑端点与后端 rebuild-model 契约路由一致', () => {
  assert.equal(rebuildOutlineModelPath('project-abc'), '/api/v1/projects/project-abc/technical-outline/rebuild-model');
});

/* ---------- 4. 响应解读：200 也可能是失败 ---------- */

test('ok 且无失败标记判成功恢复', () => {
  const outcome = rebuildOutcome({ ok: true, tree_model_failed: false, outline_source: 'model', headings: 11 });
  assert.equal(outcome.kind, 'success');
});

test('200 但 tree_model_failed 仍为真时判失败并保留后端原因', () => {
  const outcome = rebuildOutcome({
    ok: false,
    tree_model_failed: true,
    outline_source: 'rule_fallback',
    outline_reason: '模型拟目录失败（超时），已用规则目录。',
  });
  assert.equal(outcome.kind, 'still-failed');
  assert.equal(outcome.message, '模型拟目录失败（超时），已用规则目录。');
});

test('ok 为真但失败标记仍在时绝不假装成功', () => {
  const outcome = rebuildOutcome({ ok: true, tree_model_failed: true, outline_reason: '模型拟目录失败，已用规则目录。' });
  assert.equal(outcome.kind, 'still-failed');
});

test('失败且原因为空时仍给出明确说明', () => {
  const outcome = rebuildOutcome({ ok: false, tree_model_failed: true });
  assert.equal(outcome.kind, 'still-failed');
  assert.ok(outcome.message.length > 0);
});

/* ---------- 5. 按钮触发与成功后刷新/状态变化（行为级编排） ---------- */

test('点击重跑：先调契约端点，成功后刷新工作台', async () => {
  const calls = [];
  const outcome = await runOutlineRebuild('project-abc', {
    post: async path => {
      calls.push(`post:${path}`);
      return { ok: true, tree_model_failed: false, outline_source: 'model', headings: 9 };
    },
    reload: async () => { calls.push('reload'); },
  });
  assert.equal(outcome.kind, 'success');
  assert.equal(outcome.reloaded, true);
  assert.deepEqual(calls, ['post:/api/v1/projects/project-abc/technical-outline/rebuild-model', 'reload']);
});

test('重跑后仍是规则兜底：错误原因保留且工作台照样刷新（服务端已重写失败状态）', async () => {
  const calls = [];
  const outcome = await runOutlineRebuild('project-abc', {
    post: async () => {
      calls.push('post');
      return { ok: false, tree_model_failed: true, outline_source: 'rule_fallback', outline_reason: '模型拟目录失败（超时），已用规则目录。' };
    },
    reload: async () => { calls.push('reload'); },
  });
  assert.equal(outcome.kind, 'still-failed');
  assert.equal(outcome.message, '模型拟目录失败（超时），已用规则目录。');
  assert.equal(outcome.reloaded, true);
  assert.deepEqual(calls, ['post', 'reload']);
});

test('HTTP 错误（模型不可用 409）：错误上浮、不刷新工作台、原始错误保留给上报', async () => {
  const error = new Error('真实本地模型不可用，不能重跑模型目录。');
  error.status = 409;
  error.code = 'TECHNICAL_OUTLINE_MODEL_UNAVAILABLE';
  let reloads = 0;
  const outcome = await runOutlineRebuild('project-abc', {
    post: async () => { throw error; },
    reload: async () => { reloads += 1; },
    errorMessage: err => err.message,
  });
  assert.equal(outcome.kind, 'error');
  assert.equal(outcome.message, '真实本地模型不可用，不能重跑模型目录。');
  assert.equal(outcome.reloaded, false);
  assert.equal(outcome.error, error);
  assert.equal(reloads, 0);
});

test('HTTP 错误缺少消息时给出明确兜底提示', async () => {
  const outcome = await runOutlineRebuild('project-abc', {
    post: async () => { throw new TypeError('fetch failed'); },
    reload: async () => undefined,
  });
  assert.equal(outcome.kind, 'error');
  assert.ok(outcome.message.length > 0);
});

test('重跑成功但刷新失败：如实标记未刷新，不假装页面已是最新', async () => {
  const outcome = await runOutlineRebuild('project-abc', {
    post: async () => ({ ok: true, tree_model_failed: false, outline_source: 'model' }),
    reload: async () => { throw new Error('network down'); },
  });
  assert.equal(outcome.kind, 'success');
  assert.equal(outcome.reloaded, false);
});

test('刷新失败不影响失败态如实反馈', async () => {
  const outcome = await runOutlineRebuild('project-abc', {
    post: async () => ({ ok: false, tree_model_failed: true, outline_reason: '模型拟目录失败，已用规则目录。' }),
    reload: async () => { throw new Error('network down'); },
  });
  assert.equal(outcome.kind, 'still-failed');
  assert.equal(outcome.reloaded, false);
});

/* ---------- 6. 编辑台接线静态契约（防回退） ---------- */

function sourceOf(relativePath) {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8');
}

test('编辑台渲染失败告警并把目录失败原因从 parse-honesty 中排除', () => {
  const editor = sourceOf('../../src/editor/EditorPage.tsx');
  assert.ok(editor.includes('OutlineRebuildNotice'), '编辑台必须渲染 OutlineRebuildNotice');
  assert.ok(editor.includes('outlineFailureState'), '编辑台必须判定目录失败态');
  assert.ok(editor.includes('includeOutline: !outlineFailure.failed'), '失败原因不得与 parse-honesty 重复');
});

test('告警组件声明失败可见与重跑按钮契约', () => {
  const notice = sourceOf('../../src/project/OutlineRebuildNotice.tsx');
  assert.ok(notice.includes('data-testid="outline-model-failed"'), '失败告警 testid 必须存在');
  assert.ok(notice.includes('data-testid="outline-rebuild-button"'), '重跑按钮 testid 必须存在');
  assert.ok(notice.includes('重新生成目录'), '按钮文案必须是「重新生成目录」');
  assert.ok(notice.includes('type="error"'), '失败必须以错误级告警显示');
});
