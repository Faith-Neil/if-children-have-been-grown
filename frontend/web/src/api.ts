// 为什么有这个文件：让页面操作实际发到同一后台并统一处理失败。
// 它解决什么问题：保留公司登录、旧版本保护、重复请求标记与真实文件下载。
export class ApiError extends Error {
  status: number; code: string; requestId?: string; details?: Record<string, unknown>;
  constructor(status: number, code: string, message: string, requestId?: string, details?: Record<string, unknown>) {
    super(message); this.status = status; this.code = code; this.requestId = requestId; this.details = details;
  }
}

export async function request<T>(path: string, token: string | null, method = 'GET', body?: unknown, revision?: number): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && path.startsWith('/api/v1/')) {
    headers['Idempotency-Key'] = crypto.randomUUID();
    if (revision !== undefined) headers['If-Match'] = String(revision);
  }
  const response = await fetch(path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined, cache: 'no-store' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data.error?.code ?? data.code ?? 'REQUEST_FAILED', data.error?.message ?? data.message ?? '操作失败，请稍后重试。', data.request_id ?? data.traceId, data.details ?? data.error?.details);
  return data as T;
}

export async function download(path: string, token: string, filename: string) {
  const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.error?.code ?? data.code ?? 'DOWNLOAD_FAILED', data.error?.message ?? data.message ?? '下载失败，请重新检查。');
  }
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement('a'); link.href = objectUrl; link.download = filename; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function encodeFile(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = '';
  for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
  return btoa(binary);
}
