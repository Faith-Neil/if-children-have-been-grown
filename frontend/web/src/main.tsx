// 为什么有这个文件：启动 ICG 正式页面并装配设计主题。
// 它解决什么问题：所有页面共享中文组件和固定的风险、建议颜色。
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/es/locale/zh_CN';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ConfigProvider locale={zhCN} theme={{
    token: { colorPrimary: '#1E4DB7', colorInfo: '#1E4DB7', colorSuccess: '#2B9D5C', colorWarning: '#E08A1E', colorError: '#D9363E', colorText: '#1D2129', colorTextSecondary: '#86909C', colorBgLayout: '#F5F7FA', borderRadius: 6, fontSize: 13, fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif', controlHeight: 32 },
    components: { Table: { headerBg: '#F7F8FA', cellPaddingBlockSM: 11, cellPaddingInlineSM: 12 }, Tabs: { horizontalItemGutter: 26 } },
  }}><AntApp><App /></AntApp></ConfigProvider></React.StrictMode>,
);
