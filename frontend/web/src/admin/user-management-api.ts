// 为什么有这个文件：提供用户管理与停用资产交接的标准化前端 API 交互胶水层（APP-M2-T027 / INT-USER-TRANSFER-RBAC-GLUE）。
// 它解决什么问题：
// 1. 对齐 /api/v1/users 相关后端契约，支持用户列表检索、单体详情、新增用户与信息更新；
// 2. 统一捕获与解析 RFC 7807 统一错误模型（如 USER_TRANSFER_REQUIRED、PASSWORD_WEAK、FORBIDDEN、NOT_FOUND）；
// 3. 在账号停用时传递 successor_user_id，配合后端完成资产交接与账号停用闭环。

import { request, ApiError } from '../shared/api.ts';

export interface ApiUserModel {
  id: string;
  name: string;
  display_name: string;
  company_id: string;
  role: string;
  status: 'active' | 'disabled';
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ApiUserListResponse {
  total: number;
  items: ApiUserModel[];
}

export interface ApiCreateUserRequest {
  username: string;
  name: string;
  company_id: string;
  role: string;
  password: string;
  display_name?: string | null;
}

export interface ApiUpdateUserRequest {
  name?: string | null;
  display_name?: string | null;
  role?: string | null;
  status?: 'active' | 'disabled' | null;
  successor_user_id?: string | null;
}

export interface ApiTransferUserAssetsRequest {
  successor_user_id: string;
}

export interface ApiTransferUserAssetsResponse {
  success: boolean;
  from_user_id: string;
  successor_user_id: string;
  transferred_projects: Array<{
    project_id: string;
    project_name: string;
    transferred_role: string;
  }>;
  message: string;
}

/**
 * 调阅用户列表
 */
export async function fetchUsers(
  options?: { companyId?: string; role?: string; status?: string; keyword?: string },
  token?: string | null
): Promise<ApiUserListResponse> {
  const params = new URLSearchParams();
  if (options?.companyId) params.set('company_id', options.companyId);
  if (options?.role) params.set('role', options.role);
  if (options?.status) params.set('status', options.status);
  if (options?.keyword) params.set('keyword', options.keyword);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return request<ApiUserListResponse>(`/api/v1/users${queryStr}`, token ?? null, 'GET');
}

/**
 * 获取指定用户详情
 */
export async function fetchUser(userId: string, token?: string | null): Promise<ApiUserModel> {
  return request<ApiUserModel>(`/api/v1/users/${encodeURIComponent(userId)}`, token ?? null, 'GET');
}

/**
 * 新增用户（执行 Q28 定案密码强度校验）
 */
export async function createUser(
  payload: ApiCreateUserRequest,
  token?: string | null
): Promise<ApiUserModel> {
  return request<ApiUserModel>('/api/v1/users', token ?? null, 'POST', payload);
}

/**
 * 更新用户属性或执行停用（带交接接收人）
 */
export async function updateUser(
  userId: string,
  payload: ApiUpdateUserRequest,
  token?: string | null
): Promise<ApiUserModel> {
  return request<ApiUserModel>(
    `/api/v1/users/${encodeURIComponent(userId)}`,
    token ?? null,
    'PATCH',
    payload
  );
}

/**
 * 独立转交名下在投项目资产
 */
export async function transferUserAssets(
  userId: string,
  payload: ApiTransferUserAssetsRequest,
  token?: string | null
): Promise<ApiTransferUserAssetsResponse> {
  return request<ApiTransferUserAssetsResponse>(
    `/api/v1/users/${encodeURIComponent(userId)}/transfer`,
    token ?? null,
    'POST',
    payload
  );
}
