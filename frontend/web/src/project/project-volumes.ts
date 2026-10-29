// 为什么有这个文件：项目编写哪些分册（两册并合标 / 只写技术标不合标）的唯一前端判断。
// 它解决什么问题：页面各处原先写死“技术+商务”；只写技术标的项目不能再出现商务分册的检查、定稿、导出与合标入口。
import type { Volume, VolumeMode } from '../shared/types.ts';

type WithMode = { project?: { volume_mode?: VolumeMode | null } | null; team?: { volume_mode?: VolumeMode | null } | null };

export function volumeMode(workspace?: WithMode | null): VolumeMode {
  return (workspace?.project?.volume_mode ?? workspace?.team?.volume_mode) === 'technical_only' ? 'technical_only' : 'both';
}

export function projectVolumes(workspace?: WithMode | null): Volume[] {
  return volumeMode(workspace) === 'technical_only' ? ['technical'] : ['technical', 'business'];
}

export function technicalOnly(workspace?: WithMode | null): boolean {
  return volumeMode(workspace) === 'technical_only';
}

export const VOLUME_OPTION_LABEL: Record<Volume, string> = { technical: '技术分册', business: '商务分册' };

export function volumeOptions(workspace?: WithMode | null, withAll = false) {
  const items = projectVolumes(workspace).map(value => ({ value, label: VOLUME_OPTION_LABEL[value] }));
  return withAll && items.length > 1 ? [{ value: 'all', label: '全部' }, ...items] : items;
}

export const VOLUME_MODE_OPTIONS = [
  { value: 'both', label: '技术标 + 商务标（导出后合标）' },
  { value: 'technical_only', label: '只写技术标（不合标）' },
];
