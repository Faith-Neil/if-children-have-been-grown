// 为什么有这个文件：提供表单通用的脏数据检测、未保存拦截纯逻辑、服务端字段级错误就近映射与滚动定位。
// 它解决什么问题：
// 1. 脏数据检测与 ★ 关键字段变更统计，统一长表单修改项计数；
// 2. 服务端 400 / 422 等字段级错误体解析并映射为 Ant Design 表单项错误格式（{ name, errors }）；
// 3. 就近报错平滑滚动定位（scrollIntoView 与 focus），避免长表单提交失败后用户无法感知错误所在；
// 4. 浏览器 beforeunload 原生离开保护与路由切换模态确认文案。

/* ========================================================================= */
/* 1. 契约类型定义                                                           */
/* ========================================================================= */

export interface FieldChangeSummary {
  /** 表单是否处于脏数据状态（发生过修改） */
  isDirty: boolean;
  /** 已修改的字段数量 */
  modifiedCount: number;
  /** 已修改字段键名列表 */
  modifiedKeys: string[];
  /** 已修改的 ★ 关键字段数量 */
  starredModifiedCount: number;
  /** 已修改的 ★ 关键字段键名列表 */
  starredModifiedKeys: string[];
  /** 格式化的用户可见摘要提示文案 */
  summaryText: string;
}

export interface ServerFieldError {
  field: string;
  message: string;
}

export interface AntFormFieldError {
  name: string | string[];
  errors: string[];
}

export interface MappedServerErrors {
  /** 映射后的 Ant Design Form 错误项列表 */
  fieldErrors: AntFormFieldError[];
  /** 首个出错的字段名（用于平滑滚动定位） */
  firstErrorField: string | null;
  /** 顶层非字段特定的全局通用错误信息 */
  generalMessage: string | null;
}

export const FORM_LEAVE_COPY = {
  title: '当前页面有未保存的修改',
  content: '离开页面将丢失已修改的表单内容。请确认是否继续离开？',
  okText: '放弃修改并离开',
  cancelText: '留在本页继续编辑',
};

/* ========================================================================= */
/* 2. 脏数据比对与已修改项统计                                               */
/* ========================================================================= */

/**
 * 判断两个表单字段值是否等价（纯函数，处理 null、undefined、空串、两端空白与数值归一化）
 */
export function areValuesEquivalent(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if ((a === undefined || a === null || a === '') && (b === undefined || b === null || b === '')) {
    return true;
  }
  if (typeof a === 'string' && typeof b === 'string') {
    return a.trim() === b.trim();
  }
  if (typeof a === 'number' && typeof b === 'number') {
    return a === b;
  }
  if (typeof a === 'boolean' && typeof b === 'boolean') {
    return a === b;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, index) => areValuesEquivalent(item, b[index]));
  }
  return false;
}

/**
 * 计算表单脏数据状态与修改字段统计
 */
export function detectDirtyFields(
  initialValues: Record<string, any> = {},
  currentValues: Record<string, any> = {},
  starredKeys: string[] | Set<string> = []
): FieldChangeSummary {
  const starredKeySet = starredKeys instanceof Set ? starredKeys : new Set(starredKeys);
  const allKeys = new Set([...Object.keys(initialValues || {}), ...Object.keys(currentValues || {})]);

  const modifiedKeys: string[] = [];
  const starredModifiedKeys: string[] = [];

  for (const key of allKeys) {
    const initVal = initialValues ? initialValues[key] : undefined;
    const currVal = currentValues ? currentValues[key] : undefined;

    if (!areValuesEquivalent(initVal, currVal)) {
      modifiedKeys.push(key);
      if (starredKeySet.has(key)) {
        starredModifiedKeys.push(key);
      }
    }
  }

  const modifiedCount = modifiedKeys.length;
  const starredModifiedCount = starredModifiedKeys.length;
  const isDirty = modifiedCount > 0;

  let summaryText = '表单内容与初始版本一致';
  if (isDirty) {
    if (starredModifiedCount > 0) {
      summaryText = `已修改 ${modifiedCount} 项（含 ${starredModifiedCount} 项 ★ 关键字段）`;
    } else {
      summaryText = `已修改 ${modifiedCount} 项`;
    }
  }

  return {
    isDirty,
    modifiedCount,
    modifiedKeys,
    starredModifiedCount,
    starredModifiedKeys,
    summaryText,
  };
}

/* ========================================================================= */
/* 3. 服务端字段级错误解析与就近映射                                         */
/* ========================================================================= */

/**
 * 将服务端返回的错误（ApiError、422 ValidationError、details 数组或键值字典）
 * 映射为 Ant Design Form 接受的 fields 错误格式与首错字段名
 */
