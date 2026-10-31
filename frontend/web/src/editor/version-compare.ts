// 为什么有这个文件：编辑台版本对比与回退的纯计算（APP-M2-T175，PRD v1.8 §5.11.9）。
// 它解决什么问题：按段落键把两个版本逐段对上，标出未改、改动、新增、删除；改动段落再逐字标出增删；
// 版本列表显示每个版本的修改方式（手改、对话助手替换/插入、章节循环修正、系统生成、版本回退等）。

import type { ParagraphKey } from './paragraph-keys.ts';
import { diffText, type DiffPart } from './selection-rewrite-core.ts';

export type VersionRecord = {
  revision: number; content: string; actor_id: string; created_at: string;
  paragraphs?: ParagraphKey[]; version_origin?: string | null; edit_mode?: string | null;
  source?: string | null; rollback_from?: number | null; note?: string | null;
};

export type ParagraphChange =
  | { kind: 'same'; key: string; text: string }
  | { kind: 'changed'; key: string; before: string; after: string; parts: DiffPart[] }
  | { kind: 'added'; key: string; text: string }
  | { kind: 'removed'; key: string; text: string };

function texts(version: VersionRecord): Map<string, string> {
  const lines = version.content.split('\n');
  return new Map((version.paragraphs ?? []).map(p => [p.key, lines.slice(p.line_start, p.line_end + 1).join('\n')]));
}

/** 旧版本 → 新版本的逐段变化；顺序以新版本为准，删除的段落插在它原来前一段之后。 */
export function compareVersions(older: VersionRecord, newer: VersionRecord): ParagraphChange[] {
  const before = texts(older);
  const after = texts(newer);
  const out: ParagraphChange[] = [];
  const oldKeys = (older.paragraphs ?? []).map(p => p.key);
  const placed = new Set<string>();
  const flushRemovedBefore = (key: string | null) => {
    // 把旧版本里排在 key 之前、新版本已没有的段落先列出
    for (const old of oldKeys) {
      if (old === key) break;
      if (!after.has(old) && !placed.has(old)) { out.push({ kind: 'removed', key: old, text: before.get(old) ?? '' }); placed.add(old); }
    }
  };
  for (const p of newer.paragraphs ?? []) {
    const text = after.get(p.key) ?? '';
    if (before.has(p.key)) {
      flushRemovedBefore(p.key);
      const old = before.get(p.key) ?? '';
      out.push(old === text ? { kind: 'same', key: p.key, text } : { kind: 'changed', key: p.key, before: old, after: text, parts: diffText(old, text) });
    } else {
      out.push({ kind: 'added', key: p.key, text });
    }
    placed.add(p.key);
  }
  flushRemovedBefore(null);
  return out;
}

export function changeSummary(changes: ParagraphChange[]): string {
  const count = (kind: ParagraphChange['kind']) => changes.filter(c => c.kind === kind).length;
  const [changed, added, removed] = [count('changed'), count('added'), count('removed')];
  if (!changed && !added && !removed) return '两个版本正文相同';
  return [changed && `改动 ${changed} 段`, added && `新增 ${added} 段`, removed && `删除 ${removed} 段`].filter(Boolean).join('，');
}

const MODES: Record<string, string> = {
  manual: '手改', assistant_replace: '对话助手替换', assistant_insert: '对话助手插入',
  accept_ai_suggestion: '采纳 AI 建议', insert_answer_card: '插入答案卡', rollback: '版本回退',
};

/** 版本列表上的修改方式。 */
export function versionModeLabel(version: VersionRecord): string {
  if (version.source === 'chapter_loop') return '章节循环修正';
  if (version.source === 'system_generated') return '系统生成';
  if (version.edit_mode === 'rollback' || version.version_origin === 'rollback') return `版本回退（回到 v${version.rollback_from ?? '?'}）`;
  if (version.note?.startsWith('自动提交')) return version.note;
  const label = MODES[version.edit_mode ?? ''] ?? (version.version_origin === 'assistant_edit' ? '对话助手写入' : '手改');
  return label;
}

/** 能否回退到该版本：须持锁、不是当前版本、没有未提交修改。 */
export function rollbackBlocker(params: { held: boolean; isCurrent: boolean; dirty: boolean; system: boolean }): string | null {
  if (params.system) return '系统生成章节不能回退，请到数据源修改后重新生成';
  if (!params.held) return '先取得编辑权';
  if (params.isCurrent) return '这就是当前版本';
  if (params.dirty) return '有未提交的修改，先提交或放弃草稿';
  return null;
}
