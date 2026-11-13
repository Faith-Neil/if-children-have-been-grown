// 为什么有这个文件：按 company_id 读取企业设置里的公司显示名（ISSUE-052 顶栏/投标主体）。
// 它解决什么问题：避免前端写死「远山/华东」合成名，开通新公司后顶栏仍显示旧别名。

import { useEffect, useState } from 'react';
import { fetchCompanySettings } from './company-settings-api';

export function useCompanyDisplayName(companyId?: string | null, token?: string | null): string | null {
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId || !token || companyId === 'system') {
      setName(null);
      return;
    }
    let cancelled = false;
    void fetchCompanySettings(companyId, token)
      .then(settings => {
        if (!cancelled) setName((settings.company_name || '').trim() || null);
      })
      .catch(() => {
        if (!cancelled) setName(null);
      });
    return () => { cancelled = true; };
  }, [companyId, token]);

  return name;
}
