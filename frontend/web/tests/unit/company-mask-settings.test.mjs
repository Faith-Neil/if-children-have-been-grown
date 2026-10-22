// 为什么有这个文件：覆盖 APP-M2-T018 公司掩码规则动态读取与查看留痕提示的前端单元测试。
// 它解决什么问题：表格驱动断言不同公司配置下掩码规则自适应切换、留痕告警文案正确性、非法配置合规拦截与零 storage 泄密断言。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  COMPANY_MASK_RULES_KEY,
  DEFAULT_AUDIT_TRACE_NOTICE,
  DEFAULT_AUDIT_TRACE_DETAIL,
  sanitizeMaskRule,
  extractMaskRulesFromCompanySettings,
} from '../../src/admin/company-mask-settings.ts';
import {
  DEFAULT_MASK_RULES,
  maskSensitiveValue,
  assertNoSensitiveLeak,
} from '../../src/admin/sensitive-mask.ts';

test('1. 公司掩码规则提取与空值安全兜底 (extractMaskRulesFromCompanySettings)', () => {
  // 1.1 空值 / undefined / 空对象兜底
  const emptyRes = extractMaskRulesFromCompanySettings(null);
  assert.equal(emptyRes.idCardMode, 'standard');
  assert.equal(emptyRes.isCustom, false);
  assert.deepEqual(emptyRes.rules.id_card, DEFAULT_MASK_RULES.id_card);
  assert.deepEqual(emptyRes.rules.phone, DEFAULT_MASK_RULES.phone);
  assert.deepEqual(emptyRes.rules.bank_card, DEFAULT_MASK_RULES.bank_card);

  // 1.2 损坏的 JSON 字符串安全回退
  const corruptRes = extractMaskRulesFromCompanySettings('INVALID_JSON_STRING{{{');
  assert.equal(corruptRes.isCustom, false);
  assert.deepEqual(corruptRes.rules.id_card, DEFAULT_MASK_RULES.id_card);

  // 1.3 字符串快捷模式 ('strict' 与 'standard')
  const strictShortcut = extractMaskRulesFromCompanySettings('strict');
  assert.equal(strictShortcut.idCardMode, 'strict');
  assert.equal(strictShortcut.rules.id_card.prefix, 3);
  assert.equal(strictShortcut.rules.id_card.suffix, 4);

  const standardShortcut = extractMaskRulesFromCompanySettings('standard');
  assert.equal(standardShortcut.idCardMode, 'standard');
  assert.equal(standardShortcut.rules.id_card.prefix, 6);
  assert.equal(standardShortcut.rules.id_card.suffix, 4);
});

test('2. 解析嵌套 sensitive_mask_rules 公司设置与合法格式支持', () => {
  // 2.1 嵌套于 sensitive_mask_rules 下的对象
  const companyConfig = {
    [COMPANY_MASK_RULES_KEY]: {
      id_card: 'strict',
      phone: { prefix: 3, suffix: 2, fixedLength: 6 },
      bank_card: { prefix: 0, suffix: 4 },
    },
  };
  const resolved = extractMaskRulesFromCompanySettings(companyConfig);
  assert.equal(resolved.isCustom, true);
  assert.equal(resolved.idCardMode, 'strict');
  assert.equal(resolved.rules.id_card.prefix, 3);
  assert.equal(resolved.rules.id_card.suffix, 4);
  assert.equal(resolved.rules.phone.prefix, 3);
  assert.equal(resolved.rules.phone.suffix, 2);
  assert.equal(resolved.rules.phone.fixedLength, 6);

  // 2.2 JSON 序列化字符串输入支持
  const jsonStr = JSON.stringify({
    sensitive_mask_rules: {
      id_card: { prefix: 4, suffix: 4 },
      phone: { prefix: 3, suffix: 4 },
    },
  });
  const fromJson = extractMaskRulesFromCompanySettings(jsonStr);
  assert.equal(fromJson.isCustom, true);
  assert.equal(fromJson.rules.id_card.prefix, 4);
  assert.equal(fromJson.rules.id_card.suffix, 4);
});

