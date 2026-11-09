// 为什么有这个文件：ISSUE-052 公司开通与顶栏公司名可见性的纯函数。
// 它解决什么问题：平台管理员顶栏不展示公司名；新建公司表单在提交前做本地校验。

import { normalizeSystemRole } from '../shell/route-guard.ts';

export function shouldShowCompanyLabel(role?: string | null): boolean {
  return normalizeSystemRole(role) !== 'platform_admin';
}

/** 展示公司名：优先后台显示名；仅 alpha/beta 保留合成别名。 */
export function resolveCompanyDisplayName(companyId: string, displayName?: string | null): string {
  const named = (displayName || '').trim();
  if (named) return named;
  if (companyId === 'alpha') return '华东数智科技有限公司（合成）';
  if (companyId === 'beta') return '远山信息技术有限公司（合成）';
  return companyId || '未命名公司';
}

export interface CreateCompanyFormValues {
  name: string;
  admin_username: string;
  admin_name: string;
  admin_password: string;
  admin_display_name?: string;
  must_change_password: boolean;
}

export interface CreateCompanyFormIssue {
  field: keyof CreateCompanyFormValues | 'general';
  message: string;
}

export function validateCreateCompanyForm(values: CreateCompanyFormValues): {
  valid: boolean;
  issues: CreateCompanyFormIssue[];
} {
  const issues: CreateCompanyFormIssue[] = [];
  if (!(values.name || '').trim()) {
    issues.push({ field: 'name', message: '请填写公司显示名' });
  }
  if (!(values.admin_username || '').trim()) {
    issues.push({ field: 'admin_username', message: '请填写管理员用户名' });
  }
  if (!(values.admin_name || '').trim()) {
    issues.push({ field: 'admin_name', message: '请填写管理员姓名' });
  }
  if (!(values.admin_password || '').trim()) {
    issues.push({ field: 'admin_password', message: '请填写初始密码' });
  }
  return { valid: issues.length === 0, issues };
}

export interface CreateCompanyResponse {
  company: { id: string; name: string; status: string };
  admin: { id: string; company_id: string; role: string; must_change_password?: boolean };
}

type RequestFn = <T>(path: string, token: string | null, method?: string, body?: unknown) => Promise<T>;

export function createCompany(
  requestFn: RequestFn,
  token: string,
  body: CreateCompanyFormValues,
): Promise<CreateCompanyResponse> {
  return requestFn<CreateCompanyResponse>('/api/v1/companies', token, 'POST', {
    name: body.name.trim(),
    admin_username: body.admin_username.trim(),
    admin_name: body.admin_name.trim(),
    admin_password: body.admin_password,
    admin_display_name: (body.admin_display_name || '').trim() || undefined,
    must_change_password: body.must_change_password !== false,
  });
}

export function companyDetailPath(companyId: string): string {
  return `/admin/companies/${encodeURIComponent(companyId)}`;
}
