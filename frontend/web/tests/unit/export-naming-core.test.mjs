// 为什么有这个文件：验证导出命名的页面核对与预览（PRD v1.8 §5.1.4 第 9 项、§5.9.1 验收⑤；APP-M2-T086）。
// 它解决什么问题：递交版含 {编写人}、不认识的变量、空规则在页面就提示；预览按示例值替换变量并去掉非法字符。
import test from 'node:test';
import assert from 'node:assert/strict';
import { exportSettingsPath, namingProblems, previewName } from '../../src/project/export-naming-core.ts';

const variables = ['编写人', '版本', '日期', '项目名称', '分册名称', '招标编号'].map(name => ({ name, description: '' }));

test('naming problems', () => {
  assert.deepEqual(namingProblems('{项目名称}_{分册名称}', 'submission', variables), []);
  assert.deepEqual(namingProblems('{编写人}_{项目名称}', 'submission', variables), ['递交版命名不能含 {编写人}']);
  assert.deepEqual(namingProblems('{编写人}_{项目名称}', 'internal', variables), []);
  assert.deepEqual(namingProblems('{作者}', 'internal', variables), ['不认识的变量：{作者}']);
  assert.deepEqual(namingProblems('  ', 'internal', variables), ['命名规则不能为空']);
});

test('preview replaces variables and illegal characters', () => {
  assert.equal(previewName('{编写人}_{版本}_{日期}_{项目名称}', { 编写人: '张三', 版本: 'V1.0', 日期: '20260115', 项目名称: 'A/B项目' }), '张三_V1.0_20260115_A_B项目.docx');
  assert.equal(previewName('{未知}', {}), '投标文件.docx');
  assert.equal(exportSettingsPath('p 1'), '/api/v1/projects/p%201/export-settings');
});
