// 为什么有这个文件：验收 ISSUE-052 前端纯函数（顶栏公司名、开通表单校验、详情路径）。
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  shouldShowCompanyLabel,
  validateCreateCompanyForm,
  companyDetailPath,
  resolveCompanyDisplayName,
} from '../../src/admin/company-provision-core.ts';

test('platform_admin does not show company label', () => {
  assert.equal(shouldShowCompanyLabel('platform_admin'), false);
  assert.equal(shouldShowCompanyLabel('company_admin'), true);
  assert.equal(shouldShowCompanyLabel('member'), true);
});

test('resolveCompanyDisplayName prefers API display name over demo aliases', () => {
  assert.equal(resolveCompanyDisplayName('co-abcd1234', '融科智联'), '融科智联');
  assert.equal(resolveCompanyDisplayName('alpha'), '华东数智科技有限公司（合成）');
  assert.equal(resolveCompanyDisplayName('beta'), '远山信息技术有限公司（合成）');
  assert.equal(resolveCompanyDisplayName('co-abcd1234'), 'co-abcd1234');
});

test('create company form requires name, admin username, name, password', () => {
  const bad = validateCreateCompanyForm({
    name: '  ',
    admin_username: '',
    admin_name: '',
    admin_password: '',
    must_change_password: true,
  });
  assert.equal(bad.valid, false);
  assert.ok(bad.issues.length >= 3);

  const good = validateCreateCompanyForm({
    name: '合成公司',
    admin_username: 'c1',
    admin_name: '甲',
    admin_password: 'Init_Pass_2026',
    must_change_password: true,
  });
  assert.equal(good.valid, true);
  assert.equal(good.issues.length, 0);
});

test('companyDetailPath encodes company id', () => {
  assert.equal(companyDetailPath('co-abcd1234'), '/admin/companies/co-abcd1234');
});

test('parseAppPath recognizes company detail', async () => {
  const { parseAppPath } = await import('../../src/app/app-route.ts');
  const route = parseAppPath('/admin/companies/co-abcd1234');
  assert.equal(route.kind, 'company_detail');
  if (route.kind === 'company_detail') {
    assert.equal(route.companyId, 'co-abcd1234');
  }
});
