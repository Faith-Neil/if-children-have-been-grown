// 为什么有这个文件：提供 React 公司掩码设置 Hook 与 Provider 容器。
// 它解决什么问题：支持全局或子树组件透明读取公司掩码配置，并在设置变更时自动响应式刷新展示，未配置时安全兜底。

import React, { useCallback, useContext, useMemo, useState } from 'react';
import {
  DEFAULT_MASK_RULES,
  type IdCardMaskMode,
  type MaskRule,
  type SensitiveFieldType,
} from './sensitive-mask.ts';
import {
  extractMaskRulesFromCompanySettings,
  sanitizeMaskRule,
} from './company-mask-settings.ts';
import {
  CompanyMaskContext,
  DEFAULT_COMPANY_MASK_CONTEXT,
  type CompanyMaskContextType,
} from './company-mask-context.ts';

export interface CompanyMaskProviderProps {
  /** 公司设置数据（包含 sensitive_mask_rules 或直接规则对象） */
  companySettings?: unknown;
  /** 直接传入的掩码规则覆盖项 */
  rules?: Partial<Record<SensitiveFieldType, Partial<MaskRule>>>;
  /** 身份证掩码模式快捷指定 ('standard' 6+4 或 'strict' 3+4) */
  idCardMode?: IdCardMaskMode;
  /** 是否处于加载中状态 */
  loading?: boolean;
  children: React.ReactNode;
}

/**
 * 公司掩码设置上下文容器组件
 */
export function CompanyMaskProvider({
  companySettings,
  rules: explicitRules,
  idCardMode: explicitIdCardMode,
  loading = false,
  children,
}: CompanyMaskProviderProps) {
  // 1. 从外部公司设置中解析初始规则
  const initialResolved = useMemo(() => {
    const res = extractMaskRulesFromCompanySettings(companySettings);
    if (explicitIdCardMode) {
      res.idCardMode = explicitIdCardMode;
      if (explicitIdCardMode === 'strict') {
        res.rules.id_card = { prefix: 3, suffix: 4, maskChar: '*', fixedLength: undefined };
      } else {
        res.rules.id_card = { prefix: 6, suffix: 4, maskChar: '*', fixedLength: 8 };
      }
      res.isCustom = true;
    }
    if (explicitRules) {
      for (const [key, rule] of Object.entries(explicitRules)) {
        if (rule) {
          const fieldType = key as SensitiveFieldType;
          res.rules[fieldType] = sanitizeMaskRule(fieldType, rule);
          res.isCustom = true;
        }
      }
    }
    return res;
  }, [companySettings, explicitIdCardMode, explicitRules]);

  // 2. 维护运行时的动态规则覆盖状态（支持响应式即时切换）
  const [runtimeOverrides, setRuntimeOverrides] = useState<
    Partial<Record<SensitiveFieldType, MaskRule>> | null
  >(null);
  const [runtimeIdCardMode, setRuntimeIdCardMode] = useState<IdCardMaskMode | null>(null);

  // 3. 计算最终生效规则集合
  const activeSettings = useMemo(() => {
    const rules = { ...initialResolved.rules };
    let idCardMode = runtimeIdCardMode ?? initialResolved.idCardMode;

    if (runtimeOverrides) {
      for (const [key, val] of Object.entries(runtimeOverrides)) {
        if (val) {
          rules[key as SensitiveFieldType] = val;
        }
      }
    }

    const isCustom = initialResolved.isCustom || Boolean(runtimeOverrides) || Boolean(runtimeIdCardMode);
    return {
      rules,
      idCardMode,
      source: (isCustom ? 'company' : 'default') as 'company' | 'default',
    };
  }, [initialResolved, runtimeOverrides, runtimeIdCardMode]);

  // 4. 提供规则查询与更新方法
  const getRule = useCallback(
    (type: SensitiveFieldType): MaskRule => {
      return activeSettings.rules[type] || DEFAULT_MASK_RULES[type] || DEFAULT_MASK_RULES.custom;
    },
    [activeSettings.rules]
  );

  const updateRules = useCallback(
    (newRules: Partial<Record<SensitiveFieldType, Partial<MaskRule>>> | IdCardMaskMode) => {
      if (typeof newRules === 'string') {
        // 模式切换：'standard' | 'strict'
        const mode = newRules as IdCardMaskMode;
        setRuntimeIdCardMode(mode);
        setRuntimeOverrides((prev) => ({
          ...(prev || {}),
          id_card:
            mode === 'strict'
              ? { prefix: 3, suffix: 4, maskChar: '*', fixedLength: undefined }
              : { prefix: 6, suffix: 4, maskChar: '*', fixedLength: 8 },
        }));
      } else if (typeof newRules === 'object' && newRules !== null) {
        const sanitizedPatch: Partial<Record<SensitiveFieldType, MaskRule>> = {};
        for (const [key, rule] of Object.entries(newRules)) {
          if (rule) {
            const fieldType = key as SensitiveFieldType;
            sanitizedPatch[fieldType] = sanitizeMaskRule(fieldType, rule);
          }
        }
        setRuntimeOverrides((prev) => ({
          ...(prev || {}),
          ...sanitizedPatch,
        }));
      }
    },
    []
  );

  const resetRules = useCallback(() => {
    setRuntimeOverrides(null);
    setRuntimeIdCardMode(null);
  }, []);

  const contextValue: CompanyMaskContextType = useMemo(
    () => ({
      rules: activeSettings.rules,
      getRule,
      idCardMode: activeSettings.idCardMode,
      loading,
      source: activeSettings.source,
      updateRules,
      resetRules,
    }),
    [activeSettings, getRule, loading, updateRules, resetRules]
  );

  return React.createElement(
    CompanyMaskContext.Provider,
    { value: contextValue },
    children
  );
}

/**
 * 获取当前公司掩码设置与规则的 Hook
 */
export function useCompanyMaskSettings(): CompanyMaskContextType {
  const context = useContext(CompanyMaskContext);
  return context || DEFAULT_COMPANY_MASK_CONTEXT;
}

export default useCompanyMaskSettings;
