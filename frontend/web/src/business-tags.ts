// 为什么有这个文件：集中定义业务小组件（LevelTag、AiTag、DirectTag、Cite、SourceBar）的核心色彩令牌、代码映射与无障碍规则。
// 它解决什么问题：
// 1. 严格锁定 AI 紫（#6E4BD8 / #A23CC8）只能出现在 AiTag，严禁混入其他业务标签；
// 2. 统一条款级别与重要性代码（阻断/否决、关键/星号、加分/评分、资格、一般条款）；
// 3. 所有文字与背景组合严格满足 WCAG AA 4.5:1 对比度标准；
// 4. 为 Cite 引用与 SourceBar 来源条提供纯函数级别的数据格式化与指纹脱敏解析。

import type { ReactNode } from 'react';
import { contrastRatio, luminance } from './status-views.ts';

/**
 * 业务组件专用色彩令牌（严格按设计规范 §7.1、§7.4 与 §9.3 锁定）
 */
export const BIZ_COLOR_TOKENS = {
  // 阻断 / 否决项（实心红底白字 或 高对比度浅底红字）
  blockerSolidBg: '#D9363E',
  blockerSolidText: '#FFFFFF', // 对比度 4.66:1
  blockerSubtleBg: '#FFF1F0',
  blockerSubtleBorder: '#FFA39E',
  blockerSubtleText: '#A8071A', // 对比度 7.10:1

  // 关键要求 / 星号条款
  starBg: '#FFF1F0',
  starBorder: '#FFA39E',
  starText: '#CF1322', // 对比度 5.86:1

  // 警告 / 复核
  warningBg: '#FFFBE6',
  warningBorder: '#FFE58F',
  warningText: '#9A5608', // 对比度 5.12:1

  // 加分项 / 评分项（青色）
  bonusBg: '#E6FFFB',
  bonusBorder: '#87E8DE',
  bonusText: '#005C66', // 对比度 7.82:1

  // 资格要求（极客蓝）
  qualificationBg: '#E6F4FF',
  qualificationBorder: '#91CAFF',
  qualificationText: '#0958D9', // 对比度 5.53:1

  // 一般条款（中性灰）
  generalBg: '#F2F3F5',
  generalBorder: '#DCDFE6',
  generalText: '#4E5969', // 对比度 5.88:1

  // AI 专用紫色令牌（严禁外借）
  aiPurple: '#6E4BD8', // 锁定主 AI 紫
  aiAssistantPurple: '#A23CC8', // 锁定助手紫
  aiSolidBg: '#6E4BD8',
  aiSolidText: '#FFFFFF', // 对比度 5.73:1
  aiSubtleBg: '#F2EEFC',
  aiSubtleBorder: '#D8C9FA',
  aiSubtleText: '#5329B3', // 对比度 7.86:1

  // 答案卡 / 直接采用 / 直接响应（深蓝系统直查，严禁使用 AI 紫）
  directBg: '#EEF3FC',
  directBorder: '#B7C9EE',
  directText: '#1E4DB7', // 对比度 6.88:1

  // 段落来源锁定色（设计规范 §7.1）
  srcEvidence: '#1E4DB7', // 证据
  srcSnippet: '#0E8A8A', // 方案片段基色
  srcSnippetText: '#005C66', // 方案片段深色文字（保证对比度）
  srcSnippetBg: '#E6F7F7',
  srcTender: '#86909C', // 招标原文基色
  srcTenderText: '#4E5969', // 招标原文深色文字
  srcTenderBg: '#F2F3F5',
  srcModel: '#6E4BD8', // 模型撰写
  srcAssistant: '#A23CC8', // 助手撰写
  srcManual: '#2B9D5C', // 人工编写
  srcManualBg: '#F0F9F4',
  srcManualText: '#136C38', // 对比度 6.2:1
  srcSystem: '#4E5969', // 系统生成
  srcSystemBg: '#F2F3F5',

  // 变量 / 事实高亮色（规范 §7.1）
  varBg: '#FFF4D6',
  varBorder: '#F0C24B',
  varText: '#9A5608', // 对比度 4.95:1
} as const;

export { contrastRatio, luminance };

/**
 * AI 紫色彩防混用检查
 * 返回 true 表示该颜色属于 AI 紫色阶
 */
