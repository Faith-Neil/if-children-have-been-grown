// 为什么有这个文件：为系统提供 1280 / 1440 / 1680 三大断点自适应计算、侧栏折叠状态持久化记忆与多层级动态面包屑推导纯逻辑。
// 它解决什么问题：
// 1. 落实 PRD v1.8 §2.3、§5.12 与设计规范 §3.1、§3.4、§7.3、§9.6 的 1280（紧凑桌面，主内容区 1040px，表格无横滚优先）、1440（标准桌面）、1680（宽屏工作台，四栏编辑台）断点系统；
// 2. 侧栏持久化记忆：进入项目默认自动收起侧边栏以最大化编辑写作宽度，用户手动切换折叠/展开持久化到 localStorage（icg_sidebar_collapsed），刷新或切页保持记忆；
// 3. 动态层级面包屑：依据当前全局导航或项目页签层级推导面包屑路径，支持长项目名截断展示与悬停全称，上层节点提供点击快速逐级跳转回退，末级呈现纯文本当前页。

import { useEffect, useState } from 'react';

/** 三大标准断点像素值 */
export const BREAKPOINT_COMPACT = 1280;   // 紧凑桌面 (Compact Desktop)
export const BREAKPOINT_STANDARD = 1440;  // 标准桌面 (Standard Desktop)
export const BREAKPOINT_WIDE = 1680;      // 宽屏工作台 (Wide Desktop)

/** 断点层级枚举 */
export type BreakpointTier = 'sub-compact' | 'compact' | 'standard' | 'wide';

/** 断点适配元数据 */
export interface BreakpointInfo {
  /** 当前视口宽度（px） */
  width: number;
  /** 当前断点层级 */
  tier: BreakpointTier;
  /** 是否为超窄视口（< 1280px） */
  isSubCompact: boolean;
  /** 是否为紧凑桌面（1280px <= width < 1440px） */
  isCompact: boolean;
  /** 是否为标准桌面（1440px <= width < 1680px） */
  isStandard: boolean;
  /** 是否为宽屏工作台（>= 1680px） */
  isWide: boolean;
  /** 视口是否满足至少 1280px */
  isAtLeast1280: boolean;
  /** 视口是否满足至少 1440px */
  isAtLeast1440: boolean;
  /** 视口是否满足至少 1680px */
  isAtLeast1680: boolean;
  /** 编辑台推荐列数：< 1680 为 3 栏（目录 + 正文 + 综合右栏）；>= 1680 为 4 栏（目录 + 正文 + 问题来源 + 对话助手） */
  editorColumns: 3 | 4;
  /** 主内容区预估最大可用宽度（px）：紧凑桌面优先保障 1040px 内容无横滚 */
  contentWidth: number;
}

/**
 * 纯函数：根据视口宽度计算断点适配元数据
 * @param width 视口宽度（px）
 */
export function getBreakpointInfo(width: number): BreakpointInfo {
  const safeWidth = Number.isFinite(width) && width >= 0 ? Math.round(width) : BREAKPOINT_STANDARD;
  const isSubCompact = safeWidth < BREAKPOINT_COMPACT;
  const isCompact = safeWidth >= BREAKPOINT_COMPACT && safeWidth < BREAKPOINT_STANDARD;
  const isStandard = safeWidth >= BREAKPOINT_STANDARD && safeWidth < BREAKPOINT_WIDE;
  const isWide = safeWidth >= BREAKPOINT_WIDE;

  const tier: BreakpointTier = isSubCompact
    ? 'sub-compact'
    : isCompact
    ? 'compact'
    : isStandard
    ? 'standard'
    : 'wide';

  const isAtLeast1280 = safeWidth >= BREAKPOINT_COMPACT;
  const isAtLeast1440 = safeWidth >= BREAKPOINT_STANDARD;
  const isAtLeast1680 = safeWidth >= BREAKPOINT_WIDE;

  const editorColumns: 3 | 4 = isWide ? 4 : 3;

  // 预估主内容区宽度（紧凑桌面 1040px 优先表格无横滚）
  let contentWidth = 1040;
  if (isSubCompact) {
    contentWidth = Math.max(0, safeWidth - 240);
  } else if (isCompact) {
    contentWidth = 1040;
  } else if (isStandard) {
    contentWidth = 1200;
  } else {
    contentWidth = 1440;
  }

  return {
    width: safeWidth,
    tier,
    isSubCompact,
    isCompact,
    isStandard,
    isWide,
    isAtLeast1280,
    isAtLeast1440,
    isAtLeast1680,
    editorColumns,
    contentWidth,
  };
}

