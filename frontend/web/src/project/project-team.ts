// 为什么有这个文件：集中处理项目成员表单、分册范围和后台给出的权限。
// 它解决什么问题：公司角色不会被误当作本项目负责人，换人时明确交接且不转送他人的草稿。
import type { Account, Chapter, ChapterPermissions, ProjectMember, ProjectPermissions, ProjectRole, ProjectTeam, Volume, Workspace } from '../shared/types';

export type TeamMemberRow = { user_id: string; project_role: ProjectRole; volumes: Volume[] };
export type TeamFormValues = { members: TeamMemberRow[]; technical_owner_id?: string | null; business_owner_id?: string | null; assembly_owner_id?: string | null; reason?: string };
export type PlanScope = Volume | 'all';

export function teamBasis(team?: ProjectTeam): string {
  return JSON.stringify({
    members: (team?.members ?? []).map(member => ({ user_id: member.user_id, project_role: member.project_role, volumes: [...member.volumes].sort() })).sort((a, b) => a.user_id.localeCompare(b.user_id)),
    volumes: (team?.volumes ?? []).map(volume => ({ volume: volume.volume, owner_id: volume.owner_id ?? null })).sort((a, b) => a.volume.localeCompare(b.volume)),
    assembly_owner_id: team?.assembly_owner_id ?? null,
  });
}

export const projectRoleName = (role: string) => ({ lead: '项目负责人', writer: '投标编写人', readonly: '只读成员' }[role] ?? role);

export function projectCan(workspace: Pick<Workspace, 'permissions'>, permission: keyof ProjectPermissions): boolean {
  return workspace.permissions?.[permission] === true;
}

export function chapterCan(chapter: Pick<Chapter, 'permissions'> | undefined | null, permission: keyof ChapterPermissions): boolean {
  return chapter?.permissions?.[permission] === true;
}

export function teamFormValues(team?: ProjectTeam): TeamFormValues {
  return {
    members: (team?.members ?? []).map(member => ({ user_id: member.user_id, project_role: member.project_role, volumes: [...member.volumes] })),
    technical_owner_id: team?.volumes.find(volume => volume.volume === 'technical')?.owner_id ?? null,
    business_owner_id: team?.volumes.find(volume => volume.volume === 'business')?.owner_id ?? null,
    assembly_owner_id: team?.assembly_owner_id ?? null, reason: '',
  };
}

export function eligibleOwners(members: TeamMemberRow[], accounts: Pick<Account, 'id' | 'role'>[], volume?: Volume): TeamMemberRow[] {
  return members.filter(member => member.project_role !== 'readonly' && accounts.some(account => account.id === member.user_id && account.role !== 'viewer') && (!volume || member.project_role === 'lead' || member.volumes.includes(volume)));
}

export function teamPayload(values: TeamFormValues, accounts: Pick<Account, 'id' | 'role'>[], active: Volume[] = ['technical', 'business']) {
  const members = values.members.map(member => ({ user_id: member.user_id, project_role: member.project_role, volumes: member.project_role === 'lead' ? [...active] : [...new Set(member.volumes)].filter(volume => active.includes(volume)) }));
  if (!members.length || !members.some(member => member.project_role === 'lead')) throw new Error('至少保留一位项目负责人，先指定接手人再移除原负责人。');
  if (new Set(members.map(member => member.user_id)).size !== members.length) throw new Error('同一个账号只能加入项目一次。');
  for (const member of members) {
    const account = accounts.find(item => item.id === member.user_id);
    if (!account) throw new Error('请从后台给出的同公司候选账号中选择成员。');
    if (member.project_role === 'lead' && account.role !== 'manager') throw new Error('本项目负责人必须使用公司经理账号；公司编写账号可以负责分册或章节。');
    if (account.role === 'viewer' && member.project_role !== 'readonly') throw new Error('公司只读账号只能作为项目只读成员。');
  }
  const volumes = active.map(volume => {
    const owner = values[`${volume}_owner_id`] || null;
    if (owner && !eligibleOwners(members, accounts, volume).some(member => member.user_id === owner)) throw new Error(`${volume === 'technical' ? '技术' : '商务'}分册负责人必须是参与本册且可以编写的项目成员。`);
    return { volume, owner_id: owner };
  });
  const assembly = values.assembly_owner_id || null;
  if (assembly && !eligibleOwners(members, accounts).some(member => member.user_id === assembly)) throw new Error('合标负责人必须是可以编写的项目成员。');
  if (!values.reason?.trim()) throw new Error('请写明这次人员与分工调整的原因和交接安排。');
  return { members, volumes, assembly_owner_id: assembly, reason: values.reason.trim() };
}

export function planScopes(workspace: Pick<Workspace, 'permissions' | 'chapters' | 'team'>, userId: string): PlanScope[] {
  if (projectCan(workspace, 'manage_structure')) return workspace.team?.volume_mode === 'technical_only' ? ['all', 'technical'] : ['all', 'technical', 'business'];
  return (workspace.team?.volumes ?? []).filter(volume => volume.owner_id === userId && workspace.chapters.some(chapter => chapter.volume === volume.volume && chapterCan(chapter, 'manage_structure'))).map(volume => volume.volume);
}

export function assignmentCandidates(members: ProjectMember[], volume: Volume) {
  return members.filter(member => member.company_role !== 'viewer' && member.project_role !== 'readonly' && (member.project_role === 'lead' || member.volumes.includes(volume)));
}

export function volumeOperationAllowed(workspace: Pick<Workspace, 'permissions'>, operation: 'check' | 'export', volume: PlanScope): boolean {
  if (volume === 'all') return projectCan(workspace, operation === 'check' ? 'check_all' : 'export_internal');
  return workspace.permissions?.[operation === 'check' ? 'check_volumes' : 'export_volumes']?.includes(volume) === true;
}

export function projectAccessLost(error: unknown): boolean {
  return !!error && typeof error === 'object' && 'status' in error && [403, 404].includes(Number(error.status));
}

export function freezeWorkspace(workspace: Workspace): Workspace {
  return { ...workspace,
    permissions: { manage_team: false, manage_project: false, manage_structure: false, prepare_sources: false, manage_sla: false, edit_facts: false, confirm_facts: false, check_all: false, export_internal: false, check_volumes: [], export_volumes: [] },
    chapters: workspace.chapters.map(chapter => ({ ...chapter, permissions: { edit: false, confirm_plan: false, generate: false, manage_structure: false, assign: false, takeover: false } })),
    requirements: workspace.requirements.map(requirement => ({ ...requirement, permissions: { edit: false, response: false, route: false } })),
  };
}
