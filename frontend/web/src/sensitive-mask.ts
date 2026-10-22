// 为什么有这个文件：落实 PRD v1.8 §5.4.5、§2.3 与 §5.9.1 的高敏个人信息脱敏规则。
// 它解决什么问题：统一提供身份证号（3+4 或 6+4）、手机号（3+4）、银行账号（后 4 位）等高敏字段表格驱动掩码算法、原因校验与防泄漏断言。

/**
 * 敏感字段类型分类
 */
export type SensitiveFieldType =
  | 'id_card'       // 身份证号
  | 'phone'         // 手机号
  | 'bank_card'     // 银行账号
  | 'email'         // 电子邮箱
  | 'name'          // 姓名
  | 'custom';       // 自定义字段

/**
 * 掩码规则配置
 */
export interface MaskRule {
  /** 前部保留明文位数 */
  prefix: number;
  /** 后部保留明文位数 */
  suffix: number;
  /** 掩码替换符号（默认 '*'） */
  maskChar?: string;
  /** 固定掩码字符长度（若不指定则按被掩码字符实际长度补齐） */
  fixedLength?: number;
}

/**
 * 身份证掩码模式
 * - 'standard': 前 6 后 4，中间 8 位掩码（符合 18 位身份证归属地+后4校验标准）
 * - 'strict': 前 3 后 4，中间掩码（PRD §5.4.5 与交接约束 3+4 规范）
 */
export type IdCardMaskMode = 'standard' | 'strict';

/**
 * 表格驱动预置掩码规则表（落实 PRD §5.4.5 与 §6.9）
 */
export const DEFAULT_MASK_RULES: Record<SensitiveFieldType, MaskRule> = {
  id_card: { prefix: 6, suffix: 4, maskChar: '*', fixedLength: 8 },
  phone: { prefix: 3, suffix: 4, maskChar: '*', fixedLength: 4 },
  bank_card: { prefix: 0, suffix: 4, maskChar: '*' },
  email: { prefix: 2, suffix: 0, maskChar: '*', fixedLength: 3 },
  name: { prefix: 1, suffix: 1, maskChar: '*' },
  custom: { prefix: 1, suffix: 1, maskChar: '*' },
};

/**
 * 字段友好显示名称映射
 */
export const SENSITIVE_FIELD_LABELS: Record<SensitiveFieldType, string> = {
  id_card: '身份证号',
  phone: '手机号',
  bank_card: '银行账号',
  email: '电子邮箱',
  name: '姓名',
  custom: '高敏信息',
};

/**
 * 敏感字段掩码主函数
 *
 * @param value 原始明文字符串
 * @param type 敏感字段类别（默认 'id_card'）
 * @param customRule 自定义规则或覆盖项
 */
export function maskSensitiveValue(
  value?: string | null,
  type: SensitiveFieldType = 'id_card',
  customRule?: Partial<MaskRule>
): string {
  if (value === null || value === undefined) return '';
  const str = String(value).trim();
  if (!str) return '';

  const rule: MaskRule = {
    ...DEFAULT_MASK_RULES[type],
    ...(customRule || {}),
  };

  const maskChar = rule.maskChar || '*';

  // 1. 电子邮箱特殊处理
  if (type === 'email') {
    const atIndex = str.indexOf('@');
    if (atIndex > 0) {
      const namePart = str.slice(0, atIndex);
      const domainPart = str.slice(atIndex);
      const prefixLen = Math.min(rule.prefix, namePart.length);
      const maskedName =
        namePart.slice(0, prefixLen) + (rule.fixedLength ? maskChar.repeat(rule.fixedLength) : '***');
      return `${maskedName}${domainPart}`;
    }
  }

  // 2. 姓名特殊处理
  if (type === 'name') {
    if (str.length <= 1) return str;
    if (str.length === 2) return `${str[0]}${maskChar}`;
    return `${str[0]}${maskChar.repeat(str.length - 2)}${str[str.length - 1]}`;
  }

  // 3. 银行账号（只保留后 4 位）
  if (type === 'bank_card' || rule.prefix === 0) {
    const suffixLen = Math.min(rule.suffix, str.length);
    const maskedLen = str.length - suffixLen;
    const maskedPart = maskChar.repeat(maskedLen > 0 ? maskedLen : 4);
    const suffixPart = str.slice(str.length - suffixLen);
    return `${maskedPart}${suffixPart}`;
  }

  // 4. 通用位数处理（身份证、手机号、自定义）
  const { prefix, suffix } = rule;
  const totalLen = str.length;

  // 边界保护：字符串长度不足以支撑前后保留位数
  if (totalLen <= prefix + suffix) {
    if (totalLen <= 2) return maskChar.repeat(totalLen);
    return `${str[0]}${maskChar.repeat(totalLen - 2)}${str[totalLen - 1]}`;
  }

  const prefixPart = str.slice(0, prefix);
  const suffixPart = str.slice(totalLen - suffix);
  const middleLen = rule.fixedLength ?? (totalLen - prefix - suffix);
  const middlePart = maskChar.repeat(middleLen > 0 ? middleLen : 1);

  return `${prefixPart}${middlePart}${suffixPart}`;
}

