// 为什么有这个文件：验证拟派人员表格的整理规则（PRD v1.8 §5.1.4 第 4 项、R33；APP-M2-T241）。
// 它解决什么问题：空行不保存、同一人同一角色不重复；人员资料缺学历、专业、参加工作时间或证书时逐项提示；R33 问题按阻断、警告、提示排序。
import test from 'node:test';
import assert from 'node:assert/strict';
import { profileGaps, sortedIssues, staffPath, staffPayload } from '../../src/project/proposed-staff-core.ts';

test('staff payload drops blank rows and refuses duplicates', () => {
  assert.deepEqual(staffPayload([{ person_id: 'p1', role: ' 项目经理 ', position: 'A', is_key_person: true }, { person_id: '', role: '' }]),
    { staff: [{ person_id: 'p1', role: '项目经理', position: 'A', is_key_person: true }] });
  assert.throws(() => staffPayload([{ person_id: 'p1', role: '项目经理' }, { person_id: 'p1', role: '项目经理' }]), /重复/);
  assert.equal(staffPath('p 1'), '/api/v1/projects/p%201/proposed-staff');
});

test('profile gaps and issue order', () => {
  assert.deepEqual(profileGaps({ degree: null, major: '计算机', work_start: null, years: null, certificates: null }), ['学历', '参加工作时间', '证书']);
  assert.deepEqual(profileGaps({ degree: '本科', major: '计算机', work_start: null, years: 5, certificates: [] }), []);
  assert.deepEqual(profileGaps(null), ['人员资料已删除']);
  const issues = [{ id: '1', code: 'a', severity: 'info', message: '' }, { id: '2', code: 'b', severity: 'blocker', message: '' }, { id: '3', code: 'c', severity: 'warning', message: '' }];
  assert.deepEqual(sortedIssues(issues).map(i => i.id), ['2', '3', '1']);
});
