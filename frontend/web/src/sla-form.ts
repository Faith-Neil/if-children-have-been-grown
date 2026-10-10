// 为什么有这个文件：把服务承诺表单中的文字转换为明确的数值，并保留正文变量完整标记。
// 它解决什么问题：避免空值变成零、无效数字进入接口，或插入变量时意外覆盖正文。
import type { SlaScalar, SlaVariable } from './types';

export function slaScalar(value: unknown, valueType: SlaVariable['value_type'], fieldName: string): SlaScalar {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  const text = String(value).trim();
  if (valueType === 'text') return text;
  if (!/^\d+(?:\.\d+)?$/.test(text)) throw new Error(`${fieldName}请填写非负数，不能使用单位、负数或特殊数字。`);
  const numeric = Number(text);
  if (!Number.isFinite(numeric) || (valueType === 'integer' && !Number.isSafeInteger(numeric))) throw new Error(`${fieldName}需要填写${valueType === 'integer' ? '安全范围内的整数' : '有限数字'}。`);
  return numeric;
}

export const slaUnits = [{ value: 'minute', label: '分钟' }, { value: 'hour', label: '小时' }, { value: 'calendar_day', label: '自然日' }, { value: 'working_day', label: '工作日' }, { value: 'per_month', label: '次/月' }, { value: 'per_quarter', label: '次/季' }, { value: 'per_half_year', label: '次/半年' }, { value: 'per_year', label: '次/年' }, { value: 'person', label: '人' }, { value: 'piece', label: '个' }, { value: 'percent', label: '%' }, { value: 'class_hour', label: '课时' }, { value: 'month', label: '月' }, { value: '', label: '无单位（文字）' }];
export const slaGroups = [{ value: 'response', label: '响应' }, { value: 'onsite', label: '到场' }, { value: 'restore', label: '恢复' }, { value: 'inspection', label: '巡检' }, { value: 'resident', label: '驻场' }, { value: 'report', label: '报告' }, { value: 'spare_parts', label: '备件' }, { value: 'training', label: '培训' }, { value: 'warranty', label: '质保' }, { value: 'delivery', label: '交付' }, { value: 'other', label: '其他' }];
export const slaUnitName = (unit?: string) => slaUnits.find(item => item.value === unit)?.label.replace('无单位（文字）', '') ?? unit ?? '';
export function displaySlaValue(value: SlaScalar | undefined, unit?: string, empty = '未填写') {
  return value === null || value === undefined || value === '' ? empty : `${value}${unit ? ` ${slaUnitName(unit)}` : ''}`;
}

export function slaVariablePayload(value: SlaVariable): SlaVariable {
  const key = String(value.var_key || '').trim();
  if (!/^[A-Za-z][A-Za-z0-9_.-]{0,99}$/.test(key)) throw new Error('指标标识须由英文字母开头，只含字母、数字、点、下划线或短横线。');
  return { ...value, var_key: key, label: String(value.label || '').trim(), group: String(value.group || '').trim(), unit: String(value.unit || '').trim(), default_value: slaScalar(value.default_value, value.value_type, `${value.label}默认值`), best_committable_value: slaScalar(value.best_committable_value, value.value_type, `${value.label}公司能力极限`) };
}

export function insertSlaToken(content: string, start: number, end: number, token: string) {
  if (!/^\{\{sla:[A-Za-z][A-Za-z0-9_.-]{0,99}\}\}$/.test(token)) throw new Error('这不是完整的服务承诺变量，请重新读取项目矩阵。');
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > content.length) throw new Error('正文位置已变化，请重新选择插入位置。');
  return { content: content.slice(0, start) + token + content.slice(end), cursor: start + token.length };
}

export function insertSlaMeasurement(content: string, start: number, end: number, token: string, unit: string) {
  const result = insertSlaToken(content, start, end, token);
  const label = slaUnitName(unit);
  if (!label) return result;
  const after = result.content.slice(result.cursor).trimStart();
  const suffix = slaUnits.filter(item => item.value).sort((a, b) => b.label.length - a.label.length).find(item => after.startsWith(item.label) || after.startsWith(item.value));
  if (suffix && slaUnitName(suffix.value) !== label) throw new Error('选区后面的单位与变量不同，请把旧单位一并选中，再插入完整承诺。');
  return suffix ? result : { content: result.content.slice(0, result.cursor) + label + result.content.slice(result.cursor), cursor: result.cursor + label.length };
}
