为什么有这个文件：说明 APP-M2-T094（ProjectHeader 摘要条与页签）与 APP-M2-T095（项目列表与多维筛选）的具体实现、组件封装、状态流转与权限控制逻辑。

它解决什么问题：落实 PRD v1.8 §5.1.1～5.1.4 与交接规范约束：
1. 提取封装统一的 ProjectHeader 摘要组件，展示项目名称、标的金额（集成 MaskedField 掩码与审计调阅）、截止时间倒计时（≤3天标红预警）、分册列表（技术/商务两册完成度）与快速导航页签；
2. 涉密项目横幅展示（开启本地安全合规环境，禁止第三方大模型联网调用）；
3. 八角色权限感知（只读成员无编辑设置入口，自动剔除 settings 页签并禁用设置）；
4. 完善项目列表页（ProjectListPage），支持按生命周期状态（筹备中/编写中/审核中/已完成）、涉密属性（全部/涉密/普通）、分册状态（技术待写/商务待写/两册已完成）多维筛选，列表项支持快速进入工作台和查看项目元数据抽屉；
5. 架构关注点分离：将纯计算逻辑与视图解耦为 `project-header-core.ts` 和 `project-list-core.ts`，确保 Node.js 原生测试与前端构建双重健壮。

# APP-M2-T094 & T095：代码解释

