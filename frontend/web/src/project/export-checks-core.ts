// 为什么有这个文件：为合规检查红线门禁（APP-M2-T195）与整本递交版/内部稿导出（APP-M2-T196）提供纯逻辑与状态推导。
// 它解决什么问题：
// 1. 严格识别合规检查中的 blocker 级别阻断缺陷，汇总受阻章节列表与阻断原因；
// 2. 联动导出防线：若当前分册或全文存在 blocker，强置灰禁用正式递交版导出并给出阻断 Tooltip；
// 3. 规范内部评审稿（带水印）与正式递交版（盖章版式）切换、导出分册范围、快照 SHA256 版式指纹与文件大小展示。

import type { Chapter, Check, CheckIssue, Volume } from '../shared/types';

/**
 * 判定缺陷级别是否属于阻断（Blocker）级别
 * 兼容 blocker、blocking、fatal、critical、error
 */
export function isBlocker(severity: string | undefined | null): boolean {
  if (!severity || typeof severity !== 'string') return false;
  const s = severity.trim().toLowerCase();
  return ['blocker', 'blocking', 'fatal', 'critical', 'error', 'block'].includes(s);
}

export interface BlockerChapter {
  chapterId: string;
  chapterTitle: string;
  volume?: Volume;
  blockerCount: number;
  issues: CheckIssue[];
  rules: string[];
}

export interface BlockerSummary {
  hasBlockers: boolean;
  totalBlockers: number;
  blockerIssues: CheckIssue[];
  blockedChapters: BlockerChapter[];
  summaryText: string;
}

/**
 * 从当前检查批次中推导所有阻断性缺陷及受阻章节
 */
export function deriveBlockerSummary(
  check?: Check | null,
  chapters: Chapter[] = []
): BlockerSummary {
  if (!check || !Array.isArray(check.issues) || check.issues.length === 0) {
    return {
      hasBlockers: false,
      totalBlockers: 0,
      blockerIssues: [],
      blockedChapters: [],
      summaryText: '无阻断性合规缺陷',
    };
  }

  const blockerIssues = check.issues.filter(issue => isBlocker(issue.severity));
  const totalBlockers = blockerIssues.length;

  if (totalBlockers === 0) {
    return {
      hasBlockers: false,
      totalBlockers: 0,
      blockerIssues: [],
      blockedChapters: [],
      summaryText: '无阻断性合规缺陷',
    };
  }

  // 按章节分组
  const chapterMap = new Map<string, { title: string; volume?: Volume; issues: CheckIssue[]; rules: Set<string> }>();

  for (const issue of blockerIssues) {
    const cid = issue.chapter_id || 'global_non_chapter';
    let entry = chapterMap.get(cid);
    if (!entry) {
      const ch = chapters.find(c => c.id === cid);
      const title = ch?.title || (cid === 'global_non_chapter' ? (issue.requirement_id ? '服务承诺矩阵 / 招标原文' : '企业资料与通用规则') : `章节 ${cid}`);
      entry = {
        title,
        volume: ch?.volume,
        issues: [],
        rules: new Set<string>(),
      };
      chapterMap.set(cid, entry);
    }
    entry.issues.push(issue);
    if (issue.code) {
      entry.rules.add(issue.code);
    }
  }

  const blockedChapters: BlockerChapter[] = Array.from(chapterMap.entries()).map(([cid, data]) => ({
    chapterId: cid,
    chapterTitle: data.title,
    volume: data.volume,
    blockerCount: data.issues.length,
    issues: data.issues,
    rules: Array.from(data.rules),
  }));

  const summaryText = `发现 ${totalBlockers} 项阻断性合规红线缺陷，涉及 ${blockedChapters.length} 个章节/模块`;

  return {
    hasBlockers: true,
    totalBlockers,
    blockerIssues,
    blockedChapters,
    summaryText,
  };
}

/**
 * 校验是否允许生成正式递交版（APP-M2-T195 红线门禁）
 */
export function canExportSubmission(options: {
  hasBlockers: boolean;
  blockerCount?: number;
  fullContent: boolean;
  hasPassedCheck: boolean;
  parseConfirmed: boolean;
  userCanExport?: boolean;
  isFinalized?: boolean;
}): { allowed: boolean; reason: string | null } {
  if (options.userCanExport === false) {
    return { allowed: false, reason: '当前角色无权生成导出文件' };
  }
  if (!options.parseConfirmed) {
    return { allowed: false, reason: '招标文件解析结果尚未人工确认' };
  }
  if (!options.fullContent) {
    return { allowed: false, reason: '当前范围正文尚未全部提交完成' };
  }
  if (!options.hasPassedCheck) {
    return { allowed: false, reason: '当前分册尚未运行有效检查或检查未通过' };
  }
  if (options.hasBlockers) {
    const count = options.blockerCount || 1;
    return {
      allowed: false,
      reason: `存在 ${count} 项阻断性合规缺陷，禁止导出递交版`,
    };
  }
  if (options.isFinalized === false) {
    return { allowed: false, reason: '分册尚未完成定稿锁定，禁止导出正式递交版' };
  }
  return { allowed: true, reason: null };
}

