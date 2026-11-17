// 为什么有这个文件：技术卷的增量经常一次送来一整段。
// 它解决什么问题：纸面按大约每秒 60 个汉字逐字长出，点停止后不再往下写。

export const REVEAL_CHARS_PER_SECOND = 60;
const TICK_MS = 50;

export type RevealClock = {
  now(): number;
  schedule(run: () => void, delayMs: number): number;
  cancel(id: number): void;
};

export type TextReveal = {
  push(target: string): void;
  cancel(): void;
  /** 纸面追上最新全文，或已经被取消。 */
  settled(): Promise<void>;
};

export type VolumeStreamChrome = {
  label: '停止' | '生成中…' | '开始生成';
  paperWait: boolean;
};

function browserClock(): RevealClock {
  return {
    now: () => Date.now(),
    schedule: (run, delayMs) => window.setTimeout(run, delayMs),
    cancel: id => window.clearTimeout(id),
  };
}

export function createTextReveal(
  onText: (shown: string) => void,
  clock: RevealClock = browserClock(),
  charsPerSecond = REVEAL_CHARS_PER_SECOND,
): TextReveal {
  const step = Math.max(1, Math.round((charsPerSecond * TICK_MS) / 1000));
  let target = '';
  let shown = '';
  let timer: number | null = null;
  let stopped = false;
  let settle: (() => void) | null = null;
  let pending: Promise<void> | null = null;

  function paint(next: string) {
    if (next === shown) return;
    shown = next;
    onText(shown);
  }

  function finishIfCaught() {
    if (shown !== target || !settle) return;
    const done = settle;
    settle = null;
    pending = null;
    done();
  }

  function tick() {
    timer = null;
    if (stopped) return;
    if (!target.startsWith(shown)) {
      let index = 0;
      const limit = Math.min(shown.length, target.length);
      while (index < limit && shown[index] === target[index]) index += 1;
      paint(target.slice(0, index));
    }
    if (shown.length < target.length) {
      paint(target.slice(0, Math.min(target.length, shown.length + step)));
    }
    if (!stopped && shown.length < target.length) timer = clock.schedule(tick, TICK_MS);
    else finishIfCaught();
  }

  function ensure() {
    if (stopped || timer !== null) return;
    if (shown === target) {
      finishIfCaught();
      return;
    }
    timer = clock.schedule(tick, TICK_MS);
  }

  return {
    push(next: string) {
      if (stopped) return;
      target = next;
      if (shown === target) {
        finishIfCaught();
        return;
      }
      if (!pending) pending = new Promise(resolve => { settle = resolve; });
      ensure();
    },
    cancel() {
      stopped = true;
      if (timer !== null) {
        clock.cancel(timer);
        timer = null;
      }
      if (settle) {
        const done = settle;
        settle = null;
        pending = null;
        done();
      }
    },
    settled() {
      if (stopped || shown === target) return Promise.resolve();
      if (!pending) pending = new Promise(resolve => { settle = resolve; });
      return pending;
    },
  };
}

/** 流式进行时按钮是「停止」、纸面不盖撰写骨架；流式失败后也不要再扮成旧的整篇生成。 */
export function volumeStreamChrome(input: { streaming: boolean; busy: boolean; streamFailed: boolean }): VolumeStreamChrome {
  if (input.streaming) return { label: '停止', paperWait: false };
  if (input.streamFailed) return { label: '开始生成', paperWait: false };
  if (input.busy) return { label: '生成中…', paperWait: true };
  return { label: '开始生成', paperWait: false };
}

export function streamFailureNotice(message: string): string {
  const text = message.trim() || '生成请求失败';
  return text.startsWith('生成失败') ? text : `生成失败：${text}`;
}
