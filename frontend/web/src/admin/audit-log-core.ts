// 为什么有这个文件：落实 APP-M2-T157 (A-06 审计日志中心) 与 PRD v1.8 §5.10.6、§6.7、§7.3 审计留痕规范。
// 它解决什么问题：定义不可篡改的只读审计数据契约、多维检索过滤算法、敏感数据调阅理由合规性核验、排他编辑锁与模型密钥事件结构化解析，确保前端绝无篡改接口与高敏泄漏。

export type AuditActionType =
  | 'sensitive.reveal'
  | 'lock.acquire'
  | 'lock.takeover'
  | 'lock.release'
  | 'lock.timeout'
  | 'model_key.create'
  | 'model_key.update'
  | 'model_key.rotate'
  | 'model_key.revoke'
  | 'cloud.llm_call'
  | 'cloud.parse_call'
  | 'project.create'
  | 'project.status_change'
  | 'evidence.modify'
  | 'user.password_change';

export type AuditCategory =
  | 'sensitive'
  | 'lock'
  | 'key'
  | 'cloud'
  | 'project'
  | 'all';

export interface AuditLogEntry {
  id: string;
  occurred_at: string;
  user_id: string;
  user_name: string;
  user_role?: string;
  company_id: string;
  company_name?: string;
  action: AuditActionType;
  action_label: string;
  category: AuditCategory;
  target_type: 'sensitive_field' | 'chapter_lock' | 'model_config' | 'project' | 'cloud_call' | 'evidence' | 'system';
  target_id: string;
  target_name?: string;
  project_id?: string;
  project_name?: string;
  // 敏感数据调阅专用字段 (PRD §5.4.5, §7.3, Task)
  reveal_reason?: string;
  reveal_reason_length?: number;
  reveal_reason_compliant?: boolean;
  sensitive_field_type?: 'id_card' | 'bank_card' | 'phone' | 'email' | 'custom';
  sensitive_field_name?: string;
  masked_value?: string;
  // 排他锁专用字段 (PRD §5.11.9, §7.3)
  lock_chapter_id?: string;
  lock_volume?: 'technical' | 'business';
  lock_takeover_reason?: string;
  // 模型密钥专用字段 (PRD §7.3 第 16 条)
  key_event_type?: 'created' | 'updated' | 'rotated' | 'revoked';
  key_fingerprint?: string; // 如 "sk-****...a8f9"，绝不包含密钥明文！
  model_provider?: string;
  model_name?: string;
  // 云端调用字段
  is_cloud_call?: boolean;
  tokens_used?: number;
  duration_ms?: number;
  // 详细元数据
  detail?: Record<string, any>;
  result: 'success' | 'failed';
  error_code?: string;
  ip: string;
}

export interface AuditFilterParams {
  dateStart?: string;
  dateEnd?: string;
  operator?: string;
  actionType?: string;
  category?: AuditCategory;
  projectId?: string;
  companyId?: string;
  result?: 'all' | 'success' | 'failed';
  keyword?: string;
}

export interface AuditSummaryStats {
  totalCount: number;
  sensitiveRevealCount: number;
  lockEventCount: number;
  keyEventCount: number;
  cloudCallCount: number;
  successRate: number;
}

/**
 * 校验敏感信息调阅理由（合规底线：必须填写且不少于 5 个字）
 */
export function validateRevealReason(reason?: string | null): {
  valid: boolean;
  length: number;
  message?: string;
} {
  if (!reason || typeof reason !== 'string') {
    return {
      valid: false,
      length: 0,
      message: '敏感数据调阅理由不能为空，必须填写 5 字以上业务说明。',
    };
  }
  const trimmed = reason.trim();
  const length = trimmed.length;
  if (length < 5) {
    return {
      valid: false,
      length,
      message: `调阅理由不足 5 字（当前仅 ${length} 字），不符合安全审计合规要求。`,
    };
  }
  return {
    valid: true,
    length,
  };
}

/**
 * 操作类型元信息映射
 */
