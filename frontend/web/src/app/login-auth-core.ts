// 为什么有这个文件：账号密码登录的表单校验、请求与错误文案纯逻辑。
// 它解决什么问题：登录只走 POST /api/v1/auth/login；前端不内置任何账号口令，不做离线回退、不签发本地令牌。

import { ApiError, request } from '../shared/api.ts';
import type { Account } from '../shared/types.ts';

export interface LoginFormValues {
  username?: string;
  password?: string;
}

export interface LoginFormValidationResult {
  valid: boolean;
  field?: 'username' | 'password';
  message?: string;
}

export function validateLoginForm(values: LoginFormValues): LoginFormValidationResult {
  if (!values.username?.trim()) return { valid: false, field: 'username', message: '请输入用户名' };
  if (!values.password || !values.password.trim()) return { valid: false, field: 'password', message: '请输入登录密码' };
  return { valid: true };
}

/** 账号密码登录，返回访问令牌。失败如实抛出后端错误（401 凭据错误、423 账号锁定等）。 */
export async function authenticateUser(
  username: string,
  password: string,
  requestFn: typeof request = request,
): Promise<string> {
  const validation = validateLoginForm({ username, password });
  if (!validation.valid) throw new Error(validation.message || '登录表单填写有误');
  const res = await requestFn<{ access_token: string; token_type?: string; user?: Account }>(
    '/api/v1/auth/login', null, 'POST', { username: username.trim(), password },
  );
  if (!res?.access_token) throw new Error('登录响应缺少访问令牌，请联系管理员。');
  return res.access_token;
}

export interface PasswordPolicy {
  min_length: number;
  min_char_classes: number;
  char_classes: string[];
  scope: 'platform' | 'company';
  must_change_password?: boolean | null;
}

export interface PasswordLoginResult {
  token: string;
  mustChangePassword: boolean;
  policy: PasswordPolicy | null;
}

/** 账号密码登录，带回是否须先改密（APP-M2-T260）。须改密时令牌只能用于改密、读密码规则和注销。 */
export async function passwordLogin(
  username: string,
  password: string,
  requestFn: typeof request = request,
): Promise<PasswordLoginResult> {
  const validation = validateLoginForm({ username, password });
  if (!validation.valid) throw new Error(validation.message || '登录表单填写有误');
  const res = await requestFn<{ access_token: string; must_change_password?: boolean; password_policy?: PasswordPolicy | null }>(
    '/api/v1/auth/login', null, 'POST', { username: username.trim(), password },
  );
  if (!res?.access_token) throw new Error('登录响应缺少访问令牌，请联系管理员。');
  return { token: res.access_token, mustChangePassword: res.must_change_password === true, policy: res.password_policy ?? null };
}

export async function changeOwnPassword(
  token: string,
  oldPassword: string,
  newPassword: string,
  requestFn: typeof request = request,
): Promise<void> {
  await requestFn('/api/v1/auth/password', token, 'POST', { old_password: oldPassword, new_password: newPassword });
}

/** 退出登录时让服务端令牌作废；失败不阻止本地退出。 */
export async function revokeSession(token: string | null, requestFn: typeof request = request): Promise<void> {
  if (!token) return;
  try { await requestFn('/api/v1/auth/logout', token, 'POST'); } catch { /* 令牌可能已失效 */ }
}

export interface Branding { product_name: string; logo_horizontal_url?: string | null }

export async function fetchBranding(requestFn: typeof request = request): Promise<Branding | null> {
  try { return await requestFn<Branding>('/api/v1/branding', null); } catch { return null; }
}

export function formatLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return error.message || '用户名或密码错误，请核实后重试';
    if (error.status === 423) return error.message || '账号已被锁定，请联系管理员解锁';
    if (error.status === 403) return error.message || '当前账号无权登录本系统，请联系管理员';
    return error.message || '登录服务暂时不可用，请稍后重试';
  }
  if (error instanceof TypeError) return '无法连接服务器，请检查网络后重试';
  if (error instanceof Error && error.message) return error.message;
  return '登录失败，请核实账号与密码';
}
