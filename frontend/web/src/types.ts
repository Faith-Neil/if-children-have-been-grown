// 为什么有这个文件：把后台主链路的数据字段集中说明。
// 它解决什么问题：页面之间传递同一项目、条款、章节和检查状态。
export type Volume = 'technical' | 'business';
export type Account = { id: string; name: string; company_id: string; role: 'editor' | 'manager' | 'viewer' };
export type Project = { id: string; name: string; company_id: string; revision?: number; tender_number?: string; deadline?: string | null; sensitive?: boolean };
export type Source = { file_id: string; page: number; quote: string };
export type Requirement = { id: string; text: string; category: string; volume: Volume; chapter_id: string | null; status: 'pending' | 'confirmed' | 'rejected'; response: string; reason: string; evidence_ids: string[]; source: Source };
export type Fact = { id: string; key: string; value: string; status: 'pending' | 'confirmed' | 'rejected'; reason: string; source: Source };
export type Conflict = { id: string; key: string; fact_ids: string[]; selected_fact_id: string | null; status: 'pending' | 'resolved'; reason: string };
export type TenderFile = { id: string; filename: string; size: number; sha256: string; media_type: string; status: string; page_count: number; pagination: string; warnings: string[]; download_url: string; text?: string; pages?: unknown[] };
export type Preview = { file_id: string; filename: string; pagination: string; warnings: string[]; pages: { page: number; text: string }[] };
export type Candidate = { id?: string; content: string; base_revision: number; input_fingerprint: string; provider: string; is_real_model: boolean };
export type Chapter = { id: string; title: string; volume: Volume; revision: number; content: string; lock: { owner_id: string; expires_at: string } | null; draft?: { sequence: number; content: string; base_revision: number } | null; candidate?: Candidate | null; requirement_ids?: string[] };
export type CheckIssue = { id: string; code: string; severity: string; message: string; requirement_id?: string; chapter_id?: string; evidence_id?: string };
export type Check = { id: string; volume: Volume | 'all'; passed: boolean; status: string; issues: CheckIssue[]; coverage: { implemented_rules: string[]; unimplemented_rules: string[]; complete: boolean }; fingerprint: string; created_at: string };
export type Export = { id: string; kind: string; check_id: string; created_at: string; excludes_drafts: boolean; status: string; volumes: { volume: Volume; filename: string; download_url: string }[] };
export type Job = { id: string; project_id: string; type: string; status: string; progress: number; message: string; created_at: string; completed_at: string; error: { code: string; message: string } | null; recoverable: boolean };
export type Evidence = { id: string; name: string; type: string; content: string; valid_until: string | null; status: string; company_id?: string; usable_as_evidence?: boolean; reason?: string };
export type Workspace = { revision: number; input_fingerprint: string; project: Project; stage: string; files: TenderFile[]; requirements: Requirement[]; facts: Fact[]; conflicts: Conflict[]; chapters: Chapter[]; checks: Check[]; exports: Export[]; jobs: Job[]; parse_confirmed: boolean; plan_confirmed: boolean };
