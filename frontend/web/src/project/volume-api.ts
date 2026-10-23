// 为什么有这个文件：为分册定稿（finalize）、解锁（unlock）与分册状态列表提供标准 API 请求客户端与状态推导函数。
// 它解决什么问题：对齐 OpenAPI /api/v1/projects/{project_id}/volumes 契约，让项目概览、导出中心与编辑台能够准确感知分册定稿状态与门禁。

import { useCallback, useEffect, useState } from 'react';
import { request } from '../shared/api.ts';
import type {
  Volume,
  VolumeFinalizeRequest,
  VolumeFinalizeResponse,
  VolumeListResponse,
  VolumeStatus,
  VolumeStatusResponse,
  VolumeUnlockRequest,
} from '../shared/types.ts';

/**
 * 获取项目中所有分册的定稿状态列表
 * 对齐 OpenAPI operationId: listVolumesStatus
 * GET /api/v1/projects/{project_id}/volumes
 */
export async function fetchVolumesStatus(
  projectId: string,
  token: string | null
): Promise<VolumeStatus[]> {
  if (!projectId) return [];
  const resp = await request<VolumeListResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/volumes`,
    token
  );
  return resp?.volumes || [];
}

/**
 * 获取指定分册的定稿状态
 * 对齐 OpenAPI operationId: getVolumeStatus
 * GET /api/v1/projects/{project_id}/volumes/{volume_id}
 */
export async function fetchSingleVolumeStatus(
  projectId: string,
  volumeId: string,
  token: string | null
): Promise<VolumeStatusResponse> {
  return request<VolumeStatusResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/volumes/${encodeURIComponent(volumeId)}`,
    token
  );
}

/**
 * 执行分册定稿与安全门禁锁定
 * 对齐 OpenAPI operationId: finalizeVolume
 * POST /api/v1/projects/{project_id}/volumes/{volume_id}/finalize
 */
export async function finalizeVolumeApi(
  projectId: string,
  volumeId: string,
  token: string | null,
  body?: VolumeFinalizeRequest,
  revision?: number
): Promise<VolumeFinalizeResponse> {
  return request<VolumeFinalizeResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/volumes/${encodeURIComponent(volumeId)}/finalize`,
    token,
    'POST',
    body || {},
    revision
  );
}

/**
 * 解锁定稿分册以支持修改
 * 对齐 OpenAPI operationId: unlockVolume
 * POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock
 */
export async function unlockVolumeApi(
  projectId: string,
  volumeId: string,
  token: string | null,
  body: VolumeUnlockRequest,
  revision?: number
): Promise<VolumeStatusResponse> {
  return request<VolumeStatusResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/volumes/${encodeURIComponent(volumeId)}/unlock`,
    token,
    'POST',
    body,
    revision
  );
}

/**
 * 判断指定分册是否已定稿
 */
export function isVolumeFinalized(
  volumes?: VolumeStatus[] | null,
  volumeId?: string | null
): boolean {
  if (!volumes || !Array.isArray(volumes) || !volumeId) return false;
  const match = volumes.find(v => v.volume_id === volumeId);
  return Boolean(match?.is_finalized);
}

/**
 * 判断是否所有分册（技术与商务两册）均已定稿
 */
export function areAllVolumesFinalized(volumes?: VolumeStatus[] | null): boolean {
  if (!volumes || !Array.isArray(volumes) || volumes.length === 0) return false;
  const tech = volumes.find(v => v.volume_id === 'technical');
  const bus = volumes.find(v => v.volume_id === 'business');
  return Boolean(tech?.is_finalized && bus?.is_finalized);
}

export interface VolumeFinalizeMeta {
  isFinalized: boolean;
  label: string;
  badgeColor: string;
  finalizedBy: string | null;
  finalizedAt: string | null;
  unlockReason: string | null;
}

/**
 * 推导分册或全文定稿徽章元信息
 */
export function getVolumeFinalizeMeta(
  volumes?: VolumeStatus[] | null,
  volumeId?: string | 'all' | null
): VolumeFinalizeMeta {
  if (volumeId === 'all') {
    const allDone = areAllVolumesFinalized(volumes);
    return {
      isFinalized: allDone,
      label: allDone ? '分册全部定稿' : '分册未全部定稿',
      badgeColor: allDone ? 'success' : 'default',
      finalizedBy: null,
      finalizedAt: null,
      unlockReason: null,
    };
  }

  const vol = volumes?.find(v => v.volume_id === volumeId);
  const isDone = Boolean(vol?.is_finalized);
  const name = volumeId === 'technical' ? '技术分册' : volumeId === 'business' ? '商务分册' : '分册';
  return {
    isFinalized: isDone,
    label: isDone ? `${name}已定稿` : `${name}未定稿`,
    badgeColor: isDone ? 'success' : 'default',
    finalizedBy: vol?.finalized_by ?? null,
    finalizedAt: vol?.finalized_at ?? null,
    unlockReason: vol?.unlock_reason ?? null,
  };
}

/**
 * 推导导出中心「分册定稿门禁」前提检查条目
 */
export function deriveFinalizePremise(
  volumes?: VolumeStatus[] | null,
  volume?: string | 'all'
): { label: string; ready: boolean; tab: string } {
  const isAll = volume === 'all';
  const ready = isAll ? areAllVolumesFinalized(volumes) : isVolumeFinalized(volumes, volume);
  const volLabel = volume === 'technical' ? '技术分册' : volume === 'business' ? '商务分册' : '分册';
  return {
    label: isAll ? '分册定稿门禁：技术与商务两册均已定稿锁定' : `分册定稿门禁：${volLabel}已定稿锁定`,
    ready,
    tab: 'editor',
  };
}

/**
 * React Hook: 管理项目中所有分册的定稿状态并自动订阅刷新
 */
export function useVolumesStatus(
  projectId?: string,
  token?: string | null,
  revision?: number
) {
  const [volumes, setVolumes] = useState<VolumeStatus[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!projectId) return [];
    setLoading(true);
    try {
      const data = await fetchVolumesStatus(projectId, token ?? null);
      setVolumes(data);
      return data;
    } catch {
      return [];
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    void refresh();
  }, [refresh, revision]);

  return { volumes, loading, refresh, setVolumes };
}
