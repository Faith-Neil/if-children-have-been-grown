// 为什么有这个文件：把外壳和各页面从首屏入口里拆出去。
// 它解决什么问题：登录页不必先下载 ProLayout 和尚未打开的项目页。

let shellModule: ReturnType<typeof importShell> | undefined;
let editorModule: ReturnType<typeof importEditor> | undefined;
let settingsModule: ReturnType<typeof importSettings> | undefined;
let projectModule: ReturnType<typeof importProjectPages> | undefined;
let supportModule: ReturnType<typeof importSupportPages> | undefined;
let libraryModule: ReturnType<typeof importLibraryPages> | undefined;
let auditModule: ReturnType<typeof importAuditLogPage> | undefined;
let companyModule: ReturnType<typeof importCompanyManagePage> | undefined;
let dictConfigModule: ReturnType<typeof importDictConfigPage> | undefined;
let companySettingsModule: ReturnType<typeof importCompanySettingsPage> | undefined;
let usersModule: ReturnType<typeof importUsersPage> | undefined;
let snippetLibraryModule: ReturnType<typeof importSnippetLibraryPage> | undefined;
let writingArchiveModule: ReturnType<typeof importWritingArchivePage> | undefined;

function importShell() { return import('../shell/AppShell.tsx'); }
function importEditor() { return import('../editor/EditorPage.tsx'); }
function importSettings() { return import('../project/ProjectSettingsPage.tsx'); }
function importProjectPages() { return import('../project/ProjectPages.tsx'); }
function importSupportPages() { return import('./SupportPages.tsx'); }
function importLibraryPages() { return import('../library/LibraryPages.tsx'); }
function importAuditLogPage() { return import('../admin/AuditLogPage.tsx'); }
function importCompanyManagePage() { return import('../admin/CompanyManagePage.tsx'); }
function importDictConfigPage() { return import('../admin/DictConfigPage.tsx'); }
function importCompanySettingsPage() { return import('../admin/CompanySettingsPage.tsx'); }
function importUsersPage() { return import('../admin/UsersPage.tsx'); }
function importSnippetLibraryPage() { return import('../library/SnippetLibraryPage.tsx'); }
function importWritingArchivePage() { return import('../library/WritingArchivePage.tsx'); }

export function loadShell() { shellModule ??= importShell(); return shellModule; }
export function loadEditor() { editorModule ??= importEditor(); return editorModule; }
export function loadSettings() { settingsModule ??= importSettings(); return settingsModule; }
export function loadProjectPages() { projectModule ??= importProjectPages(); return projectModule; }
export function loadSupportPages() { supportModule ??= importSupportPages(); return supportModule; }
export function loadLibraryPages() { libraryModule ??= importLibraryPages(); return libraryModule; }
export function loadAuditLog() { auditModule ??= importAuditLogPage(); return auditModule; }
export function loadCompanyManage() { companyModule ??= importCompanyManagePage(); return companyModule; }
export function loadDictConfig() { dictConfigModule ??= importDictConfigPage(); return dictConfigModule; }
export function loadCompanySettings() { companySettingsModule ??= importCompanySettingsPage(); return companySettingsModule; }
export function loadUsersPage() { usersModule ??= importUsersPage(); return usersModule; }
export function loadSnippetLibraryPage() { snippetLibraryModule ??= importSnippetLibraryPage(); return snippetLibraryModule; }
export function loadWritingArchivePage() { writingArchiveModule ??= importWritingArchivePage(); return writingArchiveModule; }
