// 为什么有这个文件：平台默认品牌方标。
// 它解决什么问题：登录页、改密页和侧栏共用同一简约图标，不再用文字「标」。

import React from 'react';

export function BrandMark({ className = 'brand-square' }: { className?: string }) {
  return (
    <span className={className} aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path
          fill="currentColor"
          d="M7.2 3.5h7.1L18.5 7.7v12.8c0 .6-.5 1.1-1.1 1.1H7.2c-.6 0-1.1-.5-1.1-1.1V4.6c0-.6.5-1.1 1.1-1.1zm6.5 1.2v3.1h3.1l-3.1-3.1zM8.8 12.2h6.4v1.5H8.8v-1.5zm0 3.3h4.6v1.5H8.8v-1.5z"
        />
      </svg>
    </span>
  );
}
