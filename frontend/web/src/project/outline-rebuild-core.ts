// 为什么有这个文件：目录模型编排失败时的前端判定与重跑编排纯逻辑单源。
// 它解决什么问题：
// 1. rule_fallback 规则兜底目录绝不能伪装成可用模型目录，失败状态与原因必须可判定、可上浮；
// 2. 「重新生成目录」按钮的重跑编排（调接口→按响应判定→刷新工作台）可脱离组件独立测试；
// 3. 重跑权限与后端 tender_orchestrator.rebuild_technical_outline_model 保持一致（平台/本公司管理员）。

import { normalizeSystemRole } from '../shared/roles.ts';

/** 后端既有的模型目录重跑端点（POST，无请求体；响应 200 也可能仍是失败态，需看 tree_model_failed）。 */
export function rebuildOutlineModelPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/technical-outline/rebuild-model`;
}

export type OutlineFailureInput = {
  outline_source?: string;
  tree_model_failed?: boolean;
  outline_reason?: string;
  technical_outline?: { outline_source?: string; tree_model_failed?: boolean; outline_reason?: string } | null;
};

export type OutlineFailureState = {
  failed: boolean;
  source: string;
  reason: string;
};

/** 后端未给出具体原因时的兜底说明（与 technical_digest_outline.MODEL_FAILED 对齐）。 */
export const OUTLINE_MODEL_FAILED_GENERIC = '模型拟目录失败，已用规则目录。';

/**
 * 判定技术目录是否处于模型编排失败态。
 * 只认后端明确写下的失败信号：tree_model_failed 或 outline_source 为 rule_fallback；
 * 「模型正在编排目录」这类 rule 过渡态不算失败，不给重跑按钮。
 */
export function outlineFailureState(input: OutlineFailureInput): OutlineFailureState {
  const outline = input.technical_outline ?? null;
  const source = input.outline_source || outline?.outline_source || '';
  const failed = Boolean(
    input.tree_model_failed
    || outline?.tree_model_failed
    || source === 'rule_fallback',
  );
  const raw = outline?.outline_reason || input.outline_reason || '';
  const reason = raw.trim() || (failed ? OUTLINE_MODEL_FAILED_GENERIC : '');
  return { failed, source, reason };
}

/**
 * 重跑模型目录的前端权限预判，与后端一致：平台管理员，或本公司管理员。
 * 后端仍会再核一次（403 FORBIDDEN），这里只决定按钮是否出现。
 */
export function canRebuildOutlineModel(
  user: { role?: string | null; company_id?: string | null } | null | undefined,
  projectCompanyId?: string | null,
): boolean {
  if (!user) return false;
  const role = normalizeSystemRole(user.role);
  if (role === 'platform_admin') return true;
  return role === 'company_admin' && !!projectCompanyId && user.company_id === projectCompanyId;
}

/** rebuild-model 端点响应体（200 也可能 ok=false：模型重跑后仍失败）。 */
export type OutlineRebuildResponse = {
  ok?: boolean;
  revision?: number;
  outline_source?: string;
  tree_model_failed?: boolean;
  outline_reason?: string;
  headings?: number;
};

export type OutlineRebuildOutcome =
  | { kind: 'success'; message: string }
  | { kind: 'still-failed'; message: string };

/** 解读重跑响应：只有 ok 且不再处于失败态才算恢复；其余保留后端原因，绝不假装成功。 */
export function rebuildOutcome(result: OutlineRebuildResponse): OutlineRebuildOutcome {
  if (result.ok === true && !result.tree_model_failed) {
    return { kind: 'success', message: '模型目录已重新生成。' };
  }
  const reason = typeof result.outline_reason === 'string' ? result.outline_reason.trim() : '';
  return { kind: 'still-failed', message: reason || '模型重跑后目录仍是规则兜底。' };
}

export type OutlineRebuildRunResult = {
  kind: 'success' | 'still-failed' | 'error';
  message: string;
  /** 工作台是否已刷新到最新状态；HTTP 错误时不刷新（状态没变），200 后无论成败都刷新。 */
  reloaded: boolean;
  error?: unknown;
};

function defaultErrorMessage(error: unknown): string {
  return error instanceof Error && error.message ? error.message : '重新生成目录失败，请稍后重试。';
}

/**
 * 「重新生成目录」按钮的完整编排：先调重跑接口，再按响应解释成败；
 * 只要请求到达了服务端（HTTP 200），无论恢复与否都必须刷新工作台——
 * 服务端即便失败也会重写 failure 原因与 revision，不刷新就会展示过期状态。
 */
export async function runOutlineRebuild(
  projectId: string,
  deps: {
    post: (path: string) => Promise<OutlineRebuildResponse>;
    reload: () => Promise<unknown>;
    errorMessage?: (error: unknown) => string;
  },
): Promise<OutlineRebuildRunResult> {
  let result: OutlineRebuildResponse;
  try {
    result = await deps.post(rebuildOutlineModelPath(projectId));
  } catch (error) {
    const message = (deps.errorMessage ?? defaultErrorMessage)(error);
    return { kind: 'error', message, reloaded: false, error };
  }
  const outcome = rebuildOutcome(result);
  let reloaded = true;
  try {
    await deps.reload();
  } catch {
    reloaded = false;
  }
  return { kind: outcome.kind, message: outcome.message, reloaded };
}