export function isAiColor(hexColor?: string): boolean {
  if (!hexColor) return false;
  const normalized = hexColor.trim().toUpperCase();
  const aiPalette = [
    BIZ_COLOR_TOKENS.aiPurple.toUpperCase(),
    BIZ_COLOR_TOKENS.aiAssistantPurple.toUpperCase(),
    BIZ_COLOR_TOKENS.aiSubtleBg.toUpperCase(),
    BIZ_COLOR_TOKENS.aiSubtleBorder.toUpperCase(),
    BIZ_COLOR_TOKENS.aiSubtleText.toUpperCase(),
    '#6E4BD8',
    '#A23CC8',
    '#5329B3',
    '#F2EEFC',
    '#D8C9FA',
    '#722ED1', // AntD purple preset
    '#9254DE',
    '#B37FEB',
    '#D3ADF7',
    '#EFDBFF',
    '#F9F0FF',
  ];
  return aiPalette.includes(normalized);
}

/**
 * 业务标签色彩断言：确保非 AI 标签绝对不含 AI 紫色系
 */
export function assertNotAiColor(tagComponent: string, hexColor?: string) {
  if (isAiColor(hexColor)) {
    throw new Error(
      `[ICG 色彩规范违规] ${tagComponent} 使用了 AI 紫（${hexColor}）。根据设计规范 §9.4，紫色系为 AI 专用锁定令牌，严禁混用到其他业务标签！`
    );
  }
}

/**
 * 条款级别 / 规则级别类型
 */
export type LevelTagType =
  | 'blocker' // 阻断（实心红）
  | 'void' // 废标 / 否决项
  | 'star' // 星号 / 关键要求
  | 'warning' // 警告
  | 'bonus' // 加分项
  | 'scoring' // 评分项
  | 'qualification' // 资格要求
  | 'hint' // 提示
  | 'general'; // 一般条款

export interface ResolvedLevelTag {
  category: LevelTagType;
  label: string;
  isSolid: boolean;
  bg: string;
  color: string;
  border: string;
  ariaRole: string;
  iconType: 'close-circle' | 'star' | 'warning' | 'plus-circle' | 'check-circle' | 'info-circle' | 'minus';
}

/**
 * 解析条款级别标签的元数据与色彩方案
 */
