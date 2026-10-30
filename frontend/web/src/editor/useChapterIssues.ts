// 为什么有这个文件：编辑台读取本章问题清单并维护筛选、选中与段落高亮（APP-M2-T166）。
// 它解决什么问题：章节切换、提交新版本、项目里跑了新检查（项目版本变）时重新读取；
// 从检查页“定位”带来的问题在清单读到后交给编辑台定位一次。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { userFacingMessage } from '../shared/api.ts';
import { DEFAULT_FILTER, fetchChapterIssues, paragraphMarkers, type ChapterIssue, type ChapterIssueList, type IssueFilter } from './chapter-issues-core.ts';
import { takeIssueFocus } from './issue-focus.ts';

const FOCUS_MS = 4000;

export function useChapterIssues(params: { projectId: string; chapterId: string; token: string | null; revision?: number; projectRevision?: number }) {
  const { projectId, chapterId, token, revision, projectRevision } = params;
  const [data, setData] = useState<ChapterIssueList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<IssueFilter>(DEFAULT_FILTER);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [focusedKey, setFocusedKey] = useState<string | null>(null);
  const [pending, setPending] = useState<ChapterIssue | null>(null);
  const generation = useRef(0);

  const load = useCallback(() => {
    if (!chapterId || !token) return;
    const current = ++generation.current;
    setLoading(true);
    fetchChapterIssues(projectId, chapterId, token).then(value => {
      if (current !== generation.current) return;
      setData(value); setError(null);
      const wanted = takeIssueFocus(chapterId);
      const hit = wanted ? value.items.find(item => item.issue_id === wanted || item.id === wanted) : undefined;
      if (hit) setPending(hit);
    }).catch(failure => {
      if (current === generation.current) setError(userFacingMessage(failure));
    }).finally(() => {
      if (current === generation.current) setLoading(false);
    });
  }, [projectId, chapterId, token]);

  useEffect(() => {
    setData(null); setFilter(DEFAULT_FILTER); setActiveId(null); setFocusedKey(null); setPending(null);
  }, [chapterId]);
  useEffect(() => { load(); }, [load, revision, projectRevision]);
  useEffect(() => {
    if (!focusedKey) return;
    const timer = window.setTimeout(() => setFocusedKey(null), FOCUS_MS);
    return () => window.clearTimeout(timer);
  }, [focusedKey]);

  const markers = useMemo(() => paragraphMarkers(data?.items ?? []), [data]);
  return { data, loading, error, filter, setFilter, activeId, setActiveId, focusedKey, setFocusedKey, markers, reload: load,
    pending, clearPending: () => setPending(null) };
}
