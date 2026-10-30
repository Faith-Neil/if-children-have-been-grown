// 为什么有这个文件：验证公司 Word 模板与附件扫描件的页面规则（PRD v1.8 §5.6.2、§5.9.1 规则 1、7；APP-M2-T086、T059、T198）。
// 它解决什么问题：模板只收 .docx 且不超过 20MB；没有公司模板时导出默认平台模板且公司模板项不可选；
// 导出请求带上模板、是否插附件与水印文字；附件只收 PDF/PNG/JPG、页码范围校验、功能点标签去重。
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  defaultTemplateChoice, exportRequestBody, templateOptions, templateSourceLabel, templateUploadProblem, wordTemplatePaths,
} from '../../src/admin/word-template-core.ts';
import { attachmentPaths, normalizeTags, pageRangeLabel, pageRangeProblem, uploadProblem } from '../../src/library/attachments-core.ts';

const template = { id: 't', filename: '公司模板.docx', sha256: 'x', size_bytes: 1, uploaded_by: 'u', uploaded_at: '', applied: [], defaults: [] };

test('template upload accepts only docx up to 20MB', () => {
  assert.equal(templateUploadProblem({ name: 'a.docx', size: 1000 }), null);
  assert.match(templateUploadProblem({ name: 'a.doc', size: 1000 }), /只接受 \.docx/);
  assert.match(templateUploadProblem({ name: 'a.DOCX', size: 21 * 1024 * 1024 }), /20MB/);
  assert.equal(wordTemplatePaths.upload('alpha', '模 板.docx'), '/api/v1/companies/alpha/word-template?filename=%E6%A8%A1+%E6%9D%BF.docx');
});

test('export template options follow whether the company uploaded one', () => {
  assert.equal(defaultTemplateChoice(null), 'platform');
  assert.equal(defaultTemplateChoice(template), 'company');
  assert.deepEqual(templateOptions(null)[0], { value: 'company', label: '本公司 Word 模板（尚未上传）', disabled: true });
  assert.equal(templateOptions(template)[0].label, '本公司 Word 模板（公司模板.docx）');
  assert.equal(templateSourceLabel({ source: 'company', filename: '公司模板.docx' }), '公司模板 公司模板.docx');
  assert.equal(templateSourceLabel({ source: 'platform', filename: null }), '平台默认');
  assert.equal(templateSourceLabel(undefined), '—');
});

test('export request carries template, attachment switch and trimmed watermark', () => {
  assert.deepEqual(exportRequestBody('c', 'internal', 'all', { template: 'company', insertAttachments: true, watermark: '  仅用于甲项目投标 ' }),
    { check_id: 'c', kind: 'internal', volume: 'all', template: 'company', insert_attachments: true, attachment_watermark: '仅用于甲项目投标' });
  assert.equal('attachment_watermark' in exportRequestBody('c', 'internal', 'all', { template: 'platform', insertAttachments: false, watermark: ' ' }), false);
});

test('attachment upload, page range and tags are checked before calling the server', () => {
  assert.equal(uploadProblem({ name: '执照.PDF', size: 10 }, 100), null);
  assert.match(uploadProblem({ name: '执照.tiff', size: 10 }, 100), /只支持/);
  assert.match(uploadProblem({ name: '执照.pdf', size: 0 }, 100), /为空/);
  assert.equal(pageRangeProblem(2, 3, 3), null);
  assert.match(pageRangeProblem(2, 4, 3), /第 1～3 页/);
  assert.match(pageRangeProblem(3, 2, 3), /不能大于/);
  assert.match(pageRangeProblem(null, 2, 3), /整数/);
  assert.deepEqual(normalizeTags(['Java，监控', ' Java ', '', '日志;告警']), ['Java', '监控', '日志', '告警']);
  assert.equal(pageRangeLabel({ page_from: 1, page_to: 3, page_count: 3 }), '全部 3 页');
  assert.equal(pageRangeLabel({ page_from: 2, page_to: 3, page_count: 5 }), '第 2～3 页（共 5 页）');
  assert.equal(attachmentPaths.upload('ev 1', '执照.pdf'), '/api/v1/library/ev%201/attachments/raw?filename=%E6%89%A7%E7%85%A7.pdf');
});