/**
 * 格式化文件大小。没有真实大小时显示“—”，不推算或编造数值。
 */
export function formatFileSize(bytes?: number | null): string {
  if (typeof bytes !== 'number' || bytes <= 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * 格式化导出文件的 SHA-256 摘要。没有真实摘要时显示“—”，不生成模拟值。
 */
export function formatSha256Fingerprint(hash?: string | null): { short: string; full: string } {
  const hex = (hash || '').trim();
  if (!hex) return { short: '—', full: '' };
  const clean = hex.startsWith('sha256:') ? hex.slice(7) : hex;
  return { short: `sha256:${clean.slice(0, 10)}...`, full: `sha256:${clean}` };
}

/**
 * 导出批次状态（APP-M2-T202）：有效 / 已过期（快照仍可下载）/ 失败（整批作废、无文件）。
 */
export function exportStatusMeta(status: string): { label: string; color: string; downloadable: boolean } {
  if (status === 'valid') return { label: '有效', color: 'green', downloadable: true };
  if (status === 'failed') return { label: '生成失败，整批作废', color: 'red', downloadable: false };
  return { label: '已过期（保留当时文件）', color: 'orange', downloadable: true };
}

/** 历史列表的批次号：新批次用 batch_no，早期批次没有编号时显示导出记录编号。 */
export function exportBatchLabel(item: { id: string; batch_no?: string | null }): string {
  return item.batch_no || item.id;
}

/**
 * 导出类型元信息解析
 */
export function getExportKindMeta(kind: string): {
  label: string;
  tagColor: string;
  description: string;
  isSubmission: boolean;
} {
  const isSub = kind === 'submission' || kind === 'official';
  if (isSub) {
    return {
      label: '正式递交版',
      tagColor: 'green',
      description: '红线合规且盖章版式（无内部标记）',
      isSubmission: true,
    };
  }
  return {
    label: '内部评审稿',
    tagColor: 'blue',
    description: '带内部水印与未核验标记，供团队人工复核',
    isSubmission: false,
  };
}

/**
 * 分册范围中文文案
 */
export function getExportVolumeLabel(volume?: Volume | 'all' | string): string {
  if (volume === 'technical') return '技术分册';
  if (volume === 'business') return '商务分册';
  return '技术、商务两册合订';
}


// ---------------------------------------------------------------- 警告逐项放行（PRD §5.8：理由必填，阻断不能放行）

export const RELEASABLE_SEVERITIES = ['warning', 'info', 'hint'];

export function canReleaseIssue(issue: { severity: string; released?: unknown }, isLead: boolean): boolean {
  return isLead && RELEASABLE_SEVERITIES.includes(issue.severity) && !issue.released;
}

export function releasePath(projectId: string, checkId: string, issueId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/checks/${encodeURIComponent(checkId)}/issues/${encodeURIComponent(issueId)}/release`;
}

export function unreleasedCount(issues: { severity: string; released?: unknown }[]): number {
  return issues.filter(issue => !['info', 'hint'].includes(issue.severity) && !(RELEASABLE_SEVERITIES.includes(issue.severity) && issue.released)).length;
}


// ---------------------------------------------------------------- 合标核对清单（PRD §5.9.2，APP-M2-T200）

export function latestSubmissionWithChecklist<T extends { kind: string; merge_checklist?: unknown; created_at: string }>(exports: T[]): T | null {
  return exports.filter(item => item.kind === 'submission' && item.merge_checklist)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
}

export function checklistRowTone(status?: string | null): 'red' | 'orange' | 'green' | 'default' {
  if (status === 'failed') return 'red';
  if (status === 'not_run' || status === 'manual') return 'orange';
  if (status === 'passed') return 'green';
  return 'default';
}

export function checklistFilename(exportId: string): string {
  return `merge-checklist-${exportId}.xlsx`;
}

// 内部响应追溯表（APP-M2-T201）：项目负责人全部，分册负责人本册；后台按身份收窄范围。
export function responseTracePath(projectId: string, volume: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/response-trace.xlsx?volume=${encodeURIComponent(volume || 'all')}`;
}
