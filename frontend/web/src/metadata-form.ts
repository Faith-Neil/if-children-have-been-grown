// 为什么有这个文件：实现元数据驱动表单的纯计算逻辑、字段模式定义、★字段变更检测与字段置灰门禁。
// 它解决什么问题：
// 1. 定义与后端 getFieldMetadata 契约一致的标准 FormFieldMeta 与 FormSchema 类型；
// 2. 实时比对初始值与当前值，检测 ★ 关键字段修改并生成合规重核警示文案（规范 §5.2.2、PRD §5.12）；
// 3. 判定字段置灰（disabled）状态与悬浮原因解释（不支持字段、系统计算只读字段、无权限用户）；
// 4. 提供双行标签（中文名 + 等宽系统键）纯数据模型与内置 Fallback Schema。

/* ========================================================================= */
/* 1. 元数据驱动表单模式与字段定义                                           */
/* ========================================================================= */

export interface FormFieldOption {
  value: string | number;
  label: string;
  badge_status?: string;
  disabled?: boolean;
}

export interface FormFieldMeta {
  field_key: string;              // 字段唯一键（snake_case）
  label: string;                  // 字段中文标签
  system_key?: string;            // 系统字段键（用于双行标签排版展示）
  data_type:
    | 'string'
    | 'integer'
    | 'number'
    | 'boolean'
    | 'date'
    | 'datetime'
    | 'array'
    | 'object'
    | string;
  required?: boolean;             // 是否必填
  editable?: boolean;             // 是否允许人工编辑（false 则置灰）
  supported?: boolean;            // 当前系统版本是否支持（false 则置灰并提示未支持）
  is_starred?: boolean;           // 是否 ★ 关键字段（修改后记录转入需重新核实状态）
  is_sensitive?: boolean;         // 是否敏感字段（脱敏/掩码）
  render_type?:
    | 'text'
    | 'textarea'
    | 'number'
    | 'date'
    | 'datetime'
    | 'select'
    | 'switch'
    | 'tag'
    | 'badge'
    | 'masked'
    | string;
  placeholder?: string;           // 占位文案
  description?: string;           // 业务释义说明
  unit?: string;                  // 数值单位（元、天、人等）
  options?: FormFieldOption[];    // 枚举选项列表
  span?: number;                  // 栅格列宽（24 栅格，如 12 表示半行，24 表示整行）
  disabledReason?: string;        // 置灰禁用的详细原因解释
}

export interface FormSchema {
  category: string;               // 规范分类标识（如 org_entity, project, qualification）
  category_name: string;          // 分类中文名称
  fields: FormFieldMeta[];        // 字段列表
  description?: string;           // 模式说明
}

/* ========================================================================= */
/* 2. ★ 关键字段修改检测引擎（规范 §5.2.2、PRD §5.12）                       */
/* ========================================================================= */

export interface ModifiedStarredField {
  field_key: string;
  label: string;
  initialValue: any;
  currentValue: any;
}

/**
 * 判定两个值在表单输入场景下是否实质等价（处理空串与 undefined/null 等效）
 */
export function areValuesEquivalent(val1: any, val2: any): boolean {
  const normalize = (v: any) => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v.trim();
    return v;
  };
  return normalize(val1) === normalize(val2);
}

/**
 * 核心算法：检测当前修改的字段中是否存在 ★ 关键字段
 * 若存在，收集被修改的关键字段列表，供高亮与横幅警示使用。
 */
export function getModifiedStarredFields(
  initialValues: Record<string, any> = {},
  currentValues: Record<string, any> = {},
  fields: FormFieldMeta[] = []
): ModifiedStarredField[] {
  const modified: ModifiedStarredField[] = [];

  for (const field of fields) {
    if (!field.is_starred) continue;

    const initialVal = initialValues[field.field_key];
    const currentVal = currentValues[field.field_key];

    // 若初始值存在且被更改（或者既有记录被赋新值），记为修改
    if (!areValuesEquivalent(initialVal, currentVal)) {
      modified.push({
        field_key: field.field_key,
        label: field.label,
        initialValue: initialVal,
        currentValue: currentVal,
      });
    }
  }

  return modified;
}

/**
 * 是否存在已修改的 ★ 关键字段
 */
export function hasModifiedStarredFields(
  initialValues: Record<string, any> = {},
  currentValues: Record<string, any> = {},
  fields: FormFieldMeta[] = []
): boolean {
  return getModifiedStarredFields(initialValues, currentValues, fields).length > 0;
}

/**
 * 生成 ★ 关键字段修改后的合规提示文案
 */
export function formatStarredWarning(modifiedFields: ModifiedStarredField[]): string {
  if (!modifiedFields || !modifiedFields.length) return '';
  const names = modifiedFields.map(f => f.label).join('、');
  return `★ 关键字段（${names}）已被修改。根据项目合规规范（§5.2.2 与 PRD §5.12），修改保存后该记录将自动转入“待确认”状态，须由人工重新核对确认后方可继续作为有效证据引用。`;
}

