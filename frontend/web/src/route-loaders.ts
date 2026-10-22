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

function importShell() { return import('./AppShell.tsx'); }
function importEditor() { return import('./EditorPage.tsx'); }
function importSettings() { return import('./ProjectSettingsPage.tsx'); }
function importProjectPages() { return import('./ProjectPages.tsx'); }
function importSupportPages() { return import('./SupportPages.tsx'); }
function importLibraryPages() { return import('./LibraryPages.tsx'); }
function importAuditLogPage() { return import('./AuditLogPage.tsx'); }
function importCompanyManagePage() { return import('./CompanyManagePage.tsx'); }

export function loadShell() { shellModule ??= importShell(); return shellModule; }
export function loadEditor() { editorModule ??= importEditor(); return editorModule; }
export function loadSettings() { settingsModule ??= importSettings(); return settingsModule; }
export function loadProjectPages() { projectModule ??= importProjectPages(); return projectModule; }
export function loadSupportPages() { supportModule ??= importSupportPages(); return supportModule; }
export function loadLibraryPages() { libraryModule ??= importLibraryPages(); return libraryModule; }
export function loadAuditLog() { auditModule ??= importAuditLogPage(); return auditModule; }
export function loadCompanyManage() { companyModule ??= importCompanyManagePage(); return companyModule; }

