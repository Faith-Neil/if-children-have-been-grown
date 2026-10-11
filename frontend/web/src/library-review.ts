// 为什么有这个文件：记住资料表单实际读取和核对过的版本，并在保存、载入时再次检查。
// 它解决什么问题：刷新资料库不能让旧表单覆盖他人的新资料；核对期间再次变化也保留原填写。
import type { Evidence } from './types';

export type LibraryReadState = { company_id: string; revision: number; items: Evidence[] };
export type LibraryReader = () => Promise<LibraryReadState>;
export type LibraryWriteVersion = { company_id: string; revision: number };
export type LibraryMutation = (path: string, method: string, body: unknown, expectedRevision?: LibraryWriteVersion) => Promise<unknown>;
export type LibraryReviewBasis = LibraryWriteVersion & { item_id: string | null; item_basis: string | null; item: Evidence | null };
export type CompanyCollectionSnapshot<T> = { revision: number; items: T[] };
export type CompanyOwnedSnapshot<T> = CompanyCollectionSnapshot<T> & { company_id: string };
export type CompanyReadSession = { company_id: string; account_id: string; epoch: number };

export function companyReadSessionMatches(start: CompanyReadSession, current: CompanyReadSession): boolean {
  return !!start.company_id && !!start.account_id && start.company_id === current.company_id && start.account_id === current.account_id && start.epoch === current.epoch;
}

export function visibleCompanyCollection<T>(snapshot: CompanyOwnedSnapshot<T>, company: string): CompanyOwnedSnapshot<T> {
  return company && snapshot.company_id === company ? snapshot : { company_id: '', items: [], revision: 0 };
}

export async function readCompanyCollections<L, T>(company: string, readLibrary: () => Promise<CompanyCollectionSnapshot<L>>, readTemplates: () => Promise<CompanyCollectionSnapshot<T>>) {
  const [library, templates] = await Promise.all([readLibrary(), readTemplates()]);
  // 两次读取可能跨过一次后台保存；各自的内容只能与各自返回的版本配对。
  return { library: { company_id: company, items: library.items, revision: library.revision }, templates: { company_id: company, items: templates.items, revision: templates.revision } };
}

function validVersion(version: LibraryWriteVersion): boolean {
  return !!version.company_id && Number.isSafeInteger(version.revision) && version.revision > 0;
}

export function libraryItemBasis(item: Evidence): string {
  return JSON.stringify({ id: item.id, company_id: item.company_id ?? null, revision: item.revision ?? null,
    name: item.name, type: item.type, content: item.content, valid_until: item.valid_until ?? null,
    status: item.status, reason: item.reason ?? '', usable_as_evidence: item.usable_as_evidence ?? null });
}

export function captureLibraryReview(current: LibraryReadState, itemId: string | null): LibraryReviewBasis {
  if (!validVersion(current)) throw new Error('尚未读取有效的公司资料库版本，请重新读取后再核对。');
  const item = itemId ? current.items.find(value => value.id === itemId) : null;
  if (itemId && !item) throw new Error('这条资料已不在当前可见列表中，当前填写仍保留，不能载入或保存。');
  if (item?.company_id && item.company_id !== current.company_id) throw new Error('这条资料不属于当前公司，不能载入或保存。');
  return { company_id: current.company_id, revision: current.revision, item_id: itemId,
    item_basis: item ? libraryItemBasis(item) : null, item: item ? { ...item } : null };
}

export function libraryReviewProblem(basis: LibraryReviewBasis | null, current: LibraryReadState): string | null {
  if (!basis || !validVersion(basis) || !validVersion(current)) return '尚未读取有效的资料版本，请先核对资料。当前填写仍保留。';
  if (basis.company_id !== current.company_id) return '当前公司已变化，原公司表单不能保存到另一家公司。当前填写仍保留。';
  if (basis.item_id) {
    const item = current.items.find(value => value.id === basis.item_id);
    if (!item || item.company_id && item.company_id !== current.company_id) return '这条资料已不可见或不属于当前公司，当前填写仍保留，不能继续保存。';
    if (basis.item_basis !== libraryItemBasis(item)) return '后台这条资料已更新，当前填写仍保留。请核对原版、你的填写和后台新版，再明确载入最新资料。';
  }
  if (basis.revision !== current.revision) return '公司资料库版本已更新，当前填写仍保留。即使这条资料未变，也请明确核对最新公司版本后再保存。';
  return null;
}

export function libraryWriteVersion(basis: LibraryReviewBasis | null, current: LibraryReadState): LibraryWriteVersion {
  const problem = libraryReviewProblem(basis, current);
  if (problem || !basis) throw new Error(problem ?? '尚未核对资料版本。');
  return { company_id: basis.company_id, revision: basis.revision };
}

export function libraryMutationVersion(expected: LibraryWriteVersion | undefined, current: LibraryWriteVersion): number {
  if (!validVersion(current)) throw new Error('尚未读取有效的当前公司资料库版本。');
  if (!expected) return current.revision; // 是否允许默认版本由调用入口判断；模板入口强制携带已核对版本。
  if (!validVersion(expected)) throw new Error('本次保存缺少有效的已核对公司版本，不能自动改用最新版本。');
  if (expected.company_id !== current.company_id) throw new Error('本次保存的原公司与当前公司不同，当前填写仍保留。');
  if (expected.revision !== current.revision) throw new Error('公司资料库又有变化，当前填写仍保留，请重新核对后再保存。');
  return expected.revision;
}

export function companyCollectionMutationVersion(path: string, expected: LibraryWriteVersion | undefined, library: LibraryWriteVersion, templates: LibraryWriteVersion): number {
  if (path === '/api/v1/sla/templates' || path.startsWith('/api/v1/sla/templates/')) {
    if (!expected) throw new Error('保存模板必须携带本次已核对的模板版本，不能借用普通资料的新版本。');
    return libraryMutationVersion(expected, templates);
  }
  if (path === '/api/v1/library' || path.startsWith('/api/v1/library/')) return libraryMutationVersion(expected, library);
  throw new Error('未识别的公司资料保存入口，请重新核对。');
}

export function confirmLibraryReview(original: LibraryReviewBasis, proposed: LibraryReviewBasis, current: LibraryReadState) {
  if (original.company_id !== proposed.company_id || original.item_id !== proposed.item_id) throw new Error('当前核对窗口不属于原公司或原资料，填写未替换，请重新核对。');
  const problem = libraryReviewProblem(proposed, current);
  if (problem) throw new Error('核对期间资料库又有变化，当前填写未替换。请重新打开核对窗口。');
  return { basis: captureLibraryReview(current, proposed.item_id), replace_form: original.item_basis !== proposed.item_basis };
}

export async function loadReviewedLibrary(original: LibraryReviewBasis, proposed: LibraryReviewBasis, read: LibraryReader) {
  // 页面缓存看不到别人在另一窗口保存的内容；明确载入前必须重新读取真实后台。
  const fresh = await read();
  return confirmLibraryReview(original, proposed, fresh);
}
