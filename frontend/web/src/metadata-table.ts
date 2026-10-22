// 为什么有这个文件：实现元数据驱动表格的纯计算逻辑、字段模式定义与布局预算。
// 它解决什么问题：从字段元数据自动推导表格列配置、计算行合并（rowSpan）、
// 在 1280px 标准视口下执行无横向滚动宽度预算分配、实施合规批量操作限制门禁（星号/废标/资格禁止批量确认）。

import type { CSSProperties, ReactNode } from 'react';

/* ========================================================================= */
/* 1. 元数据字段与表格模型类型定义                                           */
/* ========================================================================= */

export type FieldDataType =
  | 'text'
  | 'longtext'     // 长文本/富文本：优先通过 ellipsis + 抽屉详情展示
  | 'number'       // 数值列：默认右对齐（规范 9.1 规则 3）
  | 'date'         // 日期
  | 'datetime'     // ISO 时间戳：等宽字体排版（规范 9.1 规则 3）
  | 'level'        // 条款级别：由 LevelTag 渲染（废标/无效/星号/重点/加分/评分/资格/一般）
  | 'cite'         // 引用证据：由 Cite 渲染（[证]、[片]、P.47、事实点）
  | 'source'       // 来源溯源：由 SourceBar 渲染（左侧 3px 条或底部指纹卡片）
  | 'status'       // 业务状态：彩色 Tag 渲染
  | 'ai'           // AI 标签：专属 AI 紫 AiTag 渲染
  | 'direct'       // 系统直出：系统蓝 DirectTag 渲染
  | 'actions';     // 操作列：最多 2 个链接 + 更多下拉（规范 9.1 规则 5）

export interface FieldMeta<T = any> {
  key: string;               // 字段唯一键（对应 dataIndex 或自定义键）
  label: string;             // 列标题
  secondaryLabel?: string;   // 二级系统键（规范 9.2 规则 2：中文名 + 等宽小字系统键两行显示）
  dataType: FieldDataType;   // 数据类型
  width?: number;            // 期望宽度（px）
  minWidth?: number;         // 最小宽度（px）
  priority?: number;         // 排序优先级：1 标识列 -> 2 分类/状态 -> 3 业务数值 -> 4 责任人 -> 5 操作（规范 9.1 规则 3）
  align?: 'left' | 'center' | 'right'; // 对齐方式
  ellipsis?: boolean;        // 是否截断显示省略号与 Tooltip
  viewInDrawer?: boolean;    // 长文本是否支持侧边抽屉查看完整内容（实现无横滚详情查看）
  sortable?: boolean;        // 是否支持排序
  filterable?: boolean;      // 是否支持筛选
  filterOptions?: Array<{ label: string; value: string | number }>;
  groupMerge?: boolean;      // 相邻相同值是否自动合并（动态 rowSpan 处理）
  hidden?: boolean;          // 是否在表格中隐藏
  required?: boolean;        // 是否为必填项（表单协作）
  starred?: boolean;         // 是否为 ★ 重点重新确认字段（规范 9.2 规则 1）
  fixed?: 'left' | 'right';  // 必须横滚时固定的列
  render?: (value: any, record: T, index: number) => ReactNode;
}

export interface TableMeta<T = any> {
  schemaId: string;
  name: string;
  description?: string;
  defaultSize?: 'small' | 'middle' | 'large'; // 默认 middle；矩阵/合规问题/资料列表默认 small（规范 9.1 规则 1）
  fields: FieldMeta<T>[];
  groupField?: string;       // 默认分组列键名
  riskRowPredicate?: (record: T) => boolean;   // 风险行高亮条件（浅红底 #FFF5F5，规范 9.1 规则 4）
  urgentRowPredicate?: (record: T) => boolean; // 3 天内截止置顶 + 红色急标签条件（规范 9.1 规则 4）
}

/* ========================================================================= */
/* 2. 1280px 标准宽度布局与无横滚预算引擎                                   */
/* ========================================================================= */

/** 1280px 标准桌面视口下的主流内容可用表格宽度（减去侧边栏 216px 与两侧外边距 24px*2） */
export const STANDARD_TABLE_AVAILABLE_WIDTH = 1040;

export interface ColumnWidthAllocation {
  key: string;
  label: string;
  dataType: FieldDataType;
  allocatedWidth: number;
  isFlexible: boolean;
  ellipsis: boolean;
  viewInDrawer: boolean;
  fixed?: 'left' | 'right';
}

