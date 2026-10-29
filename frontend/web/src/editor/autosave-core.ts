// 为什么有这个文件：编辑台自动保存与编辑锁心跳的纯计算部分（PRD v1.8 §5.11.9；APP-M2-T172）。
// 它解决什么问题：停止输入 2 秒后、以及每隔公司设置的间隔自动保存草稿；只有用户有操作时才发心跳；
// 锁在无操作时按公司设置超时释放，释放前 5 分钟提示。三个间隔取公司设置，缺省或越界时用平台默认值。

export type EditorTimings = { autosaveMs: number; heartbeatMs: number; timeoutMs: number };

export const IDLE_SAVE_MS = 2000;
export const WARN_BEFORE_MS = 5 * 60_000;
const DEFAULTS = { autosave: 10, heartbeat: 60, timeout: 30 };

function clamp(value: unknown, min: number, max: number, fallback: number): number {
  const n = typeof value === 'number' && Number.isFinite(value) ? value : fallback;
  return Math.min(max, Math.max(min, n));
}

/** 公司设置 → 毫秒；范围与后台校验一致：自动保存 5～60 秒，心跳 15～120 秒，超时 6～60 分钟。 */
export function editorTimings(settings?: { editor_autosave_seconds?: number; edit_lock_heartbeat_seconds?: number; edit_lock_timeout_minutes?: number } | null): EditorTimings {
  const autosave = clamp(settings?.editor_autosave_seconds, 5, 60, DEFAULTS.autosave);
  const heartbeat = clamp(settings?.edit_lock_heartbeat_seconds, 15, 120, DEFAULTS.heartbeat);
  const timeout = clamp(settings?.edit_lock_timeout_minutes, 6, 60, DEFAULTS.timeout);
  return { autosaveMs: autosave * 1000, heartbeatMs: heartbeat * 1000, timeoutMs: timeout * 60_000 };
}

export function shouldAutosave(state: { held: boolean; dirty: boolean; saving: boolean; paused: boolean; busy: boolean }): boolean {
  return state.held && state.dirty && !state.saving && !state.paused && !state.busy;
}

/** 心跳只在上次心跳之后有过操作时发送（无操作不续期，锁按超时自然释放）。 */
export function shouldHeartbeat(lastActivityMs: number, lastHeartbeatMs: number): boolean {
  return lastActivityMs > lastHeartbeatMs;
}

/** 剩余不到 5 分钟时返回剩余分钟数（向上取整，至少 1），否则 null。 */
export function expiryWarning(expiresAt: string | null | undefined, nowMs: number): number | null {
  if (!expiresAt) return null;
  const left = Date.parse(expiresAt) - nowMs;
  if (!Number.isFinite(left) || left <= 0 || left > WARN_BEFORE_MS) return null;
  return Math.max(1, Math.ceil(left / 60_000));
}

export function savedLabel(date: Date, auto: boolean): string {
  return `${date.toLocaleTimeString('zh-CN', { hour12: false })}${auto ? ' 自动' : ''}`;
}
