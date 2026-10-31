// 为什么有这个文件：验证项目状态按钮、人工修改标记、合作方协议、规则覆盖、分册格式、完整值类别与待办合并的纯函数（APP-M2-T097～T100）。
// 它解决什么问题：页面保存前的核对口径与后台一致，倒计时按“≤3 天标红”，不同状态只给出合法的状态变更。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  availableStatusActions, statusRequest, manualEditNote, partnerNeedsAgreement, partnersPayload, ruleOverridesPayload,
  volumeSettingsPayload, fullValuePayload, canConfirmFullValue, mergeTodoItems,
} from '../../src/project/project-settings-core.ts';
import { calculateProjectCountdown, filterProjectTabs, PROJECT_HEADER_TABS, tabAllowedByPermissions } from '../../src/project/project-header-core.ts';

test('倒计时：不超过 3 天（含恰好 3 天）标红，超过 3 天为蓝色', () => {
  const now = new Date('2026-10-22T12:00:00Z').getTime();
  const at = (ms) => new Date(now + ms).toISOString();
  const day = 24 * 3600 * 1000;
  assert.equal(calculateProjectCountdown(at(3 * day), now).color, 'red');
  assert.equal(calculateProjectCountdown(at(3 * day), now).isUrgent, true);
  assert.equal(calculateProjectCountdown(at(2 * day + 5 * 3600 * 1000), now).color, 'red');
  assert.equal(calculateProjectCountdown(at(3 * day + 60 * 1000), now).color, 'blue');
  assert.equal(calculateProjectCountdown(at(3 * day + 60 * 1000), now).isUrgent, false);
  assert.equal(calculateProjectCountdown(at(-1000), now).color, 'red');
});

test('页签按权限：没有导出权限不显示导出页签，没有权限数据时不收紧', () => {
  const tabs = [...PROJECT_HEADER_TABS];
  const none = { manage_project: false, export_internal: false, export_volumes: [] };
  assert.equal(filterProjectTabs(tabs, null, 'p1', 'project_lead', { ...none, manage_project: true }).some(t => t.key === 'export'), false);
  assert.equal(filterProjectTabs(tabs, null, 'p1', 'project_lead', { manage_project: true, export_internal: true, export_volumes: ['technical'] }).some(t => t.key === 'export'), true);
  assert.equal(filterProjectTabs(tabs, null, 'p1', 'project_lead', { manage_project: true, export_internal: false, export_volumes: ['business'] }).some(t => t.key === 'export'), true);
  assert.equal(tabAllowedByPermissions('export', undefined), true);
  assert.equal(tabAllowedByPermissions('checks', none), true);
  assert.equal(filterProjectTabs(tabs, null, 'p1', 'viewer', none).some(t => t.key === 'checks'), true);
});

test('状态按钮：只给出当前状态下合法的变更，取消和结果有必填项', () => {
  assert.deepEqual(availableStatusActions('compiling'), ['cancel']);
  assert.deepEqual(availableStatusActions('exported'), ['submit']);
  assert.deepEqual(availableStatusActions('submitted'), ['open']);
  assert.deepEqual(availableStatusActions('opened'), ['result']);
  assert.deepEqual(availableStatusActions('cancelled'), []);
  assert.deepEqual(availableStatusActions('ended'), []);
  assert.throws(() => statusRequest('cancel', ' '), /原因/);
  assert.throws(() => statusRequest('result', '', undefined), /结果/);
  assert.deepEqual(statusRequest('result', '', 'won'), { action: 'result', reason: '', result: 'won' });
  assert.deepEqual(statusRequest('cancel', ' 放弃投标 '), { action: 'cancel', reason: '放弃投标' });
});