test('3. PRD §6.9 合规安全拦截：越界与恶意试图“不掩码”的规则纠正 (sanitizeMaskRule)', () => {
  // 3.1 拦截负数
  const negativeRule = sanitizeMaskRule('id_card', { prefix: -2, suffix: -1 });
  assert.equal(negativeRule.prefix, DEFAULT_MASK_RULES.id_card.prefix);
  assert.equal(negativeRule.suffix, DEFAULT_MASK_RULES.id_card.suffix);

  // 3.2 拦截企图完全展示身份证号（prefix: 18, suffix: 0）
  const idCardBypass = sanitizeMaskRule('id_card', { prefix: 18, suffix: 0 });
  assert.ok(idCardBypass.prefix <= 8, '身份证前缀不得超过 8 位');
  assert.equal(idCardBypass.suffix, 4, '身份证后缀强制回退安全值');

  // 3.3 拦截企图破坏银行卡只留后 4 位规则（如 prefix: 12, suffix: 4）
  const bankCardBypass = sanitizeMaskRule('bank_card', { prefix: 12, suffix: 4 });
  assert.equal(bankCardBypass.prefix, 0, '银行卡严格禁止前缀明文展示');

  // 3.4 拦截空白掩码字符
  const emptyMaskChar = sanitizeMaskRule('phone', { maskChar: '   ' });
  assert.equal(emptyMaskChar.maskChar, '*', '空白 maskChar 强制纠正为 *');
});

test('4. 表格驱动：不同公司配置下掩码规则自适应输出', () => {
  const idCardSample = '110101199003072345';
  const phoneSample = '13812345678';
  const bankCardSample = '6222021234567890123';

  // 4.1 公司 A 配置：严格 3+4 身份证模式与标准手机号
  const companyA = {
    sensitive_mask_rules: {
      id_card: 'strict',
      phone: { prefix: 3, suffix: 4 },
    },
  };
  const settingsA = extractMaskRulesFromCompanySettings(companyA);
  const idCardA = maskSensitiveValue(idCardSample, 'id_card', settingsA.rules.id_card);
  const phoneA = maskSensitiveValue(phoneSample, 'phone', settingsA.rules.phone);

  // 严格 3+4 模式：110 + 11个* + 2345
  assert.equal(idCardA, '110***********2345', '公司 A 应输出为严格 3+4 模式掩码');
  assert.equal(phoneA, '138****5678', '公司 A 应输出为标准手机号掩码');

  // 4.2 公司 B 配置：标准 6+4 身份证模式与自定义 2+4 (5个*) 手机号
  const companyB = {
    sensitive_mask_rules: {
      id_card: 'standard',
      phone: { prefix: 2, suffix: 4, fixedLength: 5 },
    },
  };
  const settingsB = extractMaskRulesFromCompanySettings(companyB);
  const idCardB = maskSensitiveValue(idCardSample, 'id_card', settingsB.rules.id_card);
  const phoneB = maskSensitiveValue(phoneSample, 'phone', settingsB.rules.phone);

  // 标准 6+4 模式：110101 + 8个* + 2345
  assert.equal(idCardB, '110101********2345', '公司 B 应输出为标准 6+4 模式掩码');
  assert.equal(phoneB, '13*****5678', '公司 B 应输出为自定义 2+4 手机号掩码');

  // 4.3 未配置公司规则（默认兜底）：标准 6+4 模式与银行卡后 4 位
  const defaultSettings = extractMaskRulesFromCompanySettings();
  const idCardDefault = maskSensitiveValue(idCardSample, 'id_card', defaultSettings.rules.id_card);
  const bankDefault = maskSensitiveValue(bankCardSample, 'bank_card', defaultSettings.rules.bank_card);

  assert.equal(idCardDefault, '110101********2345', '无配置时应回退到标准 6+4 安全默认掩码');
  assert.equal(bankDefault, '***************0123', '银行卡默认只保留后 4 位');
});

test('5. 查看留痕合规警示提示文案与规范标准契约', () => {
  // 5.1 验证标准留痕告警文案
  assert.equal(
    DEFAULT_AUDIT_TRACE_NOTICE,
    '当前页面涉及敏感个人信息，调阅完整值将被记录安全审计日志（操作人、时间、原因与网络环境）'
  );

  // 5.2 验证补充说明文案
  assert.equal(
    DEFAULT_AUDIT_TRACE_DETAIL,
    '根据合规规范，调阅完整值必须填写 5 字以上业务理由，系统将如实留痕备查。'
  );
});

test('6. 动态规则与留痕上下文全链路零 storage / URL 泄露校验', () => {
  const sensitivePlaintext = '110101199003072345';

  const mockLocalStorage = {
    length: 1,
    key(i) {
      return i === 0 ? 'icg_sidebar_collapsed' : null;
    },
    getItem(k) {
      return k === 'icg_sidebar_collapsed' ? 'false' : null;
    },
  };

  const mockSessionStorage = {
    length: 0,
    key() {
      return null;
    },
    getItem() {
      return null;
    },
  };

  const mockUrl = 'https://icg.example.com/workbench?nav=workbench';

  const leakCheck = assertNoSensitiveLeak(sensitivePlaintext, {
    localStorage: mockLocalStorage,
    sessionStorage: mockSessionStorage,
    url: mockUrl,
  });

  assert.equal(leakCheck.safe, true, '高敏个人信息绝对未被写入 storage 或 URL');
});
