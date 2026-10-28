// 为什么有这个文件：按页面建立可延迟的组件，而不是在入口里直接引用。
// 它解决什么问题：只有真正打开的路由才下载对应代码。
import { lazy } from 'react';
import { loadAuditLog, loadCompanyManage, loadCompanySettings, loadDictConfig, loadEditor, loadLibraryPages, loadProjectPages, loadSettings, loadShell, loadSnippetLibraryPage, loadSupportPages, loadUsersPage, loadWritingArchivePage } from './route-loaders.ts';

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
export const LazyLibraryPage = lazy(() => loadLibraryPages().then(module => ({ default: module.LibraryPage })));
export const LazyJobsPage = lazy(() => loadSupportPages().then(module => ({ default: module.JobsPage })));
export const LazyPendingPage = lazy(() => loadSupportPages().then(module => ({ default: module.PendingPage })));
export const LazyAuditLogPage = lazy(() => loadAuditLog().then(module => ({ default: module.AuditLogPage })));
export const LazyCompanyManagePage = lazy(() => loadCompanyManage().then(module => ({ default: module.CompanyManagePage })));
export const LazyDictConfigPage = lazy(() => loadDictConfig().then(module => ({ default: module.DictConfigPage })));
export const LazyCompanySettingsPage = lazy(() => loadCompanySettings().then(module => ({ default: module.CompanySettingsPage })));
export const LazyUsersPage = lazy(() => loadUsersPage().then(module => ({ default: module.UsersPage })));
export const LazySnippetLibraryPage = lazy(() => loadSnippetLibraryPage().then(module => ({ default: module.SnippetLibraryPage })));
export const LazyWritingArchivePage = lazy(() => loadWritingArchivePage().then(module => ({ default: module.WritingArchivePage })));