/* ========================================================================= */
/* 3. 字段置灰（Disabled / Readonly）状态与原因判定                          */
/* ========================================================================= */

export interface FieldDisabledState {
  disabled: boolean;
  reason: string | null;
}

/**
 * 判定字段表单控件的置灰禁用状态与悬浮原因
 */
export function resolveFieldDisabledState(
  field: FormFieldMeta,
  userCanEdit = true
): FieldDisabledState {
  if (!field) {
    return { disabled: false, reason: null };
  }

  // 1. 当前版本明确不支持的字段置灰
  if (field.supported === false) {
    return {
      disabled: true,
      reason: field.disabledReason || '当前系统版本暂未开放此字段配置',
    };
  }

  // 2. 系统字段或只读计算字段
  if (field.editable === false) {
    return {
      disabled: true,
      reason: field.disabledReason || '该字段为系统生成或只读计算字段，不可人工编辑',
    };
  }

  // 3. 用户无编辑权限
  if (!userCanEdit) {
    return {
      disabled: true,
      reason: '当前用户角色无编辑权限（只读模式）',
    };
  }

  return { disabled: false, reason: null };
}

/* ========================================================================= */
/* 4. 双行标签（Two-line Label）纯数据模型解析                               */
/* ========================================================================= */

export interface ResolvedTwoLineLabel {
  primary: string;
  secondary: string | null;
  isStarred: boolean;
  required: boolean;
  tooltipText: string | null;
}

export function resolveTwoLineLabel(field: FormFieldMeta): ResolvedTwoLineLabel {
  const secondary = field.system_key || field.field_key || null;
  return {
    primary: field.label,
    secondary: secondary !== field.label ? secondary : null,
    isStarred: !!field.is_starred,
    required: !!field.required,
    tooltipText: field.description || null,
  };
}

/* ========================================================================= */
/* 5. 内置 Fallback Form Schemas（与后端 getFieldMetadata 契约保持一致）     */
/* ========================================================================= */

/** 公司主体表单模式（参考 kb-data-dictionary v1.9 §3.2.1） */
export const FALLBACK_ORG_ENTITY_FORM_SCHEMA: FormSchema = {
  category: 'org_entity',
  category_name: '公司主体',
  description: '公司法人实体与分支机构信息维护表单',
  fields: [
    {
      field_key: 'entity_name',
      label: '主体名称',
      system_key: 'entity_name',
      data_type: 'string',
      required: true,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '请输入营业执照上的主体全称',
      description: '修改主体名称后，名下全部资质及已挂接证据均需重新核对确认',
      span: 12,
    },
    {
      field_key: 'credit_code',
      label: '统一社会信用代码',
      system_key: 'credit_code',
      data_type: 'string',
      required: true,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '18位统一社会信用代码（GB 32100-2015）',
      span: 12,
    },
    {
      field_key: 'legal_representative',
      label: '法定代表人',
      system_key: 'legal_representative',
      data_type: 'string',
      required: true,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '照录营业执照法定代表人姓名',
      span: 12,
    },
    {
      field_key: 'entity_scope',
      label: '主体范围',
      system_key: 'entity_scope',
      data_type: 'string',
      render_type: 'select',
      required: true,
      editable: true,
      supported: true,
      is_starred: false,
      options: [
        { value: 'own', label: '本公司 / 分公司' },
        { value: 'partner', label: '合作伙伴（联合体/分包）' },
        { value: 'third_party', label: '第三方（总代/渠道）' },
      ],
      span: 12,
    },
    {
      field_key: 'reg_capital',
      label: '注册资本',
      system_key: 'reg_capital',
      data_type: 'number',
      required: false,
      editable: true,
      supported: true,
      is_starred: false,
      unit: '元',
      placeholder: '以元为单位输入注册资本',
      span: 12,
    },
    {
      field_key: 'business_term_end',
      label: '营业期限截止日',
      system_key: 'business_term_end',
      data_type: 'date',
      required: false,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '选择营业期限截止日期',
      description: '修改后需重新确认，参与招标文件营业执照有效期检查',
      span: 12,
    },
    {
      field_key: 'bank_account_hash',
      label: '基本户指纹',
      system_key: 'bank_account_hash',
      data_type: 'string',
      required: false,
      editable: false,
      supported: false,
      disabledReason: '跨公司账户不可逆指纹，当前版本暂未支持人工维护，由系统自动生成',
      placeholder: '系统自动生成指纹',
      span: 12,
    },
    {
      field_key: 'registered_address',
      label: '注册住所',
      system_key: 'registered_address',
      data_type: 'string',
      required: true,
      editable: true,
      supported: true,
      is_starred: false,
      placeholder: '营业执照注册住所',
      span: 24,
    },
    {
      field_key: 'business_scope',
      label: '经营范围',
      system_key: 'business_scope',
      data_type: 'string',
      render_type: 'textarea',
      required: false,
      editable: true,
      supported: true,
      is_starred: false,
      placeholder: '照录营业执照登记的经营范围',
      span: 24,
    },
  ],
};