export function mapServerFieldErrors(error: unknown): MappedServerErrors {
  const fieldErrors: AntFormFieldError[] = [];
  const seenFields = new Set<string>();
  let firstErrorField: string | null = null;
  let generalMessage: string | null = null;

  if (!error || typeof error !== 'object') {
    return { fieldErrors: [], firstErrorField: null, generalMessage: null };
  }

  const errObj = error as Record<string, any>;

  // 1. 尝试提取全局错误文案
  if (typeof errObj.message === 'string' && errObj.message) {
    generalMessage = errObj.message;
  } else if (typeof errObj.detail === 'string' && errObj.detail) {
    generalMessage = errObj.detail;
  }

  // 辅助函数：记录单个字段错误
  const recordFieldError = (field: string, msg: string) => {
    if (!field || typeof field !== 'string') return;
    const cleanField = field.trim();
    if (!cleanField) return;

    if (!firstErrorField) {
      firstErrorField = cleanField;
    }

    if (!seenFields.has(cleanField)) {
      seenFields.add(cleanField);
      fieldErrors.push({
        name: cleanField,
        errors: [msg || '字段验证未通过'],
      });
    } else {
      const existing = fieldErrors.find(item => item.name === cleanField);
      if (existing && msg && !existing.errors.includes(msg)) {
        existing.errors.push(msg);
      }
    }
  };

  // 2. 场景 A: 错误对象直接携带 field 和 message/reason
  if (typeof errObj.field === 'string') {
    const msg = String(errObj.message || errObj.reason || errObj.error || '验证失败');
    recordFieldError(errObj.field, msg);
  }

  // 3. 场景 B: 包含 details 数组（如 FastAPI / Pydantic / 统一错误体）
  // 结构形如 details: [{ field: "name", message: "..." }, { loc: ["body", "name"], msg: "..." }]
  if (Array.isArray(errObj.details)) {
    for (const item of errObj.details) {
      if (typeof item === 'object' && item !== null) {
        let fieldName = '';
        if (typeof item.field === 'string') {
          fieldName = item.field;
        } else if (Array.isArray(item.loc) && item.loc.length > 0) {
          fieldName = String(item.loc[item.loc.length - 1]);
        }

        const msg = String(item.message || item.msg || item.reason || item.error || '验证未通过');
        if (fieldName) {
          recordFieldError(fieldName, msg);
        }
      }
    }
  } else if (typeof errObj.details === 'object' && errObj.details !== null) {
    // 场景 C: details 为字典映射 { "credit_code": "统一社会信用代码格式错误" }
    for (const [key, val] of Object.entries(errObj.details)) {
      if (typeof val === 'string') {
        recordFieldError(key, val);
      } else if (Array.isArray(val) && val.length > 0) {
        recordFieldError(key, String(val[0]));
      }
    }
  }

  // 4. 场景 D: 嵌套在 errObj.error 内部
  if (typeof errObj.error === 'object' && errObj.error !== null) {
    const subErrors = mapServerFieldErrors(errObj.error);
    for (const sub of subErrors.fieldErrors) {
      const fieldName = Array.isArray(sub.name) ? sub.name[0] : sub.name;
      recordFieldError(fieldName, sub.errors[0]);
    }
    if (!generalMessage && subErrors.generalMessage) {
      generalMessage = subErrors.generalMessage;
    }
  }

  return {
    fieldErrors,
    firstErrorField,
    generalMessage,
  };
}

/* ========================================================================= */
/* 4. 就近定位与平滑滚动聚焦                                                 */
/* ========================================================================= */

export interface ScrollOptions {
  behavior?: ScrollBehavior;
  block?: ScrollLogicalPosition;
  focus?: boolean;
}

/**
 * 平滑滚动将指定的出错字段控件移至视口居中，并自动尝试聚焦输入框
 */
export function scrollFieldIntoView(
  fieldName: string,
  options: ScrollOptions = {}
): boolean {
  if (typeof document === 'undefined' || !fieldName) {
    return false;
  }

  const { behavior = 'smooth', block = 'center', focus = true } = options;

  // 尝试按以下选择器寻找对应的表单项或输入框
  const selectors = [
    `[data-testid="form-item-${fieldName}"]`,
    `[data-testid="input-${fieldName}"]`,
    `#${fieldName}`,
    `[name="${fieldName}"]`,
    `[id*="${fieldName}"]`,
    `.ant-form-item-has-error`,
  ];

  let targetElement: HTMLElement | null = null;
  for (const selector of selectors) {
    try {
      const el = document.querySelector<HTMLElement>(selector);
      if (el) {
        targetElement = el;
        break;
      }
    } catch {
      // 容忍非法选择器
    }
  }

  if (!targetElement) {
    return false;
  }

  // 执行平滑滚动
  try {
    targetElement.scrollIntoView({ behavior, block });
  } catch {
    // 兼容不支持配置对象的旧环境
    targetElement.scrollIntoView();
  }

  // 自动聚焦内部可交互控件
  if (focus) {
    const focusable = targetElement.querySelector<HTMLElement>(
      'input:not([disabled]), textarea:not([disabled]), [tabindex]:not([disabled]), button:not([disabled])'
    ) || targetElement;

    if (focusable && typeof focusable.focus === 'function') {
      setTimeout(() => {
        try {
          focusable.focus();
        } catch {
          // 忽略聚焦失败
        }
      }, 100);
    }
  }

  return true;
}

/* ========================================================================= */
/* 5. 离开未保存拦截纯逻辑                                                   */
/* ========================================================================= */

/**
 * 决定是否在离开页面时触发拦截提示
 */
export function shouldBlockNavigation(
  isDirty: boolean,
  isConfirmed: boolean = false
): boolean {
  if (!isDirty) return false;
  return !isConfirmed;
}

/**
 * 原生 beforeunload 事件处理器纯逻辑
 */
export function applyBeforeUnloadEvent(
  isDirty: boolean,
  event: { preventDefault(): void; returnValue: string }
): boolean {
  if (!isDirty) return false;
  event.preventDefault();
  event.returnValue = FORM_LEAVE_COPY.content;
  return true;
}
