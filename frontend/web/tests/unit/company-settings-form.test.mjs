// 为什么有这个文件：验证 APP-M2-T025 扩展字段与公司设置键表单框架的业务逻辑、合规红线门禁与角色权限。
// 它解决什么问题：
// 1. 验证公司设置初始数据集（buildInitialCompanySettings）；
// 2. 验证“只能调严不能调宽”安全基线（validateCompanySettings 密码长度/字符类数下限）；
// 3. 验证 9.11 核心编辑锁心跳三元数学约束（自动保存 <= 心跳，心跳*10 <= 锁超时，超时 >= 5m）；
// 4. 验证废标阻断导出门禁与数值上下限越界拦截；
// 5. 验证 8 大标准 RBAC 角色权限矩阵与只读感知；
// 6. 验证 CompanySettingsPage.tsx 与 GlobalPagesContent.tsx 静态 AST 契约与无占位壳要求。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  buildInitialCompanySettings,
  checkCompanySettingsPermission,
  validateCompanySettings,
  PLATFORM_SETTING_BOUNDS,
  DEFAULT_CUSTOM_FIELDS,
} from '../../src/admin/company-settings-core.ts';

function parseSource(relPath) {
  const fullPath = path.resolve(import.meta.dirname, relPath);
  const content = fs.readFileSync(fullPath, 'utf8');
  const tree = ts.createSourceFile(
    fullPath,
    content,
    ts.ScriptTarget.Latest,
    true
  );
  return { content, tree };
}

test('1. 公司设置初始数据集与平台基线定义（buildInitialCompanySettings）', () => {
  const settings = buildInitialCompanySettings('alpha', '华东数智科技有限公司');
  assert.equal(settings.company_id, 'alpha');
  assert.equal(settings.company_name, '华东数智科技有限公司');

  // 1.1 密码策略基线
  assert.equal(settings.password_min_length, 8);
  assert.equal(settings.password_min_char_classes, 3);
  assert.equal(settings.password_expire_days, 90);

  // 1.2 编辑锁与自动保存基线
  assert.equal(settings.editor_autosave_seconds, 10);
  assert.equal(settings.edit_lock_heartbeat_seconds, 60);
  assert.equal(settings.edit_lock_timeout_minutes, 30);

  // 1.3 核心合规红线
  assert.equal(settings.export_redline_blocking, true, '废标红线导出门禁默认强制开启');
  assert.equal(settings.force_local_model, true, '涉密本地模型门禁默认强制开启');

  // 1.4 扩展字段收录
  assert.ok(settings.custom_fields.length >= 3);
  assert.equal(settings.custom_fields[0].field_key, 'custom_sla_grade');
});

test('2. 核心安全红线：“公司设置只能调严不能调宽”合规校验', () => {
  const base = buildInitialCompanySettings();

  // 2.1 密码最少位数不能低于平台下限 8 位
  const invalidPassLen = validateCompanySettings({ ...base, password_min_length: 7 });
  assert.equal(invalidPassLen.valid, false);
  const issueLen = invalidPassLen.issues.find(i => i.code === 'PASSWORD_MIN_LENGTH_TOO_LOW');
  assert.ok(issueLen, '低于 8 位必须触发 PASSWORD_MIN_LENGTH_TOO_LOW');
  assert.match(issueLen.message, /不能低于平台安全基线 8 位/);

  // 正向：调严至 12 位放行
  const validPassLen = validateCompanySettings({ ...base, password_min_length: 12 });
  assert.equal(validPassLen.valid, true);

  // 2.2 密码最少字符类别不能低于平台下限 3 类
  const invalidCharClasses = validateCompanySettings({ ...base, password_min_char_classes: 2 });
  assert.equal(invalidCharClasses.valid, false);
  const issueClasses = invalidCharClasses.issues.find(i => i.code === 'PASSWORD_CHAR_CLASSES_TOO_LOW');
  assert.ok(issueClasses, '低于 3 类必须触发 PASSWORD_CHAR_CLASSES_TOO_LOW');
  assert.match(issueClasses.message, /不能低于平台安全基线 3 类/);

  // 正向：调严至 4 类放行
  const validCharClasses = validateCompanySettings({ ...base, password_min_char_classes: 4 });
  assert.equal(validCharClasses.valid, true);
});

test('3. 规范 9.11 编辑锁心跳三元联动数学约束校验', () => {
  const base = buildInitialCompanySettings();

  // 3.1 规则 ①：自动保存间隔必须 <= 心跳间隔
  const rule1Fail = validateCompanySettings({
    ...base,
    editor_autosave_seconds: 70,
    edit_lock_heartbeat_seconds: 60,
  });
  assert.equal(rule1Fail.valid, false);
  assert.ok(rule1Fail.issues.some(i => i.code === 'AUTOSAVE_GREATER_THAN_HEARTBEAT'));

  // 3.2 规则 ②：心跳间隔的 10 倍必须 <= 锁超时时间（秒）
  // 举例：心跳 60s * 10 = 600s，锁超时 8m = 480s (600 > 480) 必须拦截
  const rule2Fail = validateCompanySettings({
    ...base,
    edit_lock_heartbeat_seconds: 60,
    edit_lock_timeout_minutes: 8,
  });
  assert.equal(rule2Fail.valid, false);
  assert.ok(rule2Fail.issues.some(i => i.code === 'HEARTBEAT_RATIO_EXCEEDS_TIMEOUT'));

  // 3.3 规则 ③：锁超时时间不能低于 5 分钟
  const rule3Fail = validateCompanySettings({
    ...base,
    edit_lock_timeout_minutes: 4,
  });
  assert.equal(rule3Fail.valid, false);
  assert.ok(rule3Fail.issues.some(i => i.code === 'LOCK_TIMEOUT_TOO_SHORT'));

  // 3.4 三元规则正向用例：10s / 60s / 30m
  const allPass = validateCompanySettings({
    ...base,
    editor_autosave_seconds: 10,
    edit_lock_heartbeat_seconds: 60,
    edit_lock_timeout_minutes: 30,
  });
  assert.equal(allPass.valid, true);
});

