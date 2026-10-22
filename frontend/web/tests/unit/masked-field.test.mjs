// 为什么有这个文件：验证高敏个人信息脱敏规则（身份证、手机号、银行卡号）、调阅原因强校验与防泄露断言。
// 它解决什么问题：落实 PRD v1.8 §5.4.5、§2.3 与 §5.9.1，确保高敏信息默认掩码展示、无权角色无法查看完整值、调阅原因必须强校验且不可空白，且完整明文绝不写入 storage 或 URL。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  assertNoSensitiveLeak,
  DEFAULT_MASK_RULES,
  maskBankCard,
  maskIdCard,
  maskPhone,
  maskSensitiveValue,
  validateRevealReason,
} from '../../src/admin/sensitive-mask.ts';
import { can } from '../../src/shell/can-directive.ts';

/* ========================================================================= */
/* 1. 表格驱动：高敏字段掩码规则测试                                         */
/* ========================================================================= */

test('table-driven: 身份证号掩码规则（标准 6+4 与严格 3+4）', () => {
  // 1. 标准 18 位二代身份证（标准模式：前 6 后 4，中间 8 个 *）
  assert.equal(maskIdCard('110101199003072345', 'standard'), '110101********2345');
  assert.equal(maskIdCard('31011520000101888X', 'standard'), '310115********888X');

  // 2. 严格 3+4 模式（PRD §5.4.5 与原交接验收约束：前 3 位与后 4 位明文，中间全部 *）
  assert.equal(maskIdCard('110101199003072345', 'strict'), '110***********2345');
  assert.equal(maskIdCard('31011520000101888X', 'strict'), '310***********888X');

  // 3. 15 位一代身份证
  assert.equal(maskIdCard('110101900307234', 'standard'), '110101********7234');
  assert.equal(maskIdCard('110101900307234', 'strict'), '110********7234');

  // 4. 空值与异常边界保护
  assert.equal(maskIdCard(''), '');
  assert.equal(maskIdCard(null), '');
  assert.equal(maskIdCard(undefined), '');
});

test('table-driven: 手机号码掩码规则（前 3 后 4，中间 4 个 *）', () => {
  assert.equal(maskPhone('13812345678'), '138****5678');
  assert.equal(maskPhone('18900001111'), '189****1111');
  assert.equal(maskPhone('15099998888'), '150****8888');

  // 空值保护
  assert.equal(maskPhone(''), '');
  assert.equal(maskPhone(null), '');
});

test('table-driven: 银行账号掩码规则（只保留后 4 位明文）', () => {
  assert.equal(maskBankCard('6222021234567890123'), '***************0123');
  assert.equal(maskBankCard('6214850200001234'), '************1234');
  assert.equal(maskBankCard('9558801001001234567'), '***************4567');

  // 空值保护
  assert.equal(maskBankCard(''), '');
  assert.equal(maskBankCard(null), '');
});

test('table-driven: 电子邮箱与姓名掩码规则', () => {
  // 电子邮箱：保留前 2 位与域名，用户名中段掩码
  assert.equal(maskSensitiveValue('zhangsan@company.com', 'email'), 'zh***@company.com');
  assert.equal(maskSensitiveValue('li@qq.com', 'email'), 'li***@qq.com');

  // 姓名：2 字遮蔽后字；3 字以上保留首尾字
  assert.equal(maskSensitiveValue('张三', 'name'), '张*');
  assert.equal(maskSensitiveValue('李小龙', 'name'), '李*龙');
  assert.equal(maskSensitiveValue('诸葛孔明', 'name'), '诸**明');
});

/* ========================================================================= */
/* 2. 查看原因强校验测试（空白/字数不足/合法理由）                           */
/* ========================================================================= */