export function getAuditActionMeta(action: AuditActionType): {
  label: string;
  category: AuditCategory;
  color: string;
  description: string;
} {
  switch (action) {
    case 'sensitive.reveal':
      return {
        label: '脱敏数据调阅',
        category: 'sensitive',
        color: 'purple',
        description: '调阅身份证、银行卡等高敏完整值并留痕备查',
      };
    case 'lock.acquire':
      return {
        label: '获取章节编辑锁',
        category: 'lock',
        color: 'blue',
        description: '成功取得章节正文排他独占编辑锁',
      };
    case 'lock.takeover':
      return {
        label: '抢占/接管编辑锁',
        category: 'lock',
        color: 'orange',
        description: '负责人或管理员强制接管其他成员的排他编辑锁',
      };
    case 'lock.release':
      return {
        label: '主动释放编辑锁',
        category: 'lock',
        color: 'cyan',
        description: '编写人保存草稿后主动释放章节编辑排他锁',
      };
    case 'lock.timeout':
      return {
        label: '编辑锁超时释放',
        category: 'lock',
        color: 'volcano',
        description: '停止心跳超过配置超时阈值，系统自动释放排他锁',
      };
    case 'model_key.create':
      return {
        label: '新建模型配置密钥',
        category: 'key',
        color: 'green',
        description: '新增推理模型服务访问凭据，密文加密存储',
      };
    case 'model_key.update':
      return {
        label: '更新模型配置密钥',
        category: 'key',
        color: 'geekblue',
        description: '修改模型服务端点或安全参数',
      };
    case 'model_key.rotate':
      return {
        label: '安全密钥定期轮换',
        category: 'key',
        color: 'gold',
        description: '执行合规要求的模型访问密钥轮换，旧密钥失效',
      };
    case 'model_key.revoke':
      return {
        label: '吊销模型访问密钥',
        category: 'key',
        color: 'red',
        description: '停用并清除已废弃或存在风险的模型密钥',
      };
    case 'cloud.llm_call':
      return {
        label: '云端模型生成调用',
        category: 'cloud',
        color: 'magenta',
        description: '非涉密项目向合规云端模型发起章节草拟请求',
      };
    case 'cloud.parse_call':
      return {
        label: '云端招标文件解析',
        category: 'cloud',
        color: 'arcoblue',
        description: '向云端 MinerU/解析服务发起招标文件解析',
      };
    case 'project.create':
      return {
        label: '新建投标项目',
        category: 'project',
        color: 'blue',
        description: '立项建立新项目及基础空间配置',
      };
    case 'project.status_change':
      return {
        label: '项目状态流转',
        category: 'project',
        color: 'default',
        description: '变更项目或分册编制阶段状态',
      };
    case 'evidence.modify':
      return {
        label: '企业资料修改',
        category: 'project',
        color: 'default',
        description: '修改企业资质、业绩或服务承诺条款',
      };
    case 'user.password_change':
      return {
        label: '修改密码',
        category: 'sensitive',
        color: 'default',
        description: '账号依据公司密码安全策略完成密码更新',
      };
    default:
      return {
        label: '系统常规操作',
        category: 'all',
        color: 'default',
        description: '系统内部常规生命周期事件',
      };
  }
}

/**
 * 格式化密钥指纹（绝不泄漏明文，遵循 PRD §7.2 存储加密与脱敏要求）
 */
export function formatMaskedKeyFingerprint(rawKeyOrFingerprint?: string | null): string {
  if (!rawKeyOrFingerprint) return 'sk-****[未配置]';
  const clean = rawKeyOrFingerprint.trim();
  if (clean.startsWith('sk-****') || clean.startsWith('loc-****')) {
    return clean;
  }
  if (clean.length <= 8) {
    return 'sk-****';
  }
  const suffix = clean.slice(-4);
  return `sk-****${suffix}`;
}

/**
 * 格式化等宽时间字符串 (ISO -> YYYY-MM-DD HH:mm:ss)
 */
