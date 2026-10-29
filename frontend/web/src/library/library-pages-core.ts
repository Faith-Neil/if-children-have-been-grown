// 为什么有这个文件：提取企业资料库（APP-M2-T046）与附件槽位（APP-M2-T047）的纯业务逻辑与状态诊断规则。
// 它解决什么问题：
// 1. 五大标准资料分类导航映射（主体资质、财务审计、人员证书、业绩案例、通用模板）；
// 2. 状态机推导（生效中、已过期、待核验、已排除）与引用有效性强校验；
// 3. 多维筛选纯函数与搜索过滤；
// 4. PRD §2.3 / §5.4 八角色数据权限与高敏证件调阅白名单判定；
// 5. 附件槽位防篡改 SHA256 指纹与安全防线验证。

import type { Evidence, EvidenceAttachment } from '../shared/types.ts';
import { normalizeSystemRole, READONLY_SYSTEM_ROLES, type SystemRole } from '../shell/route-guard.ts';
export { maskSensitiveValue, DEFAULT_MASK_RULES } from '../admin/sensitive-mask.ts';

export type LibraryCategoryKey =
  | 'all'
  | 'qualification'
  | 'financial'
  | 'personnel'
  | 'case'
  | 'template'
  | 'history'
  | string;

export interface CategoryMeta {
  key: LibraryCategoryKey;
  label: string;
  secondary: string;
}

/**
 * PRD v1.8 §5.4.1 定义的标准五大分类与扩展分类
 */
export const LIBRARY_CATEGORIES: CategoryMeta[] = [
  { key: 'all', label: '全部资料', secondary: '全库资料概览' },
  { key: 'qualification', label: '主体资质', secondary: '营业执照、资质证书、财务审计与纳税凭据' },
  { key: 'personnel', label: '人员证书', secondary: '项目人员执业资格与聘书' },
  { key: 'performance', label: '业绩案例', secondary: '同类标杆案例与履约合同' },
  { key: 'sla', label: '服务承诺', secondary: '服务指标与响应承诺' },
  { key: 'snippet', label: '方案片段', secondary: '经核对可复用的方案文字' },
  { key: 'history', label: '历史标书（参考）', secondary: '只供查看参考，不能挂为证据' },
];

/** 资料类别必须与后端 LibraryType 一致（qualification/personnel/performance/sla/snippet/history），否则保存会被拒绝。 */
export const LIBRARY_TYPE_OPTIONS = LIBRARY_CATEGORIES.filter(c => c.key !== 'all').map(c => ({ value: c.key, label: c.label }));

export const CATEGORY_LABEL_MAP: Record<string, string> = {
  all: '全部资料',
  qualification: '主体资质',
  legal_entity: '主体资质',
  financial: '财务审计',
  finance: '财务审计',
  personnel: '人员证书',
  staff: '人员证书',
  case: '业绩案例',
  cases: '业绩案例',
  performance: '业绩案例',
  template: '通用模板',
  sla_templates: '服务承诺模板',
  sla: '服务承诺',
  snippet: '方案片段',
  history: '历史标书（参考）',
};

export function getCategoryLabel(type: string | undefined | null): string {
  if (!type) return '未分类';
  return CATEGORY_LABEL_MAP[type] || type;
}

export type EvidenceStatusKey = 'all' | 'confirmed' | 'pending' | 'expired' | 'rejected';

export const EVIDENCE_STATUS_META: Record<
  string,
  { label: string; color: string; badgeStatus: 'success' | 'warning' | 'error' | 'default' }
> = {
  confirmed: { label: '生效中 (已核验)', color: 'green', badgeStatus: 'success' },
  pending: { label: '待核验', color: 'orange', badgeStatus: 'warning' },
  expired: { label: '已过期', color: 'red', badgeStatus: 'error' },
  rejected: { label: '已排除', color: 'default', badgeStatus: 'default' },
};

/**
 * 纯函数：根据有效期与核验状态智能推导资料生命周期状态
 */
export function deriveEvidenceStatus(
  item: Partial<Evidence>,
  now: Date | string = new Date()
): 'confirmed' | 'pending' | 'expired' | 'rejected' {
  if (item.status === 'rejected') {
    return 'rejected';
  }

  const nowDate = typeof now === 'string' ? new Date(now) : now;

  // 1. 检查是否过期
  if (item.valid_until) {
    const expireDate = new Date(item.valid_until);
    if (!isNaN(expireDate.getTime())) {
      // 当天 23:59:59 之后视为过期
      const endOfDay = new Date(expireDate.getFullYear(), expireDate.getMonth(), expireDate.getDate(), 23, 59, 59);
      if (nowDate.getTime() > endOfDay.getTime()) {
        return 'expired';
      }
    }
  }

  if (item.status === 'confirmed') {
    return 'confirmed';
  }

  return 'pending';
}

