// 为什么有这个文件：项目设置里的目录模型选项必须让人看见主机，避免把 local-b.local 当成可用模型。
// 它解决什么问题：选项文案带上 name、model 和主机；保存只改 technical_structure，其它任务原样带上。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { structureBoundLabel, structureEffectiveLabel, structureModelOptions, structureRouteBody } from '../../src/project/structure-model-route.ts';

test('目录模型选项带上主机，保存只改目录任务', () => {
  const options = structureModelOptions([
    { id: 'local-b', name: 'local-b', model: 'local-b', provider: 'openai', is_local: true, base_url: 'http://local-b.local/v1/chat/completions' },
    { id: 'cloud', name: '云端', model: 'qwen-cloud', provider: 'openai', is_local: false, base_url: 'https://api.example.com/v1' },
    { id: 'demo', name: '演示', model: 'demo', provider: 'demo', is_local: true, base_url: 'http://demo.local/v1' },
    { id: 'nine', name: '目录九号', model: 'qwen3.5:9b', provider: 'openai', is_local: true, base_url: 'http://192.168.0.246:11434/v1' },
  ]);
  assert.deepEqual(options.map(item => item.value), ['local-b', 'nine']);
  assert.match(options[0].label, /local-b/);
  assert.match(options[0].label, /local-b\.local/);
  assert.match(options[1].label, /qwen3\.5:9b/);
  assert.match(options[1].label, /192\.168\.0\.246/);

  const body = structureRouteBody({
    revision: 3,
    tasks: [
      { task: 'chapter_generation', primary_config_id: 'nine', fallback_config_id: null },
      { task: 'technical_structure', primary_config_id: 'local-b', fallback_config_id: 'spare' },
      { task: 'assistant_qa', primary_config_id: null, fallback_config_id: null },
    ],
  }, 'nine');
  assert.equal(body.revision, 3);
  assert.deepEqual(body.routes, [
    { task: 'chapter_generation', primary_config_id: 'nine', fallback_config_id: null },
    { task: 'technical_structure', primary_config_id: 'nine', fallback_config_id: 'spare' },
    { task: 'assistant_qa', primary_config_id: null, fallback_config_id: null },
  ]);
});

test('structureBoundLabel prefers server primary_model', () => {
  const label = structureBoundLabel({
    revision: 1,
    tasks: [{
      task: 'technical_structure',
      primary_config_id: 'cfg-9b',
      fallback_config_id: null,
      primary_name: '目录九号',
      primary_model: 'qwen3.5:9b',
    }],
  }, [{ id: 'cfg-9b', name: '目录九号', model: 'should-not-win', provider: 'openai', is_local: true, base_url: 'http://x' }]);
  assert.equal(label, '目录九号 · qwen3.5:9b');
});

test('structureEffectiveLabel shows the saved model or a stale id', () => {
  const base = { task: 'technical_structure', fallback_config_id: null };
  assert.equal(structureEffectiveLabel({ ...base, primary_config_id: 'cfg-9b', primary_model: 'qwen3.5:9b' }), 'qwen3.5:9b');
  assert.equal(structureEffectiveLabel({ ...base, primary_config_id: null }), '未指定');
  assert.equal(structureEffectiveLabel({ ...base, primary_config_id: 'cfg-gone', primary_missing: true }), '配置失效');
  assert.equal(structureEffectiveLabel(undefined), '未指定');
});