/** 投标项目表单模式（参考 PRD v1.8 §5.1.4 与 field_metadata.py） */
export const FALLBACK_PROJECT_FORM_SCHEMA: FormSchema = {
  category: 'project',
  category_name: '投标项目',
  description: '投标项目基本信息与规则配置表单',
  fields: [
    {
      field_key: 'project_name',
      label: '项目名称',
      system_key: 'project_name',
      data_type: 'string',
      required: true,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '请输入项目全称',
      description: '★ 关键字段，修改后需重新确认项目名称及一致性检查',
      span: 12,
    },
    {
      field_key: 'tender_no',
      label: '招标编号',
      system_key: 'tender_no',
      data_type: 'string',
      required: false,
      editable: true,
      supported: true,
      is_starred: false,
      placeholder: '招标/采购项目编号',
      span: 12,
    },
    {
      field_key: 'bid_deadline_at',
      label: '投标截止时间',
      system_key: 'bid_deadline_at',
      data_type: 'datetime',
      required: false,
      editable: true,
      supported: true,
      is_starred: true,
      placeholder: '选择投标截止时间',
      description: '★ 关键字段，修改后触发 3 天内急迫标书提醒重新计算',
      span: 12,
    },
    {
      field_key: 'project_category_code',
      label: '项目大类',
      system_key: 'project_category_code',
      data_type: 'string',
      render_type: 'select',
      required: true,
      editable: true,
      supported: true,
      is_starred: false,
      options: [
        { value: 'service', label: '服务' },
        { value: 'goods', label: '货物' },
        { value: 'engineering', label: '工程' },
      ],
      span: 12,
    },
    {
      field_key: 'budget_amount',
      label: '项目预算',
      system_key: 'budget_amount',
      data_type: 'number',
      required: false,
      editable: true,
      supported: true,
      is_starred: false,
      unit: '元',
      placeholder: '输入预算金额',
      span: 12,
    },
    {
      field_key: 'is_sensitive',
      label: '敏感项目保密',
      system_key: 'is_sensitive',
      data_type: 'boolean',
      render_type: 'switch',
      required: true,
      editable: true,
      supported: true,
      is_starred: false,
      description: '敏感项目禁止调用公网大模型，强制仅使用本地模型',
      span: 12,
    },
    {
      field_key: 'advanced_feature_flag',
      label: '二期高级特性',
      system_key: 'advanced_feature_flag',
      data_type: 'string',
      required: false,
      editable: false,
      supported: false,
      disabledReason: '二期协同特性，当前版本暂未开放',
      span: 24,
    },
  ],
};

export const BUILTIN_FORM_SCHEMAS: Record<string, FormSchema> = {
  org_entity: FALLBACK_ORG_ENTITY_FORM_SCHEMA,
  project: FALLBACK_PROJECT_FORM_SCHEMA,
};

/**
 * 解析 FormSchema：支持传入 Schema 对象或 category 字符串
 */
export function resolveFormSchema(schemaOrCategory: FormSchema | string): FormSchema {
  if (typeof schemaOrCategory === 'object' && schemaOrCategory && Array.isArray(schemaOrCategory.fields)) {
    return schemaOrCategory;
  }
  const cat = typeof schemaOrCategory === 'string' ? schemaOrCategory : (schemaOrCategory as any)?.category || '';
  const found = BUILTIN_FORM_SCHEMAS[cat];
  if (found) return found;

  return {
    category: cat || 'fallback-form',
    category_name: cat || '通用表单',
    fields: [
      { field_key: 'name', label: '名称', data_type: 'string', required: true, is_starred: true },
      { field_key: 'remarks', label: '备注', data_type: 'string', render_type: 'textarea' },
    ],
  };
}

/**
 * 客户端加载元数据函数（优先尝试真实 HTTP 接口，失败或离线时平滑降级到内置 Schema）
 */
export async function fetchFieldMetadata(
  category: string,
  token?: string
): Promise<FormSchema> {
  if (typeof window !== 'undefined' && window.fetch) {
    try {
      const headers: Record<string, string> = { Accept: 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await window.fetch(`/api/v1/metadata/fields/${encodeURIComponent(category)}`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.fields)) {
          return {
            category: data.category || category,
            category_name: data.category_name || category,
            fields: data.fields.map((f: any) => ({
              ...f,
              supported: f.supported !== false, // 默认支持
              span: f.render_type === 'textarea' || f.data_type === 'object' ? 24 : 12,
            })),
          };
        }
      }
    } catch {
      // 离线或无后端环境静默降级
    }
  }

  // 离线环境与测试环境安全降级
  return resolveFormSchema(category);
}