export function formatMonospaceTime(isoOrTimestamp?: string | number | null): string {
  if (!isoOrTimestamp) return '-';
  try {
    const d = new Date(isoOrTimestamp);
    if (Number.isNaN(d.getTime())) return String(isoOrTimestamp);
    const pad = (n: number) => String(n).padStart(2, '0');
    const year = d.getFullYear();
    const month = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const hours = pad(d.getHours());
    const minutes = pad(d.getMinutes());
    const seconds = pad(d.getSeconds());
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch {
    return String(isoOrTimestamp);
  }
}

/**
 * 只读保护契约断言：验证审计日志绝对不可被篡改、编辑或删除
 */
export function assertAuditLogReadOnly(operation: string): void {
  const forbiddenOps = ['delete', 'remove', 'edit', 'update', 'modify', 'clear', 'truncate', 'drop'];
  const lower = operation.toLowerCase();
  for (const op of forbiddenOps) {
    if (lower.includes(op)) {
      throw new Error(`【安全底线拦截】审计日志受系统级只读保护，严禁执行 [${operation}] 操作！所有日志仅支持追加写入。`);
    }
  }
}

/**
 * 预置真实多维审计演示日志数据集合（覆盖脱敏调阅、排他编辑锁、模型密钥变更事件与云端调用）
 */
export const DEFAULT_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'audit-log-1001',
    occurred_at: '2026-10-22 14:35:12',
    user_id: 'alpha-editor',
    user_name: '张明',
    user_role: 'bid_writer',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'sensitive.reveal',
    action_label: '脱敏数据调阅',
    category: 'sensitive',
    target_type: 'sensitive_field',
    target_id: 'field-legal-idcard',
    target_name: '法定代表人身份证号码',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    reveal_reason: '核验投标资格预审申请表中法定代表人身份证原件复印件信息',
    reveal_reason_length: 27,
    reveal_reason_compliant: true,
    sensitive_field_type: 'id_card',
    sensitive_field_name: '法定代表人身份证号',
    masked_value: '310115********1234',
    ip: '192.168.10.42',
    result: 'success',
    detail: {
      field_key: 'legal_representative_id',
      component: 'MaskedField',
      reason_rule_checked: 'pass_min_5_chars',
    },
  },
  {
    id: 'audit-log-1002',
    occurred_at: '2026-10-22 14:18:05',
    user_id: 'alpha-manager',
    user_name: '王强',
    user_role: 'project_lead',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'lock.takeover',
    action_label: '抢占/接管编辑锁',
    category: 'lock',
    target_type: 'chapter_lock',
    target_id: 'chap-tech-02',
    target_name: '第二章 关键技术架构与性能指标方案',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    lock_chapter_id: 'chap-tech-02',
    lock_volume: 'technical',
    lock_takeover_reason: '编写人离线超过 45 分钟且项目今日 17:00 截标，负责人紧急接管修订',
    ip: '192.168.10.15',
    result: 'success',
    detail: {
      previous_lock_owner: 'alpha-editor',
      previous_lock_acquired_at: '2026-10-22 13:20:00',
      takeover_rule: 'lead_or_volume_owner_override',
    },
  },
  {
    id: 'audit-log-1003',
    occurred_at: '2026-10-22 13:50:22',
    user_id: 'alpha-manager',
    user_name: '王强',
    user_role: 'project_lead',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'model_key.rotate',
    action_label: '安全密钥定期轮换',
    category: 'key',
    target_type: 'model_config',
    target_id: 'cfg-llm-cloud-qwen',
    target_name: 'Qwen-2.5-72B-Instruct 云端接入凭证',
    key_event_type: 'rotated',
    key_fingerprint: 'sk-****8f92',
    model_provider: 'Alibaba Cloud ModelStudio',
    model_name: 'qwen-2.5-72b-instruct',
    ip: '192.168.10.15',
    result: 'success',
    detail: {
      rotation_policy: 'monthly_compliance_rotation',
      previous_key_fingerprint: 'sk-****31c8',
      plaintext_status: 'never_stored_in_plaintext',
    },
  },
  {
    id: 'audit-log-1004',
    occurred_at: '2026-10-22 12:40:15',
    user_id: 'alpha-editor',
    user_name: '张明',
    user_role: 'bid_writer',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'sensitive.reveal',
    action_label: '脱敏数据调阅',
    category: 'sensitive',
    target_type: 'sensitive_field',
    target_id: 'field-bank-account',
    target_name: '企业基本账户银行卡号',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    reveal_reason: '核对开户行许可证与投标保函出具基本账户号',
    reveal_reason_length: 21,
    reveal_reason_compliant: true,
    sensitive_field_type: 'bank_card',
    sensitive_field_name: '基本账户银行账号',
    masked_value: '************5678',
    ip: '192.168.10.42',
    result: 'success',
  },
  {
    id: 'audit-log-1005',
    occurred_at: '2026-10-22 11:22:40',
    user_id: 'alpha-editor',
    user_name: '张明',
    user_role: 'bid_writer',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'lock.release',
    action_label: '主动释放编辑锁',
    category: 'lock',
    target_type: 'chapter_lock',
    target_id: 'chap-tech-01',
    target_name: '第一章 投标总体说明与服务承诺',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    lock_chapter_id: 'chap-tech-01',
    lock_volume: 'technical',
    ip: '192.168.10.42',
    result: 'success',
    detail: {
      saved_draft_sequence: 4,
      released_voluntarily: true,
    },
  },
  {
    id: 'audit-log-1006',
    occurred_at: '2026-10-22 10:15:00',
    user_id: 'sys-worker',
    user_name: '系统后台任务服务',
    user_role: 'system',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'lock.timeout',
    action_label: '编辑锁超时释放',
    category: 'lock',
    target_type: 'chapter_lock',
    target_id: 'chap-biz-03',
    target_name: '第三章 商务偏离表与投标报价说明',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    lock_chapter_id: 'chap-biz-03',
    lock_volume: 'business',
    ip: '127.0.0.1',
    result: 'success',
    detail: {
      timeout_threshold_minutes: 30,
      auto_submitted_draft: true,
    },
  },
  {
    id: 'audit-log-1007',
    occurred_at: '2026-10-22 09:30:18',
    user_id: 'alpha-manager',
    user_name: '王强',
    user_role: 'company_admin',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'model_key.update',
    action_label: '更新模型配置密钥',
    category: 'key',
    target_type: 'model_config',
    target_id: 'cfg-llm-local-vllm',
    target_name: '本地 vLLM 私有推理引擎安全端点',
    key_event_type: 'updated',
    key_fingerprint: 'loc-****33a1',
    model_provider: 'Local vLLM Cluster',
    model_name: 'DeepSeek-R1-Distill-Qwen-32B',
    ip: '192.168.10.15',
    result: 'success',
  },
  {
    id: 'audit-log-1008',
    occurred_at: '2026-10-21 16:45:00',
    user_id: 'alpha-editor',
    user_name: '张明',
    user_role: 'bid_writer',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'cloud.llm_call',
    action_label: '云端模型生成调用',
    category: 'cloud',
    target_type: 'cloud_call',
    target_id: 'call-llm-9021',
    target_name: '大模型章节草拟服务',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    is_cloud_call: true,
    tokens_used: 3240,
    duration_ms: 2180,
    ip: '192.168.10.42',
    result: 'success',
  },
  {
    id: 'audit-log-1009',
    occurred_at: '2026-10-21 14:10:33',
    user_id: 'alpha-manager',
    user_name: '王强',
    user_role: 'project_lead',
    company_id: 'alpha',
    company_name: '华东数智科技有限公司',
    action: 'project.create',
    action_label: '新建投标项目',
    category: 'project',
    target_type: 'project',
    target_id: 'p-alpha-01',
    target_name: '2026年智慧医疗一体化建设项目',
    project_id: 'p-alpha-01',
    project_name: '2026年智慧医疗一体化建设项目',
    ip: '192.168.10.15',
    result: 'success',
  },
  {
    id: 'audit-log-1010',
    occurred_at: '2026-10-21 11:05:19',
    user_id: 'beta-editor',
    user_name: '李峰',
    user_role: 'bid_writer',
    company_id: 'beta',
    company_name: '远山信息技术有限公司',
    action: 'sensitive.reveal',
    action_label: '脱敏数据调阅',
    category: 'sensitive',
    target_type: 'sensitive_field',
    target_id: 'field-lead-phone',
    target_name: '项目授权代表手机号码',
    project_id: 'p-beta-01',
    project_name: '跨省政务大数据平台投标项目',
    reveal_reason: '核实投标现场开标授权委托人联系电话真实性',
    reveal_reason_length: 22,
    reveal_reason_compliant: true,
    sensitive_field_type: 'phone',
    sensitive_field_name: '授权代表手机号',
    masked_value: '138****8899',
    ip: '10.20.4.11',
    result: 'success',
  },
];

