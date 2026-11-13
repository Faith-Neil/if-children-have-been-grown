// 为什么有这个文件：核对知识库管理页的角色口径、设置差量提交与数据集提示。
// 它解决什么问题：防止界面放开后端不允许的操作，或保存设置时把别人刚改的字段覆盖回去。

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  KB_KIND_LABEL, KB_UPLOAD_ACCEPT, canUploadHistory, datasetWarnings, embeddingChangeWarning, kbApi, kbPermissions,
  metadataValueLabel, settingsDiff,
} from '../../src/library/kb-admin-core.ts';

const base = { revision: 3, embedding_model: 'a@x', rerank_id: '', llm_id: '', similarity_threshold: 0.2,
  keywords_weight: 0.7, use_pipelines: true, language: 'Chinese', profiles: {} };

test('roles match backend gates', () => {
  assert.deepEqual(kbPermissions('member'), { read: true, write: false, connection: false });
  assert.deepEqual(kbPermissions('data_admin'), { read: true, write: false, connection: false });
  assert.deepEqual(kbPermissions('company_admin'), { read: true, write: true, connection: true });
  assert.deepEqual(kbPermissions('manager'), { read: true, write: false, connection: false });
  assert.deepEqual(kbPermissions('viewer'), { read: true, write: false, connection: false });
  assert.equal(canUploadHistory('manager'), false);
  assert.equal(canUploadHistory('project_lead'), false);
  assert.equal(canUploadHistory('member'), false);
  assert.equal(canUploadHistory('company_admin'), true);
  assert.equal(canUploadHistory('viewer'), false);
});

test('settings diff only sends changed fields and warns on embedding change', () => {
  const diff = settingsDiff(base, { ...base, similarity_threshold: 0.15, embedding_model: 'b@y' });
  assert.deepEqual(diff, { similarity_threshold: 0.15, embedding_model: 'b@y' });
  assert.match(embeddingChangeWarning(base, diff), /重建/);
  assert.equal(embeddingChangeWarning(base, { keywords_weight: 0.5 }), '');
});

test('knowledge page exposes history and materials only', () => {
  assert.deepEqual(Object.keys(KB_KIND_LABEL), ['history', 'materials']);
  assert.equal(KB_KIND_LABEL.history, '历史标书');
  assert.equal(KB_KIND_LABEL.materials, '资料库');
  assert.equal(KB_UPLOAD_ACCEPT.materials, '.pdf,.docx,.doc,.xls,.xlsx,.ppt,.pptx');
  assert.equal(KB_UPLOAD_ACCEPT.history, '.pdf,.docx,.doc');
});

test('metadata value labels use Chinese display names', () => {
  assert.equal(metadataValueLabel('content_role', 'bidder_response'), '投标响应');
  assert.equal(metadataValueLabel('technical_domain', 'data_security'), '数据安全');
  assert.equal(metadataValueLabel('content_role', 'custom_value'), 'custom_value');
});

test('dataset warnings and urls', () => {
  assert.deepEqual(datasetWarnings(null), ['尚未建立']);
  assert.deepEqual(datasetWarnings({ mode: 'pipeline', rebuild_required: true, reparse_required: true }),
    ['嵌入模型已更换，需要重建', '摄入流程已更新，已有文档需重新解析']);
  assert.equal(kbApi.chunk('history', 'd 1', 'c'), '/api/v1/kb-admin/datasets/history/documents/d%201/chunks/c');
});
