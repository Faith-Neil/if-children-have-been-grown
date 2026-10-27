// 为什么有这个文件：落实 APP-M2-T024 (A-03 字典配置页) 与 PRD v1.8 §5.10.3、§6.9 纯逻辑层。
// 它解决什么问题：
// 1. 统一管理 6 大核心业务状态码表（项目、章节、长任务、合规检查、导出交付、编辑租约）与系统字段元数据；
// 2. 贯彻“已使用代码只能停用，不可直接硬删除”核心安全红线；
// 3. 实现精细化角色感知（平台管理员/公司管理员具备编辑停用权，写作者与只读角色严格只读保护）；
// 4. 提供纯函数过滤、统计与合法性校验，保证 UI 与脱敏隔离可独立单元测试。

import {
  getAllStatusesForDomain,
  STATUS_DOMAINS,
  STATUS_DOMAIN_LABELS,
  type StatusDomain,
} from '../shared/status-registry.ts';

export interface DictItem {
  id: string;
  category: string;
  categoryLabel: string;
  domain?: StatusDomain;
  code: string;
  label: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
  isInUse: boolean;
  isBuiltin: boolean;
  metadata?: {
    dataType?: string;
    renderType?: string;
    isStarred?: boolean;
    isBlocker?: boolean;
    contrastRatio?: number;
  };
}

export interface DictCategorySummary {
  category: string;
  categoryLabel: string;
  domain?: StatusDomain;
  totalCount: number;
  activeCount: number;
  inUseCount: number;
}

export interface DictPermissionResult {
  canEdit: boolean;
  canToggleStatus: boolean;
  canDelete: boolean;
  isPlatformAdmin: boolean;
  isCompanyAdmin: boolean;
  isReadOnly: boolean;
  roleLabel: string;
  noticeText: string;
}

export interface DictFilterParams {
  category?: string;
  keyword?: string;
  statusFilter?: 'all' | 'active' | 'inactive';
}

/**
 * 角色权限校验：仅平台管理员与公司管理员具备编辑/停用权限，写作者与审计员严格只读
 */
export function checkDictPermission(role?: string | null): DictPermissionResult {
  const normRole = (role || '').trim().toLowerCase();

  const isPlatformAdmin = normRole === 'platform_admin';
  const isCompanyAdmin = normRole === 'company_admin';
  const canEdit = isPlatformAdmin || isCompanyAdmin;

  let roleLabel = '只读人员';
  if (isPlatformAdmin) roleLabel = '平台管理员';
  else if (isCompanyAdmin) roleLabel = '公司管理员';
  else if (normRole === 'group_admin') roleLabel = '集团管理员 (只读)';
  else if (normRole === 'project_lead') roleLabel = '项目负责人 (只读)';
  else if (normRole === 'bid_writer') roleLabel = '标书编写人 (只读)';
  else if (normRole === 'auditor') roleLabel = '合规审计员 (只读)';
  else if (normRole === 'data_admin') roleLabel = '数据管理员 (只读)';

  const noticeText = canEdit
    ? '您具备字典参数管理权限。注意：已在生产业务中使用的状态代码只能停用，不可直接删除。'
    : `当前身份为【${roleLabel}】，字典与字段元数据处于只读调阅状态。修改参数请联系平台或企业管理员。`;

  return {
    canEdit,
    canToggleStatus: canEdit,
    canDelete: false, // 业务内置与已使用代码坚决禁止硬删除
    isPlatformAdmin,
    isCompanyAdmin,
    isReadOnly: !canEdit,
    roleLabel,
    noticeText,
  };
}

/**
 * 核心安全红线：“已使用代码只能停用，不可直接硬删除”
 */
export function validateCodeDeactivation(item: DictItem): {
  allowed: boolean;
  canHardDelete: boolean;
  reason: string;
} {
  if (item.isInUse) {
    return {
      allowed: true, // 允许停用
      canHardDelete: false, // 严禁硬删除
      reason: '已使用代码只能停用，不可直接硬删除',
    };
  }

  if (item.isBuiltin) {
    return {
      allowed: true,
      canHardDelete: false,
      reason: '系统内置核心代码不可删除，仅可按需切换启用/停用',
    };
  }

  return {
    allowed: true,
    canHardDelete: true,
    reason: '未被引用的自定义代码允许删除',
  };
}

/**
 * 状态停用/启用切换
 */
export function toggleDictItemActive(
  items: DictItem[],
  itemId: string,
  targetActive: boolean
): { updatedItems: DictItem[]; modifiedItem: DictItem | null; error?: string } {
  const idx = items.findIndex(i => i.id === itemId);
  if (idx === -1) {
    return { updatedItems: items, modifiedItem: null, error: '未找到指定字典代码项' };
  }

  const current = items[idx];
  // 停用验证
  if (!targetActive) {
    const check = validateCodeDeactivation(current);
    if (!check.allowed) {
      return { updatedItems: items, modifiedItem: null, error: check.reason };
    }
  }

  const updatedItem: DictItem = {
    ...current,
    isActive: targetActive,
  };

  const nextItems = [...items];
  nextItems[idx] = updatedItem;

  return { updatedItems: nextItems, modifiedItem: updatedItem };
}

/**
 * 构建初始标准字典与元数据代码列表
 */
