// 为什么有这个文件：为顶栏徽标与任务中心抽屉提供集中的状态管理 Hook。
// 它解决什么问题：
// 1. 集中管理顶栏角标计数（当前公司运行中 + 排队中任务）；
// 2. 维护任务抽屉展开/收起状态及四分类页签切换；
// 3. 实时推导任务多维归一化与筛选结果，解耦视图渲染与数据转换。

import { useMemo, useState } from 'react';
import {
  calculateActiveTaskCount,
  computeTaskCounts,
  filterTasks,
  normalizeTask,
  type RawTaskInput,
  type TaskCounts,
  type TaskFilterKey,
  type TaskItem,
} from './task-center.ts';

export interface UseTaskBadgeOptions {
  tasks: RawTaskInput[];
  companyId?: string;
  initialFilter?: TaskFilterKey;
  initialOpen?: boolean;
}

export interface UseTaskBadgeResult {
  /** 顶栏角标数字：当前公司运行中 + 等待中的任务数 */
  activeCount: number;
  /** 四分类实时计数 */
  counts: TaskCounts;
  /** 全量归一化后的任务列表 */
  normalizedTasks: TaskItem[];
  /** 当前筛选分类 */
  filter: TaskFilterKey;
  setFilter: (filter: TaskFilterKey) => void;
  /** 抽屉是否开启 */
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
  /** 关键词搜索 */
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  /** 当前过滤后的任务列表 */
  filteredTasks: TaskItem[];
}

export function useTaskBadge({
  tasks,
  companyId,
  initialFilter = 'all',
  initialOpen = false,
}: UseTaskBadgeOptions): UseTaskBadgeResult {
  const [drawerOpen, setDrawerOpen] = useState(initialOpen);
  const [filter, setFilter] = useState<TaskFilterKey>(initialFilter);
  const [searchQuery, setSearchQuery] = useState('');

  // 1. 归一化全量任务
  const normalizedTasks = useMemo(() => {
    if (!Array.isArray(tasks)) return [];
    return tasks.map(t => normalizeTask(t));
  }, [tasks]);

  // 2. 计算顶栏角标数量 (运行中 + 排队中)
  const activeCount = useMemo(() => {
    return calculateActiveTaskCount(tasks, companyId);
  }, [tasks, companyId]);

  // 3. 计算四分类数量
  const counts = useMemo(() => {
    return computeTaskCounts(normalizedTasks, companyId);
  }, [normalizedTasks, companyId]);

  // 4. 当前条件过滤列表
  const filteredTasks = useMemo(() => {
    return filterTasks(normalizedTasks, filter, {
      companyId,
      searchQuery,
    });
  }, [normalizedTasks, filter, companyId, searchQuery]);

  return {
    activeCount,
    counts,
    normalizedTasks,
    filter,
    setFilter,
    drawerOpen,
    openDrawer: () => setDrawerOpen(true),
    closeDrawer: () => setDrawerOpen(false),
    toggleDrawer: () => setDrawerOpen(prev => !prev),
    searchQuery,
    setSearchQuery,
    filteredTasks,
  };
}