/**
 * 结构化多维过滤算法
 */
export function filterAuditLogs(
  logs: AuditLogEntry[],
  filters: AuditFilterParams
): AuditLogEntry[] {
  return logs.filter(log => {
    // 1. 时间范围筛选
    if (filters.dateStart) {
      const logTime = new Date(log.occurred_at).getTime();
      const startTime = new Date(filters.dateStart).getTime();
      if (!Number.isNaN(logTime) && !Number.isNaN(startTime) && logTime < startTime) {
        return false;
      }
    }
    if (filters.dateEnd) {
      const logTime = new Date(log.occurred_at).getTime();
      const endTime = new Date(filters.dateEnd).getTime();
      if (!Number.isNaN(logTime) && !Number.isNaN(endTime) && logTime > endTime) {
        return false;
      }
    }

    // 2. 操作类别筛选
    if (filters.category && filters.category !== 'all') {
      if (log.category !== filters.category) {
        return false;
      }
    }

    // 3. 具体操作类型筛选
    if (filters.actionType && filters.actionType !== 'all') {
      if (log.action !== filters.actionType) {
        return false;
      }
    }

    // 4. 操作人筛选 (匹配 ID 或 姓名)
    if (filters.operator && filters.operator.trim()) {
      const op = filters.operator.trim().toLowerCase();
      const matchName = log.user_name.toLowerCase().includes(op);
      const matchId = log.user_id.toLowerCase().includes(op);
      if (!matchName && !matchId) {
        return false;
      }
    }

    // 5. 项目 ID / 名称筛选
    if (filters.projectId && filters.projectId.trim()) {
      const p = filters.projectId.trim().toLowerCase();
      const matchPId = log.project_id?.toLowerCase().includes(p);
      const matchPName = log.project_name?.toLowerCase().includes(p);
      if (!matchPId && !matchPName) {
        return false;
      }
    }

    // 6. 公司租户筛选
    if (filters.companyId && filters.companyId !== 'all') {
      if (log.company_id !== filters.companyId) {
        return false;
      }
    }

    // 7. 结果筛选
    if (filters.result && filters.result !== 'all') {
      if (log.result !== filters.result) {
        return false;
      }
    }

    // 8. 综合关键字检索 (匹配目标、理由、详情)
    if (filters.keyword && filters.keyword.trim()) {
      const kw = filters.keyword.trim().toLowerCase();
      const inTarget = log.target_name?.toLowerCase().includes(kw);
      const inReason = log.reveal_reason?.toLowerCase().includes(kw);
      const inAction = log.action_label.toLowerCase().includes(kw);
      const inIp = log.ip.includes(kw);
      if (!inTarget && !inReason && !inAction && !inIp) {
        return false;
      }
    }

    return true;
  });
}

/**
 * 汇总统计计算
 */
export function computeAuditSummaryStats(logs: AuditLogEntry[]): AuditSummaryStats {
  const totalCount = logs.length;
  let sensitiveRevealCount = 0;
  let lockEventCount = 0;
  let keyEventCount = 0;
  let cloudCallCount = 0;
  let successCount = 0;

  for (const log of logs) {
    if (log.category === 'sensitive') sensitiveRevealCount++;
    if (log.category === 'lock') lockEventCount++;
    if (log.category === 'key') keyEventCount++;
    if (log.category === 'cloud' || log.is_cloud_call) cloudCallCount++;
    if (log.result === 'success') successCount++;
  }

  const successRate = totalCount > 0 ? Math.round((successCount / totalCount) * 100) : 100;

  return {
    totalCount,
    sensitiveRevealCount,
    lockEventCount,
    keyEventCount,
    cloudCallCount,
    successRate,
  };
}
