// 为什么有这个文件：验证用户填写项目截止时间后的实际接口值。
// 它解决什么问题：防止空日期创建失败、北京时间偏移或无效日期进入后台。
import test from 'node:test';
import assert from 'node:assert/strict';
import { deadlineForApi, deadlineForForm, projectBasis, projectFields } from '../../frontend/web/src/project-form.ts';

test('blank fields use the documented clearing value, not null', () => {
  assert.deepEqual(projectFields({ name: '测试项目', sensitive: false }), { name: '测试项目', tender_number: '', deadline: '', sensitive: false });
});
test('Shanghai input and UTC API values round trip including next-day boundaries', () => {
  assert.equal(deadlineForApi('2026-12-31 17:00'), '2026-12-31T09:00:00.000Z');
  assert.equal(deadlineForForm('2026-12-31T09:00:00.000Z'), '2026-12-31 17:00');
  assert.equal(deadlineForForm('2026-12-31T23:30:00Z'), '2027-01-01 07:30');
  assert.equal(deadlineForApi('2027-01-01 07:30'), '2026-12-31T23:30:00.000Z');
});
test('invalid dates and ambiguous input are rejected before project creation', () => {
  for (const value of ['2026-02-30 17:00', '2026-13-01 17:00', '2026-12-31 25:00', '2026/12/31', '明天']) assert.throws(() => deadlineForApi(value));
});

test('fresh versions after an unrelated save cannot silently bless stale project fields', () => {
  const original = { name: '项目甲', tender_number: 'A', deadline: '2026-12-31T09:00:00Z', sensitive: false };
  assert.equal(projectBasis({ ...original, revision: 99 }), projectBasis(original));
  for (const change of [{ name: '项目乙' }, { tender_number: 'B' }, { deadline: '' }, { sensitive: true }]) assert.notEqual(projectBasis({ ...original, ...change }), projectBasis(original));
});
