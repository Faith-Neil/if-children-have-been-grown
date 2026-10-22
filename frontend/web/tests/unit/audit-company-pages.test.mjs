// 为什么有这个文件：覆盖 APP-M2-T157 (A-06 审计日志中心) 与 APP-M2-T026 (A-01 企业租户管理页) 前端核心业务逻辑单元测试。
// 它解决什么问题：
// 1. 验证敏感数据脱敏调阅记录（调阅人、时间、>=5字调阅理由合规检验）；
// 2. 验证章节排他编辑锁抢占/接管/释放/超时等全生命周期事件解析；
// 3. 验证模型密钥变更事件（创建、更新、轮换、吊销）与指纹脱敏，确保绝无明文泄密；
// 4. 验证审计日志系统级只读保护契约（阻断一切删除、编辑、清空尝试）；
// 5. 验证审计日志多维检索与过滤算法（按时间范围、操作人、操作类型、项目ID、关键词）；
// 6. 验证企业租户安全合规参数基线校验（掩码不可关闭、密码最少位数>=8、字符类数>=3、自动保存<=心跳<=锁超时）；
// 7. 验证集团管理员、公司管理员、平台管理员与只读角色的权限感知与管理按钮隐匿；
// 8. 验证停用公司租户二次确认安全防线。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  validateRevealReason,
  getAuditActionMeta,
  formatMaskedKeyFingerprint,
  formatMonospaceTime,
  assertAuditLogReadOnly,
  filterAuditLogs,
  computeAuditSummaryStats,
  DEFAULT_AUDIT_LOGS,
} from '../../src/admin/audit-log-core.ts';

import {
  PLATFORM_BASELINE,
  validateCompanyComplianceSettings,
  canManageCompanySettings,
  validateDisableConfirmation,
  DEFAULT_COMPANIES,
} from '../../src/admin/company-manage-core.ts';

/* ========================================================================= */
/* 1. APP-M2-T157: 敏感数据调阅理由合规性验证 (validateRevealReason)          */
/* ========================================================================= */

test('APP-M2-T157: 敏感数据调阅理由合规门禁校验 (>= 5 字规则)', () => {
  // 1.1 空值与非字符串拦截
  const emptyRes = validateRevealReason(null);
  assert.equal(emptyRes.valid, false);
  assert.equal(emptyRes.length, 0);
  assert.match(emptyRes.message || '', /理由不能为空/);

  const undefinedRes = validateRevealReason(undefined);
  assert.equal(undefinedRes.valid, false);

  const blankRes = validateRevealReason('    ');
  assert.equal(blankRes.valid, false);
  assert.equal(blankRes.length, 0);

  // 1.2 理由字数少于 5 字被坚决拦截
  const shortRes1 = validateRevealReason('查看');
  assert.equal(shortRes1.valid, false);
  assert.equal(shortRes1.length, 2);
  assert.match(shortRes1.message || '', /不足 5 字/);

  const shortRes2 = validateRevealReason('投标核验');
  assert.equal(shortRes2.valid, false);
  assert.equal(shortRes2.length, 4);

  // 1.3 恰好 5 字达到合规底线
  const exact5Res = validateRevealReason('核验身份证');
  assert.equal(exact5Res.valid, true);
  assert.equal(exact5Res.length, 5);
  assert.equal(exact5Res.message, undefined);

  // 1.4 详细业务合规理由 (>= 5 字)
  const fullRes = validateRevealReason('项目商务标书资格审查材料核验需要，核对开户许可证');
  assert.equal(fullRes.valid, true);
  assert.equal(fullRes.length, 24);
});

/* ========================================================================= */
/* 2. APP-M2-T157: 章节排他编辑锁与模型密钥事件元信息映射                     */
/* ========================================================================= */

