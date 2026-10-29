// 为什么有这个文件：把后台主链路的数据字段集中说明。
// 它解决什么问题：页面之间传递同一项目、条款、章节和检查状态。
import type { SystemRole } from './roles.ts';

export type Volume = 'technical' | 'business';

export interface VolumeStatus {
  volume_id: Volume;
  project_id: string;
  is_finalized: boolean;
  finalized_by?: string | null;
  finalized_at?: string | null;
  unlocked_by?: string | null;
  unlocked_at?: string | null;
  unlock_reason?: string | null;
  cross_review?: CrossReview | null;
  pending_human_issues?: number;
}

export type CrossReviewStatus = 'none' | 'pending' | 'approved' | 'returned';
export interface CrossReview {
  status: CrossReviewStatus;
  stale: boolean;
  reviewer_id?: string | null;
  reviewer_name?: string | null;
  assigned_by?: string | null;
  assigned_at?: string | null;
  decided_at?: string | null;
  decision_note?: string;
  history?: { at: string; action: string; actor_id: string; note?: string; reviewer_id?: string }[];
}

export type HumanIssueStatus = 'pending_fix' | 'pending_human' | 'resolved' | 'human_handled' | 'rejected' | 'void';
export interface HumanIssue {
  id: string; number: string; chapter_id: string; volume: Volume; code: string; rule: string;
  source: 'rule' | 'model_review'; level: 'blocker' | 'warning' | 'hint'; severity: 'high' | 'medium' | 'low';
  status: HumanIssueStatus; route: 'auto_fix' | 'direct_human' | 'escalated_human';
  human_reason?: string | null; human_reason_label: string; paragraph_index: number; quote: string;
  message: string; suggestion: string; fix_count: number; loop_no: number;
  permissions: { resolve: boolean; reject: boolean };
}
export interface ChapterLoopState {
  chapter_id: string; loop_no: number; kind: string; status: 'completed' | 'pending_human' | 'human_handled';
  status_label: string; stop_reason: string; stop_reason_label: string; max_rounds: number; rolled_back: boolean;
  started_at: string; stale: boolean; loop_count: number;
  started_by?: string | null; checked_revision?: number | null; result_revision?: number | null;
  meta?: ChapterLoopMeta;
  rounds: LoopRound[];
}
export interface LoopRound {
  round: number; found: number; new: number; resolved: number; modified_paragraphs: number[]; conclusion: string;
  codes?: string[]; fixes?: { paragraph_index: number; by: 'model' | 'rule'; codes: string[] }[];
}
export interface SummaryRelay {
  status: 'used' | 'missing' | 'not_applicable' | 'not_recorded'; chapter_id?: string; title?: string;
  summary?: string; message?: string; revision?: number;
}
export interface ChapterLoopMeta {
  task?: string; task_label?: string; model?: string | null; is_real_model?: boolean; model_config_id?: string | null;
  model_name?: string | null; fixer?: string; base_revision?: number | null; context_fingerprint?: string | null;
  inputs?: Partial<Record<'requirements' | 'evidence' | 'snippets' | 'facts' | 'omitted' | 'truncated', number>> & { critical?: boolean };
  summary_relay?: SummaryRelay;
}
export interface ChapterLoopHistoryEntry {
  loop_no: number; kind: string; stop_reason: string; stop_reason_label?: string; rounds: LoopRound[]; rolled_back: boolean;
  started_at: string; started_by?: string | null; checked_revision?: number | null; result_revision?: number | null; meta?: ChapterLoopMeta;
}
export interface ChapterLoopRow {
  chapter_id: string; title: string; volume: Volume; number: number; chapter_revision: number; has_content: boolean;
  assignee_name?: string | null; volume_finalized: boolean; can_recheck: boolean; loop: ChapterLoopState | null;
  pending: number; resolved: number;
}
export interface ChapterLoopList {
  revision: number; project_id: string; volume: Volume | 'all';
  totals: Record<'chapters' | 'not_started' | 'completed' | 'pending_human' | 'human_handled' | 'stale', number>;
  chapters: ChapterLoopRow[];
}
export interface ChapterLoopDetail {
  revision: number; chapter_id: string; title: string; volume: Volume; chapter_revision: number;
  loop: ChapterLoopState | null; history: ChapterLoopHistoryEntry[];
  counts: Record<HumanIssueStatus, number>; issues: HumanIssue[];
}
export interface HumanQueueChapter {
  chapter_id: string; title: string; volume: Volume; number: number; assignee_id?: string | null;
  assignee_name?: string | null; volume_finalized: boolean; can_recheck: boolean; loop: ChapterLoopState | null;
  issues: HumanIssue[];
}
export interface HumanQueue {
  revision: number; project_id: string; volume: Volume | 'all'; deadline: string;
  summary: { pending: number; chapters: number; by_reason: { reason: string; label: string; count: number }[] };
  chapters: HumanQueueChapter[];
}
export type ScanHitState = 'suspected' | 'covered' | 'added' | 'excluded';
export interface ScanHit {
  id: string; file_id: string; filename: string; page: number; quote: string; terms: string[];
  status: 'open' | 'added' | 'excluded'; state: ScanHitState; covered_by?: string | null; reason: string; scan_version: string;
}
export interface ScanHitList {
  revision: number; project_id: string; scan_version: string; can_handle: boolean; hits: ScanHit[];
  summary: { total: number; suspected: number; covered: number; added: number; excluded: number; too_many: boolean };
}