- **对应任务**：
  - [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094) · ProjectHeader 摘要条与页签（无“资料匹配”）
  - [APP-M2-T095](../tasks/APP-M2.md#app-m2-t095) · 项目列表与多维筛选
- **关联 Issue**：[ISSUE-007](../../issues/ISSUE-007.md) · 编辑台与项目工作台主链路
- **交付文档**：[APP-M2-T094 交付](../delivery/APP-M2-T094.md)
- **日期**：2026-10-22
- **涉及源码与测试**：
  - `frontend/web/src/ProjectHeader.tsx`：ProjectHeader 项目摘要条与快速导航页签组件
  - `frontend/web/src/project-header-core.ts`：倒计时计算、金额格式化与八角色页签过滤纯函数
  - `frontend/web/src/ProjectListPage.tsx`：项目列表页、多维筛选栏与元数据详情抽屉组件
  - `frontend/web/src/project-list-core.ts`：生命周期阶段推导、分册状态推导与多维筛选纯函数
  - `frontend/web/src/ProjectPages.tsx`：模块统一导出更新
  - `frontend/web/src/App.tsx`：工作台与项目主外壳组件替换
  - `frontend/web/src/types.ts`：扩充 Project 实体类型可选字段
  - `tests/frontend/project-header-list.test.mjs`：专属单元测试用例

---

## 1. 核心设计与技术决策

### 1.1 架构分层：业务逻辑与 UI 渲染解耦
为了让项目生命周期状态推导、分册完成度计算、截止倒计时算法与角色权限过滤能够在轻量级 Node.js 原生测试套件中快速执行，同时兼顾 Web 端的响应式渲染与 Ant Design 组件复用，设计了严格的核心纯函数层：
- `project-header-core.ts`：纯 TypeScript，无 React / DOM 依赖，包含：
  - `calculateProjectCountdown(deadline, now?)`：计算剩余天数、小时数、紧急状态（`isUrgent: days < 3`）与过期判定；
  - `formatCurrencyAmount(amount)`：将数字或数字串格式化为标准千分位货币文本 `¥ 12,800,000.00`；
  - `canAccessProjectSettings(role, customPermissions?)`：八角色权限过滤，只读成员（`viewer`, `auditor`, `readonly` 等）禁止访问项目设置；
  - `filterProjectTabs(tabs, session, projectId, userRole, customPermissions?)`：过滤可用页签数组。
- `project-list-core.ts`：纯 TypeScript，包含：
  - `deriveProjectStatus(project)`：根据显式状态或章节与分册状态推导当前阶段（`preparing` / `writing` / `reviewing` / `completed`）；
  - `deriveVolumeStatus(project)`：推导技术分册与商务分册的各自状态及是否两册均已提交；
  - `filterProjectList(projects, criteria)`：执行包含关键词、生命周期状态、涉密属性与分册状态的多维联合过滤。

### 1.2 高敏商业信息脱敏与审计调阅（标的金额集成 MaskedField）
在政府采购与大型企业投标场景中，项目的“标的金额（预算金额）”属于企业一级商业秘密：
- 摘要条与列表项中默认执行脱敏掩码显示：保留前 2 位（`¥ `）与后 3 位（`.00`），中间全部以 `*` 遮蔽（如 `¥ *******.00`）；
- 紧密集成项目既有的 `<MaskedField>` 与 `<RevealFieldModal>`，调阅完整值前必须输入不少于 5 字的合规业务理由；
- 实施八角色权限隔离：项目负责人（`project_lead`）与公司管理员（`company_admin`）具备调阅完整值权限；只读成员（`viewer`）与审核人员（`auditor`）调阅按钮置灰并展示“仅项目负责人与公司管理员有权调阅完整标的金额”的悬浮 Tooltip。

### 1.3 投标截止时间倒计时（≤3 天紧急标红）
- 根据投标截止时间（`project.deadline`）与当前时间计算毫秒差；
- 若已过期，状态标记为 `expired`，返回红色 Tag（“已截止”）；
- 若剩余时间 `0 < days < 3`，状态标记为 `urgent`，返回橙色/红色告警 Tag（如“剩余 2 天 6 小时”），并在列表项对应列强化提醒；
- 若剩余时间充足（≥3 天），返回正常蓝色 Tag（如“剩余 5 天 3 小时”）。

### 1.4 涉密项目横幅展示（Sensitive Project Banner）
- 依据 `project.sensitive` 字段智能感知；
- 在 `ProjectHeader` 顶部渲染醒目的保密提示横幅（Alert）：标识“涉密项目 · 本地安全合规模式运行中”，明确声明系统已切断外部第三方大模型联网调用，敏感数据受严格审计与掩码保护；
- 在项目列表中对涉密项目附加保密锁图标与 `<Tag color="volcano">涉密</Tag>` 标签。

### 1.5 八角色感知：只读成员无编辑设置入口
- 依据 PRD v1.8 §2.2 / §2.3 的八角色 RBAC 规范，通过 `normalizeSystemRole` 将旧版角色（`viewer`, `readonly`, `auditor`）归一化；
- 在 `filterProjectTabs` 中判断用户角色是否属于 `READONLY_SYSTEM_ROLES`；
- 只读成员登录时，页签中彻底移除 `settings`（项目设置）项，导航与页面无任何进入设置的写入口，从源头上切断越权隐患。

---

## 2. 状态流转与组件调用链

### 2.1 ProjectHeader 组件流转架构
```text
Workspace / Project / ApplicationSession / User
                    │
                    ▼
          ProjectHeader.tsx
 ┌──────────────────┼──────────────────┐
 │                  │                  │
 ▼                  ▼                  ▼
[涉密横幅]       [核心状态条]        [元数据与脱敏]
project.sensitive   - 项目名称         - 招标编号
Alert (本地运行)     - 角色 Tag         - 投标主体
                    - 分册进度 Strip    - 标的金额 (MaskedField)
                                       - 截止倒计时 (≤3天标红)
                                       - 检查阻断数 / 待确认数
                    │
                    ▼
         [八角色快速导航页签]
       filterProjectTabs() 过滤
       - 概览 / 招标文件 / 解析结果 / 矩阵 / 事实表 / 编辑台 / 检查 / 导出
       - 只读成员自动剔除 settings（项目设置）
```

### 2.2 ProjectListPage 多维筛选流转架构
```text
Project[] 原始列表
        │
        ▼
[用户筛选交互]:
  1. 关键字搜索（项目名称 / 招标编号）
  2. 状态下拉框（全部 / 筹备中 / 编写中 / 审核中 / 已完成）
  3. 涉密属性下拉框（全部 / 涉密项目 / 普通项目）
  4. 分册状态下拉框（全部 / 技术分册待写 / 商务分册待写 / 两册均已完成）
        │
        ▼
   filterProjectList() 纯函数过滤
        │
        ▼
 filteredList (过滤后结果集)
        │
        ├───────────────────────────────┐
        ▼                               ▼
[Ant Design Table 渲染]       [项目元数据详情 Drawer]
- 名称与涉密 Tag               - 点击“元数据”按钮展开
- 招标编号                      - 基本属性（ID、名称、公司、涉密等级）
- 标的金额 (MaskedField 掩码)   - 标的金额调阅与审计
- 状态 Tag (推导阶段)           - 截止倒计时与时间节点
- 截止倒计时 (≤3天标红)          - 技术/商务两册编制进度
- 分册状态徽标                  - 一键直接进入工作台
- 操作（进入工作台 / 查看元数据）
```

---

## 3. 核心改动文件明细

| 文件路径 | 模块类型 | 核心改动说明 |
|---|---|---|
| `frontend/web/src/project-header-core.ts` | 业务核心 | 封装倒计时计算、金额千分位格式化、八角色权限过滤纯函数 |
| `frontend/web/src/project-list-core.ts` | 业务核心 | 封装项目生命周期状态推导、分册状态推导与多维筛选纯函数 |
| `frontend/web/src/ProjectHeader.tsx` | UI 组件 | 封装统一项目摘要条、涉密横幅、MaskedField 脱敏标的金额与页签导航 |
| `frontend/web/src/ProjectListPage.tsx` | UI 组件 | 封装项目列表多维筛选页、统计卡片与项目元数据抽屉 |
| `frontend/web/src/ProjectPages.tsx` | 模块入口 | 重导出 `ProjectHeader` 与 `ProjectListPage` |
| `frontend/web/src/App.tsx` | 应用主外壳 | 将原内联 project-header 和简陋 Table 替换为标准新组件 |
| `frontend/web/src/types.ts` | 类型声明 | 为 `Project` 增加 `target_amount`、`status`、`stage`、`volumes_status` 等可选字段 |
| `frontend/web/src/editor-conflict.ts` | 兼容增强 | 为 `WordCountInfo` 增加 `current`、`target`、`percentage` 兼容别名字段 |
| `tests/frontend/project-header-list.test.mjs` | 单元测试 | 5 个测试用例，覆盖倒计时判定、金额脱敏、页签权限隔离与多维筛选 |

---

## 4. 边界条件与异常保护

1. **倒计时空值与非法时间保护**：当 `deadline` 为 `null`、`undefined` 或非法日期格式时，`calculateProjectCountdown` 返回 `status: 'none'`，展示“未设定截止时间”或“截止时间格式无效”，不抛出异常。
2. **标的金额非数字安全解析**：当 `target_amount` 为字符串（如 `"12800000"` 或包含非数字字符）时，自动正则清洗并转换为浮点数格式化；若为空则安全降级为“未填写”。
3. **只读权限越权拦截**：只读成员无法通过 UI 界面查看或点击“项目设置”；在标的金额调阅弹窗中，只读成员的“查看完整金额”按钮被自动置灰禁用并带有权限解释 Tooltip。
4. **涉密数据防公网泄露**：涉密项目展示醒目安全策略横幅，并在元数据抽屉中明确告知离线合规运行约束。