test('APP-M2-T157: 操作类型元信息映射与事件分类准确性', () => {
  // 2.1 脱敏数据调阅
  const revealMeta = getAuditActionMeta('sensitive.reveal');
  assert.equal(revealMeta.category, 'sensitive');
  assert.equal(revealMeta.color, 'purple');
  assert.match(revealMeta.label, /脱敏数据调阅/);

  // 2.2 排他编辑锁系列
  const acquireMeta = getAuditActionMeta('lock.acquire');
  assert.equal(acquireMeta.category, 'lock');
  assert.match(acquireMeta.label, /获取章节编辑锁/);

  const takeoverMeta = getAuditActionMeta('lock.takeover');
  assert.equal(takeoverMeta.category, 'lock');
  assert.equal(takeoverMeta.color, 'orange');
  assert.match(takeoverMeta.label, /抢占\/接管编辑锁/);

  const releaseMeta = getAuditActionMeta('lock.release');
  assert.equal(releaseMeta.category, 'lock');

  const timeoutMeta = getAuditActionMeta('lock.timeout');
  assert.equal(timeoutMeta.category, 'lock');

  // 2.3 模型密钥系列
  const keyRotateMeta = getAuditActionMeta('model_key.rotate');
  assert.equal(keyRotateMeta.category, 'key');
  assert.match(keyRotateMeta.label, /安全密钥定期轮换/);

  const keyUpdateMeta = getAuditActionMeta('model_key.update');
  assert.equal(keyUpdateMeta.category, 'key');

  // 2.4 云端调用系列
  const cloudLlmMeta = getAuditActionMeta('cloud.llm_call');
  assert.equal(cloudLlmMeta.category, 'cloud');
});

/* ========================================================================= */
/* 3. APP-M2-T157: 模型密钥脱敏指纹格式化与明文零泄漏保障                    */
/* ========================================================================= */

test('APP-M2-T157: 模型密钥脱敏指纹格式化与明文防泄漏断言', () => {
  // 3.1 真实完整密钥绝不原样输出
  const rawKey1 = 'sk-proj-948123049182309128309123809123809128309182309128309';
  const masked1 = formatMaskedKeyFingerprint(rawKey1);
  assert.equal(masked1.startsWith('sk-****'), true);
  assert.equal(masked1.endsWith('8309'), true);
  assert.equal(masked1.includes('948123049182309128309123809123809128309182309128309'), false);

  // 3.2 已脱敏指纹保持原样
  const existingMasked = 'sk-****8f92';
  assert.equal(formatMaskedKeyFingerprint(existingMasked), 'sk-****8f92');

  const localMasked = 'loc-****33a1';
  assert.equal(formatMaskedKeyFingerprint(localMasked), 'loc-****33a1');

  // 3.3 空值安全提示
  assert.match(formatMaskedKeyFingerprint(null), /未配置/);
  assert.match(formatMaskedKeyFingerprint(''), /未配置/);
});

/* ========================================================================= */
/* 4. APP-M2-T157: 审计日志系统级只读保护契约 (assertAuditLogReadOnly)         */
/* ========================================================================= */

test('APP-M2-T157: 只读保护契约断言：严禁前端提供删除与篡改接口', () => {
  // 4.1 允许只读操作
  assert.doesNotThrow(() => assertAuditLogReadOnly('query'));
  assert.doesNotThrow(() => assertAuditLogReadOnly('read'));
  assert.doesNotThrow(() => assertAuditLogReadOnly('export_read_only'));
  assert.doesNotThrow(() => assertAuditLogReadOnly('view_detail'));

  // 4.2 拦截任何删除、编辑或清空操作
  assert.throws(() => assertAuditLogReadOnly('delete_log'), /严禁执行 \[delete_log\] 操作/);
  assert.throws(() => assertAuditLogReadOnly('edit_audit'), /严禁执行 \[edit_audit\] 操作/);
  assert.throws(() => assertAuditLogReadOnly('update_record'), /严禁执行 \[update_record\] 操作/);
  assert.throws(() => assertAuditLogReadOnly('clear_all_logs'), /严禁执行 \[clear_all_logs\] 操作/);
  assert.throws(() => assertAuditLogReadOnly('truncate_table'), /严禁执行 \[truncate_table\] 操作/);
});

/* ========================================================================= */
/* 5. APP-M2-T157: 多维检索与过滤算法 (filterAuditLogs)                       */
/* ========================================================================= */