export function resolveLevelTag(
  rawLevel?: string,
  options?: { isSolid?: boolean; customLabel?: string }
): ResolvedLevelTag {
  const norm = (rawLevel || 'general').trim().toLowerCase();
  const custom = options?.customLabel;

  // 1. 阻断 / 否决 / 废标
  if (
    norm === 'blocker' ||
    norm === 'void' ||
    norm === 'veto' ||
    norm === '否决' ||
    norm === '否决项' ||
    norm === '废标' ||
    norm === '废标条款'
  ) {
    const isSolid = options?.isSolid !== false; // 阻断默认实心红底白字
    return {
      category: 'blocker',
      label: custom ?? (norm === 'void' || norm.includes('废标') ? '废标条款' : norm.includes('否决') ? '否决项' : '阻断'),
      isSolid,
      bg: isSolid ? BIZ_COLOR_TOKENS.blockerSolidBg : BIZ_COLOR_TOKENS.blockerSubtleBg,
      color: isSolid ? BIZ_COLOR_TOKENS.blockerSolidText : BIZ_COLOR_TOKENS.blockerSubtleText,
      border: isSolid ? BIZ_COLOR_TOKENS.blockerSolidBg : BIZ_COLOR_TOKENS.blockerSubtleBorder,
      ariaRole: 'alert',
      iconType: 'close-circle',
    };
  }

  // 2. 关键要求 / 星号条款
  if (
    norm === 'star' ||
    norm === 'critical' ||
    norm === 'key' ||
    norm === '星号' ||
    norm === '关键' ||
    norm === '关键要求' ||
    norm === '实质性条款'
  ) {
    const isSolid = Boolean(options?.isSolid);
    return {
      category: 'star',
      label: custom ?? (norm.includes('星号') || norm === 'star' ? '星号条款' : '关键要求'),
      isSolid,
      bg: isSolid ? BIZ_COLOR_TOKENS.blockerSolidBg : BIZ_COLOR_TOKENS.starBg,
      color: isSolid ? BIZ_COLOR_TOKENS.blockerSolidText : BIZ_COLOR_TOKENS.starText,
      border: isSolid ? BIZ_COLOR_TOKENS.blockerSolidBg : BIZ_COLOR_TOKENS.starBorder,
      ariaRole: 'status',
      iconType: 'star',
    };
  }

  // 3. 警告 / 复核
  if (norm === 'warning' || norm === '警告' || norm === '需复核' || norm === 'review_required') {
    return {
      category: 'warning',
      label: custom ?? (norm === 'review_required' || norm === '需复核' ? '需复核' : '警告'),
      isSolid: false,
      bg: BIZ_COLOR_TOKENS.warningBg,
      color: BIZ_COLOR_TOKENS.warningText,
      border: BIZ_COLOR_TOKENS.warningBorder,
      ariaRole: 'status',
      iconType: 'warning',
    };
  }

  // 4. 加分项 / 评分项
  if (
    norm === 'bonus' ||
    norm === 'scoring' ||
    norm === '加分' ||
    norm === '加分项' ||
    norm === '评分' ||
    norm === '评分项'
  ) {
    return {
      category: 'bonus',
      label: custom ?? (norm.includes('加分') || norm === 'bonus' ? '加分项' : '评分项'),
      isSolid: false,
      bg: BIZ_COLOR_TOKENS.bonusBg,
      color: BIZ_COLOR_TOKENS.bonusText,
      border: BIZ_COLOR_TOKENS.bonusBorder,
      ariaRole: 'status',
      iconType: 'plus-circle',
    };
  }

  // 5. 资格要求
  if (norm === 'qualification' || norm === '资格' || norm === '资格要求') {
    return {
      category: 'qualification',
      label: custom ?? '资格要求',
      isSolid: false,
      bg: BIZ_COLOR_TOKENS.qualificationBg,
      color: BIZ_COLOR_TOKENS.qualificationText,
      border: BIZ_COLOR_TOKENS.qualificationBorder,
      ariaRole: 'status',
      iconType: 'check-circle',
    };
  }

  // 6. 提示
  if (norm === 'hint' || norm === '提示') {
    return {
      category: 'hint',
      label: custom ?? '提示',
      isSolid: false,
      bg: BIZ_COLOR_TOKENS.directBg,
      color: BIZ_COLOR_TOKENS.directText,
      border: BIZ_COLOR_TOKENS.directBorder,
      ariaRole: 'note',
      iconType: 'info-circle',
    };
  }

  // 7. 缺省：一般条款
  return {
    category: 'general',
    label: custom ?? '一般条款',
    isSolid: false,
    bg: BIZ_COLOR_TOKENS.generalBg,
    color: BIZ_COLOR_TOKENS.generalText,
    border: BIZ_COLOR_TOKENS.generalBorder,
    ariaRole: 'status',
    iconType: 'minus',
  };
}

/**
 * AI 变体类型
 */
export type AiTagVariant =
  | 'suggestion' // AI 建议
  | 'generated' // AI 生成
  | 'candidate' // 整章候选
  | 'model' // 模型撰写 / 模型建议
  | 'assistant' // 助手建议 / 助手撰写
  | 'demo' // 演示建议
  | 'default';

export interface ResolvedAiTag {
  label: string;
  isSolid: boolean;
  bg: string;
  color: string;
  border: string;
  ariaLabel: string;
}

/**
 * 解析 AI 标签（严格锁定 AI 紫色系）
 */
export function resolveAiTag(
  variant: AiTagVariant = 'suggestion',
  options?: { isSolid?: boolean; customLabel?: string }
): ResolvedAiTag {
  const isSolid = Boolean(options?.isSolid);
  let defaultLabel = 'AI 建议';

  switch (variant) {
    case 'generated':
      defaultLabel = 'AI 生成';
      break;
    case 'candidate':
      defaultLabel = '整章候选';
      break;
    case 'model':
      defaultLabel = '模型建议';
      break;
    case 'assistant':
      defaultLabel = '助手建议';
      break;
    case 'demo':
      defaultLabel = '演示建议';
      break;
    case 'suggestion':
    default:
      defaultLabel = 'AI 建议';
      break;
  }

  const label = options?.customLabel ?? defaultLabel;

  return {
    label,
    isSolid,
    bg: isSolid ? BIZ_COLOR_TOKENS.aiSolidBg : BIZ_COLOR_TOKENS.aiSubtleBg,
    color: isSolid ? BIZ_COLOR_TOKENS.aiSolidText : BIZ_COLOR_TOKENS.aiSubtleText,
    border: isSolid ? BIZ_COLOR_TOKENS.aiSolidBg : BIZ_COLOR_TOKENS.aiSubtleBorder,
    ariaLabel: `AI辅助标识：${label}`,
  };
}