export interface ColumnBudgetResult {
  availableWidth: number;
  totalAllocatedWidth: number;
  fitsWithoutScroll: boolean;
  scrollX: number | undefined;
  columns: ColumnWidthAllocation[];
}

/**
 * 核心算法：1280px 宽度预算分配。
 * 优先保证在 1040px 内不产生横向滚动条；长文本列动态自适应并启用省略号/抽屉查看。
 */
export function calculateColumnWidthBudget(
  fields: FieldMeta[],
  availableWidth = STANDARD_TABLE_AVAILABLE_WIDTH,
  minFlexibleWidth = 100
): ColumnBudgetResult {
  const visibleFields = fields.filter(f => !f.hidden);
  if (!visibleFields.length) {
    return {
      availableWidth,
      totalAllocatedWidth: 0,
      fitsWithoutScroll: true,
      scrollX: undefined,
      columns: [],
    };
  }

  // 1. 区分固定列与自适应/长文本列
  let fixedWidthSum = 0;
  const flexibleCols: FieldMeta[] = [];
  const fixedCols: Array<{ field: FieldMeta; width: number }> = [];

  for (const field of visibleFields) {
    if (field.dataType === 'longtext' || (!field.width && field.dataType === 'text')) {
      flexibleCols.push(field);
    } else {
      // 默认宽度估算
      let defaultWidth = field.width;
      if (!defaultWidth) {
        switch (field.dataType) {
          case 'actions': defaultWidth = 110; break;
          case 'level': defaultWidth = 110; break;
          case 'status': defaultWidth = 95; break;
          case 'ai': defaultWidth = 100; break;
          case 'direct': defaultWidth = 100; break;
          case 'cite': defaultWidth = 130; break;
          case 'source': defaultWidth = 130; break;
          case 'datetime': defaultWidth = 135; break;
          case 'date': defaultWidth = 105; break;
          case 'number': defaultWidth = 90; break;
          default: defaultWidth = 120; break;
        }
      }
      fixedCols.push({ field, width: defaultWidth });
      fixedWidthSum += defaultWidth;
    }
  }

  const remainingWidth = availableWidth - fixedWidthSum;
  const flexibleCount = flexibleCols.length;

  let fitsWithoutScroll = true;
  let scrollX: number | undefined = undefined;
  const allocations: ColumnWidthAllocation[] = [];

  if (flexibleCount > 0 && remainingWidth >= flexibleCount * minFlexibleWidth) {
    // 剩余宽度充足：平分给自适应长文本列，实现 100% 无横滚
    const perFlexWidth = Math.floor(remainingWidth / flexibleCount);
    for (const item of fixedCols) {
      allocations.push({
        key: item.field.key,
        label: item.field.label,
        dataType: item.field.dataType,
        allocatedWidth: item.width,
        isFlexible: false,
        ellipsis: !!item.field.ellipsis,
        viewInDrawer: !!item.field.viewInDrawer,
        fixed: item.field.fixed,
      });
    }
    for (let i = 0; i < flexibleCount; i++) {
      const field = flexibleCols[i];
      // 最后一列补齐微小像素舍入误差
      const width = i === flexibleCount - 1
        ? remainingWidth - perFlexWidth * (flexibleCount - 1)
        : perFlexWidth;
      allocations.push({
        key: field.key,
        label: field.label,
        dataType: field.dataType,
        allocatedWidth: width,
        isFlexible: true,
        ellipsis: true, // 长文本必定启用省略保护
        viewInDrawer: field.viewInDrawer !== false, // 默认支持抽屉详情查看
        fixed: field.fixed,
      });
    }
  } else if (flexibleCount > 0) {
    // 剩余宽度不足但存在长文本列：分配最小宽度，若总和超出则开启 scroll.x 并固定关键列
    const totalRequired = fixedWidthSum + flexibleCount * minFlexibleWidth;
    if (totalRequired > availableWidth) {
      fitsWithoutScroll = false;
      scrollX = totalRequired;
    }
    for (const item of fixedCols) {
      allocations.push({
        key: item.field.key,
        label: item.field.label,
        dataType: item.field.dataType,
        allocatedWidth: item.width,
        isFlexible: false,
        ellipsis: !!item.field.ellipsis,
        viewInDrawer: !!item.field.viewInDrawer,
        // 超宽时首列和操作列自动固定（规范 9.1 规则 2）
        fixed: item.field.fixed || (item.field.dataType === 'actions' ? 'right' : undefined),
      });
    }
    for (const field of flexibleCols) {
      allocations.push({
        key: field.key,
        label: field.label,
        dataType: field.dataType,
        allocatedWidth: minFlexibleWidth,
        isFlexible: true,
        ellipsis: true,
        viewInDrawer: field.viewInDrawer !== false,
        fixed: field.fixed,
      });
    }
  } else {
    // 全是固定列
    if (fixedWidthSum > availableWidth) {
      fitsWithoutScroll = false;
      scrollX = fixedWidthSum;
    }
    for (const item of fixedCols) {
      allocations.push({
        key: item.field.key,
        label: item.field.label,
        dataType: item.field.dataType,
        allocatedWidth: item.width,
        isFlexible: false,
        ellipsis: !!item.field.ellipsis,
        viewInDrawer: !!item.field.viewInDrawer,
        fixed: item.field.fixed,
      });
    }
  }

  // 恢复原始字段优先级排序
  const fieldOrderMap = new Map(visibleFields.map((f, i) => [f.key, i]));
  allocations.sort((a, b) => (fieldOrderMap.get(a.key) ?? 0) - (fieldOrderMap.get(b.key) ?? 0));

  // 超出预算需要横滚时，强制第一列固定到左侧，操作列固定到右侧（规范 9.1 规则 2）
  if (!fitsWithoutScroll && allocations.length > 0) {
    if (!allocations[0].fixed) {
      allocations[0].fixed = 'left';
    }
    const actionCol = allocations.find(c => c.dataType === 'actions' || c.key === 'actions');
    if (actionCol && !actionCol.fixed) {
      actionCol.fixed = 'right';
    }
  }

  const totalAllocatedWidth = allocations.reduce((sum, col) => sum + col.allocatedWidth, 0);

  return {
    availableWidth,
    totalAllocatedWidth,
    fitsWithoutScroll,
    scrollX,
    columns: allocations,
  };
}