test('APP-M2-T157: 审计日志多维检索过滤测试', () => {
  const sampleLogs = [...DEFAULT_AUDIT_LOGS];

  // 5.1 按事件分类筛选
  const sensitiveLogs = filterAuditLogs(sampleLogs, { category: 'sensitive' });
  assert.equal(sensitiveLogs.every(l => l.category === 'sensitive'), true);
  assert.ok(sensitiveLogs.length >= 2);

  const lockLogs = filterAuditLogs(sampleLogs, { category: 'lock' });
  assert.equal(lockLogs.every(l => l.category === 'lock'), true);
  assert.ok(lockLogs.length >= 3);

  const keyLogs = filterAuditLogs(sampleLogs, { category: 'key' });
  assert.equal(keyLogs.every(l => l.category === 'key'), true);
  assert.ok(keyLogs.length >= 2);

  // 5.2 按具体操作类型筛选
  const takeoverLogs = filterAuditLogs(sampleLogs, { actionType: 'lock.takeover' });
  assert.equal(takeoverLogs.length, 1);
  assert.equal(takeoverLogs[0].action, 'lock.takeover');
  assert.equal(takeoverLogs[0].lock_chapter_id, 'chap-tech-02');

  // 5.3 按操作人筛选
  const zhangLogs = filterAuditLogs(sampleLogs, { operator: '张明' });
  assert.equal(zhangLogs.every(l => l.user_name.includes('张明') || l.user_id.includes('张明')), true);

  const adminLogs = filterAuditLogs(sampleLogs, { operator: 'alpha-manager' });
  assert.equal(adminLogs.every(l => l.user_id === 'alpha-manager'), true);

  // 5.4 按项目 ID 检索
  const projectLogs = filterAuditLogs(sampleLogs, { projectId: 'p-alpha-01' });
  assert.equal(projectLogs.every(l => l.project_id === 'p-alpha-01'), true);

  // 5.5 按时间范围过滤
  const timeLogs = filterAuditLogs(sampleLogs, {
    dateStart: '2026-10-22 00:00:00',
    dateEnd: '2026-10-22 23:59:59',
  });
  assert.equal(timeLogs.every(l => l.occurred_at.startsWith('2026-10-22')), true);

  // 5.6 综合统计汇总计算
  const stats = computeAuditSummaryStats(sampleLogs);
  assert.equal(stats.totalCount, sampleLogs.length);
  assert.ok(stats.sensitiveRevealCount >= 2);
  assert.ok(stats.lockEventCount >= 3);
  assert.ok(stats.keyEventCount >= 2);
  assert.equal(stats.successRate, 100);
});

/* ========================================================================= */
/* 6. APP-M2-T026: 公司安全合规参数基线校验 (validateCompanyComplianceSettings) */
/* ========================================================================= */

test('APP-M2-T026: 企业合规参数基线校验与门禁拦截', () => {
  // 6.1 合规正常配置
  const compliantConfig = {
    mask_strict_mode_enabled: true,
    password_min_length: 8,
    password_min_char_classes: 3,
    editor_autosave_seconds: 10,
    edit_lock_heartbeat_seconds: 60,
    edit_lock_timeout_minutes: 30,
  };
  const validResult = validateCompanyComplianceSettings(compliantConfig);
  assert.equal(validResult.valid, true);
  assert.equal(validResult.issues.length, 0);

  // 6.2 密码最少长度低于平台基线 8 位被拦截 (PRD §5.10.2: 只能调高，不能低于平台默认值)
  const weakPasswordConfig = {
    ...compliantConfig,
    password_min_length: 6, // 违规
  };
  const resWeakPassword = validateCompanyComplianceSettings(weakPasswordConfig);
  assert.equal(resWeakPassword.valid, false);
  const pwLengthIssue = resWeakPassword.issues.find(i => i.field === 'password_min_length');
  assert.ok(pwLengthIssue);
  assert.match(pwLengthIssue.message, /不能低于平台安全基线 8 位/);

  // 6.3 密码字符类数低于平台基线 3 类被拦截 (PRD §5.10.2: 至少包含三类，不能低于平台默认值)
  const weakCharClassesConfig = {
    ...compliantConfig,
    password_min_char_classes: 2, // 违规
  };
  const resWeakClasses = validateCompanyComplianceSettings(weakCharClassesConfig);
  assert.equal(resWeakClasses.valid, false);
  const pwClassesIssue = resWeakClasses.issues.find(i => i.field === 'password_min_char_classes');
  assert.ok(pwClassesIssue);
  assert.match(pwClassesIssue.message, /不能低于平台默认 3 类/);

  // 6.4 自动保存间隔大于心跳间隔被拦截 (PRD §5.11.9: editor_autosave_seconds <= edit_lock_heartbeat_seconds)
  const invalidAutosaveConfig = {
    ...compliantConfig,
    editor_autosave_seconds: 90,
    edit_lock_heartbeat_seconds: 60,
  };
  const resAutosave = validateCompanyComplianceSettings(invalidAutosaveConfig);
  assert.equal(resAutosave.valid, false);
  assert.ok(resAutosave.issues.some(i => i.field === 'editor_autosave_seconds'));

  // 6.5 心跳间隔 10 倍大于锁超时时间被拦截 (PRD §5.11.9: edit_lock_heartbeat_seconds * 10 <= timeout_minutes * 60)
  const invalidHeartbeatConfig = {
    ...compliantConfig,
    editor_autosave_seconds: 10,
    edit_lock_heartbeat_seconds: 120, // 120 * 10 = 1200秒
    edit_lock_timeout_minutes: 15,    // 15 * 60 = 900秒，1200 > 900 违规
  };
  const resHeartbeat = validateCompanyComplianceSettings(invalidHeartbeatConfig);
  assert.equal(resHeartbeat.valid, false);
  assert.ok(resHeartbeat.issues.some(i => i.field === 'edit_lock_heartbeat_seconds'));

  // 6.6 企图关闭高敏脱敏保护被红线拦截 (PRD §6.9: 不提供关闭掩码开关)
  const disabledMaskConfig = {
    ...compliantConfig,
    mask_strict_mode_enabled: false,
  };
  const resDisableMask = validateCompanyComplianceSettings(disabledMaskConfig);
  assert.equal(resDisableMask.valid, false);
  assert.ok(resDisableMask.issues.some(i => i.field === 'mask_strict_mode_enabled'));
  assert.match(resDisableMask.issues[0].message, /脱敏强合规规则不可关闭/);
});

