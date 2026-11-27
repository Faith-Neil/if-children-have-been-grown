// 为什么有这个文件：技术分册按节流式写入编辑台。
// 它解决什么问题：多节同时出字时各自累加，界面按帧合并高频增量。
// 生成是服务端会话：断开只停订阅；重新订阅时先重放积压（live 为假），session.live 之后才是实时增量。

import { newIdempotencyKey, streamEvents } from '../shared/api.ts';
import type { TechnicalHeading } from '../shared/types.ts';

export type SectionPhase = 'queued' | 'writing' | 'done' | 'failed' | 'cancelled';

/** 已扇出、尚未轮到模型的节。 */
export const SECTION_QUEUED_HINT = '排队等待中…';
/** 模型已开写、还没吐出第一个字。 */
export const SECTION_WAITING_HINT = '正在等待模型…';

export type SectionSlot = {
  id: string;
  title: string;
  phase: SectionPhase;
  text: string;
  message: string;
};

export type VolumePhase = 'idle' | 'streaming' | 'done' | 'cancelled' | 'failed';

export type VolumeStreamState = {
  phase: VolumePhase;
  concurrency: number;
  order: string[];
  sections: Record<string, SectionSlot>;
  chapterId: string;
  revision: number | null;
  failed: string[];
  message: string;
  replay: boolean;
  /** 生成会话的任务编号，停止时用它取消。 */
  jobId: string;
  /** 积压已重放完，之后的增量是实时的。 */
  live: boolean;
  /** 后端 task.patched 汇报的最新生成阶段。 */
  stages: Record<string, string>;
  /** task.patched 的到达序（最新在末尾）。并发节交错汇报时，阶段胶囊按事件时间而非扇出顺序取。 */
  stageOrder: string[];
};

export type SectionEvent =
  | { event: 'session.started'; job_id: string }
  | { event: 'session.live' }
  | { event: 'sections.fanout'; concurrency: number; section_ids: string[] }
  | { event: 'section.started'; section_id: string; title: string }
  | { event: 'section.delta'; section_id: string; text: string }
  | { event: 'section.done'; section_id: string; text: string }
  | { event: 'section.failed'; section_id: string; message: string }
  | { event: 'section.cancelled'; section_id: string }
  | { event: 'task.patched'; task_id: string; stage: string }
  | { event: 'volume.done'; chapter_id: string; revision: number | null; failed: string[]; replay: boolean }
  | { event: 'volume.cancelled' }
  | { event: 'volume.failed'; message: string };

const LIVE_PHASE: ReadonlySet<SectionPhase> = new Set(['queued', 'writing', 'done', 'failed']);

export function emptyVolumeStream(): VolumeStreamState {
  return {
    phase: 'idle',
    concurrency: 0,
    order: [],
    sections: {},
    chapterId: '',
    revision: null,
    failed: [],
    message: '',
    replay: false,
    jobId: '',
    live: false,
    stages: {},
    stageOrder: [],
  };
}

export function leafKey(heading: Pick<TechnicalHeading, 'task_id' | 'requirement_id' | 'number'>): string {
  const task = heading.task_id?.trim();
  if (task) return task;
  const requirement = heading.requirement_id?.trim();
  if (requirement) return requirement;
  return (heading.number ?? '').trim();
}

