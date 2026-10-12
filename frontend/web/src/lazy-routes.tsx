// 为什么有这个文件：按页面建立可延迟的组件，而不是在入口里直接引用。
// 它解决什么问题：只有真正打开的路由才下载对应代码。
import { lazy } from 'react';
import { loadEditor, loadProjectPages, loadSettings, loadShell, loadSupportPages } from './route-loaders.ts';

export const LazyAppShell = lazy(() => loadShell().then(module => ({ default: module.AppShell })));
export const LazyEditorPage = lazy(() => loadEditor());
export const LazyProjectSettingsPage = lazy(() => loadSettings());
export const LazyOverviewPage = lazy(() => loadProjectPages().then(module => ({ default: module.OverviewPage })));
export const LazyTenderPage = lazy(() => loadProjectPages().then(module => ({ default: module.TenderPage })));
export const LazyParsePage = lazy(() => loadProjectPages().then(module => ({ default: module.ParsePage })));
export const LazyMatrixPage = lazy(() => loadProjectPages().then(module => ({ default: module.MatrixPage })));
export const LazyFactsPage = lazy(() => loadProjectPages().then(module => ({ default: module.FactsPage })));
export const LazyChecksPage = lazy(() => loadProjectPages().then(module => ({ default: module.ChecksPage })));
export const LazyExportPage = lazy(() => loadProjectPages().then(module => ({ default: module.ExportPage })));
export const LazyLibraryPage = lazy(() => loadSupportPages().then(module => ({ default: module.LibraryPage })));
export const LazyJobsPage = lazy(() => loadSupportPages().then(module => ({ default: module.JobsPage })));
export const LazyPendingPage = lazy(() => loadSupportPages().then(module => ({ default: module.PendingPage })));
