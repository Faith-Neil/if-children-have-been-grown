为什么有这个文件：用普通话解释资料表单如何保护旧填写和协作者的新资料。

它解决什么问题：让接手者能找到实际判断和请求入口，不把页面按钮变灰当成完整保护。

# APP-M1-T16代码解释

日期：2026-10-11。关联[ISSUE-008](../../issues/ISSUE-008.md)。版本library-basis-1，分支`codex/repository-foundation`；本次修现有文字资料及公司服务承诺模板的并发覆盖，不实现完整C01/C06。

## 页面与后台是同一个产品

`ICG/frontend doc`是目标设计/交接资料；[App](../../frontend/web/src/App.tsx)加载真实项目和资料，资料表单在[SupportPages](../../frontend/web/src/SupportPages.tsx)。用户保存时，页面把内容和自己实际核对过的公司版本交给`backend/bid-core`中的资料路由。后台只在版本匹配时原子保存，意思是“这次修改要么全部成功，要么一点也不留下”。没有第二套独立产品或资料库。

## 实际数据流

1. 页面把完整资料集合交给依据核验，顶栏和列表搜索只过滤展示。搜索不代表记录被删或失去权限。
2. 打开记录时，[library-review](../../frontend/web/src/library-review.ts)的`captureLibraryReview`保存公司、公司资料版本和记录字段的快照。快照就是当时看见的一份副本；后续刷新不能自动把它变成新版。
3. 保存处理函数等待表单校验后，重新检查当前编辑窗口、角色和忙碌状态；`libraryWriteVersion`核对原依据，再把原公司/版本作为第四参数传给App保存入口。App的`libraryMutationVersion`再次核对，真实后台还用`If-Match`核验版本。
4. 409表示“你读到的版本已经过时”。页面只刷新当前后台状态，保留原依据和填写，因此下一次点击也不能借新版本覆盖资料。
5. 明确核对入口重新读取后台，展示最初资料、未保存填写、后台新资料。点击确认后，`loadReviewedLibrary`再次真实读取；若核对期间又变，拒绝载入且填写不动。目标未变只更新已核对公司版本并保留填写；目标已变则在明确提示后载入最新资料，再重新修改。
6. 编辑窗口切换/关闭用会话序号保护待决回调；读取时检查登录会话及公司，切换账号后的旧请求不能替换新页面资料。

公司版本是一整个公司资料集合的修改序号，记录版本是某条资料的修改序号。当前后台使用公司版本锁住写入，因此另一条资料变化也须明确核对；这是保守保护，不是生产数据库锁。

## 兼容性、验证和限制

新增真实[后台接口回归](../../tests/backend/test_library_basis.py)验证原后台旧版本拒绝、无副作用、重复操作、跨公司和只读；[前端函数回归](../../frontend/web/tests/library-review.test.mjs)执行页面实际使用的依据/异步载入函数。

公司SLA模板表单在[SlaPages](../../frontend/web/src/SlaPages.tsx)，使用[template-review](../../frontend/web/src/template-review.ts)保存完整字段、业务版本、记录版本及指标数组依据。`copyTemplate`深拷贝指标，避免表单编辑改变原依据；`templateWriteVersion`绑定实际读取的版本，`loadReviewedTemplate`真实再GET后才允许载入。

App保存两个带公司身份的内容/版本副本，`readCompanyCollections`将每次GET返回的集合和版本成对保存；`companyCollectionMutationVersion`按请求路径选自己的依据，模板入口强制携带已核对版本，不能借普通资料的新版本。读模板只更新模板副本，不升级旧资料依据。登录/退出/401清公司数据，`visibleCompanyCollection`隐藏非本公司副本，`companyReadSessionMatches`拒绝另一账号、公司或过期页面的迟到读取。

[独立模板接口反例](../../tests/backend/test_sla_template_basis.py)验证30→90、数组增删及无副作用；[模板函数回归](../../frontend/web/tests/template-review.test.mjs)执行真实依据和异步读取函数。最终后台229、前端58、类型检查与构建通过，GUI验证30→90→120及最终120→150、重新核对成功保存和切公司无残留；具体版本与6张真实截图见验证记录。无新增后台接口，OpenAPI48路径56操作不变。

实际命令、页面反例和数量见[验证记录](../testing/2026-10-11-library-basis.md)。当前没有负责人权限、受限ACL、独立审核、完整附件或引用历史；这些继续APP-M2。没有改变模型和数据库替换接口。浏览器未收到的最新并发写入最终仍由后台版本拒绝，网络失败不更换表单；无法用任何有限测试声称所有未来场景都不会出错。