/**
 * 身份证号专属掩码函数（支持标准 6+4 与严格 3+4 模式）
 */
export function maskIdCard(value?: string | null, mode: IdCardMaskMode = 'standard'): string {
  if (mode === 'strict') {
    return maskSensitiveValue(value, 'id_card', { prefix: 3, suffix: 4, fixedLength: undefined });
  }
  return maskSensitiveValue(value, 'id_card', { prefix: 6, suffix: 4, fixedLength: 8 });
}

/**
 * 手机号专属掩码函数（前 3 后 4，中间 4 位）
 */
export function maskPhone(value?: string | null): string {
  return maskSensitiveValue(value, 'phone');
}

/**
 * 银行账号专属掩码函数（只保留后 4 位）
 */
export function maskBankCard(value?: string | null): string {
  return maskSensitiveValue(value, 'bank_card');
}

/**
 * 查看原因强校验（必须填写且不可为空白）
 *
 * @param reason 用户输入的查看原因
 * @param minLength 最少字数要求（默认 5 个字）
 */
export function validateRevealReason(
  reason?: string | null,
  minLength = 5
): { valid: boolean; message?: string } {
  if (!reason || typeof reason !== 'string') {
    return { valid: false, message: '请填写查看原因（必填项，不可为空白）' };
  }

  const clean = reason.trim();
  if (clean.length === 0) {
    return { valid: false, message: '查看原因不可全为空白字符，请详细说明调阅理由' };
  }

  if (clean.length < minLength) {
    return {
      valid: false,
      message: `查看原因字数不足（当前 ${clean.length} 字，至少需 ${minLength} 字），请详细说明具体业务调阅需要`,
    };
  }

  return { valid: true };
}

/**
 * 安全合规断言：验证敏感高敏明文绝对没有被写入任何持久化媒介或 URL
 *
 * @param plaintext 完整敏感明文
 * @param targets 检查目标环境对象
 */
export function assertNoSensitiveLeak(
  plaintext?: string | null,
  targets?: {
    localStorage?: Pick<Storage, 'getItem' | 'length' | 'key'> | null;
    sessionStorage?: Pick<Storage, 'getItem' | 'length' | 'key'> | null;
    url?: string | null;
  }
): { safe: boolean; leakLocation?: string } {
  if (!plaintext || plaintext.trim().length === 0) return { safe: true };
  const target = plaintext.trim();

  // 1. 检查 URL
  if (targets?.url && targets.url.includes(target)) {
    return { safe: false, leakLocation: 'url' };
  }

  // 2. 检查 localStorage
  if (targets?.localStorage) {
    const ls = targets.localStorage;
    const count = ls.length || 0;
    for (let i = 0; i < count; i++) {
      const key = ls.key(i);
      if (key) {
        const val = ls.getItem(key);
        if (val && val.includes(target)) {
          return { safe: false, leakLocation: `localStorage:${key}` };
        }
      }
    }
  }

  // 3. 检查 sessionStorage
  if (targets?.sessionStorage) {
    const ss = targets.sessionStorage;
    const count = ss.length || 0;
    for (let i = 0; i < count; i++) {
      const key = ss.key(i);
      if (key) {
        const val = ss.getItem(key);
        if (val && val.includes(target)) {
          return { safe: false, leakLocation: `sessionStorage:${key}` };
        }
      }
    }
  }

  return { safe: true };
}
