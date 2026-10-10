// 为什么有这个文件：把后台主链路的数据字段集中说明。
// 它解决什么问题：页面之间传递同一项目、条款、章节和检查状态。
export type Volume = 'technical' | 'business';
export type Account = { id: string; name: string; company_id: string; role: 'editor' | 'manager' | 'viewer' };
export type Project = { id: string; name: string; company_id: string; revision?: number; tender_number?: string; deadline?: string | null; sensitive?: boolean };
export type Source = { file_id: string; page: number; quote: string; filename?: string; sha256?: string; pagination?: string };
export type Requirement = { id: string; text: string; category: string; volume: Volume; chapter_id: string | null; status: 'pending' | 'confirmed' | 'rejected'; response: string; reason: string; evidence_ids: string[]; source: Source };
export type Fact = { id: string; key: string; value: string; status: 'pending' | 'confirmed' | 'rejected' | 'needs_review'; reason: string; source: Source | null; source_type?: string; sla_var_key?: string; unit?: string; required?: boolean };
export type SlaScalar = string | number | null;
export type SlaVariable = { var_key: string; label: string; group: string; value_type: 'integer' | 'decimal' | 'text'; default_value: SlaScalar; unit: string; compare_direction: 'lower_better' | 'higher_better' | 'exact'; best_committable_value: SlaScalar };
export type SlaTemplate = { id: string; company_id: string; revision: number; version_no: string; name: string; edition: string; service_hours: string; body_text: string; status: string; reason?: string; variables: SlaVariable[] };
export type SlaRow = SlaVariable & { project_value: SlaScalar; project_unit: string; tender_required_value: SlaScalar; tender_unit: string; requirement_id: string | null; source: Source | null; source_stale: boolean; judgment: 'satisfied' | 'not_satisfied' | 'exceeds_capability' | 'missing' | 'manual' | 'not_required' | 'unquantified'; judgment_label: string; message: string; exceeds_capability: boolean; review: { actor_id?: string; reviewer_id?: string; reviewed_by?: string; reviewed_at?: string; created_at?: string; at?: string; actor_name?: string; reason: string } | null; fact_status: Fact['status']; variable_token: string };
export type ProjectSla = { template_id: string; template_name: string; template_revision: number; template_stale: boolean; rows: SlaRow[]; commitments?: { id: string; filename: string; download_url: string; status: 'valid' | 'stale'; created_at: string }[] };
export type Conflict = { id: string; key: string; fact_ids: string[]; selected_fact_id: string | null; status: 'pending' | 'resolved'; reason: string };
export type TenderFile = { id: string; filename: string; size: number; sha256: string; media_type: string; status: string; page_count: number; pagination: string; warnings: string[]; download_url: string; text?: string; pages?: unknown[] };
export type Preview = { file_id: string; filename: string; pagination: string; warnings: string[]; pages: { page: number; text: string }[] };
export type ChapterWritingInput = { fact_ids: string[]; writing_points: string; target_length: number | null };
export type WritingPlan = { confirmed_by: string | null; confirmed_by_name?: string | null; confirmed_at: string | null; chapters: (ChapterWritingInput & { id: string })[] };
export type WritingInputSnapshot = {
  scope: 'whole_chapter'; created_at: string; input_fingerprint: string;
  project: { id: string; name: string; tender_number?: string; deadline?: string | null; sensitive?: boolean };
  chapter: { id: string; title: string; volume: Volume; base_revision: number };
  plan: ChapterWritingInput & { confirmed_by: string | null; confirmed_at: string | null };
  requirements: Pick<Requirement, 'id' | 'text' | 'response' | 'status' | 'source' | 'evidence_ids'>[];
  evidence: { id: string; name: string; revision: number; type: string; valid_until: string | null; status: string; content: string; requirement_ids: string[] }[];
  facts: (Pick<Fact, 'id' | 'key' | 'value' | 'status' | 'source' | 'source_type' | 'sla_var_key'> & { unit: string; required: boolean; variable: string; label?: string })[];
  omitted_inputs: { kind: string; id: string; label: string; reason: string }[];
  official_content: string;
};
export type WritingInputPreview = { source_scope: 'whole_chapter'; input_snapshot: WritingInputSnapshot; ready: boolean; issues: { code: string; message: string }[] };
export type Candidate = { id?: string; content: string; base_revision: number; input_fingerprint: string; provider: string; is_real_model: boolean; source_scope?: 'whole_chapter' | null; input_snapshot?: WritingInputSnapshot | null; status?: 'valid' | 'stale' };
export type Chapter = { id: string; title: string; volume: Volume; revision: number; content: string; lock: { owner_id: string; expires_at: string } | null; draft?: { sequence: number; content: string; base_revision: number; input_fingerprint?: string | null } | null; candidate?: Candidate | null; requirement_ids?: string[]; writing_input?: ChapterWritingInput };
export type CheckIssue = { id: string; code: string; severity: string; message: string; requirement_id?: string; chapter_id?: string; evidence_id?: string };
export type Check = { id: string; volume: Volume | 'all'; passed: boolean; status: string; issues: CheckIssue[]; coverage: { implemented_rules: string[]; unimplemented_rules: string[]; complete: boolean }; fingerprint: string; created_at: string };
export type Export = { id: string; kind: string; check_id: string; created_at: string; excludes_drafts: boolean; status: string; volumes: { volume: Volume; filename: string; download_url: string }[] };
export type Job = { id: string; project_id: string; type: string; status: string; progress: number; message: string; created_at: string; completed_at: string; error: { code: string; message: string } | null; recoverable: boolean };
export type Evidence = { id: string; name: string; type: string; content: string; valid_until: string | null; status: string; company_id?: string; usable_as_evidence?: boolean; reason?: string; revision?: number };
export type Workspace = { revision: number; input_fingerprint: string; project: Project; stage: string; files: TenderFile[]; requirements: Requirement[]; facts: Fact[]; conflicts: Conflict[]; chapters: Chapter[]; checks: Check[]; exports: Export[]; jobs: Job[]; parse_confirmed: boolean; plan_confirmed: boolean; sla?: ProjectSla | null; writing_plan?: WritingPlan };