test('人工修改标记与合作方缺协议', () => {
  const edits = { tenderee_name: { by: 'u1', at: '2026-10-30T08:15:00+00:00' } };
  assert.match(manualEditNote(edits, 'tenderee_name', () => '张三'), /已人工修改（张三，2026-10-30 08:15）/);
  assert.equal(manualEditNote(edits, 'agency_name', () => '张三'), null);
  const partners = [{ partner_entity_id: 'a', agreement_ok: true }, { partner_entity_id: 'b', agreement_ok: false, problem: '缺协议' }];
  assert.deepEqual(partnerNeedsAgreement(partners).map(p => p.partner_entity_id), ['b']);
  assert.deepEqual(partnersPayload([{ partner_entity_id: ' a ', agreement_attachment_id: ' ' }, { partner_entity_id: '' }]),
    [{ partner_entity_id: 'a', agreement_attachment_id: null }]);
  assert.throws(() => partnersPayload([{ partner_entity_id: 'a' }, { partner_entity_id: 'a' }]), /重复/);
});

test('规则覆盖：取值范围、规则名与重复', () => {
  const ok = ruleOverridesPayload([{ rule_key: 'proof_valid_days.纳税证明', value: 90, source_requirement_id: 'r1' }, { rule_key: 'check_service_period', value: true }]);
  assert.equal(ok.overrides.length, 2);
  assert.equal(ok.overrides[0].source_requirement_id, 'r1');
  for (const bad of [{ rule_key: 'proof_valid_days.', value: 30 }, { rule_key: 'proof_valid_days.资质', value: 0 }, { rule_key: 'social_insurance_months', value: 121 },
    { rule_key: 'check_service_period', value: 1 }, { rule_key: 'other', value: true }]) {
    assert.throws(() => ruleOverridesPayload([bad]));
  }
  assert.throws(() => ruleOverridesPayload([{ rule_key: 'require_own_staff', value: true }, { rule_key: 'require_own_staff', value: false }]), /重复/);
});

test('分册设置：递交文件名不得含编写人变量或姓名，内部截止时间须可解析', () => {
  const row = { volume: 'technical', compile_mode: 'system', separate_seal: false, page_numbering: 'per_volume', blind_bid: true };
  assert.equal(volumeSettingsPayload([{ ...row, submit_file_name: ' 技术标正本 ' }], ['张三']).volumes[0].submit_file_name, '技术标正本');
  assert.throws(() => volumeSettingsPayload([{ ...row, submit_file_name: '{编写人}_技术标' }], []), /编写人/);
  assert.throws(() => volumeSettingsPayload([{ ...row, submit_file_name: '张三技术标' }], ['张三']), /张三/);
  assert.throws(() => volumeSettingsPayload([{ ...row, internal_deadline: '明天' }], []), /格式/);
  assert.equal(volumeSettingsPayload([{ ...row, internal_deadline: '' }], []).volumes[0].internal_deadline, null);
});

test('完整值类别：勾选须有依据，只有项目负责人可勾选；待办合并后仍可跳转', () => {
  assert.throws(() => fullValuePayload(['id_number'], []), /依据/);
  assert.deepEqual(fullValuePayload([], ['r1']), { categories: [], basis_requirement_ids: [] });
  assert.deepEqual(fullValuePayload(['phone'], ['r1']), { categories: ['phone'], basis_requirement_ids: ['r1'] });
  assert.equal(canConfirmFullValue({ manage_project: true }), true);
  assert.equal(canConfirmFullValue({ manage_project: false }), false);
  assert.equal(canConfirmFullValue(undefined), false);
  const merged = mergeTodoItems([{ title: '上传', tab: 'tender', done: true }], [{ code: 'X', title: '合作方缺协议', detail: '缺协议', tab: 'settings' }]);
  assert.equal(merged.length, 2);
  assert.deepEqual([merged[1].tab, merged[1].done], ['settings', false]);
});

test('拟派人员占用提示：只提示，写明对方项目和角色', async () => {
  const { occupancyMessages } = await import('../../src/project/proposed-staff-core.ts');
  assert.deepEqual(occupancyMessages(undefined), []);
  const [text] = occupancyMessages([{ person_id: 'p', person_name: '李工', role: '技术负责人', other_project_id: 'x', other_project_name: '甲项目', other_role: '项目经理' }]);
  assert.match(text, /李工已在“甲项目”拟派为项目经理，本项目拟派为技术负责人/);
});