/**
 * 直接采用 / 直接响应标签变体（答案卡直查）
 */
export type DirectTagVariant =
  | 'direct' // 系统直查 · 未经模型
  | 'adopt' // 直接采用
  | 'response' // 直接响应
  | 'struct' // 结构化直查
  | 'default';

export interface ResolvedDirectTag {
  label: string;
  bg: string;
  color: string;
  border: string;
  ariaLabel: string;
}

/**
 * 解析 DirectTag（严格使用系统直查蓝，绝不使用 AI 紫）
 */
export function resolveDirectTag(
  variant: DirectTagVariant = 'direct',
  customLabel?: string
): ResolvedDirectTag {
  let defaultLabel = '系统直查 · 未经模型';
  switch (variant) {
    case 'adopt':
      defaultLabel = '直接采用';
      break;
    case 'response':
      defaultLabel = '直接响应';
      break;
    case 'struct':
      defaultLabel = '结构化直查';
      break;
    case 'direct':
    default:
      defaultLabel = '系统直查 · 未经模型';
      break;
  }

  const label = customLabel ?? defaultLabel;

  // 严格断言防守
  assertNotAiColor('DirectTag', BIZ_COLOR_TOKENS.directText);

  return {
    label,
    bg: BIZ_COLOR_TOKENS.directBg,
    color: BIZ_COLOR_TOKENS.directText,
    border: BIZ_COLOR_TOKENS.directBorder,
    ariaLabel: `来源标识：${label}`,
  };
}

/**
 * 引用类型定义
 */
export type CiteType =
  | 'evidence' // 资料证据（如 [1] 或 [证]）
  | 'snippet' // 方案片段（如 [2] 或 [片]）
  | 'tender' // 招标原文（如 P.47 或 [原]）
  | 'fact' // 项目事实 / SLA 变量（黄底下划线）
  | 'none'; // 无知识库来源

export interface CiteMetadata {
  title?: string;
  version?: string | number;
  validUntil?: string;
  status?: string;
  assignee?: string;
  fingerprint?: string;
  quote?: string;
  page?: number | string;
}

export interface ResolvedCite {
  type: CiteType;
  marker: string;
  bg: string;
  color: string;
  border: string;
  isSuperscript: boolean;
  hasUnderline: boolean;
  metadata: CiteMetadata;
  ariaLabel: string;
}

/**
 * 解析引用标注元数据与展示样式
 */
export function resolveCite(
  type: CiteType = 'evidence',
  customMarker?: ReactNode,
  metadata?: CiteMetadata
): ResolvedCite {
  const meta = metadata ?? {};
  let defaultMarker = '[1]';
  let isSuperscript = true;
  let hasUnderline = false;
  let bg: string = BIZ_COLOR_TOKENS.directBg;
  let color: string = BIZ_COLOR_TOKENS.directText;
  let border: string = BIZ_COLOR_TOKENS.directBorder;

  switch (type) {
    case 'evidence':
      defaultMarker = meta.version ? `[证·v${meta.version}]` : '[证]';
      bg = BIZ_COLOR_TOKENS.directBg;
      color = BIZ_COLOR_TOKENS.directText;
      border = BIZ_COLOR_TOKENS.directBorder;
      isSuperscript = true;
      break;
    case 'snippet':
      defaultMarker = meta.version ? `[片·v${meta.version}]` : '[片]';
      bg = BIZ_COLOR_TOKENS.srcSnippetBg;
      color = BIZ_COLOR_TOKENS.srcSnippetText;
      border = BIZ_COLOR_TOKENS.bonusBorder;
      isSuperscript = true;
      break;
    case 'tender':
      defaultMarker = meta.page ? `P.${meta.page}` : '[原]';
      bg = BIZ_COLOR_TOKENS.srcTenderBg;
      color = BIZ_COLOR_TOKENS.srcTenderText;
      border = BIZ_COLOR_TOKENS.generalBorder;
      isSuperscript = true;
      break;
    case 'fact':
      defaultMarker = meta.title ?? '[变量]';
      bg = BIZ_COLOR_TOKENS.varBg;
      color = BIZ_COLOR_TOKENS.varText;
      border = BIZ_COLOR_TOKENS.varBorder;
      isSuperscript = false; // 变量行内高亮，不上标
      hasUnderline = true;
      break;
    case 'none':
      defaultMarker = '无知识库来源';
      bg = BIZ_COLOR_TOKENS.generalBg;
      color = BIZ_COLOR_TOKENS.generalText;
      border = BIZ_COLOR_TOKENS.generalBorder;
      isSuperscript = false;
      break;
  }

  const markerStr = typeof customMarker === 'string' || typeof customMarker === 'number'
    ? String(customMarker)
    : defaultMarker;

  return {
    type,
    marker: markerStr,
    bg,
    color,
    border,
    isSuperscript,
    hasUnderline,
    metadata: meta,
    ariaLabel: `引用标注：${markerStr}，来源类型：${type}`,
  };
}

