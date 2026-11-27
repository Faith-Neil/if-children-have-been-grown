// 为什么有这个文件：编辑台来源指纹过期的识别与恢复重试纯逻辑（ISSUE-059 组2e，追踪号 056a411dff69418f92eafbed9649791b）。
// 它解决什么问题：
// 1. 项目级输入指纹涵盖全项目章节正文/版本，任何章节生成、提交或保存成功都会使其变化，
//    编辑器持有的旧指纹在保存/提交时被后端 409 INPUT_FINGERPRINT_STALE / REQUIRED 拒绝；
// 2. 识别这类拒绝（它们不是章节版本冲突，不能进入 OCC 合并流程，而是走来源刷新恢复）；
// 3. 恢复动作的统一编排：先拉取最新项目指纹，再用新指纹原样重试用户当前草稿内容的写入——
//    绝不改写、替换或丢弃用户文字；章节版本冲突由写入路径内部落入既有合并流程（handed-off）。

import { ApiError } from '../shared/api.ts';

export const INPUT_FINGERPRINT_ERROR_CODES = new Set(['INPUT_FINGERPRINT_REQUIRED', 'INPUT_FINGERPRINT_STALE']);

/** 判定错误是否为来源指纹缺失/过期。这两类 409 不是版本冲突，不能进入正文合并流程。 */
export function isInputFingerprintError(error: unknown): boolean {
  if (error instanceof ApiError) return INPUT_FINGERPRINT_ERROR_CODES.has(error.code);
  const code = (error as { code?: unknown } | null | undefined)?.code;
  return typeof code === 'string' && INPUT_FINGERPRINT_ERROR_CODES.has(code);
}

export type FingerprintWriteTarget = 'draft' | 'commit';

export interface FingerprintRecoveryState {
  target: FingerprintWriteTarget;
  message: string;
}

export type FingerprintRecoveryOutcome =
  | { status: 'saved'; fingerprint: string | null }
  | { status: 'handed-off'; fingerprint: string | null }
  | { status: 'write-error'; fingerprint: string | null; error: unknown }
  | { status: 'fetch-error'; error: unknown };

/**
 * 恢复重试编排：
 * 1. fetchFingerprint 拉取服务端最新项目指纹；拉取失败不尝试写入（status: fetch-error）；
 * 2. write 用新指纹原样重试当前编辑器内容；write 返回 false 表示写入已被其他流程接管
 *    （章节切换 epoch 失效，或章节 revision 冲突已进入既有合并流程），恢复入口随之关闭；
 * 3. write 抛错（含指纹再次过期）如实上抛给调用方走统一错误提示。
 * 无论是 saved / handed-off / write-error，只要拿到了新指纹都回传，调用方应采纳——
 * 它是当时服务端的真实项目指纹，比编辑器持有的任何旧值都新。
 */
export async function recoverFingerprintedWrite(args: {
  fetchFingerprint: () => Promise<string | null>;
  write: (fingerprint: string | null) => Promise<boolean>;
}): Promise<FingerprintRecoveryOutcome> {
  let fingerprint: string | null;
  try {
    fingerprint = await args.fetchFingerprint();
  } catch (error) {
    return { status: 'fetch-error', error };
  }
  try {
    const saved = await args.write(fingerprint);
    return { status: saved ? 'saved' : 'handed-off', fingerprint };
  } catch (error) {
    return { status: 'write-error', fingerprint, error };
  }
}