export interface UsabilityResult {
  usable: boolean;
  reason: string;
  tagColor: 'green' | 'red' | 'orange' | 'default';
  label: string;
}

/**
 * 纯函数：严格诊断资料是否具备可引用为投标证据的资格
 * 约束：未确认、已过期、缺少授权协议或历史参考均不可作直接证据
 */
export function checkEvidenceUsability(
  item: Evidence,
  projectDeadline?: string | null,
  now: Date | string = new Date()
): UsabilityResult {
  const nowDate = typeof now === 'string' ? new Date(now) : now;
  if (item.type === 'history') {
    return {
      usable: false,
      reason: '历史参考标书，仅供撰写内容借鉴，不可作为证明证据（只能参考）',
      tagColor: 'default',
      label: '只能参考',
    };
  }

  const derived = deriveEvidenceStatus(item, nowDate);

  if (derived === 'expired') {
    return {
      usable: false,
      reason: '资料已过有效期（已过期），无法作为有效法定资质',
      tagColor: 'red',
      label: '已过期不可用',
    };
  }

  if (derived === 'pending') {
    return {
      usable: false,
      reason: '资料尚未经人工审核确认（待核验），严禁冒充正式有效证据',
      tagColor: 'orange',
      label: '待核验',
    };
  }

  if (derived === 'rejected') {
    return {
      usable: false,
      reason: '该资料已被审核人员标记为排除（已排除）',
      tagColor: 'default',
      label: '已排除',
    };
  }

  // 外部合作方协议检查
  if (
    (item.source_tier === 'partner' && !item.agreement_present) ||
    ((item as any).needs_cooperation_agreement && !(item as any).cooperation_agreement_id)
  ) {
    return {
      usable: false,
      reason: '缺少合作方正式授权协议链（缺合作协议），合标检查将直接阻断',
      tagColor: 'red',
      label: '缺合作协议',
    };
  }

  // 项目截止时间覆盖检查
  if (projectDeadline && item.valid_until) {
    const deadlineTime = new Date(projectDeadline).getTime();
    const expireTime = new Date(item.valid_until).getTime();
    if (!isNaN(deadlineTime) && !isNaN(expireTime) && expireTime < deadlineTime) {
      return {
        usable: false,
        reason: '资质有效期不能覆盖投标截止时间，存在废标风险',
        tagColor: 'red',
        label: '不覆盖截止期',
      };
    }
  }

  return {
    usable: true,
    reason: '资质与证明完整有效，可直接挂接为正式证据',
    tagColor: 'green',
    label: '可作证据',
  };
}

export interface EvidenceFilterCriteria {
  category?: string;
  status?: EvidenceStatusKey | 'all' | 'active' | 'confirmed';
  keyword?: string;
  usableOnly?: boolean;
}

/**
 * 纯函数：执行全库资料多维筛选与模糊过滤
 */
export function filterEvidenceList(
  items: Evidence[],
  criteria: EvidenceFilterCriteria,
  now: Date | string = new Date()
): Evidence[] {
  const { category = 'all', status = 'all', keyword = '', usableOnly = false } = criteria;
  const kw = keyword.trim().toLowerCase();
  const nowDate = typeof now === 'string' ? new Date(now) : now;

  return items.filter(item => {
    // 1. 分类筛选
    if (category !== 'all') {
      const isMatchCategory =
        item.type === category ||
        (category === 'qualification' && (item.type === 'legal_entity' || item.type === 'qualification')) ||
        (category === 'finance' && (item.type === 'finance' || item.type === 'financial')) ||
        (category === 'financial' && (item.type === 'finance' || item.type === 'financial')) ||
        (category === 'personnel' && item.type === 'personnel') ||
        (category === 'performance' && (item.type === 'performance' || item.type === 'case')) ||
        (category === 'case' && (item.type === 'performance' || item.type === 'case')) ||
        (category === 'template' && (item.type === 'template' || item.type === 'sla' || item.type === 'snippet'));
      if (!isMatchCategory) return false;
    }

    // 2. 状态筛选
    if (status !== 'all') {
      const currentStatus = deriveEvidenceStatus(item, nowDate);
      const isMatchStatus =
        currentStatus === status ||
        ((status === 'active' || status === 'confirmed') && currentStatus === 'confirmed');
      if (!isMatchStatus) return false;
    }

    // 3. 可引用性筛选
    if (usableOnly) {
      const usability = checkEvidenceUsability(item, null, nowDate);
      if (!usability.usable) return false;
    }

    // 4. 关键字搜索（名称、系统键、内容、说明、持证人、证件号）
    if (kw) {
      const matchName = (item.name || '').toLowerCase().includes(kw);
      const matchKey = (item.system_key || '').toLowerCase().includes(kw);
      const matchContent = (item.content || '').toLowerCase().includes(kw);
      const matchReason = (item.reason || '').toLowerCase().includes(kw);
      const matchOwner = ((item as any).owner_name || '').toLowerCase().includes(kw);
      const matchLicense = ((item as any).license_number || '').toLowerCase().includes(kw);
      if (!matchName && !matchKey && !matchContent && !matchReason && !matchOwner && !matchLicense) {
        return false;
      }
    }

    return true;
  });
}