/* ========================================================================= */
/* 3. 动态列/行合并（rowSpan）计算引擎                                       */
/* ========================================================================= */

/**
 * 计算动态单元格纵向合并（rowSpan）：
 * 遍历数据集，对连续相同值的第 1 项返回 span 计数，后续相同项返回 0。
 */
export function calculateRowSpans<T>(
  data: T[],
  groupKey: keyof T | ((item: T) => any)
): number[] {
  if (!data || !data.length) return [];
  const spans: number[] = new Array(data.length).fill(0);
  const getter = typeof groupKey === 'function' ? groupKey : (item: T) => item[groupKey];

  let startIndex = 0;
  while (startIndex < data.length) {
    const currentValue = getter(data[startIndex]);
    let count = 1;
    while (
      startIndex + count < data.length &&
      getter(data[startIndex + count]) === currentValue
    ) {
      count++;
    }
    spans[startIndex] = count;
    for (let k = 1; k < count; k++) {
      spans[startIndex + k] = 0;
    }
    startIndex += count;
  }
  return spans;
}

/* ========================================================================= */
/* 4. 合规批量确认门禁校验（规范 9.1 规则 6 / 5.2.2）                         */
/* ========================================================================= */

/**
 * 星号、废标、资格三类抽取条目不提供批量确认（5.2.2 规范与设计规范 9.1 规则 6）
 */
export const NON_BATCHABLE_CATEGORIES = new Set([
  'star',
  'blocker',
  'disqualification',
  'qualification',
  'scoring_critical',
  'critical',
]);

export interface BatchConfirmValidation {
  allowed: boolean;
  totalSelected: number;
  nonBatchableCount: number;
  reasons: string[];
}

export function canBatchConfirm(records: any[]): BatchConfirmValidation {
  if (!records || !records.length) {
    return {
      allowed: true,
      totalSelected: 0,
      nonBatchableCount: 0,
      reasons: [],
    };
  }

  let nonBatchableCount = 0;
  for (const item of records) {
    const category = item.category || item.level || item.rule_level || item.type;
    if (category && NON_BATCHABLE_CATEGORIES.has(String(category).toLowerCase())) {
      nonBatchableCount++;
    }
  }

  const allowed = nonBatchableCount === 0;
  const reasons: string[] = [];
  if (!allowed) {
    reasons.push(
      `选中的条目中包含 ${nonBatchableCount} 项星号（★）、废标或资格审查类条款。依据项目合规规范（§5.2.2），该类关键条款禁止批量确认，必须逐项单独人工核对。`
    );
  }

  return {
    allowed,
    totalSelected: records.length,
    nonBatchableCount,
    reasons,
  };
}