export interface VolumeFinalizeRequest {
  check_id?: string | null;
}

export interface VolumeUnlockRequest {
  reason: string;
}

export interface VolumeFinalizeResponse {
  revision: number;
  project_id: string;
  volume_id: string;
  is_finalized: boolean;
  finalized_by?: string | null;
  finalized_at?: string | null;
  volume?: VolumeStatus | null;
}

export interface VolumeStatusResponse {
  revision: number;
  project_id: string;
  volume_id: string;
  is_finalized: boolean;
  finalized_by?: string | null;
  finalized_at?: string | null;
  unlocked_by?: string | null;
  unlocked_at?: string | null;
  unlock_reason?: string | null;
  volume?: VolumeStatus | null;
}

export interface VolumeListResponse {
  revision: number;
  project_id: string;
  volumes: VolumeStatus[];
}
export type AuthMode = 'authenticated';
export type RoleMode = 'rbac-8roles';
export type AccountRole = SystemRole | 'editor' | 'manager' | 'viewer' | 'readonly' | 'reviewer' | 'writer' | 'lead';
export type Account = { id: string; name: string; company_id: string; role: AccountRole };
// 支持合成演示模式与正式八角色会话；导航与动作采用后台返回值。
export type ApplicationSession = {
  auth_mode: AuthMode; role_mode: RoleMode;
  user: Account & { roles: string[]; primary_role: string };
  scope: { kind: 'company'; active_company_id: string; allowed_company_ids: string[] };
  navigation: { route_id: string; path: string; access: 'read' | 'write' }[];
  allowedActions: string[]; home_path: string;
  session: { expires_at: string | null; renew_supported: boolean };
  project_access?: { id: string; revision: number; route_permissions: string[]; permissions: ProjectPermissions; chapters: { id: string; volume: Volume; permissions: ChapterPermissions }[] };
};
export type VolumeMode = 'both' | 'technical_only';
export type Project = {
  id: string;
  volume_mode?: VolumeMode;
  name: string;
  company_id: string;
  revision?: number;
  tender_number?: string;
  deadline?: string | null;
  sensitive?: boolean;
  target_amount?: number | string;
  status?: 'preparing' | 'writing' | 'reviewing' | 'completed' | string;
  stage?: string;
  volumes_status?: { technical?: string; business?: string };
  description?: string;
  created_at?: string;
};
export type ProjectRole = 'lead' | 'writer' | 'readonly';
export type ProjectMember = { user_id: string; name: string; company_role: Account['role']; project_role: ProjectRole; volumes: Volume[] };
export type ProjectTeam = { volume_mode?: VolumeMode;
  members: ProjectMember[]; volumes: { volume: Volume; owner_id: string | null; owner_name: string | null }[];
  assembly_owner_id: string | null; available_accounts: Account[];
  handoffs: { id: string; actor_id: string; at: string; reason: string; chapter_ids: string[]; previous_user_ids: string[]; preserved_draft_count: number; revoked_lock_count: number }[];
};
export type ProjectPermissions = { manage_team: boolean; manage_project: boolean; manage_structure: boolean; prepare_sources: boolean; manage_sla: boolean; edit_facts: boolean; confirm_facts: boolean; check_all: boolean; export_internal: boolean; check_volumes: Volume[]; export_volumes: Volume[] };
export type ChapterPermissions = { edit: boolean; confirm_plan: boolean; generate: boolean; manage_structure: boolean; assign: boolean; takeover: boolean };
export type Source = { file_id: string; page: number; quote: string; filename?: string; sha256?: string; pagination?: string };
export type Requirement = { id: string; text: string; category: string; volume: Volume; chapter_id: string | null; status: 'pending' | 'confirmed' | 'rejected'; response: string; reason: string; evidence_ids: string[]; source: Source; permissions?: { edit: boolean; response: boolean; route: boolean }; proof_requirements?: string; section_path?: string[]; section_kind?: string; score?: number | null };
export type Fact = { id: string; key: string; value: string; status: 'pending' | 'confirmed' | 'rejected' | 'needs_review'; reason: string; source: Source | null; source_type?: string; sla_var_key?: string; unit?: string; required?: boolean };
export type SlaScalar = string | number | null;
export type SlaVariable = { var_key: string; label: string; group: string; value_type: 'integer' | 'decimal' | 'text'; default_value: SlaScalar; unit: string; compare_direction: 'lower_better' | 'higher_better' | 'exact'; best_committable_value: SlaScalar };
export type SlaTemplate = { id: string; company_id: string; revision: number; version_no: string; name: string; edition: string; service_hours: string; body_text: string; status: string; reason?: string; variables: SlaVariable[] };
export type SlaRow = SlaVariable & { project_value: SlaScalar; project_unit: string; tender_required_value: SlaScalar; tender_unit: string; requirement_id: string | null; source: Source | null; source_stale: boolean; judgment: 'satisfied' | 'not_satisfied' | 'exceeds_capability' | 'missing' | 'manual' | 'not_required' | 'unquantified'; judgment_label: string; message: string; exceeds_capability: boolean; review: { actor_id?: string; reviewer_id?: string; reviewed_by?: string; reviewed_at?: string; created_at?: string; at?: string; actor_name?: string; reason: string } | null; fact_status: Fact['status']; variable_token: string };
export type ProjectSla = { template_id: string; template_name: string; template_revision: number; template_stale: boolean; rows: SlaRow[]; commitments?: { id: string; filename: string; download_url: string; status: 'valid' | 'stale'; created_at: string }[] };
export type Conflict = { id: string; key: string; fact_ids: string[]; selected_fact_id: string | null; status: 'pending' | 'resolved'; reason: string };
export type TenderFile = { id: string; filename: string; size: number; sha256: string; media_type: string; status: string; page_count: number; pagination: string; warnings: string[]; download_url: string; text?: string; pages?: unknown[]; extraction?: TenderExtractionSummary };
export type TenderExtractionSummary = { structured: boolean; sections: number; extracted: number; mandatory: number; by_section_kind: Record<string, number>; skipped_items: Record<string, number> };
export type Preview = { file_id: string; filename: string; pagination: string; warnings: string[]; pages: { page: number; text: string; regions?: { text: string; boxes: number[][] }[] }[] };
export type ChapterWritingInput = { fact_ids: string[]; writing_points: string; target_length: number | null; confirmed_by?: string | null; confirmed_by_name?: string | null; confirmed_at?: string | null; is_current?: boolean };
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
  /** 公司知识库检索候选：只是写作参考，引用写 cite_tag（[片:id]）；挂到响应矩阵后才是 [证]。 */
  retrieved_evidence?: RetrievedEvidence[];
  official_content: string;
};
export type WritingInputPreview = { source_scope: 'whole_chapter'; input_snapshot: WritingInputSnapshot; ready: boolean; issues: { code: string; message: string }[] };
export type Candidate = { id?: string; content: string; base_revision: number; input_fingerprint: string; provider: string; is_real_model: boolean; source_scope?: 'whole_chapter' | null; input_snapshot?: WritingInputSnapshot | null; status?: 'valid' | 'stale' };
export type Chapter = { id: string; title: string; volume: Volume; revision: number; content: string; lock: { owner_id: string; expires_at: string } | null; draft?: { sequence: number; content: string; base_revision: number; input_fingerprint?: string | null } | null; candidate?: Candidate | null; requirement_ids?: string[]; writing_input?: ChapterWritingInput; assignee_id?: string | null; assignee_name?: string | null; permissions?: ChapterPermissions };
export type CheckRelease = { reason: string; by: string; by_name?: string; at: string; decision?: 'keep' | 'accept' };
export type CheckIssue = {
  id: string; code: string; severity: string; message: string; requirement_id?: string; chapter_id?: string; evidence_id?: string;
  rule_id?: string; release_key?: string; released?: CheckRelease | null;
  details?: { paragraph_index?: number; quote?: string; fragments?: string[]; targets?: { kind: string; name: string; submitted_on?: string | null }[]; values?: string[] };
};
export type Check = { id: string; volume: Volume | 'all'; passed: boolean; status: string; issues: CheckIssue[]; coverage: { implemented_rules: string[]; unimplemented_rules: string[]; complete: boolean }; fingerprint: string; created_at: string };
export type MergeChecklistSection = { no: number; item: string; action: string; rows: { text: string; source?: string | null; status?: string | null }[] };
export type MergeChecklist = { export_id: string; check_id?: string | null; project_name: string; generated_at: string; volumes: Volume[]; sections: MergeChecklistSection[] };
export type Export = {
  id: string;
  kind: string;
  merge_checklist?: MergeChecklist;
  merge_checklist_url?: string;
  check_id: string;
  created_at: string;
  excludes_drafts: boolean;
  status: string;
  volumes: { volume: Volume; filename: string; download_url: string; file_size?: number; size_bytes?: number; sha256?: string; fingerprint?: string }[];
  volume?: Volume | 'all';
  created_by?: string;
  operator_name?: string;
  file_size?: number;
  size_bytes?: number;
  sha256?: string;
  fingerprint?: string;
};
export type Job = { id: string; project_id: string; type: string; status: string; progress: number; message: string; created_at: string; completed_at: string; error: { code: string; message: string } | null; recoverable: boolean };
export type EvidenceAttachment = {
  id: string;
  name: string;
  size: number;
  sha256?: string;
  download_url?: string;
  uploaded_at?: string;
  content_type?: string;
};