export function buildInitialDictItems(): DictItem[] {
  const items: DictItem[] = [];

  // 1. 注入 6 大状态注册表 (来自 status-registry.ts)
  for (const domain of STATUS_DOMAINS) {
    const statuses = getAllStatusesForDomain(domain);
    statuses.forEach((st, idx) => {
      items.push({
        id: `dict_${domain}_${st.code}`,
        category: `status_${domain}`,
        categoryLabel: `${STATUS_DOMAIN_LABELS[domain]} (${domain})`,
        domain,
        code: st.code,
        label: st.label,
        description: st.description,
        sortOrder: (idx + 1) * 10,
        isActive: true,
        isInUse: true, // 核心 6 大状态码全部标记为已在业务中使用
        isBuiltin: true,
        metadata: {
          dataType: 'string',
          renderType: 'tag',
          isStarred: domain === 'check' && st.code === 'blocker',
          isBlocker: domain === 'check' && st.code === 'blocker',
        },
      });
    });
  }

  // 2. 注入核心字段元数据字典 (对标 PRD §4.16 与 /api/v1/metadata/fields/all)
  const fieldDefs: Array<{
    category: string;
    categoryLabel: string;
    code: string;
    label: string;
    dataType: string;
    renderType: string;
    description: string;
    isStarred?: boolean;
    isBlocker?: boolean;
  }> = [
    {
      category: 'field_project',
      categoryLabel: '项目字段元数据 (project)',
      code: 'project_name',
      label: '项目全称',
      dataType: 'string',
      renderType: 'input',
      description: '招标文件所载明的招标项目正式法定全称',
      isStarred: true,
    },
    {
      category: 'field_project',
      categoryLabel: '项目字段元数据 (project)',
      code: 'budget_amount_cents',
      label: '标的预算金额(分)',
      dataType: 'integer',
      renderType: 'currency',
      description: '项目招标控制价上限金额',
      isStarred: true,
    },
    {
      category: 'field_project',
      categoryLabel: '项目字段元数据 (project)',
      code: 'security_level',
      label: '项目密级',
      dataType: 'string',
      renderType: 'select',
      description: '涉密项目强制使用内网本地大模型',
      isBlocker: true,
    },
    {
      category: 'field_tender',
      categoryLabel: '招标文件元数据 (tender)',
      code: 'tender_type',
      label: '招标方式',
      dataType: 'string',
      renderType: 'select',
      description: '公开招标 / 邀请招标 / 竞争性谈判 / 单一来源',
    },
    {
      category: 'field_tender',
      categoryLabel: '招标文件元数据 (tender)',
      code: 'deadline_at',
      label: '投标截止时间',
      dataType: 'datetime',
      renderType: 'datetime_picker',
      description: '开标及投标书最终提交截止时限',
      isStarred: true,
    },
    {
      category: 'field_evidence',
      categoryLabel: '企业资料与证据元数据 (evidence)',
      code: 'evidence_type',
      label: '证据资质类型',
      dataType: 'string',
      renderType: 'select',
      description: '主体资质 / 财务审计 / 人员证书 / 业绩案例',
    },
    {
      category: 'field_evidence',
      categoryLabel: '企业资料与证据元数据 (evidence)',
      code: 'hash_fingerprint',
      label: 'SHA256哈希指纹',
      dataType: 'string',
      renderType: 'monospace',
      description: '资质原件附件防篡改 64 位不可逆校验码',
      isStarred: true,
    },
    {
      category: 'field_sla',
      categoryLabel: 'SLA 服务承诺元数据 (sla)',
      code: 'response_limit_hours',
      label: '故障响应时限(小时)',
      dataType: 'number',
      renderType: 'number',
      description: '售后技术服务现场与电话响应最长允许时限',
      isStarred: true,
    },
    {
      category: 'field_sla',
      categoryLabel: 'SLA 服务承诺元数据 (sla)',
      code: 'warranty_period_months',
      label: '原厂质保期(月)',
      dataType: 'integer',
      renderType: 'number',
      description: '软硬件设备及集成服务免费质保周期',
      isBlocker: true,
    },
  ];

  fieldDefs.forEach((f, idx) => {
    items.push({
      id: `dict_field_${f.code}`,
      category: f.category,
      categoryLabel: f.categoryLabel,
      code: f.code,
      label: f.label,
      description: f.description,
      sortOrder: (idx + 1) * 10,
      isActive: true,
      isInUse: true,
      isBuiltin: true,
      metadata: {
        dataType: f.dataType,
        renderType: f.renderType,
        isStarred: f.isStarred,
        isBlocker: f.isBlocker,
      },
    });
  });

  return items;
}

/**
 * 字典项分类统计汇总
 */
export function computeCategorySummaries(items: DictItem[]): DictCategorySummary[] {
  const map = new Map<string, DictCategorySummary>();

  for (const item of items) {
    if (!map.has(item.category)) {
      map.set(item.category, {
        category: item.category,
        categoryLabel: item.categoryLabel,
        domain: item.domain,
        totalCount: 0,
        activeCount: 0,
        inUseCount: 0,
      });
    }
    const sum = map.get(item.category)!;
    sum.totalCount += 1;
    if (item.isActive) sum.activeCount += 1;
    if (item.isInUse) sum.inUseCount += 1;
  }

  return Array.from(map.values());
}

/**
 * 多维检索与过滤
 */
export function filterDictItems(
  items: DictItem[],
  params: DictFilterParams
): DictItem[] {
  const { category, keyword, statusFilter } = params;
  const kw = (keyword || '').trim().toLowerCase();

  return items.filter(item => {
    // 分类匹配
    if (category && category !== 'all' && item.category !== category) {
      return false;
    }

    // 启用/停用过滤
    if (statusFilter === 'active' && !item.isActive) return false;
    if (statusFilter === 'inactive' && item.isActive) return false;

    // 关键字检索（支持代码、显示名、描述）
    if (kw) {
      const matchCode = item.code.toLowerCase().includes(kw);
      const matchLabel = item.label.toLowerCase().includes(kw);
      const matchDesc = item.description.toLowerCase().includes(kw);
      if (!matchCode && !matchLabel && !matchDesc) return false;
    }

    return true;
  });
}