/**
 * React 自定义 Hook：监听浏览器视口宽度变化并响应式更新断点状态
 * Node/无头环境下优雅降级为 1440 标准桌面
 */
export function useBreakpoint(): BreakpointInfo {
  const [info, setInfo] = useState<BreakpointInfo>(() => {
    if (typeof window !== 'undefined') {
      return getBreakpointInfo(window.innerWidth);
    }
    return getBreakpointInfo(BREAKPOINT_STANDARD);
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let rafId: number | null = null;
    const handleResize = () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        setInfo(getBreakpointInfo(window.innerWidth));
      });
    };

    window.addEventListener('resize', handleResize);
    setInfo(getBreakpointInfo(window.innerWidth));

    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return info;
}

// ==========================================
// 侧栏折叠状态持久化记忆
// ==========================================

/** 侧栏折叠偏好存储键名 */
export const SIDEBAR_COLLAPSED_STORAGE_KEY = 'icg_sidebar_collapsed';

/**
 * 读取 localStorage 中的侧栏折叠持久化状态
 * @param storage 可选自定义 Storage 对象（方便测试与隔离）
 * @returns true: 已收起; false: 已展开; null: 未设置或不可用
 */
export function readStoredSidebarCollapsed(storage?: Storage): boolean | null {
  try {
    const target = storage ?? (typeof window !== 'undefined' ? window.localStorage : undefined);
    if (!target) return null;
    const value = target.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY);
    if (value === 'true') return true;
    if (value === 'false') return false;
    return null;
  } catch {
    return null;
  }
}

/**
 * 写入侧栏折叠持久化状态至 localStorage
 * @param collapsed 是否折叠
 * @param storage 可选自定义 Storage 对象
 * @returns 写入是否成功
 */
export function writeStoredSidebarCollapsed(collapsed: boolean, storage?: Storage): boolean {
  try {
    const target = storage ?? (typeof window !== 'undefined' ? window.localStorage : undefined);
    if (!target) return false;
    target.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(collapsed));
    return true;
  } catch {
    return false;
  }
}

/**
 * 计算初始化或进入页面时的侧栏折叠状态
 * 规则：
 * 1. 若用户在 localStorage 中有显式持久化设置，优先遵守用户偏好；
 * 2. 若用户尚未设置偏好：
 *    - 进入项目页面（工作台/编辑台）时，默认自动收起（true），最大化编辑宽度；
 *    - 在全局常规页面时，默认展开（false）。
 */
export function resolveInitialSidebarCollapsed(options: {
  isInProject: boolean;
  storedValue: boolean | null;
  defaultGlobalCollapsed?: boolean;
}): boolean {
  if (options.storedValue !== null) {
    return options.storedValue;
  }
  if (options.isInProject) {
    return true;
  }
  return options.defaultGlobalCollapsed ?? false;
}

/**
 * 当路由或操作发生切换、进入项目空间时的侧栏折叠建议值
 * 若用户尚未持久化显式展开偏好（storedValue !== false），则进入项目时自动收起侧栏。
 */
export function onEnterProjectCollapse(
  currentCollapsed: boolean,
  storedValue: boolean | null
): boolean {
  if (storedValue !== null) {
    return storedValue;
  }
  return true;
}

// ==========================================
// 动态多层级面包屑推导
// ==========================================

export interface BreadcrumbItemData {
  /** 唯一键名 */
  key: string;
  /** 呈现文字（长名称截断后） */
  title: string;
  /** 完整文字（用于 tooltip / title 属性展示） */
  fullTitle?: string;
  /** 可点击回跳的路径；当前页（末级）为 undefined */
  path?: string;
  /** 是否为当前活动末级页面 */
  isCurrent?: boolean;
}

export interface BreadcrumbContext {
  pathname?: string;
  nav?: string;
  tab?: string;
  volume?: 'technical' | 'business' | string;
  workspace?: {
    project: {
      id: string;
      name: string;
      tender_number?: string;
    };
  } | null;
  missing?: string | null;
  maxProjectNameLength?: number;
}

/** 项目内页签的中文友好映射 */
export const PROJECT_TAB_LABELS: Record<string, string> = {
  overview: '项目概览',
  tender: '招标文件',
  parse: '解析结果',
  matrix: '响应矩阵',
  facts: '项目事实表',
  editor: '编辑台',
  manual: '人工处理队列',
  checks: '合规检查',
  export: '导出递交',
  settings: '项目设置',
};

