// 为什么有这个文件：提供 React 公司掩码设置上下文实例，解耦 Hook 层与 Provider 组件层。
// 它解决什么问题：支持页面与组件树全局响应式感知公司掩码规则动态变动，避免循环依赖。

import React from 'react';
import {
  DEFAULT_MASK_RULES,
  type IdCardMaskMode,
  type MaskRule,
  type SensitiveFieldType,
} from './sensitive-mask.ts';

/**
 * 公司掩码上下文状态与方法契约
 */
export interface CompanyMaskContextType {
  /** 当前生效的各字段掩码规则表 */
  rules: Record<SensitiveFieldType, MaskRule>;
  /** 获取特定字段类型的生效掩码规则 */
  getRule: (type: SensitiveFieldType) => MaskRule;
  /** 身份证掩码模式 ('standard' | 'strict') */
  idCardMode: IdCardMaskMode;
  /** 掩码配置加载状态 */
  loading: boolean;
  /** 规则来源 ('company' 表示已配置公司规则，'default' 表示平台安全兜底) */
  source: 'company' | 'default';
  /** 动态更新/切换掩码规则（支持传入字段规则补丁或身份证模式） */
  updateRules: (
    newRules: Partial<Record<SensitiveFieldType, Partial<MaskRule>>> | IdCardMaskMode
  ) => void;
  /** 重置为平台默认安全规则 */
  resetRules: () => void;
}

/**
 * 默认平台兜底上下文值
 */
export const DEFAULT_COMPANY_MASK_CONTEXT: CompanyMaskContextType = {
  rules: { ...DEFAULT_MASK_RULES },
  getRule: (type: SensitiveFieldType) => DEFAULT_MASK_RULES[type] || DEFAULT_MASK_RULES.custom,
  idCardMode: 'standard',
  loading: false,
  source: 'default',
  updateRules: () => {},
  resetRules: () => {},
};

/**
 * 全局/局部公司掩码上下文
 */
export const CompanyMaskContext = React.createContext<CompanyMaskContextType>(
  DEFAULT_COMPANY_MASK_CONTEXT
);
