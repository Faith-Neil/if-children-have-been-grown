// 为什么有这个文件：首次登录与被重置后强制修改密码的表单规则（APP-M2-T260 / PRD v1.8 §5.12.1 规则 3、验收⑧）。
// 它解决什么问题：页面就近提示缺少哪一项，判断口径与服务端 icg/domain/auth_service.py 的 password_problems 一致：
// 只认 ASCII 大写、小写、数字和其他可打印 ASCII 符号；空格、中文允许但不计入任何一类。

import type { PasswordPolicy } from './login-auth-core.ts';

export const DEFAULT_POLICY: PasswordPolicy = {
  min_length: 8, min_char_classes: 3, char_classes: ['大写字母', '小写字母', '数字', '符号'], scope: 'platform',
};

const CLASS_ORDER = [['upper', '大写字母'], ['lower', '小写字母'], ['digit', '数字'], ['symbol', '符号']] as const;
type CharClass = typeof CLASS_ORDER[number][0];

export function charClasses(password: string): Set<CharClass> {
  const found = new Set<CharClass>();
  for (const c of password) {
    if (c >= 'A' && c <= 'Z') found.add('upper');
    else if (c >= 'a' && c <= 'z') found.add('lower');
    else if (c >= '0' && c <= '9') found.add('digit');
    else if (c >= '!' && c <= '~') found.add('symbol');
  }
  return found;
}

/** 与服务端相同措辞的逐项问题；空数组表示满足。 */
export function passwordProblems(password: string, policy: PasswordPolicy = DEFAULT_POLICY): string[] {
  const problems: string[] = [];
  const length = [...password].length;
  if (length < policy.min_length) problems.push(`至少 ${policy.min_length} 位（现 ${length} 位）`);
  const found = charClasses(password);
  if (found.size < policy.min_char_classes) {
    const missing = CLASS_ORDER.filter(([key]) => !found.has(key)).map(([, label]) => label).join('、');
    problems.push(`大写字母、小写字母、数字、符号中至少含 ${policy.min_char_classes} 类（现 ${found.size} 类，缺少${missing}）`);
  }
  return problems;
}

export function policyText(policy: PasswordPolicy): string {
  return `至少 ${policy.min_length} 位，大写字母、小写字母、数字、符号中至少含 ${policy.min_char_classes} 类`;
}

export interface PasswordChangeForm { oldPassword: string; newPassword: string; confirmPassword: string }

export interface PasswordChangeCheck { ok: boolean; field?: keyof PasswordChangeForm; problems: string[] }

export function checkPasswordChange(form: PasswordChangeForm, policy: PasswordPolicy = DEFAULT_POLICY): PasswordChangeCheck {
  if (!form.oldPassword) return { ok: false, field: 'oldPassword', problems: ['请输入当前密码'] };
  const problems = passwordProblems(form.newPassword, policy);
  if (form.newPassword && form.newPassword === form.oldPassword) problems.push('不能与当前密码相同');
  if (problems.length) return { ok: false, field: 'newPassword', problems };
  if (form.confirmPassword !== form.newPassword) return { ok: false, field: 'confirmPassword', problems: ['两次输入的新密码不一致'] };
  return { ok: true, problems: [] };
}
