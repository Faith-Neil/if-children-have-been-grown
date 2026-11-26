// 为什么有这个文件：大块增量仍应在纸面上逐字长出，停止后不再往下写。
import assert from 'node:assert/strict';
import test from 'node:test';
import { createTextReveal, streamFailureNotice, volumeStreamChrome } from '../../src/editor/text-reveal.ts';

const CHAPTER = '巡'.repeat(200);

function manualClock() {
  let now = 0;
  let seq = 1;
  const queue = [];
  return {
    now: () => now,
    schedule(run, delayMs) {
      const id = seq;
      seq += 1;
      queue.push({ id, at: now + delayMs, run });
      return id;
    },
    cancel(id) {
      const index = queue.findIndex(item => item.id === id);
      if (index >= 0) queue.splice(index, 1);
    },
    advance(ms) {
      const end = now + ms;
      for (;;) {
        const due = queue.filter(item => item.at <= end).sort((left, right) => left.at - right.at || left.id - right.id);
        if (!due.length) break;
        const next = due[0];
        queue.splice(queue.findIndex(item => item.id === next.id), 1);
        now = next.at;
        next.run();
      }
      now = end;
    },
  };
}

test('a large delta drips about sixty characters per second and stays a prefix', () => {
  const paints = [];
  const clock = manualClock();
  const reveal = createTextReveal(text => paints.push(text), clock);
  reveal.push(CHAPTER);
  assert.equal(paints.length, 0);
  clock.advance(50);
  assert.equal(paints.at(-1).length < 20, true);
  assert.equal(CHAPTER.startsWith(paints.at(-1)), true);
  clock.advance(950);
  const shown = paints.at(-1);
  assert.equal(shown.length >= 40 && shown.length <= 80, true);
  assert.equal(shown.length < CHAPTER.length, true);
  assert.equal(CHAPTER.startsWith(shown), true);
  clock.advance(4000);
  assert.equal(paints.at(-1), CHAPTER);
});

test('cancel stops the drip and a later push continues from the shown prefix', () => {
  const paints = [];
  const clock = manualClock();
  const reveal = createTextReveal(text => paints.push(text), clock);
  reveal.push('巡'.repeat(30));
  clock.advance(200);
  const frozen = paints.at(-1);
  reveal.cancel();
  clock.advance(1000);
  assert.equal(paints.at(-1), frozen);
  assert.equal(frozen.length < 30, true);

  const continued = [];
  const clock2 = manualClock();
  const again = createTextReveal(text => continued.push(text), clock2);
  again.push('巡'.repeat(9));
  clock2.advance(1000);
  assert.equal(continued.at(-1), '巡'.repeat(9));
  again.push('巡'.repeat(40));
  clock2.advance(500);
  const next = continued.at(-1);
  assert.equal(next.startsWith('巡'.repeat(9)), true);
  assert.equal(next.length > 9 && next.length < 40, true);
});

test('the generate button says stop while the stream is live, and ordinary busy never fakes writing', () => {
  assert.deepEqual(volumeStreamChrome({ streaming: true, busy: true, streamFailed: false }), {
    label: '停止',
    paperWait: true,
  });
  assert.deepEqual(volumeStreamChrome({ streaming: false, busy: true, streamFailed: true }), {
    label: '开始生成',
    paperWait: false,
  });
  assert.deepEqual(volumeStreamChrome({ streaming: false, busy: true, streamFailed: false }), {
    label: '生成中…',
    paperWait: false,
  });
  assert.equal(streamFailureNotice('连接被拒绝'), '生成失败：连接被拒绝');
  assert.equal(streamFailureNotice(''), '生成失败：生成请求失败');
});

test('jump shows the backlog at once and later pushes drip from there', async () => {
  const paints = [];
  const clock = manualClock();
  const reveal = createTextReveal(text => paints.push(text), clock);
  reveal.jump(CHAPTER);
  assert.equal(paints.at(-1), CHAPTER);
  await reveal.settled();
  reveal.push(`${CHAPTER}新`);
  assert.equal(paints.at(-1), CHAPTER);
  clock.advance(50);
  assert.equal(paints.at(-1), `${CHAPTER}新`);
});