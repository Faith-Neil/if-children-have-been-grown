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
