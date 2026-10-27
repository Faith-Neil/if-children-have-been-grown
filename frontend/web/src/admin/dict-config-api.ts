// 为什么有这个文件：提供数据字典与状态码表配置的标准化前端 API 交互层（APP-M2-T024 / A-03）。
// 它解决什么问题：
// 1. 对齐 /api/v1/metadata/dict/* 后端契约，支持字典分类调阅、代码项列表、新建、启停用与删除；
// 2. 统一捕获与解析 RFC 7807 统一错误响应（如 DICT_ITEM_IN_USE、DICT_CODE_DUPLICATED、FORBIDDEN）；
// 3. 配合 checkDictPermission 保证前端视图与后端 RBAC 门禁保持双向一致性。

import { request, ApiError } from '../shared/api.ts';

export interface ApiDictTypeItem {
  type_code: string;
  type_name: string;
  scope: string;
  description: string;
  total_items: number;
  active_items: number;
}

export interface ApiDictTypeListResponse {
  total: number;
  items: ApiDictTypeItem[];
}

export interface ApiDictItemModel {
  id: string;
  type_code: string;
  item_code: string;
  label: string;
  description: string;
  sort_order: number;
  is_disabled: boolean;
  in_use: boolean;
  is_builtin: boolean;
  company_id?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ApiDictItemListResponse {
  type_code: string;
  type_name: string;
  total: number;
  items: ApiDictItemModel[];
}

export interface ApiCreateDictItemRequest {
  type_code: string;
  item_code: string;
  label: string;
  description?: string;
  sort_order?: number;
  metadata?: Record<string, unknown> | null;
}

export interface ApiUpdateDictItemRequest {
  label?: string;
  description?: string;
  sort_order?: number;
  is_disabled?: boolean;
  metadata?: Record<string, unknown> | null;
}

export interface ApiDeleteDictItemResponse {
  success: boolean;
  message: string;
  type_code: string;
  item_code: string;
}

/**
 * 调阅所有数据字典分类列表
 */
export async function fetchDictTypes(token: string | null): Promise<ApiDictTypeListResponse> {
  return request<ApiDictTypeListResponse>('/api/v1/metadata/dict/types', token, 'GET');
}

/**
 * 调阅指定分类下的所有代码项列表
 */
export async function fetchDictItems(
  typeCode: string,
  token: string | null,
  options?: { includeDisabled?: boolean; keyword?: string }
): Promise<ApiDictItemListResponse> {
  const params = new URLSearchParams();
  if (options?.includeDisabled !== undefined) {
    params.set('include_disabled', String(options.includeDisabled));
  }
  if (options?.keyword) {
    params.set('keyword', options.keyword);
  }
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return request<ApiDictItemListResponse>(`/api/v1/metadata/dict/types/${typeCode}/items${queryStr}`, token, 'GET');
}

/**
 * 新增自定义字典代码项（需管理员权限，同类型下代码不可重复）
 */
export async function createDictItem(
  payload: ApiCreateDictItemRequest,
  token: string | null
): Promise<ApiDictItemModel> {
  return request<ApiDictItemModel>('/api/v1/metadata/dict/items', token, 'POST', payload);
}

/**
 * 更新字典项属性或切换启停用状态（需管理员权限）
 */
export async function updateDictItem(
  typeCode: string,
  itemCode: string,
  payload: ApiUpdateDictItemRequest,
  token: string | null
): Promise<ApiDictItemModel> {
  return request<ApiDictItemModel>(
    `/api/v1/metadata/dict/items/${typeCode}/${itemCode}`,
    token,
    'PATCH',
    payload
  );
}

/**
 * 物理删除未引用的自定义字典代码项（核心红线：系统内置或已在业务中使用的代码严禁硬删除）
 */
export async function deleteDictItem(
  typeCode: string,
  itemCode: string,
  token: string | null
): Promise<ApiDeleteDictItemResponse> {
  return request<ApiDeleteDictItemResponse>(
    `/api/v1/metadata/dict/items/${typeCode}/${itemCode}`,
    token,
    'DELETE'
  );
}

export { ApiError };