/* ========================================================================= */
/* 5. 风险行与急迫行判定规则（规范 9.1 规则 4）                              */
/* ========================================================================= */

/**
 * 判定当前行是否属于风险行（浅红底 #FFF5F5，.row-danger）
 * 涵盖：阻断/废标、证据失效、待确认或负偏离
 */
export function isRiskRow<T = any>(
  record: T,
  customPredicate?: (rec: T) => boolean
): boolean {
  if (!record) return false;
  if (customPredicate && customPredicate(record)) return true;

  const item = record as any;
  if (item.level === 'blocker' || item.category === 'blocker' || item.category === 'disqualification') {
    return true;
  }
  if (item.status === 'pending' || item.status === 'rejected' || item.evidence_invalid === true) {
    return true;
  }
  if (item.risk === true || item.has_deviation === true) {
    return true;
  }
  return false;
}

/**
 * 判定项目是否属于 3 天内截止的紧迫行（置顶 + 红色急标签，规范 9.1 规则 4）
 */
export function isUrgentRow<T = any>(
  record: T,
  daysThreshold = 3,
  customPredicate?: (rec: T) => boolean,
  now = new Date()
): boolean {
  if (!record) return false;
  if (customPredicate && customPredicate(record)) return true;
  const item = record as any;
  const deadline = item.deadline || item.due_at || item.expire_at;
  if (!deadline) return false;

  const deadlineDate = new Date(deadline);
  if (isNaN(deadlineDate.getTime())) return false;

  const diffMs = deadlineDate.getTime() - now.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= 0 && diffDays <= daysThreshold;
}

/**
 * 等宽时间格式化（规范 9.1 规则 3：时间用等宽字体）
 */
export function formatDateTimeMonospace(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return String(dateStr);
  }
}

/* ========================================================================= */
/* 6. 内置 Mock 元数据 Schema（后端尚未实现时的官方 Fallback）              */
/* ========================================================================= */

/** 要求矩阵 Schema */
export const REQUIREMENTS_MATRIX_SCHEMA: TableMeta = {
  schemaId: 'requirements-matrix',
  name: '要求矩阵',
  description: '招标文件条款抽取、级别判定与我方响应对齐表格',
  defaultSize: 'small', // 规范 9.1 规则 1：矩阵默认使用 small
  groupField: 'level',
  riskRowPredicate: (item: any) => isRiskRow(item),
  urgentRowPredicate: (item: any) => isUrgentRow(item),
  fields: [
    {
      key: 'code',
      label: '条款编号',
      secondaryLabel: 'clause_code',
      dataType: 'text',
      width: 95,
      priority: 1,
    },
    {
      key: 'level',
      label: '条款级别',
      secondaryLabel: 'rule_level',
      dataType: 'level',
      width: 110,
      priority: 2,
      groupMerge: true, // 相同级别相邻合并
    },
    {
      key: 'text',
      label: '要求原文',
      secondaryLabel: 'requirement_text',
      dataType: 'longtext',
      viewInDrawer: true,
      ellipsis: true,
      priority: 1,
    },
    {
      key: 'volume',
      label: '归属分册',
      secondaryLabel: 'volume_scope',
      dataType: 'text',
      width: 90,
      priority: 2,
    },
    {
      key: 'response',
      label: '响应要点',
      secondaryLabel: 'our_response',
      dataType: 'longtext',
      viewInDrawer: true,
      ellipsis: true,
      priority: 3,
    },
    {
      key: 'cite',
      label: '关联证据',
      secondaryLabel: 'evidence_link',
      dataType: 'cite',
      width: 140,
      priority: 3,
    },
    {
      key: 'source',
      label: '来源指纹',
      secondaryLabel: 'input_fingerprint',
      dataType: 'source',
      width: 135,
      priority: 3,
    },
    {
      key: 'status',
      label: '确认状态',
      secondaryLabel: 'confirm_status',
      dataType: 'status',
      width: 90,
      priority: 2,
    },
    {
      key: 'actions',
      label: '操作',
      dataType: 'actions',
      width: 110,
      align: 'center',
      priority: 5,
      fixed: 'right',
    },
  ],
};

