// 为什么有这个文件：判断项目是否走技术方案单一路径。
// 它解决什么问题：产品已收口为仅技术标；不再根据 volume_mode=both 暴露商务分册入口。
import type { Volume, VolumeMode } from '../shared/types.ts';

type WithMode = { project?: { volume_mode?: VolumeMode | null } | null; team?: { volume_mode?: VolumeMode | null } | null };

/** 产品固定为技术标路径；忽略历史 both 字段。 */
export function volumeMode(_workspace?: WithMode | null): VolumeMode {
  return 'technical_only';
}

export function projectVolumes(_workspace?: WithMode | null): Volume[] {
  return ['technical'];
}

export function technicalOnly(_workspace?: WithMode | null): boolean {
  return true;
}

export const VOLUME_OPTION_LABEL: Record<Volume, string> = { technical: '技术方案', business: '商务方案' };

export function volumeOptions(_workspace?: WithMode | null, _withAll = false) {
  return [{ value: 'technical' as Volume, label: VOLUME_OPTION_LABEL.technical }];
}
