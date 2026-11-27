// 为什么有这个文件：技术卷的增量经常一次送来一整段。
// 它解决什么问题：纸面按柔和流畅的速度逐字长出，点停止后不再往下写。

export const REVEAL_CHARS_PER_SECOND = 72;
const TICK_MS = 50;

export type RevealClock = {
  now(): number;
  schedule(run: () => void, delayMs: number): number;
  cancel(id: number): void;
};

export type TextReveal = {
  push(target: string): void;
  /** 直接显示到 target，不逐字（重新订阅时的积压）。 */
  jump(target: string): void;
  cancel(): void;
  /** 纸面追上最新全文，或已经被取消。 */
  settled(): Promise<void>;
};

export type VolumeStreamChrome = {
  label: '停止' | '生成中…' | '开始生成';
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
    jump(next: string) {
      if (stopped) return;
      target = next;
      paint(next);
      finishIfCaught();
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

/** 只有真实活跃的技术卷 SSE 会话才允许出现“AI 正在撰写”；普通加载、保存或刷新绝不能误显撰写态。 */
export function volumeStreamChrome(input: { streaming: boolean; busy: boolean; streamFailed: boolean }): VolumeStreamChrome {
  if (input.streaming) return { label: '停止' };
  if (input.streamFailed) return { label: '开始生成' };
  if (input.busy) return { label: '生成中…' };
  return { label: '开始生成' };
}

export function streamFailureNotice(message: string): string {
  const text = message.trim() || '生成请求失败';
  return text.startsWith('生成失败') ? text : `生成失败：${text}`;
}