/** 企业资料库 Schema */
export const LIBRARY_RECORDS_SCHEMA: TableMeta = {
  schemaId: 'library-records',
  name: '企业资料列表',
  description: '公司资质证书、人员信息与通用证明材料库',
  defaultSize: 'small', // 规范 9.1 规则 1：资料列表用 small
  groupField: 'category',
  fields: [
    {
      key: 'category',
      label: '资料分类',
      secondaryLabel: 'record_type',
      dataType: 'text',
      width: 100,
      priority: 1,
      groupMerge: true,
    },
    {
      key: 'name',
      label: '资料名称',
      secondaryLabel: 'record_title',
      dataType: 'longtext',
      viewInDrawer: true,
      ellipsis: true,
      priority: 1,
    },
    {
      key: 'system_key',
      label: '系统键',
      secondaryLabel: 'sys_key',
      dataType: 'text',
      width: 120,
      priority: 2,
    },
    {
      key: 'valid_until',
      label: '有效期至',
      secondaryLabel: 'expire_date',
      dataType: 'datetime',
      width: 135,
      priority: 3,
    },
    {
      key: 'status',
      label: '核对状态',
      secondaryLabel: 'audit_status',
      dataType: 'status',
      width: 95,
      priority: 2,
    },
    {
      key: 'actions',
      label: '操作',
      dataType: 'actions',
      width: 110,
      align: 'center',
      priority: 5,
      fixed: 'right',
    },
  ],
};

/** 项目事实表 Schema */
export const FACTS_MATRIX_SCHEMA: TableMeta = {
  schemaId: 'facts-matrix',
  name: '项目事实表',
  description: '从招标文件抽取的投标关键指标、事实与参数对照',
  defaultSize: 'middle',
  fields: [
    {
      key: 'fact_key',
      label: '事实名称',
      secondaryLabel: 'fact_key',
      dataType: 'text',
      width: 140,
      priority: 1,
    },
    {
      key: 'value',
      label: '数值 / 取值',
      secondaryLabel: 'fact_val',
      dataType: 'number',
      align: 'right',
      width: 110,
      priority: 3,
    },
    {
      key: 'unit',
      label: '单位',
      dataType: 'text',
      width: 70,
      priority: 3,
    },
    {
      key: 'cite',
      label: '关联证据',
      secondaryLabel: 'evidence',
      dataType: 'cite',
      width: 135,
      priority: 3,
    },
    {
      key: 'status',
      label: '确认状态',
      dataType: 'status',
      width: 95,
      priority: 2,
    },
    {
      key: 'actions',
      label: '操作',
      dataType: 'actions',
      width: 100,
      align: 'center',
      priority: 5,
      fixed: 'right',
    },
  ],
};

export const BUILTIN_TABLE_SCHEMAS: Record<string, TableMeta> = {
  'requirements-matrix': REQUIREMENTS_MATRIX_SCHEMA,
  'library-records': LIBRARY_RECORDS_SCHEMA,
  'facts-matrix': FACTS_MATRIX_SCHEMA,
};

/**
 * 解析 TableMeta：支持传入已有的 TableMeta 对象或 schemaId 字符串
 */
export function resolveTableMeta(schemaOrId: TableMeta | string): TableMeta {
  if (typeof schemaOrId === 'object' && schemaOrId && Array.isArray(schemaOrId.fields)) {
    return schemaOrId;
  }
  const idStr = typeof schemaOrId === 'string' ? schemaOrId : (schemaOrId as any)?.schemaId || '';
  const found = BUILTIN_TABLE_SCHEMAS[idStr];
  if (found) return found;

  // 兜底生成简易元数据
  return {
    schemaId: idStr || 'fallback-table',
    name: idStr || '数据表格',
    defaultSize: 'middle',
    fields: [
      { key: 'id', label: 'ID', dataType: 'text', width: 80, priority: 1 },
      { key: 'name', label: '名称', dataType: 'longtext', viewInDrawer: true, priority: 1 },
      { key: 'status', label: '状态', dataType: 'status', width: 100, priority: 2 },
      { key: 'actions', label: '操作', dataType: 'actions', width: 100, align: 'center', priority: 5 },
    ],
  };
}

/**
 * 模拟异步获取字段元数据（兼容未来真实后端 getFieldMetadata 接口）
 */
export async function fetchFieldMetadataMock(schemaId: string): Promise<TableMeta> {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 10));
  return resolveTableMeta(schemaId);
}
