// 为什么有这个文件：覆盖大模型弹窗配置（ModelConfigModal）与核心合规校验单测。
// 它解决什么问题：
// 1. 验证大模型参数合法性校验（URL、超时、Max Tokens）；
// 2. 验证 PRD §6.4 涉密与敏感项目本地化模型约束（is_local 与 allow_sensitive 双门禁）；
// 3. 验证密钥更新四项语义（省略/空字符串清除/掩码保持/新密钥加密）。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  validateModelConfig,
  isModelAllowedForSensitiveProject,
  buildModelUpdatePayload,
} from '../../src/admin/model-config-core.ts';

test('validateModelConfig: 正常参数校验通过', () => {
  const result = validateModelConfig({
    name: '默认本地模型',
    base_url: 'http://127.0.0.1:8000',
    model: 'qwen2.5-72b',
    timeout_seconds: 60,
    max_tokens: 2048,
  });

  assert.equal(result.valid, true);
  assert.equal(Object.keys(result.errors).length, 0);
});

test('validateModelConfig: 异常参数与协议拦截', () => {
  const emptyName = validateModelConfig({
    name: '',
    base_url: 'http://127.0.0.1:8000',
    model: 'qwen2.5-72b',
  });
  assert.equal(emptyName.valid, false);
  assert.equal(emptyName.errors.name, '配置名称不能为空');

  const invalidUrl = validateModelConfig({
    name: '模型',
    base_url: 'ftp://127.0.0.1:8000',
    model: 'qwen2.5-72b',
  });
  assert.equal(invalidUrl.valid, false);
  assert.equal(invalidUrl.errors.base_url, '服务地址协议必须为 http 或 https');

  const invalidTimeout = validateModelConfig({
    name: '模型',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o',
    timeout_seconds: 0,
    max_tokens: 1024,
  });
  assert.equal(invalidTimeout.valid, false);
  assert.ok(invalidTimeout.errors.timeout_seconds);
});

test('isModelAllowedForSensitiveProject: 涉密项目本地模型双门禁 (PRD §6.4)', () => {
  // 本地且允许涉密 -> 通过
  assert.equal(
    isModelAllowedForSensitiveProject({ is_local: true, allow_sensitive: true }),
    true
  );

  // 云端模型即便标记 allow_sensitive 也严禁用于涉密项目
  assert.equal(
    isModelAllowedForSensitiveProject({ is_local: false, allow_sensitive: true }),
    false
  );

  // 本地模型但未标记 allow_sensitive 也不放行
  assert.equal(
    isModelAllowedForSensitiveProject({ is_local: true, allow_sensitive: false }),
    false
  );
});

test('buildModelUpdatePayload: 密钥更新四项语义', () => {
  const current = {
    id: 'cfg-1',
    name: '原配置',
    provider: 'openai-compatible',
    base_url: 'http://127.0.0.1:8000',
    model: 'qwen2.5-72b',
    is_local: true,
    allow_sensitive: true,
    stream_enabled: true,
    json_mode_enabled: false,
    revision: 2,
    has_api_key: true,
    api_key_masked: 'sk-***cdef',
    timeout_seconds: 60,
    max_tokens: 1024,
  };

  // 1. 传回掩码：保留原有掩码字符串
  const keepMaskPayload = buildModelUpdatePayload(
    { ...current, api_key: 'sk-***cdef' },
    current
  );
  assert.equal(keepMaskPayload.api_key, 'sk-***cdef');

  // 2. 传空字符串：代表清除密钥
  const clearPayload = buildModelUpdatePayload(
    { ...current, api_key: '' },
    current
  );
  assert.equal(clearPayload.api_key, '');

  // 3. 传入新明文：传给后端加密
  const newKeyPayload = buildModelUpdatePayload(
    { ...current, api_key: 'sk-new-super-secret-key' },
    current
  );
  assert.equal(newKeyPayload.api_key, 'sk-new-super-secret-key');
});
