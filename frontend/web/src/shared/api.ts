// 为什么有这个文件：让页面操作实际发到同一后台并统一处理失败。
// 它解决什么问题：保留公司登录、旧版本保护、重复请求标记与真实文件下载。
export class ApiError extends Error {
  status: number; code: string; requestId?: string; details?: Record<string, unknown>;
  constructor(status: number, code: string, message: string, requestId?: string, details?: Record<string, unknown>) {
    super(message); this.status = status; this.code = code; this.requestId = requestId; this.details = details;
  }
}

export const retryLimit = 3;

// 错误来源只留在私有映射，不把令牌放进可序列化错误或用户提示。
const failureSession = new WeakMap<object, string | null>();

export function isRequestFailureCurrent(error: unknown, currentToken: string | null): boolean {
  return !error || typeof error !== 'object' || !failureSession.has(error)
    || failureSession.get(error) === currentToken;
}

function rememberFailureSession(error: unknown, token: string | null): never {
  if (error && typeof error === 'object') failureSession.set(error, token);
  throw error;
}

export function canRetryStatus(status: number, code?: string) {
  if (status === 503) return code !== 'SECRET_KEY_UNAVAILABLE';
  if (status !== 502) return false;
  return !code || code === 'REQUEST_FAILED';
}

export function userFacingMessage(error: unknown) {
  if (error instanceof ApiError) return error.requestId ? `${error.message}（追踪号 ${error.requestId}）` : error.message;
  return error instanceof Error && error.message ? error.message : '操作失败，请稍后重试。';
}

function textField(source: Record<string, unknown> | null, key: string) {
  const value = source?.[key];
  return typeof value === 'string' && value ? value : undefined;
}

export function apiFailure(status: number, data: unknown, headerId?: string) {
  const body = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  const nested = body.error && typeof body.error === 'object' ? body.error as Record<string, unknown> : null;
  // 严格优先解构规范体 {code, message, details, traceId}，旧结构 {error, request_id} 仅作兼容兜底
  const code = textField(body, 'code') ?? textField(nested, 'code') ?? 'REQUEST_FAILED';
  const message = textField(body, 'message') ?? textField(nested, 'message') ?? '操作失败，请稍后重试。';
  const requestId = headerId || textField(body, 'traceId') || textField(body, 'request_id');
  const details = body.details && typeof body.details === 'object'
    ? body.details as Record<string, unknown>
    : nested?.details && typeof nested.details === 'object' ? nested.details as Record<string, unknown> : undefined;
  return new ApiError(status, code, message, requestId, details);
}

function defaultWait(ms: number) {
  return new Promise<void>(resolve => { setTimeout(resolve, ms); });
}

async function runAttempts<T>(action: () => Promise<T>, wait: (ms: number) => Promise<void>, allowRetry = true) {
  let last: unknown;
  for (let attempt = 0; attempt < retryLimit; attempt += 1) {
    try {
      return await action();
    } catch (error) {
      last = error;
      const eligible = error instanceof ApiError ? canRetryStatus(error.status, error.code) : error instanceof TypeError;
      if (!allowRetry || !eligible || attempt === retryLimit - 1) throw error;
      await wait(200 * 2 ** attempt);
    }
  }
  throw last;
}

async function readJson(response: Response) {
  return response.json().catch(() => ({}));
}

function isChapterVersionWrite(path: string, method: string) {
  if (method === 'GET') return false;
  const bare = path.split(/[?#]/, 1)[0];
  return /^\/api\/chapters\/[^/]+\/versions$/.test(bare);
}

function chapterVersionPayload(body: unknown) {
  const source = body && typeof body === 'object' && !Array.isArray(body) ? { ...(body as Record<string, unknown>) } : {};
  const supplied = source.idempotency_key;
  const key = typeof supplied === 'string' && supplied ? supplied : crypto.randomUUID();
  source.idempotency_key = key;
  return { key, body: source };
}

export async function request<T>(path: string, token: string | null, method = 'GET', body?: unknown, revision?: number, wait: (ms: number) => Promise<void> = defaultWait): Promise<T> {
  const version = isChapterVersionWrite(path, method) ? chapterVersionPayload(body) : undefined;
  const outbound = version ? version.body : body;
  const idempotencyKey = version?.key ?? (method !== 'GET' && path.startsWith('/api/v1/') ? crypto.randomUUID() : undefined);
  const allowRetry = method === 'GET' || idempotencyKey !== undefined;
  return runAttempts(async () => {
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (outbound !== undefined) headers['Content-Type'] = 'application/json';
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    if (method !== 'GET' && path.startsWith('/api/v1/') && revision !== undefined) headers['If-Match'] = String(revision);
    const response = await fetch(path, { method, headers, body: outbound !== undefined ? JSON.stringify(outbound) : undefined, cache: 'no-store' });
    const data = await readJson(response);
    if (!response.ok) throw apiFailure(response.status, data, response.headers.get('X-Request-ID') ?? undefined);
    return data as T;
  }, wait, allowRetry).catch(error => rememberFailureSession(error, token));
}

export async function download(path: string, token: string, filename: string, wait: (ms: number) => Promise<void> = defaultWait) {
  const response = await runAttempts(async () => {
    const result = await fetch(path, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
    if (!result.ok) throw apiFailure(result.status, await readJson(result), result.headers.get('X-Request-ID') ?? undefined);
    return result;
  }, wait).catch(error => rememberFailureSession(error, token));
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement('a'); link.href = objectUrl; link.download = filename; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

/** 带身份读取原件字节（如在页面内用 PDF.js 显示招标原件），失败按统一错误处理。 */
export async function fetchBytes(path: string, token: string, wait: (ms: number) => Promise<void> = defaultWait): Promise<Uint8Array> {
  const response = await runAttempts(async () => {
    const result = await fetch(path, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
    if (!result.ok) throw apiFailure(result.status, await readJson(result), result.headers.get('X-Request-ID') ?? undefined);
    return result;
  }, wait).catch(error => rememberFailureSession(error, token));
  return new Uint8Array(await response.arrayBuffer());
}

export async function encodeFile(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = '';
  for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
  return btoa(binary);
}

// 全应用统一上传上限（与后台 ICG_MAX_UPLOAD_MB 默认值一致，后台仍会再核一次）。
export const MAX_UPLOAD_MB = 100;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

export function uploadTooLarge(file: { size: number }): string | null {
  return file.size > MAX_UPLOAD_BYTES ? `单个文件不能超过 ${MAX_UPLOAD_MB}MB（当前 ${(file.size / 1024 / 1024).toFixed(1)}MB）。` : null;
}

export function rawUploadPath(path: string, params: Record<string, string>): string {
  const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''));
  return `${path}?${query.toString()}`;
}

// 大文件二进制直传：请求体就是文件本身，不先转 base64（100MB 文件不再在浏览器里拼出 134MB 字符串）。
export async function uploadRaw<T>(path: string, token: string | null, file: Blob, revision?: number): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': crypto.randomUUID() };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (revision !== undefined) headers['If-Match'] = String(revision);
  const response = await fetch(path, { method: 'POST', headers, body: file, cache: 'no-store' });
  const data = await readJson(response);
  if (!response.ok) throw rememberFailureSession(apiFailure(response.status, data, response.headers.get('X-Request-ID') ?? undefined), token);
  return data as T;
}
