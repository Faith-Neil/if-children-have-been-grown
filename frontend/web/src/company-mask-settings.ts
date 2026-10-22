// 为什么有这个文件：落实 PRD v1.8 §5.4.5、§5.9.1、§6.9 及设计规范 9.10 的公司级掩码规则读取与留痕规范。
// 它解决什么问题：支持从公司设置（sensitive_mask_rules）中动态解析脱敏规则、确保“每类保留位数可调但绝不可关闭掩码”的合规底线、提供默认安全兜底与留痕合规提示常量。

import {
  DEFAULT_MASK_RULES,
  type IdCardMaskMode,
  type MaskRule,
  type SensitiveFieldType,
} from './sensitive-mask.ts';

/**
 * 公司高敏掩码规则系统键（PRD §6.9 / 字典 4.10）
 */
export const COMPANY_MASK_RULES_KEY = 'sensitive_mask_rules';

/**
 * 留痕审计提示标准文案（PRD §5.4.5 / §7.3）
 */
export const DEFAULT_AUDIT_TRACE_NOTICE =
  '当前页面涉及敏感个人信息，调阅完整值将被记录安全审计日志（操作人、时间、原因与网络环境）';

/**
 * 留痕审计补充说明文案
 */
export const DEFAULT_AUDIT_TRACE_DETAIL =
  '根据合规规范，调阅完整值必须填写 5 字以上业务理由，系统将如实留痕备查。';

/**
 * 公司掩码规则配置结构定义
 */
export interface CompanyMaskRulesConfig {
  /** 身份证掩码模式或自定义规则 */
  id_card?: IdCardMaskMode | Partial<MaskRule>;
  /** 手机号掩码规则 */
  phone?: Partial<MaskRule>;
  /** 银行账号掩码规则 */
  bank_card?: Partial<MaskRule>;
  /** 电子邮箱掩码规则 */
  email?: Partial<MaskRule>;
  /** 姓名掩码规则 */
  name?: Partial<MaskRule>;
  /** 自定义高敏字段掩码规则 */
  custom?: Partial<MaskRule>;
  /** 额外扩展字段类型 */
  [key: string]: unknown;
}

/**
 * 解析后的公司掩码规则集合
 */
export interface ResolvedCompanyMaskSettings {
  /** 各字段类型的最终生效规则 */
  rules: Record<SensitiveFieldType, MaskRule>;
  /** 身份证掩码模式 ('standard' 6+4 或 'strict' 3+4) */
  idCardMode: IdCardMaskMode;
  /** 是否应用了公司自定义配置（false 表示使用平台安全默认值） */
  isCustom: boolean;
}

/**
 * 安全约束检验：落实 PRD §6.9 “每类保留的前后位数可调，但不能设为‘不掩码’，不提供关闭掩码的开关”
 *
 * 验证规则并限制：
 * 1. prefix 与 suffix 必须为非负整数；
 * 2. 禁止将 prefix 或 suffix 设得过大以试图完全显示；
 * 3. maskChar 不得为空白。
 */
export function sanitizeMaskRule(
  type: SensitiveFieldType,
  customRule?: Partial<MaskRule> | null
): MaskRule {
  const defaultRule = DEFAULT_MASK_RULES[type] || DEFAULT_MASK_RULES.custom;
  if (!customRule || typeof customRule !== 'object') {
    return { ...defaultRule };
  }

  let prefix = typeof customRule.prefix === 'number' ? Math.floor(customRule.prefix) : defaultRule.prefix;
  let suffix = typeof customRule.suffix === 'number' ? Math.floor(customRule.suffix) : defaultRule.suffix;

  // 1. 拦截负数
  if (prefix < 0) prefix = defaultRule.prefix;
  if (suffix < 0) suffix = defaultRule.suffix;

  // 2. 拦截尝试“不掩码”的越界设置（PRD §6.9 合规防线）
  // 针对不同字段设定合理的保留上限，防止恶意配置 prefix=18, suffix=0 绕过脱敏
  if (type === 'id_card') {
    // 身份证最少保留 3 位掩码，prefix 不得超过 8，suffix 至少 1 且不大于 6
    if (prefix > 8) prefix = 6;
    if (suffix > 6 || suffix < 1) suffix = 4;
  } else if (type === 'phone') {
    // 手机号最少保留 4 位掩码
    if (prefix > 4) prefix = 3;
    if (suffix > 4 || suffix < 1) suffix = 4;
  } else if (type === 'bank_card') {
    // 银行卡严格禁止前缀明文展示，只允许保留后 4 位左右
    prefix = 0;
    if (suffix > 6 || suffix < 1) suffix = 4;
  }

  const maskChar =
    typeof customRule.maskChar === 'string' && customRule.maskChar.trim().length > 0
      ? customRule.maskChar
      : defaultRule.maskChar || '*';

  const fixedLength =
    typeof customRule.fixedLength === 'number' && customRule.fixedLength > 0
      ? Math.floor(customRule.fixedLength)
      : defaultRule.fixedLength;

  return {
    prefix,
    suffix,
    maskChar,
    fixedLength,
  };
}

