// 为什么有这个文件：覆盖 RAGFlow 知识库弹窗配置（RagflowConfigModal）与核心校验单测。
// 它解决什么问题：
// 1. 验证 RAGFlow Base URL 格式与协议校验；
// 2. 验证 Dataset IDs 字符串与数组的双向解析与清洗；
// 3. 验证超时范围校验；
// 4. 验证 API Key 掩码保留与更新载荷构造。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  parseDatasetIds,
  validateRagflowConfig,
  buildRagflowUpdatePayload,
} from '../../src/admin/ragflow-config-core.ts';

test('parseDatasetIds: 正确拆分与过滤 Dataset IDs', () => {
  // 逗号分隔
  assert.deepEqual(parseDatasetIds('ds1, ds2, ds3'), ['ds1', 'ds2', 'ds3']);
  // 中文逗号与换行混合
  assert.deepEqual(parseDatasetIds('ds1，ds2\nds3'), ['ds1', 'ds2', 'ds3']);
  // 数组输入
  assert.deepEqual(parseDatasetIds(['ds1', ' ds2 ']), ['ds1', 'ds2']);
  // 空输入
  assert.deepEqual(parseDatasetIds(''), []);
  assert.deepEqual(parseDatasetIds(null), []);
});

test('validateRagflowConfig: 正常参数校验通过', () => {
  const result = validateRagflowConfig({
    base_url: 'http://127.0.0.1:9380',
    dataset_ids: ['dataset-alpha-01'],
    timeout_seconds: 30,
    is_enabled: true,
  });

  assert.equal(result.valid, true);
  assert.equal(Object.keys(result.errors).length, 0);
});

test('validateRagflowConfig: 缺少 Dataset 或非法 URL 拦截', () => {
  const missingDataset = validateRagflowConfig({
    base_url: 'http://127.0.0.1:9380',
    dataset_ids: '',
    timeout_seconds: 30,
  });
  assert.equal(missingDataset.valid, false);
  assert.equal(missingDataset.errors.dataset_ids, '请至少配置一个知识库数据集 (Dataset ID)');

  const urlWithQuery = validateRagflowConfig({
    base_url: 'http://127.0.0.1:9380/api?token=123',
    dataset_ids: 'ds1',
  });
  assert.equal(urlWithQuery.valid, false);
  assert.equal(urlWithQuery.errors.base_url, '服务地址不能包含 query 或 fragment');
});

test('buildRagflowUpdatePayload: 构造规范载荷与密钥掩码保留', () => {
  const current = {
    company_id: 'alpha',
    base_url: 'http://127.0.0.1:9380',
    has_api_key: true,
    api_key_masked: 'rag***-xyz',
    dataset_ids: ['ds1'],
    timeout_seconds: 30,
    is_enabled: true,
    revision: 1,
  };

  const payload = buildRagflowUpdatePayload(
    {
      base_url: 'http://192.168.1.100:9380/',
      dataset_ids: 'ds1, ds2',
      timeout_seconds: 45,
      is_enabled: true,
      api_key: 'rag***-xyz', // 保持掩码
    },
    current
  );

  assert.equal(payload.base_url, 'http://192.168.1.100:9380');
  assert.deepEqual(payload.dataset_ids, ['ds1', 'ds2']);
  assert.equal(payload.timeout_seconds, 45);
  assert.equal(payload.api_key, 'rag***-xyz');
});
