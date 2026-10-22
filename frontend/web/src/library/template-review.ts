// 为什么有这个文件：记住服务承诺模板及指标数组实际读取过的内容和版本。
// 它解决什么问题：普通资料刷新不能为旧模板背书，核对期间后台再次修改也不覆盖未保存填写。
import type { SlaTemplate } from '../shared/types';
import type { LibraryWriteVersion } from './library-review';

export type TemplateReadState = LibraryWriteVersion & { items: SlaTemplate[] };
export type TemplateReader = () => Promise<TemplateReadState>;
export type TemplateReviewBasis = LibraryWriteVersion & { template_id: string | null; template_basis: string | null; template: SlaTemplate | null };

function validVersion(version: LibraryWriteVersion): boolean {
  return !!version.company_id && Number.isSafeInteger(version.revision) && version.revision > 0;
}

export function templateItemBasis(item: SlaTemplate): string {
  return JSON.stringify({ id: item.id, company_id: item.company_id, revision: item.revision, name: item.name,
    version_no: item.version_no, edition: item.edition, service_hours: item.service_hours, body_text: item.body_text,
    status: item.status, reason: item.reason ?? '', variables: item.variables.map(variable => ({
      var_key: variable.var_key, label: variable.label, group: variable.group, value_type: variable.value_type,
      default_value: variable.default_value, unit: variable.unit, compare_direction: variable.compare_direction,
      best_committable_value: variable.best_committable_value,
    })) });
}

export function copyTemplate(item: SlaTemplate): SlaTemplate {
  return { ...item, variables: item.variables.map(variable => ({ ...variable })) };
}

export function captureTemplateReview(current: TemplateReadState, templateId: string | null): TemplateReviewBasis {
  if (!validVersion(current)) throw new Error('尚未读取有效的公司模板版本，请重新读取后再核对。');
  const item = templateId ? current.items.find(value => value.id === templateId) : null;
  if (templateId && !item) throw new Error('这份模板已不可见，当前填写仍保留，不能载入或保存。');
  if (item && item.company_id !== current.company_id) throw new Error('这份模板不属于当前公司，不能载入或保存。');
  return { company_id: current.company_id, revision: current.revision, template_id: templateId,
    template_basis: item ? templateItemBasis(item) : null, template: item ? copyTemplate(item) : null };
}

export function templateReviewProblem(basis: TemplateReviewBasis | null, current: TemplateReadState): string | null {
  if (!basis || !validVersion(basis) || !validVersion(current)) return '尚未读取有效的模板版本，请先核对。当前填写仍保留。';
  if (basis.company_id !== current.company_id) return '当前公司已变化，原模板不能保存到另一家公司。当前填写仍保留。';
  if (basis.template_id) {
    const item = current.items.find(value => value.id === basis.template_id);
    if (!item || item.company_id !== current.company_id) return '这份模板已不可见或不属于当前公司，当前填写仍保留，不能继续保存。';
    if (templateItemBasis(item) !== basis.template_basis) return '后台这份服务模板或指标已更新，当前填写仍保留。请核对原模板、你的填写和后台新版，再明确载入。';
  }
  if (basis.revision !== current.revision) return '模板读取版本已更新，当前填写仍保留。请明确核对当前模板版本后再保存。';
  return null;
}

export function templateWriteVersion(basis: TemplateReviewBasis | null, current: TemplateReadState): LibraryWriteVersion {
  const problem = templateReviewProblem(basis, current);
  if (problem || !basis) throw new Error(problem ?? '尚未核对模板版本。');
  return { company_id: basis.company_id, revision: basis.revision };
}

export async function loadReviewedTemplate(original: TemplateReviewBasis, proposed: TemplateReviewBasis, read: TemplateReader) {
  if (original.company_id !== proposed.company_id || original.template_id !== proposed.template_id) throw new Error('当前核对窗口不属于原公司或原模板，填写未替换，请重新核对。');
  const fresh = await read();
  if (templateReviewProblem(proposed, fresh)) throw new Error('核对期间模板库又有变化，当前填写未替换。请重新打开核对窗口。');
  return { basis: captureTemplateReview(fresh, proposed.template_id), replace_form: original.template_basis !== proposed.template_basis };
}