export type Evidence = {
  id: string; name: string; type: string; content: string; valid_until: string | null; status: string; company_id?: string;
  usable_as_evidence?: boolean; reason?: string; revision?: number; match_score?: number;
  source_tier?: 'own' | 'partner' | 'reference'; agreement_present?: boolean; restricted?: boolean;
  source?: { filename?: string; page?: number; quote?: string };
  system_key?: string;
  id_card?: string;
  phone?: string;
  bank_account?: string;
  attachments?: EvidenceAttachment[];
  referenced_project_count?: number;
  last_modified_by?: string;
  created_at?: string;
};
export type Workspace = { revision: number; input_fingerprint: string; project: Project; stage: string; files: TenderFile[]; requirements: Requirement[]; facts: Fact[]; conflicts: Conflict[]; chapters: Chapter[]; checks: Check[]; exports: Export[]; jobs: Job[]; parse_confirmed: boolean; plan_confirmed: boolean; sla?: ProjectSla | null; writing_plan?: WritingPlan; team?: ProjectTeam; permissions?: ProjectPermissions; volumes?: VolumeStatus[]; human_queue_pending?: number; omissions_pending?: number };

export type SnippetSyncStatus = 'synced' | 'unsynced' | 'failed' | 'sync_failed' | string;
export type SnippetPublication = {
  id: string;
  company_id: string;
  title?: string;
  product: string;
  snippet_type: string;
  variables: string[];
  source_group?: string;
  boilerplate_group?: string;
  draft_body?: string;
  published_body: string;
  draft_revision?: number;
  published_revision: number;
  kb_sync_status: SnippetSyncStatus;
  updated_at: string;
};

