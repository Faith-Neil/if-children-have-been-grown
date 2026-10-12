// 为什么有这个文件：用已批准的 ProLayout 放侧栏、顶栏和内容区。
// 它解决什么问题：保留原 ICG 深色侧栏、白顶栏和菜单，而不是再手写一套外壳。
import type { ReactNode } from 'react';
import { Button } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { ProLayout } from '@ant-design/pro-layout';

const proLayoutToken = {
  bgLayout: '#F5F7FA',
  colorPrimary: '#1E4DB7',
  header: {
    colorBgHeader: '#FFFFFF',
    colorHeaderTitle: '#1D2129',
    heightLayoutHeader: 56,
    colorTextRightActionsItem: '#4E5969',
    colorBgRightActionsItemHover: '#F2F3F5',
    colorTextMenu: '#4E5969',
    colorTextMenuSelected: '#1E4DB7',
    colorBgMenuItemSelected: '#EEF3FC',
  },
  sider: {
    colorMenuBackground: '#0F1C3F',
    colorMenuItemDivider: 'rgba(255,255,255,0.08)',
    colorTextMenu: 'rgba(255,255,255,0.72)',
    colorTextMenuSecondary: 'rgba(255,255,255,0.56)',
    colorTextMenuSelected: '#FFFFFF',
    colorTextMenuActive: '#FFFFFF',
    colorTextMenuItemHover: '#FFFFFF',
    colorBgMenuItemSelected: '#1E4DB7',
    colorBgMenuItemHover: 'rgba(255,255,255,0.06)',
    colorBgMenuItemActive: 'rgba(255,255,255,0.10)',
    colorTextMenuTitle: '#FFFFFF',
    colorTextSubMenuSelected: '#FFFFFF',
    colorBgCollapsedButton: '#FFFFFF',
    colorTextCollapsedButton: '#4E5969',
    colorTextCollapsedButtonHover: '#1E4DB7',
    paddingInlineLayoutMenu: 8,
    paddingBlockLayoutMenu: 8,
  },
  pageContainer: {
    colorBgPageContainer: '#F5F7FA',
    paddingInlinePageContainerContent: 0,
    paddingBlockPageContainerContent: 0,
    colorBgPageContainerFixed: '#FFFFFF',
  },
};

export function AppShell({ collapsed, onCollapsed, menuPath, menu, onNavigate, breadcrumb, actions, children }: {
  collapsed: boolean;
  onCollapsed: (collapsed: boolean) => void;
  menuPath: string;
  menu: { path: string; name: string; icon: ReactNode }[];
  onNavigate: (path: string) => void;
  breadcrumb: ReactNode;
  actions: ReactNode;
  children: ReactNode;
}) {
  return <ProLayout className="icg-shell" title="智能投标系统" logo={<span className="brand-square">标</span>} layout="side" navTheme="realDark" locale="zh-CN" fixSiderbar fixedHeader siderWidth={216} breakpoint={false} disableMobile collapsed={collapsed} onCollapse={onCollapsed} collapsedButtonRender={false} contentStyle={{ padding: 0 }} token={proLayoutToken} location={{ pathname: menuPath }} route={{ path: '/', routes: menu }} menu={{ locale: false }} menuItemRender={(item, dom) => {
    const path = item.path || '/workbench';
    return <a href={path} onClick={event => { if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return; event.preventDefault(); onNavigate(path); }}>{dom}</a>;
  }} headerContentRender={() => <div className="topbar-leading"><Button type="text" aria-label="收起或展开导航" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => onCollapsed(!collapsed)} />{breadcrumb}</div>} actionsRender={() => [<div className="topbar-right" key="actions">{actions}</div>]} footerRender={false} pageTitleRender={() => 'ICG · 智能投标系统'} ErrorBoundary={false}>{children}</ProLayout>;
}
