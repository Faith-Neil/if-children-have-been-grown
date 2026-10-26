// 为什么有这个文件：提取编辑权租约锁定与心跳续期状态机（useEditorLock）。
// 它解决什么问题：解耦编辑锁状态维护、30秒心跳自动续期、失权拦截与锁释放，降低 EditorPage 复杂度。

import { useEffect, useRef, useState } from 'react';
import { ApiError, request } from '../shared/api.ts';

export interface Lease {
  lease_token: string;
  expires_at: string;
  owner_id: string;
}

export interface UseEditorLockOptions {
  chapterId: string;
  token: string;
  canEdit: boolean;
  epoch: React.MutableRefObject<number>;
  report: (error: unknown) => void;
  reload: () => Promise<unknown>;
  setNotice: (notice: string) => void;
}

export function useEditorLock({
  chapterId,
  token,
  canEdit,
  epoch,
  report,
  reload,
  setNotice,
}: UseEditorLockOptions) {
  const [lease, setLease] = useState<Lease | null>(null);
  const currentLease = useRef<Lease | null>(null);

  const held = canEdit && !!lease && Date.parse(lease.expires_at) > Date.now();

  // 1. 权限失效拦截：当用户失去编辑权限且持有锁时，主动清空锁并提示
  useEffect(() => {
    if (!canEdit && currentLease.current) {
      currentLease.current = null;
      setLease(null);
      setNotice('本节分工或项目权限已经变化，写入口已关闭。当前文字仍保留，可先保留一份本地文字，再核对最新分工。');
    }
  }, [canEdit, setNotice]);

  // 2. 30秒心跳续期状态机：在持有锁期间定期向后台 POST /lock/renew 续期
  useEffect(() => {
    if (!lease) return;
    const start = epoch.current;
    const timer = window.setInterval(async () => {
      const activeLease = currentLease.current;
      if (!activeLease || start !== epoch.current) return;
      try {
        const renewed = await request<Lease>(
          `/api/chapters/${chapterId}/lock/renew`,
          token,
          'POST',
          { lease_token: activeLease.lease_token }
        );
        if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) {
          currentLease.current = renewed;
          setLease(renewed);
        }
      } catch (error) {
        if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) {
          currentLease.current = null;
          setLease(null);
          setNotice('编辑权续期失败，文字已保留在当前页面。请重新取得编辑权后核对版本再保存。');
          report(error);
          if (error instanceof ApiError && [403, 404].includes(error.status)) {
            void reload().catch(report);
          }
        }
      }
    }, 30_000);

    return () => window.clearInterval(timer);
  }, [lease?.lease_token, chapterId, token, epoch, reload, report, setNotice]);

  // 3. 取得编辑锁
  const acquireLock = async (reason: string | null = null): Promise<Lease> => {
    const result = await request<Lease>(`/api/chapters/${chapterId}/lock`, token, 'POST', {
      takeover_reason: reason,
    });
    currentLease.current = result;
    setLease(result);
    return result;
  };

  // 4. 释放编辑锁
  const releaseLock = async (targetChapterId?: string): Promise<void> => {
    const target = targetChapterId || chapterId;
    const active = currentLease.current;
    currentLease.current = null;
    setLease(null);
    if (active && target) {
      await request(`/api/chapters/${target}/lock/release`, token, 'POST', {
        lease_token: active.lease_token,
      });
    }
  };

  // 5. 清理本地锁状态（不发送远程释放）
  const clearLease = () => {
    currentLease.current = null;
    setLease(null);
  };

  return {
    lease,
    setLease,
    currentLease,
    held,
    acquireLock,
    releaseLock,
    clearLease,
  };
}
