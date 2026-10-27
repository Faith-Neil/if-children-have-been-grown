// 为什么有这个文件：提供非演示模式下基于账号密码凭据认证的前端 API 层（FE-LOGIN-ACCOUNT-PASSWORD / BE-AUTH-SUPER-ADMIN）。
// 它解决什么问题：
// 1. 对齐 /api/v1/auth/login 后端契约，支持超管与正式账号密码认证；
// 2. 统一捕获与解析 RFC 7807 统一错误响应（如 401 INVALID_CREDENTIALS）；
// 3. 成功后直接返回规范 Access Token 与 Account 信息，无缝衔接可信会话加载。

import { request, ApiError } from './api.ts';
import type { Account } from './types.ts';

export interface AuthLoginRequest {
  username: string;
  password: string;
}

export interface AuthLoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: Account;
}

/**
 * 账号密码登录认证接口 (POST /api/v1/auth/login)
 */
export async function loginWithCredentials(
  username: string,
  password: string
): Promise<AuthLoginResponse> {
  return request<AuthLoginResponse>('/api/v1/auth/login', null, 'POST', {
    username: username.trim(),
    password,
  });
}

export { ApiError };
