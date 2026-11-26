// 为什么有这个文件：启动 ICG 正式页面并装配设计主题与 React-Router 现代化路由环境。
// 它解决什么问题：所有页面共享中文组件、React-Router 浏览器路由上下文和固定的风险、建议颜色。
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/es/locale/zh_CN';
import { BrowserRouter } from 'react-router-dom';
import App from './app/App';
import './shared/styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={{
      token: { colorPrimary: '#1E4DB7', colorInfo: '#1E4DB7', colorSuccess: '#237804', colorWarning: '#B54708', colorError: '#D9363E', colorText: '#1D2129', colorTextSecondary: '#4E5969', colorBgLayout: '#F4F6FA', colorBgContainer: '#FFFFFF', colorBorder: '#DDE3EE', colorBorderSecondary: '#E8EDF5', borderRadius: 8, borderRadiusLG: 12, borderRadiusSM: 6, boxShadowTertiary: '0 1px 2px rgba(15, 28, 63, 0.04), 0 8px 24px rgba(15, 28, 63, 0.06)', fontSize: 13, fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif', controlHeight: 32, motionDurationMid: '0.2s', motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)' },
      components: { Table: { headerBg: '#F8FAFD', cellPaddingBlockSM: 11, cellPaddingInlineSM: 12 }, Tabs: { horizontalItemGutter: 26 }, Card: { borderRadiusLG: 12 }, Button: { borderRadius: 8 }, Input: { borderRadius: 8 }, Select: { borderRadius: 8 }, Tag: { borderRadiusSM: 6 }, Drawer: { borderRadiusLG: 16 }, Modal: { borderRadiusLG: 16 } },
    }}>
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