/**
 * 从原始输入解析公司掩码规则（支持 JSON 字符串、对象或嵌套 settings 格式）
 *
 * @param rawSettings 公司设置输入（可以是完整 settings 对象、sensitive_mask_rules 属性或独立规则对象）
 */
export function extractMaskRulesFromCompanySettings(
  rawSettings?: unknown
): ResolvedCompanyMaskSettings {
  // 1. 安全兜底初始化
  const resolvedRules: Record<SensitiveFieldType, MaskRule> = {
    id_card: { ...DEFAULT_MASK_RULES.id_card },
    phone: { ...DEFAULT_MASK_RULES.phone },
    bank_card: { ...DEFAULT_MASK_RULES.bank_card },
    email: { ...DEFAULT_MASK_RULES.email },
    name: { ...DEFAULT_MASK_RULES.name },
    custom: { ...DEFAULT_MASK_RULES.custom },
  };

  let idCardMode: IdCardMaskMode = 'standard';
  let isCustom = false;

  if (!rawSettings) {
    return { rules: resolvedRules, idCardMode, isCustom: false };
  }

  let parsed: Record<string, unknown> | null = null;

  // 2. 解析 JSON 字符串
  if (typeof rawSettings === 'string') {
    try {
      parsed = JSON.parse(rawSettings);
    } catch {
      // 若字符串为 'strict' 或 'standard'，直接作为身份证模式
      if (rawSettings === 'strict' || rawSettings === 'standard') {
        parsed = { id_card: rawSettings };
      }
    }
  } else if (typeof rawSettings === 'object' && rawSettings !== null) {
    parsed = rawSettings as Record<string, unknown>;
  }

  if (!parsed) {
    return { rules: resolvedRules, idCardMode, isCustom: false };
  }

  // 3. 提取 sensitive_mask_rules 节点（如果传入的是包含公司整体配置的容器）
  const rulesConfig = (
    parsed[COMPANY_MASK_RULES_KEY] && typeof parsed[COMPANY_MASK_RULES_KEY] === 'object'
      ? parsed[COMPANY_MASK_RULES_KEY]
      : parsed.mask_rules && typeof parsed.mask_rules === 'object'
      ? parsed.mask_rules
      : parsed
  ) as Record<string, unknown>;

  // 4. 解析 id_card 专属规则
  if (rulesConfig.id_card) {
    isCustom = true;
    if (rulesConfig.id_card === 'strict') {
      idCardMode = 'strict';
      resolvedRules.id_card = { prefix: 3, suffix: 4, maskChar: '*', fixedLength: undefined };
    } else if (rulesConfig.id_card === 'standard') {
      idCardMode = 'standard';
      resolvedRules.id_card = { prefix: 6, suffix: 4, maskChar: '*', fixedLength: 8 };
    } else if (typeof rulesConfig.id_card === 'object' && rulesConfig.id_card !== null) {
      const customIdCard = rulesConfig.id_card as Partial<MaskRule> & { mode?: IdCardMaskMode };
      if (customIdCard.mode === 'strict' || (customIdCard.prefix === 3 && customIdCard.suffix === 4)) {
        idCardMode = 'strict';
      }
      resolvedRules.id_card = sanitizeMaskRule('id_card', customIdCard);
    }
  }

  // 5. 解析其他字段规则
  const fieldTypes: SensitiveFieldType[] = ['phone', 'bank_card', 'email', 'name', 'custom'];
  for (const field of fieldTypes) {
    if (rulesConfig[field] && typeof rulesConfig[field] === 'object') {
      isCustom = true;
      resolvedRules[field] = sanitizeMaskRule(
        field,
        rulesConfig[field] as Partial<MaskRule>
      );
    }
  }

  return {
    rules: resolvedRules,
    idCardMode,
    isCustom,
  };
}
