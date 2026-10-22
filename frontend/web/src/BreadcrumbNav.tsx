// 为什么有这个文件：封装符合 ICG 规范的动态层级面包屑导航组件。
// 它解决什么问题：
// 1. 基于 Ant Design 5 Breadcrumb 规范，呈现由纯逻辑层推导的多层级导航轨迹；
// 2. 支持上层节点可点击快速逐级跳转回退，末级呈现语义化当前页（aria-current="page" 与 .breadcrumb-leaf 样式）；
// 3. 悬停提示完整名称，并在窄屏/紧凑视口下防止文字换行溢出。

import type { ReactNode } from 'react';
import { Breadcrumb } from 'antd';
import type { BreadcrumbItemData } from './responsive';

export interface BreadcrumbNavProps {
  /** 面包屑项数据清单 */
  items: BreadcrumbItemData[];
  /** 路径跳转回调函数 */
  onNavigate: (path: string) => void;
  /** 自定义外层 CSS 类名 */
  className?: string;
  /** 扩展插槽（如额外操作或状态提示） */
  extra?: ReactNode;
}

export function BreadcrumbNav({
  items,
  onNavigate,
  className = 'topbar-breadcrumb',
  extra,
}: BreadcrumbNavProps) {
  const antdItems = items.map(item => {
    const isLeaf = item.isCurrent || !item.path;
    return {
      key: item.key,
      title: isLeaf ? (
        <span
          className="breadcrumb-leaf"
          title={item.fullTitle}
          aria-current="page"
          data-testid={`breadcrumb-leaf-${item.key}`}
        >
          {item.title}
        </span>
      ) : (
        <a
          href={item.path}
          title={item.fullTitle}
          data-testid={`breadcrumb-link-${item.key}`}
          onClick={event => {
            if (
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey ||
              event.button !== 0
            ) {
              return;
            }
            event.preventDefault();
            onNavigate(item.path!);
          }}
        >
          {item.title}
        </a>
      ),
    };
  });

  return (
    <nav
      aria-label="面包屑导航"
      className="topbar-breadcrumb-nav"
      data-testid="topbar-breadcrumb-nav"
    >
      <Breadcrumb className={className} items={antdItems} />
      {extra}
    </nav>
  );
}

export default BreadcrumbNav;