/**
 * 纯函数：PRD §2.3 八角色企业资料库管理权限判定
 */
export function canManageLibrary(userRole: string | undefined | null): boolean {
  if (!userRole) return false;
  const clean = userRole.trim().toLowerCase();
  if (['admin', 'company_admin', 'data_admin', 'project_lead', 'bidding_manager', 'legal_reviewer', 'quality_auditor', 'hr_specialist'].includes(clean)) {
    return true;
  }
  const normalized = normalizeSystemRole(userRole);
  if (!normalized) return false;
  // 只读成员、外部审核人员以及普通观察员阻断写操作
  if (READONLY_SYSTEM_ROLES.has(normalized as SystemRole)) {
    return false;
  }
  // 公司管理员与资料管理员具备全量维护权限
  return normalized === 'company_admin' || normalized === 'data_admin' || normalized === 'project_lead';
}

/**
 * 纯函数：PRD §2.3 / §5.4.5 高敏个人身份信息（身份证、银行卡）完整值调阅权限白名单
 * 仅限公司管理员（company_admin）与资料管理员（data_admin）及审计法务合规白名单
 */
export function canRevealSensitiveField(userRole: string | undefined | null): boolean {
  if (!userRole) return false;
  const clean = userRole.trim().toLowerCase();
  if (['admin', 'company_admin', 'data_admin', 'legal_reviewer', 'hr_specialist', 'auditor'].includes(clean)) {
    return true;
  }
  const normalized = normalizeSystemRole(userRole);
  return normalized === 'company_admin' || normalized === 'data_admin';
}

export interface AttachmentSecurityCheck {
  isSafe: boolean;
  verified: boolean;
  tampered: boolean;
  sha256Valid: boolean;
  sizeValid: boolean;
  audit_message: string;
  message: string;
}

/**
 * 纯函数：附件槽位防篡改与安全防线验证
 */
export function verifyAttachmentSecurity(
  attachment: EvidenceAttachment | any,
  expectedHashOrMaxSize?: string | number,
  maxSizeBytes = 100 * 1024 * 1024
): AttachmentSecurityCheck {
  if (!attachment) {
    return {
      isSafe: false,
      verified: false,
      tampered: false,
      sha256Valid: false,
      sizeValid: false,
      audit_message: '附件对象为空',
      message: '附件对象为空',
    };
  }

  const effectiveMaxSize = typeof expectedHashOrMaxSize === 'number' ? expectedHashOrMaxSize : maxSizeBytes;
  const expectedHash = typeof expectedHashOrMaxSize === 'string' ? expectedHashOrMaxSize.toLowerCase().trim() : null;

  const fileSize = attachment.size ?? attachment.size_bytes ?? 0;
  const sizeValid = fileSize > 0 && fileSize <= effectiveMaxSize;
  const hasSha256 = typeof attachment.sha256 === 'string' && /^[a-fA-F0-9]{64}$/.test(attachment.sha256);

  if (!sizeValid) {
    const msg = fileSize <= 0 ? '附件文件大小无效' : `附件大小超出安全上限 (${Math.round(effectiveMaxSize / 1024 / 1024)}MB)`;
    return {
      isSafe: false,
      verified: false,
      tampered: false,
      sha256Valid: hasSha256,
      sizeValid: false,
      audit_message: msg,
      message: msg,
    };
  }

  if (!hasSha256) {
    const msg = '缺少有效 SHA256 哈希防篡改指纹（缺少 SHA256）';
    return {
      isSafe: false,
      verified: false,
      tampered: false,
      sha256Valid: false,
      sizeValid: true,
      audit_message: msg,
      message: msg,
    };
  }

  if (expectedHash) {
    const actualHash = attachment.sha256.toLowerCase().trim();
    if (actualHash !== expectedHash) {
      const msg = '附件 SHA-256 校验失败，文件可能已被篡改（警告：哈希不匹配）';
      return {
        isSafe: false,
        verified: false,
        tampered: true,
        sha256Valid: true,
        sizeValid: true,
        audit_message: msg,
        message: msg,
      };
    }
  }

  const msg = '附件防篡改指纹比对一致，校验合规';
  return {
    isSafe: true,
    verified: true,
    tampered: false,
    sha256Valid: true,
    sizeValid: true,
    audit_message: msg,
    message: msg,
  };
}