test('4. 废标阻断硬门禁与平台参数上下限越界拦截', () => {
  const base = buildInitialCompanySettings();

  // 4.1 废标红线导出门禁不可关闭
  const redlineDisabled = validateCompanySettings({
    ...base,
    export_redline_blocking: false,
  });
  assert.equal(redlineDisabled.valid, false);
  assert.ok(redlineDisabled.issues.some(i => i.code === 'REDLINE_BLOCKING_CANNOT_BE_DISABLED'));

  // 4.2 大纲深度越界（允许 2~5 级）
  const outlineTooDeep = validateCompanySettings({
    ...base,
    outline_max_depth: 6,
  });
  assert.equal(outlineTooDeep.valid, false);
  assert.ok(outlineTooDeep.issues.some(i => i.code === 'OUTLINE_MAX_DEPTH_OUT_OF_RANGE'));

  const outlineTooShallow = validateCompanySettings({
    ...base,
    outline_max_depth: 1,
  });
  assert.equal(outlineTooShallow.valid, false);
  assert.ok(outlineTooShallow.issues.some(i => i.code === 'OUTLINE_MAX_DEPTH_OUT_OF_RANGE'));
});

test('5. 8 大角色精细化权限感知与只读安全判定（checkCompanySettingsPermission）', () => {
  // 管理员角色拥有完全控制权
  const platformAdmin = checkCompanySettingsPermission('platform_admin');
  assert.equal(platformAdmin.canEdit, true);
  assert.equal(platformAdmin.canSave, true);
  assert.equal(platformAdmin.isReadOnly, false);

  const companyAdmin = checkCompanySettingsPermission('company_admin');
  assert.equal(companyAdmin.canEdit, true);
  assert.equal(companyAdmin.canSave, true);
  assert.equal(companyAdmin.isReadOnly, false);

  // 业务编写人与只读角色严格只读
  const readonlyRoles = ['project_lead', 'bid_writer', 'auditor', 'viewer', 'data_admin', 'reviewer', 'readonly'];
  for (const role of readonlyRoles) {
    const perm = checkCompanySettingsPermission(role);
    assert.equal(perm.canEdit, false, `${role} 不能修改设置`);
    assert.equal(perm.canSave, false, `${role} 不能保存设置`);
    assert.equal(perm.isReadOnly, true, `${role} 必须呈现只读态`);
    assert.ok(perm.readOnlyNotice, `${role} 必须包含只读提示`);
  }
});

test('6. CompanySettingsPage.tsx AST 静态契约与组件规范断言', () => {
  const { content } = parseSource('../../src/admin/CompanySettingsPage.tsx');

  // 6.1 必须包含核心测试契约 ID
  assert.ok(content.includes('data-testid="company-settings-overview"'), '包含概览统计卡片');
  assert.ok(content.includes('data-testid="company-settings-permission-tag"'), '包含权限徽标');
  assert.ok(content.includes('data-testid="company-settings-tabs"'), '包含主分类选项卡');
  assert.ok(content.includes('data-testid="input-password-min-length"'), '包含密码长度输入框');
  assert.ok(content.includes('data-testid="input-password-min-char-classes"'), '包含密码字符类数输入框');
  assert.ok(content.includes('data-testid="input-editor-autosave"'), '包含自动保存输入框');
  assert.ok(content.includes('data-testid="input-edit-lock-heartbeat"'), '包含心跳输入框');
  assert.ok(content.includes('data-testid="input-edit-lock-timeout"'), '包含锁超时输入框');
  assert.ok(content.includes('data-testid="switch-redline-blocking"'), '包含废标红线开关');
  assert.ok(content.includes('data-testid="switch-force-local-model"'), '包含涉密本地模型开关');
  assert.ok(content.includes('data-testid="custom-fields-table"'), '包含扩展字段表格');
  assert.ok(content.includes('data-testid="btn-add-custom-field"'), '包含新增扩展字段按钮');
  assert.ok(content.includes('data-testid="company-settings-save-btn"'), '包含保存按钮');
  assert.ok(content.includes('data-testid="company-settings-reset-btn"'), '包含重置按钮');
  assert.ok(content.includes('data-testid="company-settings-readonly-alert"'), '包含只读警示条');
  assert.ok(content.includes('data-testid="company-settings-validation-alert"'), '包含校验警示条');

  // 6.2 废标阻断开关必须禁用不可关闭
  assert.ok(content.includes('checked={settings.export_redline_blocking}'), '废标阻断开关绑定状态');
  assert.ok(content.includes('disabled={true}'), '废标阻断开关必须硬禁用');
});

test('7. GlobalPagesContent.tsx 路由集成与拒绝空壳断言', () => {
  const { content } = parseSource('../../src/app/GlobalPagesContent.tsx');

  // 7.1 必须正确装配 CompanySettingsPage
  assert.ok(content.includes('CompanySettingsPage'), '必须引用 CompanySettingsPage');
  assert.ok(content.includes("key: 'settings'"), '必须装配 settings 页签');
  assert.ok(content.includes('A-05 扩展字段与公司设置'), '必须命名为 A-05 扩展字段与公司设置');

  // 7.2 杜绝在 admin.rules 下继续挂载“管理规则说明”占位壳
  assert.ok(!content.includes('管理规则（只读）'), '必须彻底清空 admin.rules 下的 PendingPage 占位壳');
});
