// 为什么有这个文件：antd 5.29 起废弃 InputNumber 的 addonAfter，官方替代是 Space.Compact 组合。
// 它解决什么问题：统一“数字输入框 + 单位后缀”写法，避免各设置页各自内联拼接样式。

import React from 'react';
import { InputNumber, Space } from 'antd';
import type { InputNumberProps } from 'antd';

export interface UnitInputNumberProps<T extends string | number = string | number>
  extends InputNumberProps<T> {
  unit: React.ReactNode;
}

export function UnitInputNumber<T extends string | number = string | number>({
  unit,
  style,
  ...rest
}: UnitInputNumberProps<T>) {
  return (
    <Space.Compact style={{ width: '100%' }}>
      <InputNumber {...rest} style={{ width: '100%', ...style }} />
      <span
        style={{
          padding: '0 11px',
          display: 'flex',
          alignItems: 'center',
          flex: 'none',
          border: '1px solid #d9d9d9',
          borderLeft: 0,
          borderRadius: '0 6px 6px 0',
          background: 'rgba(0,0,0,0.02)',
          color: 'rgba(0,0,0,0.65)',
        }}
      >
        {unit}
      </span>
    </Space.Compact>
  );
}

export default UnitInputNumber;
