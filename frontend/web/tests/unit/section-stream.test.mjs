// 为什么有这个文件：核对技术分册按节流式写入时，各节文字不串、停止会断开、高频增量会合并。
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  applySectionEvent,
  assembleVolume,
  createDeltaCoalescer,
  emptyVolumeStream,
  leafKey,
  parseSectionEvent,
  runSectionVolumeStream,
  technicalVolumeStreamPath,
} from '../../src/editor/section-stream.ts';

const headings = [
  { level: 1, number: '1', title: '总体', requirement_id: null, task_id: null },
  { level: 2, number: '1.1', title: '巡检', requirement_id: 'r1', task_id: 't-inspect' },
  { level: 2, number: '1.2', title: '主机', requirement_id: 'r2', task_id: 't-host' },
];

const base = '1 总体\n\n1.1 巡检\n旧巡检\n\n1.2 主机\n旧主机\n';

function frame(event) {
  return `event: ${event.event}\ndata: ${JSON.stringify(event)}\n\n`;
}

function sseResponse(text) {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
}

test('leaf key prefers task id, then requirement id, then number', () => {
  assert.equal(leafKey({ task_id: 't1', requirement_id: 'r1', number: '1.1' }), 't1');
  assert.equal(leafKey({ task_id: '  ', requirement_id: 'r1', number: '1.1' }), 'r1');
  assert.equal(leafKey({ task_id: null, requirement_id: null, number: '1.1' }), '1.1');
  assert.equal(technicalVolumeStreamPath('p/1'), '/api/v1/projects/p%2F1/technical-volume/stream');
});

test('parallel deltas stay in their own sections', () => {
  let state = emptyVolumeStream();
  state = applySectionEvent(state, { event: 'section.started', section_id: 't-inspect', title: '巡检' });
  state = applySectionEvent(state, { event: 'section.started', section_id: 't-host', title: '主机' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-host', text: '乙' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-inspect', text: '甲' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-host', text: '二' });
  const shown = assembleVolume(headings, base, state.sections);
  assert.match(shown, /1\.1 巡检\n甲\n/);
  assert.match(shown, /1\.2 主机\n乙二\n/);
  assert.equal(shown.includes('甲二'), false);
  assert.equal(shown.includes('乙甲'), false);
  assert.equal(state.sections['t-inspect'].text, '甲');
  assert.equal(state.sections['t-host'].text, '乙二');
});

test('section done replaces that section and leaves the neighbor', () => {
  let state = applySectionEvent(emptyVolumeStream(), { event: 'section.delta', section_id: 't-inspect', text: '半' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-host', text: '主机句' });
  state = applySectionEvent(state, { event: 'section.done', section_id: 't-inspect', text: '巡检全文' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-inspect', text: '迟到' });
  const shown = assembleVolume(headings, base, state.sections);
  assert.match(shown, /1\.1 巡检\n巡检全文\n/);
  assert.match(shown, /1\.2 主机\n主机句\n/);
  assert.equal(shown.includes('迟到'), false);
  assert.equal(shown.includes('半'), false);
});

test('cancelled section keeps its old body', () => {
  let state = applySectionEvent(emptyVolumeStream(), { event: 'section.delta', section_id: 't-inspect', text: '新巡检' });
  state = applySectionEvent(state, { event: 'section.delta', section_id: 't-host', text: '新主机' });
  state = applySectionEvent(state, { event: 'section.cancelled', section_id: 't-inspect' });
  const shown = assembleVolume(headings, base, state.sections);
  assert.match(shown, /1\.1 巡检\n旧巡检\n/);
  assert.match(shown, /1\.2 主机\n新主机\n/);
});

test('coalescer keeps sections apart and merges repeats', () => {
  const coalescer = createDeltaCoalescer();
  coalescer.add('t-inspect', '甲');
  coalescer.add('t-host', '乙');
  coalescer.add('t-inspect', '丙');
  coalescer.drop('t-host');
  assert.deepEqual(coalescer.drain(), [{ section_id: 't-inspect', text: '甲丙' }]);
  assert.deepEqual(coalescer.drain(), []);
});

test('unknown event is ignored', () => {
  assert.equal(parseSectionEvent({ event: 'job.progress', text: 'x' }), null);
  assert.equal(parseSectionEvent('nope'), null);
  const parsed = parseSectionEvent({ event: 'section.delta', section_id: 't-inspect', text: '甲' });
  assert.deepEqual(parsed, { event: 'section.delta', section_id: 't-inspect', text: '甲' });
});

test('stream paints each section once per frame and sends auth', async context => {
  const bodies = [
    frame({ event: 'sections.fanout', concurrency: 3, section_ids: ['t-inspect', 't-host'] }),
    frame({ event: 'section.started', section_id: 't-inspect', title: '巡检' }),
    frame({ event: 'section.delta', section_id: 't-inspect', text: '甲' }),
    frame({ event: 'section.delta', section_id: 't-host', text: '乙' }),
    frame({ event: 'section.delta', section_id: 't-inspect', text: '丙' }),
    frame({ event: 'section.done', section_id: 't-inspect', text: '甲丙' }),
    frame({ event: 'section.done', section_id: 't-host', text: '乙' }),
    frame({ event: 'volume.done', chapter_id: 'ch-1', revision: 8, failed: [], replay: false }),
  ].join('');
  let schedules = 0;
  context.mock.method(globalThis, 'fetch', async (path, options) => {
    assert.equal(path, '/api/v1/projects/proj/technical-volume/stream');
    assert.equal(options.method, 'POST');
    assert.equal(options.headers.Authorization, 'Bearer synthetic-session');
    assert.equal(options.headers.Accept, 'text/event-stream');
    assert.equal(options.headers['If-Match'], '4');
    assert.match(options.headers['Idempotency-Key'], /^[0-9a-f-]{36}$/);
    assert.equal(options.signal.aborted, false);
    assert.deepEqual(JSON.parse(options.body), {});
    return sseResponse(bodies);
  });
  const paints = [];
  const outcome = await runSectionVolumeStream({
    projectId: 'proj',
    token: 'synthetic-session',
    revision: 4,
    headings,
    baseContent: base,
    signal: new AbortController().signal,
    schedule: () => { schedules += 1; },
    onText: markdown => { paints.push(markdown); },
  });
  assert.equal(schedules, 1);
  assert.equal(outcome.phase, 'done');
  assert.equal(outcome.chapterId, 'ch-1');
  assert.equal(outcome.revision, 8);
  const last = paints[paints.length - 1];
  assert.match(last, /1\.1 巡检\n甲丙\n/);
  assert.match(last, /1\.2 主机\n乙\n/);
  assert.equal(last.includes('旧主机'), false);
  assert.equal(last.includes('旧巡检'), false);
});

test('abort rejects and does not finish the volume', async context => {
  const controller = new AbortController();
  context.mock.method(globalThis, 'fetch', async (_path, options) => {
    assert.equal(options.signal, controller.signal);
    controller.abort();
    throw Object.assign(new Error('The operation was aborted'), { name: 'AbortError' });
  });
  const paints = [];
  await assert.rejects(runSectionVolumeStream({
    projectId: 'proj',
    token: 'synthetic-session',
    revision: 4,
    headings,
    baseContent: base,
    signal: controller.signal,
    onText: markdown => { paints.push(markdown); },
  }), error => error.name === 'AbortError');
  assert.equal(controller.signal.aborted, true);
  assert.deepEqual(paints, []);
});