export type ForbiddenWordSeverity = 'blocker' | 'warning' | 'suggestion';
export type ForbiddenWordCategory = 'exaggeration' | 'buyer_tone' | 'competitor' | 'cliche' | string;

export interface ForbiddenWord {
  id: string;
  word: string;
  category: ForbiddenWordCategory;
  severity: ForbiddenWordSeverity;
  replacement_suggestion: string;
  reason: string;
}

export interface TypographyRule {
  id: string;
  category: string;
  rule_name: string;
  standard: string;
  bad_case?: string;
  good_case?: string;
}

export interface QualitySample {
  id: string;
  title: string;
  volume: Volume;
  chapter_name: string;
  scoring_dimension: string;
  word_count: number;
  tags: string[];
  excerpt: string;
  full_content: string;
  revision: number;
  updated_at: string;
}

export interface CompanyWritingProfile {
  company_id: string;
  company_name: string;
  self_reference: string;
  tenderer_reference: string;
  tone_preference: string;
  summary_sentence_strategy: string;
  style_token_budget?: number;
  typography_rules: TypographyRule[];
  forbidden_words: ForbiddenWord[];
  quality_samples: QualitySample[];
}

export interface RetrievedEvidence {
  id: string;
  path: string;
  tag: string;
  cite_tag?: string;
  name?: string;
  source_type?: string;
  score?: number;
  chunk_id?: string;
  document_id?: string;
  content: string;
  attachable: boolean;
  reference_only: boolean;
}