test('validateRevealReason enforces mandatory non-empty business explanation', () => {
  // 1. 空值或 undefined 拦截
  const emptyRes = validateRevealReason('');
  assert.equal(emptyRes.valid, false);
  assert.ok(emptyRes.message?.includes('必填项'));

  const nullRes = validateRevealReason(null);
  assert.equal(nullRes.valid, false);

  // 2. 全空白字符（空格、换行、制表符）拦截
  const whitespaceRes = validateRevealReason('   \t \n  ');
  assert.equal(whitespaceRes.valid, false);
  assert.ok(whitespaceRes.message?.includes('不可全为空白'));

  // 3. 字数不足（小于 5 个字）拦截
  const shortRes1 = validateRevealReason('查看');
  assert.equal(shortRes1.valid, false);
  assert.ok(shortRes1.message?.includes('字数不足'));

  const shortRes2 = validateRevealReason('   测试理由 ');
  assert.equal(shortRes2.valid, false); // trim 后仅 4 字

  // 4. 合法理由（>= 5 个有效非空字符）通过
  const validRes1 = validateRevealReason('用于拟派项目技术负责人投标资质核验');
  assert.equal(validRes1.valid, true);

  const validRes2 = validateRevealReason('   已取得该员工书面授权用于投标   ');
  assert.equal(validRes2.valid, true);
});

/* ========================================================================= */
/* 3. 权限控制断言：仅公司管理员与资料管理员可查看完整高敏身份证号           */
/* ========================================================================= */

test('table-driven: 8 system roles permission on id_card:view', () => {
  const allowedRoles = ['company_admin', 'data_admin'];
  const forbiddenRoles = [
    'platform_admin',
    'group_admin',
    'project_lead',
    'bid_writer',
    'auditor',
    'viewer',
  ];

  for (const role of allowedRoles) {
    const res = can('id_card:view', undefined, { role });
    assert.equal(res.allowed, true, `Role ${role} should be permitted to view full ID card`);
  }

  for (const role of forbiddenRoles) {
    const res = can('id_card:view', undefined, { role });
    assert.equal(res.allowed, false, `Role ${role} should be strictly forbidden from viewing full ID card`);
    assert.ok(res.reason?.includes('公司管理员与资料管理员'));
  }
});

/* ========================================================================= */
/* 4. 安全防护断言：完整高敏明文绝对没有被写入 storage 或 URL                 */
/* ========================================================================= */

test('assertNoSensitiveLeak verifies full plaintext is never written to storage or URL', () => {
  const secretId = '110101199003072345';

  // 模拟干净的安全环境
  const cleanLocalStorage = {
    length: 2,
    key: (i) => ['theme', 'last_project_tab'][i],
    getItem: (k) => ({ theme: 'light', last_project_tab: 'overview' }[k] ?? null),
  };
  const cleanSessionStorage = {
    length: 1,
    key: () => 'session_ticket',
    getItem: () => 'ticket-abc-123',
  };
  const cleanUrl = 'https://icg.example.com/projects/p-101/members?tab=personnel';

  const cleanCheck = assertNoSensitiveLeak(secretId, {
    localStorage: cleanLocalStorage,
    sessionStorage: cleanSessionStorage,
    url: cleanUrl,
  });
  assert.equal(cleanCheck.safe, true);

  // 模拟泄露到 URL
  const leakedUrl = `https://icg.example.com/reveal?id=${secretId}`;
  const urlCheck = assertNoSensitiveLeak(secretId, { url: leakedUrl });
  assert.equal(urlCheck.safe, false);
  assert.equal(urlCheck.leakLocation, 'url');

  // 模拟泄露到 localStorage
  const leakedLocalStorage = {
    length: 1,
    key: () => 'cached_employee_id_card',
    getItem: () => secretId,
  };
  const lsCheck = assertNoSensitiveLeak(secretId, { localStorage: leakedLocalStorage });
  assert.equal(lsCheck.safe, false);
  assert.equal(lsCheck.leakLocation, 'localStorage:cached_employee_id_card');

  // 模拟泄露到 sessionStorage
  const leakedSessionStorage = {
    length: 1,
    key: () => 'temp_user_plain',
    getItem: () => `ID:${secretId}`,
  };
  const ssCheck = assertNoSensitiveLeak(secretId, { sessionStorage: leakedSessionStorage });
  assert.equal(ssCheck.safe, false);
  assert.equal(ssCheck.leakLocation, 'sessionStorage:temp_user_plain');
});
