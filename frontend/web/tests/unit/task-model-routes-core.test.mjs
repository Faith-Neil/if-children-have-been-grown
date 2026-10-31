// 为什么有这个文件：验证任务与模型对应表的下拉过滤（PRD v1.8 §6.4；APP-M2-T040，验收要求备用下拉过滤规则表格驱动）。
// 它解决什么问题：示例模型不出现；只能本地的任务云端不可选；首选本地时备用云端不可选；备用不含首选本身。
import test from 'node:test';
import assert from 'node:assert/strict';
import { routeFallbackOptions, routePrimaryOptions } from '../../src/admin/task-model-routes-core.ts';

const cfg = (id, is_local, provider = 'openai-compatible') => ({ id, name: id, model: id, is_local, provider });
const configs = [cfg('local-a', true), cfg('local-b', true), cfg('cloud-c', false), cfg('demo', true, 'demo')];
const row = (primary, local_only = false) => ({ task: 't', name: 't', local_only, primary_config_id: primary, fallback_config_id: null });

const cases = [
  ['primary options hide demo', routePrimaryOptions(configs, row(null)).map(o => o.value), ['local-a', 'local-b', 'cloud-c']],
  ['local-only primary disables cloud', routePrimaryOptions(configs, row(null, true)).filter(o => o.disabled).map(o => o.value), ['cloud-c']],
  ['fallback excludes primary', routeFallbackOptions(configs, row('local-a')).map(o => o.value), ['local-b', 'cloud-c']],
  ['local primary disables cloud fallback', routeFallbackOptions(configs, row('local-a')).filter(o => o.disabled).map(o => o.value), ['cloud-c']],
  ['cloud primary allows any fallback', routeFallbackOptions(configs, row('cloud-c')).filter(o => o.disabled).map(o => o.value), []],
];
for (const [name, actual, expected] of cases) test(name, () => assert.deepEqual(actual, expected));