/* ========================================================================= */
/* 7. APP-M2-T026: 集团管理员 vs 公司管理员权限感知与按钮隐匿                */
/* ========================================================================= */

test('APP-M2-T026: 权限感知判定：区分集团管理员、公司管理员、平台管理员与只读人员', () => {
  // 7.1 本公司管理员 (company_admin): 具备本公司合规配置编辑权限，但不能自毁停用公司
  const companyAdminRes = canManageCompanySettings({
    role: 'company_admin',
    targetCompanyId: 'alpha',
    userCompanyId: 'alpha',
  });
  assert.equal(companyAdminRes.canEdit, true);
  assert.equal(companyAdminRes.canDisable, false);
  assert.equal(companyAdminRes.canViewAudit, true);
  assert.equal(companyAdminRes.roleLabel, '公司管理员');

  // 7.2 集团管理员 (group_admin): 跨公司查看，严禁编辑任何公司配置，非公司管理员隐藏管理按钮
  const groupAdminRes = canManageCompanySettings({
    role: 'group_admin',
    targetCompanyId: 'alpha',
    userCompanyId: 'grp-01',
  });
  assert.equal(groupAdminRes.canEdit, false);
  assert.equal(groupAdminRes.canDisable, false);
  assert.equal(groupAdminRes.canViewAudit, true);
  assert.match(groupAdminRes.readOnlyNotice || '', /集团管理员.*全局监管/);

  // 7.3 平台管理员 (platform_admin): 具备开通与停用公司的最高管理权限
  const platformAdminRes = canManageCompanySettings({
    role: 'platform_admin',
    targetCompanyId: 'alpha',
    userCompanyId: 'platform',
  });
  assert.equal(platformAdminRes.canEdit, true);
  assert.equal(platformAdminRes.canDisable, true);
  assert.equal(platformAdminRes.canToggleStatus, true);

  // 7.4 跨公司非本租户管理员: 阻断编辑
  const otherCompanyAdminRes = canManageCompanySettings({
    role: 'company_admin',
    targetCompanyId: 'beta',
    userCompanyId: 'alpha',
  });
  assert.equal(otherCompanyAdminRes.canEdit, false);

  // 7.5 普通只读成员 (viewer): 纯只读
  const viewerRes = canManageCompanySettings({
    role: 'viewer',
    targetCompanyId: 'alpha',
    userCompanyId: 'alpha',
  });
  assert.equal(viewerRes.canEdit, false);
  assert.equal(viewerRes.canDisable, false);
});

/* ========================================================================= */
/* 8. APP-M2-T026: 停用租户二次确认保护校验 (validateDisableConfirmation)     */
/* ========================================================================= */

test('APP-M2-T026: 停用公司租户二次确认输入校验 (PRD §5.10.1 约束)', () => {
  const targetName = '华东数智科技有限公司';

  // 8.1 名称完全一致时通过
  assert.equal(validateDisableConfirmation('华东数智科技有限公司', targetName), true);
  assert.equal(validateDisableConfirmation('  华东数智科技有限公司  ', targetName), true);

  // 8.2 错误名称或缺字拦截
  assert.equal(validateDisableConfirmation('华东数智', targetName), false);
  assert.equal(validateDisableConfirmation('远山信息技术有限公司', targetName), false);
  assert.equal(validateDisableConfirmation('', targetName), false);
  assert.equal(validateDisableConfirmation('   ', targetName), false);
});
