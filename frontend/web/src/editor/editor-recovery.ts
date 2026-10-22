// 为什么有这个文件：在恢复旧草稿或历史正文前核对最新后台版本。
// 它解决什么问题：防止核对期间的新正文或新草稿被恢复操作悄悄覆盖。
type Snapshot = {
  id: string; revision: number;
  draft?: { base_revision: number; sequence: number; content: string; input_fingerprint?: string | null } | null;
};

export function recoveryWrite(snapshot: Snapshot, latest: Snapshot, content: string) {
  if (snapshot.id !== latest.id || snapshot.revision !== latest.revision) {
    throw new Error('正文版本已变化，恢复尚未保存。请查看最新版本后重新核对。');
  }
  const sameDraft = snapshot.draft?.base_revision === latest.draft?.base_revision
    && snapshot.draft?.sequence === latest.draft?.sequence
    && snapshot.draft?.content === latest.draft?.content
    && snapshot.draft?.input_fingerprint === latest.draft?.input_fingerprint;
  if (!sameDraft) throw new Error('个人草稿已变化，恢复尚未保存。请重新读取草稿后核对。');
  return { base_revision: latest.revision, sequence: (latest.draft?.sequence ?? 0) + 1, content };
}