/** 全局一级路由导航的中文映射 */
export const GLOBAL_ROUTE_LABELS: Record<string, string> = {
  workbench: '投标项目工作台',
  library: '企业资料库',
  knowledge: '知识库',
  writing: '写作档案',
  'admin.rules': '管理后台',
  jobs: '后台任务',
};

/**
 * 格式化长项目名称，超出字符限制时添加省略号，保证顶栏面包屑不溢出换行
 * @param name 原始项目全名
 * @param maxLength 最大允许字符长度（默认 16）
 */
export function formatProjectShortName(name: string, maxLength = 16): string {
  if (!name) return '未命名项目';
  const trimmed = name.trim();
  if (!trimmed) return '未命名项目';
  if (trimmed.length <= maxLength) return trimmed;
  return `${trimmed.slice(0, maxLength - 1)}…`;
}

/**
 * 纯函数：根据当前上下文推导多层级面包屑路径
 * 规则（符合 PRD v1.8 §3.4，最多 4 级）：
 * 1. 404 页面：工作台 > 页面不存在（末级纯文本）；
 * 2. 项目内页面：工作台（可回跳） > [项目简称]（可回跳概览） > 当前页签（如编辑台，末级纯文本）；
 *    若在编辑台且指定分册，支持推导至第 4 级：工作台 > [项目] > 编辑台 > 技术/商务分册；
 * 3. 全局页面：工作台（若是其他全局页，第一级工作台可跳） > 当前全局功能页（末级纯文本）。
 */
export function deriveBreadcrumbs(context: BreadcrumbContext = {}): BreadcrumbItemData[] {
  const {
    nav = 'workbench',
    tab = 'overview',
    volume,
    workspace,
    missing,
    maxProjectNameLength = 16,
  } = context;

  // 1. 页面不存在（404）
  if (missing) {
    return [
      {
        key: 'workbench',
        title: '工作台',
        fullTitle: '投标项目工作台',
        path: '/workbench',
      },
      {
        key: 'missing',
        title: '页面不存在',
        fullTitle: '页面不存在',
        isCurrent: true,
      },
    ];
  }

  // 2. 项目内页面（有激活的 workspace 且 nav 为 workbench）
  if (workspace && nav === 'workbench') {
    const projectId = workspace.project.id;
    const fullProjectName = workspace.project.name || '未命名项目';
    const shortProjectName = formatProjectShortName(fullProjectName, maxProjectNameLength);

    const items: BreadcrumbItemData[] = [
      {
        key: 'workbench',
        title: '工作台',
        fullTitle: '投标项目工作台',
        path: '/workbench',
      },
      {
        key: 'project',
        title: shortProjectName,
        fullTitle: fullProjectName,
        path: `/projects/${encodeURIComponent(projectId)}/overview`,
      },
    ];

    // 如果当前就在项目概览页
    if (tab === 'overview') {
      items.push({
        key: 'tab-overview',
        title: '项目概览',
        fullTitle: '项目概览',
        isCurrent: true,
      });
      return items;
    }

    const tabLabel = PROJECT_TAB_LABELS[tab] ?? tab;

    // 若在编辑台并提供了分册信息
    if (tab === 'editor' && volume) {
      const volumeLabel = volume === 'technical' ? '技术分册' : volume === 'business' ? '商务分册' : volume;
      items.push({
        key: 'tab-editor',
        title: '编辑台',
        fullTitle: '编辑台',
        path: `/projects/${encodeURIComponent(projectId)}/editor`,
      });
      items.push({
        key: 'editor-volume',
        title: volumeLabel,
        fullTitle: `编辑台 · ${volumeLabel}`,
        isCurrent: true,
      });
      return items;
    }

    // 其它常规页签（招标文件、解析结果、响应矩阵、编辑台等）
    items.push({
      key: `tab-${tab}`,
      title: tabLabel,
      fullTitle: tabLabel,
      isCurrent: true,
    });
    return items;
  }

  // 3. 全局页面
  if (nav === 'workbench') {
    return [
      {
        key: 'workbench',
        title: '工作台',
        fullTitle: '投标项目工作台',
        isCurrent: true,
      },
    ];
  }

  const globalName = GLOBAL_ROUTE_LABELS[nav] ?? nav;
  return [
    {
      key: 'workbench',
      title: '工作台',
      fullTitle: '投标项目工作台',
      path: '/workbench',
    },
    {
      key: nav,
      title: globalName,
      fullTitle: globalName,
      isCurrent: true,
    },
  ];
}