/**
 * 段落来源条布局与元数据解析
 */
export type SourceKind =
  | 'evidence' // 证据
  | 'snippet' // 方案片段
  | 'tender' // 招标原文
  | 'model' // 模型撰写
  | 'assistant' // 对话助手撰写
  | 'manual' // 人工编写
  | 'system'; // 系统生成

export interface ResolvedSourceBar {
  kind: SourceKind;
  kindLabel: string;
  color: string;
  bg: string;
  sourceName: string;
  versionLabel?: string;
  formattedFingerprint?: string;
  isStale: boolean;
  statusLabel: string;
  ariaLabel: string;
}

/**
 * 格式化哈希/指纹（取前 8 位或前缀并保留完整回溯）
 */
export function formatFingerprint(fingerprint?: string | null): string {
  if (!fingerprint) return '无依据指纹';
  const clean = fingerprint.trim();
  if (clean.length <= 8) return `fp:${clean}`;
  return `fp:${clean.substring(0, 8)}...`;
}

/**
 * 解析 SourceBar 来源条数据
 */
export function resolveSourceBar(props: {
  kind?: SourceKind;
  sourceName?: string;
  version?: string | number;
  fingerprint?: string | null;
  status?: 'confirmed' | 'stale' | 'pending' | 'review_required' | string;
  statusText?: string;
}): ResolvedSourceBar {
  const kind = props.kind ?? 'evidence';
  let kindLabel = '资料证据';
  let color: string = BIZ_COLOR_TOKENS.srcEvidence;
  let bg: string = BIZ_COLOR_TOKENS.directBg;

  switch (kind) {
    case 'evidence':
      kindLabel = '资料证据';
      color = BIZ_COLOR_TOKENS.srcEvidence;
      bg = BIZ_COLOR_TOKENS.directBg;
      break;
    case 'snippet':
      kindLabel = '方案片段';
      color = BIZ_COLOR_TOKENS.srcSnippet;
      bg = BIZ_COLOR_TOKENS.srcSnippetBg;
      break;
    case 'tender':
      kindLabel = '招标原文';
      color = BIZ_COLOR_TOKENS.srcTenderText;
      bg = BIZ_COLOR_TOKENS.srcTenderBg;
      break;
    case 'model':
      kindLabel = '模型撰写';
      color = BIZ_COLOR_TOKENS.srcModel;
      bg = BIZ_COLOR_TOKENS.aiSubtleBg;
      break;
    case 'assistant':
      kindLabel = '助手撰写';
      color = BIZ_COLOR_TOKENS.srcAssistant;
      bg = BIZ_COLOR_TOKENS.aiSubtleBg;
      break;
    case 'manual':
      kindLabel = '人工编写';
      color = BIZ_COLOR_TOKENS.srcManual;
      bg = BIZ_COLOR_TOKENS.srcManualBg;
      break;
    case 'system':
      kindLabel = '系统生成';
      color = BIZ_COLOR_TOKENS.srcSystem;
      bg = BIZ_COLOR_TOKENS.srcSystemBg;
      break;
  }

  const isStale = props.status === 'stale' || props.status === 'review_required';
  const statusLabel =
    props.statusText ??
    (props.status === 'confirmed'
      ? '已确认'
      : props.status === 'stale'
      ? '来源已变化待核对'
      : props.status === 'review_required'
      ? '需复核'
      : '待确认');

  const sourceName = props.sourceName ?? `${kindLabel}来源`;
  const versionLabel = props.version !== undefined ? `v${props.version}` : undefined;
  const formattedFingerprint = props.fingerprint ? formatFingerprint(props.fingerprint) : undefined;

  return {
    kind,
    kindLabel,
    color,
    bg,
    sourceName,
    versionLabel,
    formattedFingerprint,
    isStale,
    statusLabel,
    ariaLabel: `段落来源条：${sourceName} ${versionLabel ?? ''} [${statusLabel}] ${formattedFingerprint ?? ''}`.trim(),
  };
}
