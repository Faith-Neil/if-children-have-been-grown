// 为什么有这个文件：项目设置“拟派人员”的纯函数（PRD v1.8 §5.1.4 第 4 项、R33；APP-M2-T241）。
// 它解决什么问题：把表格行整理成保存请求（去空行、查重复）、给人员资料缺项写出提示、把 R33 结果按严重程度排序展示。

export type StaffProfile = { degree: string | null; major: string | null; work_start: string | null; years: number | null; certificates: string[] | null };
export type StaffRow = { id?: string; person_id: string; role: string; position?: 'A' | 'B' | null; is_key_person?: boolean; person_name?: string; profile?: StaffProfile | null };
export type R33Issue = { id: string; code: string; severity: 'blocker' | 'warning' | 'info'; message: string; requirement_id?: string | null };
export type StaffResult = { revision?: number; staff: StaffRow[]; roles: string[]; r33: { passed: boolean; severity: string; finding_summary: string; issues: R33Issue[] } };

export const staffPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/proposed-staff`;

export function staffPayload(rows: StaffRow[]): { staff: StaffRow[] } {
  const staff: StaffRow[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const role = (row.role ?? '').trim();
    if (!row.person_id || !role) continue;
    const key = `${row.person_id}|${role}`;
    if (seen.has(key)) throw new Error('同一人不要重复拟派为同一角色。');
    seen.add(key);
    staff.push({ ...(row.id ? { id: row.id } : {}), person_id: row.person_id, role, position: row.position ?? null, is_key_person: !!row.is_key_person });
  }
  return { staff };
}

export function profileGaps(profile: StaffProfile | null | undefined): string[] {
  if (!profile) return ['人员资料已删除'];
  const gaps: string[] = [];
  if (!profile.degree) gaps.push('学历');
  if (!profile.major) gaps.push('专业');
  if (!profile.work_start && profile.years === null) gaps.push('参加工作时间');
  if (profile.certificates === null) gaps.push('证书');
  return gaps;
}

const ORDER = { blocker: 0, warning: 1, info: 2 } as const;

export function sortedIssues(issues: R33Issue[]): R33Issue[] {
  return issues.slice().sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
}

export const SEVERITY_LABEL = { blocker: '阻断', warning: '警告', info: '提示' } as const;