export function technicalVolumeStreamPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/technical-volume/stream`;
}

export function technicalVolumeSessionPath(jobId: string): string {
  return `/api/v1/jobs/${encodeURIComponent(jobId)}/section-events`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === 'string' ? value : null;
}

function readStringList(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const items: string[] = [];
  for (const item of value) {
    if (typeof item !== 'string') return null;
    items.push(item);
  }
  return items;
}

/** 事件 JSON 在边界收成节流事件。缺字段或未知 event 丢弃。 */
export function parseSectionEvent(raw: unknown): SectionEvent | null {
  if (!isRecord(raw)) return null;
  const name = readString(raw, 'event');
  if (!name) return null;
  if (name === 'session.started') {
    const jobId = readString(raw, 'job_id');
    return jobId ? { event: 'session.started', job_id: jobId } : null;
  }
  if (name === 'session.live') return { event: 'session.live' };
  if (name === 'sections.fanout') {
    const sectionIds = readStringList(raw.section_ids);
    if (!sectionIds) return null;
    const concurrency = typeof raw.concurrency === 'number' && raw.concurrency > 0 ? raw.concurrency : sectionIds.length;
    return { event: 'sections.fanout', concurrency, section_ids: sectionIds };
  }
  if (name === 'section.started') {
    const sectionId = readString(raw, 'section_id');
    if (!sectionId) return null;
    return { event: 'section.started', section_id: sectionId, title: readString(raw, 'title') ?? '' };
  }
  if (name === 'section.delta') {
    const sectionId = readString(raw, 'section_id');
    const text = readString(raw, 'text');
    if (!sectionId || text === null) return null;
    return { event: 'section.delta', section_id: sectionId, text };
  }
  if (name === 'section.done') {
    const sectionId = readString(raw, 'section_id');
    const text = readString(raw, 'text');
    if (!sectionId || text === null) return null;
    return { event: 'section.done', section_id: sectionId, text };
  }
  if (name === 'section.failed') {
    const sectionId = readString(raw, 'section_id');
    if (!sectionId) return null;
    return { event: 'section.failed', section_id: sectionId, message: readString(raw, 'message') ?? '本节生成失败' };
  }
  if (name === 'section.cancelled') {
    const sectionId = readString(raw, 'section_id');
    if (!sectionId) return null;
    return { event: 'section.cancelled', section_id: sectionId };
  }
  if (name === 'task.patched') {
    const taskId = readString(raw, 'task_id');
    const stage = readString(raw, 'stage');
    if (!taskId || !stage) return null;
    return { event: 'task.patched', task_id: taskId, stage };
  }
  if (name === 'volume.done') {
    const failed = readStringList(raw.failed) ?? [];
    const revision = typeof raw.revision === 'number' ? raw.revision : null;
    return {
      event: 'volume.done',
      chapter_id: readString(raw, 'chapter_id') ?? '',
      revision,
      failed,
      replay: raw.replay === true,
    };
  }
  if (name === 'volume.cancelled') return { event: 'volume.cancelled' };
  if (name === 'volume.failed') return { event: 'volume.failed', message: readString(raw, 'message') ?? '生成失败' };
  return null;
}

function slot(state: VolumeStreamState, id: string, patch: Partial<SectionSlot> & { phase: SectionPhase; text: string }): VolumeStreamState {
  const previous = state.sections[id];
  const next: SectionSlot = {
    id,
    title: patch.title ?? previous?.title ?? '',
    phase: patch.phase,
    text: patch.text,
    message: patch.message ?? previous?.message ?? '',
  };
  return {
    ...state,
    phase: state.phase === 'idle' ? 'streaming' : state.phase,
    sections: { ...state.sections, [id]: next },
  };
}

function sectionBody(current: SectionSlot): string {
  if (current.text) return current.text;
  if (current.phase === 'failed' && current.message) return current.message;
  if (current.phase === 'queued') return SECTION_QUEUED_HINT;
  if (current.phase === 'writing') return SECTION_WAITING_HINT;
  return '';
}

/** 生成过程中的短状态，给顶栏提示用。 */
export function streamProgressNotice(state: VolumeStreamState, headings: TechnicalHeading[]): string {
  const titleOf = (id: string) => {
    const current = state.sections[id];
    if (current?.title?.trim()) return current.title.trim();
    const heading = headings.find(item => leafKey(item) === id);
    return heading ? `${heading.number} ${heading.title}`.trim() : id;
  };
  const writing = state.order.filter(id => state.sections[id]?.phase === 'writing');
  const queued = state.order.filter(id => state.sections[id]?.phase === 'queued');
  const done = state.order.filter(id => state.sections[id]?.phase === 'done').length;
  const total = state.order.length;
  const parts: string[] = [];
  if (total > 0) parts.push(`已完成 ${done}/${total} 节`);
  if (writing.length > 0) {
    const names = writing.map(titleOf).slice(0, 3).join('、');
    const more = writing.length > 3 ? `等 ${writing.length} 节` : names;
    parts.push(writing.length > 3 ? `正在写：${more}` : `正在写：${names}`);
  }
  if (queued.length > 0) parts.push(`排队 ${queued.length} 节`);
  return parts.join(' · ') || '正在生成…';
}

export type StreamStageName = 'retrieve' | 'deviate' | 'write_section' | 'unknown' | '';

function normalizeStage(value: string | undefined): StreamStageName {
  if (value === 'retrieve' || value === 'deviate' || value === 'write_section') return value;
  return value ? 'unknown' : '';
}

/** 多节并发时按 task.patched 事件到达序取阶段：优先最近汇报且仍在写作的节；都没有写作节则取最近一次汇报。 */
export function activeStreamStage(state: VolumeStreamState): StreamStageName {
  for (let index = state.stageOrder.length - 1; index >= 0; index -= 1) {
    const id = state.stageOrder[index];
    if (state.sections[id]?.phase === 'writing' && state.stages[id]) return normalizeStage(state.stages[id]);
  }
  const latest = state.stageOrder[state.stageOrder.length - 1];
  return normalizeStage(latest ? state.stages[latest] : undefined);
}

/** 是否有任何活跃/完成节已经吐出正文；用于区分阶段呼吸胶囊和首字后的文字画布。 */
export function hasVisibleStreamText(state: VolumeStreamState): boolean {
  return state.order.some(id => {
    const current = state.sections[id];
    return Boolean(current && current.phase !== 'cancelled' && current.text.trim());
  });
}

export function streamingStageLabel(stage: StreamStageName): string {
  if (stage === 'retrieve') return '正在检索招标与知识库资料…';
  if (stage === 'deviate') return '正在核对偏离要求…';
  if (stage === 'write_section') return '正在撰写本节正文…';
  return '正在准备生成…';
}

export function applySectionEvent(state: VolumeStreamState, event: SectionEvent): VolumeStreamState {
  if (state.phase === 'done' || state.phase === 'cancelled' || state.phase === 'failed') return state;
  switch (event.event) {
    case 'session.started':
      return { ...state, jobId: event.job_id };
    case 'session.live':
      return { ...state, live: true };
    case 'sections.fanout': {
      let next: VolumeStreamState = {
        ...state,
        phase: 'streaming',
        concurrency: event.concurrency,
        order: event.section_ids.slice(),
      };
      for (const id of event.section_ids) {
        const previous = next.sections[id];
        if (previous && previous.phase !== 'cancelled' && previous.phase !== 'queued') continue;
        next = slot(next, id, { phase: 'queued', text: '', title: previous?.title ?? '' });
      }
      return next;
    }
    case 'section.started': {
      const previous = state.sections[event.section_id];
      if (previous && previous.phase !== 'cancelled' && previous.phase !== 'queued') return state;
      return slot(state, event.section_id, { phase: 'writing', text: '', title: event.title || previous?.title });
    }
    case 'section.delta': {
      const previous = state.sections[event.section_id];
      // 排队节收到首包时直接开写；已完成/失败/取消的增量丢掉。
      if (previous && previous.phase !== 'writing' && previous.phase !== 'queued') return state;
      const base = previous?.phase === 'writing' ? previous.text : '';
      return slot(state, event.section_id, {
        phase: 'writing',
        text: `${base}${event.text}`,
        title: previous?.title,
      });
    }
    case 'section.done':
      return slot(state, event.section_id, { phase: 'done', text: event.text });
    case 'section.failed':
      return slot(state, event.section_id, {
        phase: 'failed',
        text: state.sections[event.section_id]?.text ?? '',
        message: event.message,
      });
    case 'section.cancelled':
      return slot(state, event.section_id, { phase: 'cancelled', text: '' });
    case 'task.patched': {
      const order = state.stageOrder.filter(id => id !== event.task_id);
      order.push(event.task_id);
      return { ...state, stages: { ...state.stages, [event.task_id]: event.stage }, stageOrder: order };
    }
    case 'volume.done':
      return {
        ...state,
        phase: 'done',
        chapterId: event.chapter_id,
        revision: event.revision,
        failed: event.failed.slice(),
        replay: event.replay,
      };
    case 'volume.cancelled':
      return { ...state, phase: 'cancelled' };
    case 'volume.failed':
      return { ...state, phase: 'failed', message: event.message };
    default: {
      const unreachable: never = event;
      return unreachable;
    }
  }
}

function isLeaf(heading: TechnicalHeading): boolean {
  return Boolean(heading.task_id || heading.requirement_id);
}

function liveSlot(sections: Record<string, SectionSlot>, heading: TechnicalHeading): SectionSlot | null {
  const current = sections[leafKey(heading)];
  if (!current || !LIVE_PHASE.has(current.phase)) return null;
  return current;
}

function buildFromHeadings(headings: TechnicalHeading[], sections: Record<string, SectionSlot>): string {
  const lines: string[] = [];
  for (const heading of headings) {
    lines.push(`${heading.number} ${heading.title}`.trim());
    if (isLeaf(heading)) {
      const current = liveSlot(sections, heading);
      if (current) {
        const body = sectionBody(current);
        if (body) lines.push(body);
      } else {
        lines.push('待补');
      }
    }
    lines.push('');
  }
  const text = lines.join('\n').trim();
  return text ? `${text}\n` : '';
}

/** 只替换正在写、已完成或失败的节。其余行保持原文。 */
export function assembleVolume(headings: TechnicalHeading[], baseContent: string, sections: Record<string, SectionSlot>): string {
  const updating = headings.filter(heading => liveSlot(sections, heading));
  if (updating.length === 0) return baseContent;
  if (!baseContent.trim()) return buildFromHeadings(headings, sections);
  const lines = baseContent.replace(/\r\n/g, '\n').split('\n');
  const markers = headings.map(heading => ({
    heading,
    index: lines.findIndex(line => line.trim() === `${heading.number} ${heading.title}`.trim()),
  }));
  const found = markers.filter(item => liveSlot(sections, item.heading));
  if (found.some(item => item.index < 0)) return buildFromHeadings(headings, sections);
  const next = lines.slice();
  const ordered = found.slice().sort((left, right) => right.index - left.index);
  for (const item of ordered) {
    const current = liveSlot(sections, item.heading);
    if (!current) continue;
    let end = next.length;
    for (const other of markers) {
      if (other.index > item.index) end = Math.min(end, other.index);
    }
    const body = sectionBody(current);
    const bodyLines = body === '' ? [] : body.replace(/\r\n/g, '\n').split('\n');
    if (end < next.length && bodyLines[bodyLines.length - 1] !== '') bodyLines.push('');
    next.splice(item.index + 1, end - item.index - 1, ...bodyLines);
  }
  const text = next.join('\n');
  return text.endsWith('\n') ? text : `${text}\n`;
}

export function createDeltaCoalescer() {
  const pending = new Map<string, string>();
  return {
    add(sectionId: string, text: string) {
      pending.set(sectionId, `${pending.get(sectionId) ?? ''}${text}`);
    },
    drop(sectionId: string) {
      pending.delete(sectionId);
    },
    drain(): Array<{ section_id: string; text: string }> {
      const items = [...pending.entries()].map(([section_id, text]) => ({ section_id, text }));
      pending.clear();
      return items;
    },
  };
}

function defaultSchedule(run: () => void): number {
  if (typeof requestAnimationFrame === 'function') return requestAnimationFrame(run);
  queueMicrotask(run);
  return 0;
}

/** 给了 jobId 就重新订阅这个生成会话；否则按 revision 与 section 开始生成。 */
export async function runSectionVolumeStream(input: {
  projectId: string;
  token: string;
  revision?: number;
  jobId?: string;
  section?: string;
  headings: TechnicalHeading[];
  baseContent: string;
  signal: AbortSignal;
  onText: (markdown: string, state: VolumeStreamState) => void;
  schedule?: (run: () => void) => number | void;
}): Promise<VolumeStreamState> {
  const coalescer = createDeltaCoalescer();
  let state = emptyVolumeStream();
  let frame = 0;
  let queued = false;
  let closed = false;
  const schedule = input.schedule ?? defaultSchedule;

  const publish = () => {
    if (closed || input.signal.aborted) return;
    input.onText(assembleVolume(input.headings, input.baseContent, state.sections), state);
  };

  const flush = () => {
    queued = false;
    if (frame && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(frame);
    frame = 0;
    if (closed || input.signal.aborted) return;
    const pieces = coalescer.drain();
    if (pieces.length === 0) return;
    for (const piece of pieces) {
      state = applySectionEvent(state, { event: 'section.delta', section_id: piece.section_id, text: piece.text });
    }
    publish();
  };

  const queue = () => {
    if (queued || closed || input.signal.aborted) return;
    queued = true;
    frame = schedule(flush) || 0;
  };

  const target = input.jobId
    ? { path: technicalVolumeSessionPath(input.jobId), body: undefined, headers: undefined }
    : {
      path: technicalVolumeStreamPath(input.projectId),
      body: input.section ? { section: input.section } : {},
      headers: { 'If-Match': String(input.revision), 'Idempotency-Key': newIdempotencyKey() },
    };
  try {
    await streamEvents(target.path, input.token, target.body, raw => {
      if (closed || input.signal.aborted) return;
      const parsed = parseSectionEvent(raw);
      if (!parsed) return;
      if (parsed.event === 'section.delta') {
        coalescer.add(parsed.section_id, parsed.text);
        queue();
        return;
      }
      if (parsed.event === 'section.done' || parsed.event === 'section.failed' || parsed.event === 'section.cancelled') {
        coalescer.drop(parsed.section_id);
      }
      flush();
      if (closed || input.signal.aborted) return;
      state = applySectionEvent(state, parsed);
      publish();
    }, input.signal, target.headers);
  } finally {
    if (!input.signal.aborted) flush();
    closed = true;
    if (frame && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(frame);
  }
  if (state.phase === 'streaming' || state.phase === 'idle') {
    return { ...state, phase: 'failed', message: state.message || '生成中断，本次不写入。' };
  }
  return state;
}
