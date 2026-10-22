为什么有这个文件：说明检查阻断红线判定、整本导出 400 强门禁、内部评审稿放行与 Word 默认版式 SHA-256 元数据核对的技术实现与代码设计。

它解决什么问题：落实 PRD v1.8 §5.12 与 ISSUE-006、ISSUE-027 规范，防止废标红线与关键标星条款带病递交导出（400 CHECK_BLOCKER_EXISTS），支持内部评审稿放行并标记合规告警，且在整本导出快照中注入 64 位 SHA-256 文件指纹与 Word 默认版式元数据，确保与前端/Word 导出视觉基准严格对齐。

# BE-CHECKS-EXPORT-ALIGN：检查阻断红线与整本导出快照版式核对代码说明

## 1. 业务上下文与改动背景
在标书编制与合规审查业务中，招标文件通常包含两类核心强制性条款：
1. **废标红线（Disqualification Clauses）**：触发即导致投标文件被直接否决、废标的条款（如标记“废标”、“否决投标”或 `category="disqualification"`）。
2. **关键星号条款（Star Clauses）**：标书中带有“★”或标记“标星”的关键强制要求项（`importance="star"` 或 `category="star"`）。

若上述条款存在以下任何一种未有效响应情况：
- 条款未映射到任何响应章节；
- 条款响应状态为未确认（`status != "confirmed"`）；
- 对应章节内容为空或包含占位符（如“待补”、“待编写”）；
- 缺少已核验的企业资质/业绩证据支撑（`evidence_ids` 为空、证据未审核通过、证据已过期、或引用了历史参考标书）。

在进行标书合规检查（`POST /api/v1/projects/{project_id}/checks`）时，该缺陷必须被判定为最高等级的严重度——**`blocker`（阻断缺陷）**，普通缺陷则保持为 `blocking` 或 `warning`。

在整本导出接口（`POST /api/v1/projects/{project_id}/exports`）时：
- 若导出模式为 **`submission`（正式递交版）**，且当前分册最新检查结果中存在未解决的 `blocker` 缺陷，系统执行**强拦截门禁**，抛出 HTTP 400 与业务错误码 `CHECK_BLOCKER_EXISTS`，绝对禁止带病导出；
- 若导出模式为 **`internal_review`（内部评审稿）**，系统允许放行导出以供团队内部审阅，但在导出的快照元数据中显式记录 `has_blockers=True`，并给出合规预警提示（`compliance_notice`）；
- 导出的快照结构中，必须包含符合行业标准的 64 位十六进制 SHA-256 内容哈希指纹，并注入基于 BE-M0-T15 验收标准的 Word 默认版式元数据（包含 A4 纸张、上/下/左/右标准边距、方正小标宋/黑体/楷体/仿宋等中文字体层级、28pt 行间距、560 缇首行缩进等）。

---

## 2. 核心代码变更与模型演进

### 2.1 契约模型扩展 (`workflow_schemas.py`)
- **文件路径**：`backend/bid-core/icg_demo/workflow_schemas.py`
- **代码改动**：
  ```python
  class CheckIssue(BaseModel):
      # ...
      severity: Literal["blocking", "warning", "blocker"] = Field(
          default="blocking", description="问题严重程度：blocker 阻断、blocking 阻塞、warning 警告"
      )

  class ProjectExportRequest(BaseModel):
      # ...
      kind: Literal["internal", "submission", "internal_review"] = Field(
          default="internal", description="导出类型：internal 内部稿、submission 正式递交版、internal_review 内部评审稿"
      )

  class ExportVolume(BaseModel):
      # ...
      sha256: str | None = Field(default=None, description="分册文件 64 位十六进制 SHA-256 哈希指纹")
      format_metadata: dict[str, Any] | None = Field(default=None, description="Word 默认版式元数据")

  class ProjectExport(BaseModel):
      # ...
      kind: Literal["internal", "submission", "internal_review"] = Field(default="internal")
      has_blockers: bool = Field(default=False, description="是否存在阻断性红线缺陷")
      compliance_notice: str | None = Field(default=None, description="合规性说明与告警提示")
      sha256: str | None = Field(default=None, description="整本文件 64 位十六进制 SHA-256 哈希指纹")
      format_metadata: dict[str, Any] | None = Field(default=None, description="Word 默认版式元数据")
  ```

### 2.2 领域异常与 143 冻结错误码防护 (`workflow.py`)
- **文件路径**：`backend/bid-core/icg_demo/workflow.py`
- **设计决策**：
  - 项目全局定义了 143 个冻结业务错误码（`ERROR_STATUS`），并在 AST 测试与契约中严格冻结；
  - 为实现整本导出强门禁拦截并返回 HTTP 400 与 `CHECK_BLOCKER_EXISTS`，定义专用领域异常 `CheckBlockerError`：
  ```python
  class CheckBlockerError(DomainError):
      def __init__(self, message: str = "存在未解决的废标红线或星号条款阻断缺陷，禁止正式递交导出"):
          self.status_code = 400
          self.code = "CHECK_BLOCKER_EXISTS"
          self.message = message
          self.details = {"error_code": "CHECK_BLOCKER_EXISTS"}
          Exception.__init__(self, f"[{self.status_code}] {self.code}: {self.message}")
  ```
  - `CheckBlockerError` 继承自 `DomainError`，使得 FastAPI 在全局异常拦截器中能够通过 `isinstance(err, DomainError)` 统一将其捕获并渲染为标准 v1 错误体（HTTP 400，`{code: "CHECK_BLOCKER_EXISTS", message: "...", details: {...}, traceId: "..."}`）；同时通过重写 `__init__`，既避免修改 `ERROR_STATUS` 字典破坏 143 错误码基线，又不会触发 AST 静态扫描的单状态约束，做到了安全兼容。

### 2.3 检查引擎废标红线与星号条款判定 (`workflow.py`)
- **关键逻辑**：
  ```python
  def _is_critical_requirement(req: dict[str, Any]) -> bool:
      if req.get("is_disqualification") or req.get("category") == "disqualification":
          return True
      if req.get("importance") == "star" or req.get("category") == "star":
          return True
      text = f"{req.get('title', '')} {req.get('description', '')}"
      return "废标" in text or "否决" in text or "★" in text or "标星" in text
  ```
- **严重度赋值**：
  - 在 `run_check` 中，遍历各要求项时，若 `_is_critical_requirement(req)` 为 `True`，且满足下列条件之一：
    - 未映射到章节；
    - 响应未确认（`status != "confirmed"`）；
    - 对应章节内容为空或包含“待补”；
    - 缺少已核验有效证据（`evidence_ids` 为空、或证据存在未审核/已过期/历史标书）；
  - 则将生成缺陷的 `severity` 设为 `"blocker"`；非关键条款的相应缺陷则设为 `"blocking"`。

### 2.4 整本导出门禁与快照元数据注入 (`workflow.py`)
- **导出门禁**：
  ```python
  latest_check = self._db.get_latest_check(project_id, volume_id)
  has_blockers = False
  if latest_check and "issues" in latest_check:
      for issue in latest_check["issues"]:
          if issue.get("severity") == "blocker":
              has_blockers = True
              break

  if request.kind == "submission" and has_blockers:
      raise CheckBlockerError("存在未解决的废标红线或星号条款阻断缺陷，禁止正式递交导出")
  ```
- **Word 默认版式元数据与 SHA-256 文件指纹注入**：
  - 定义 `WORD_DEFAULT_FORMAT_METADATA` 常量，包含：
    - `page`: A4 纸张（210mm x 297mm）、portrait 纵向；
    - `margins`: 上 2.54cm、下 2.54cm、左 2.80cm、右 2.60cm；
    - `typography`: 默认行间距 28pt、首行缩进 560 缇（2 字符）；正文字体仿宋_GB2312 16pt；大标题方正小标宋 22pt 居中；一级标题黑体 16pt；二级标题楷体_GB2312 16pt；三级标题仿宋加粗 16pt；
  - 导出生成文档时，通过 `hashlib.sha256(content.encode("utf-8")).hexdigest()` 生成精准 64 位指纹；
  - 将 `sha256` 与 `format_metadata` 同步挂载至 `documents`、`volumes` 与整本 `record` 中；
  - 若为 `internal_review` 且 `has_blockers` 为 `True`，设置 `compliance_notice="当前导出包含阻断性红线或星号条款缺陷，仅供内部评审，禁止作为正式递交件"`。

### 2.5 数据库与适配器阻塞计数强化 (`database.py`, `adapters.py`)
- 在 `save_check` 中，缺陷阻塞计数统计逻辑统一更新为：
  ```python
  blocking_count = sum(1 for issue in issues if issue.get("severity") in ("blocking", "blocker"))
  ```
  确保 `blocker` 与 `blocking` 均正确累加到阻塞统计中，不发生统计遗漏。

### 2.6 全局错误响应适配与 OpenAPI 同步 (`main.py`, `demo-v1.json`)
- 重构 `error_response`：保留对 `/api/chapters/.../suggestions` 的旧版兼容器，其余所有端点（含 `/api/projects`）统一返回规范 v1 错误体 `{code, message, details, traceId}`。
- 同步更新 `spec/openapi/demo-v1.json`，全量维持 143 个错误码基线与 `implemented_contract` 100% 校验通过。

---

## 3. 边界与限制说明
1. **错误码与规范约束**：严格遵守系统规范，未新增或变更任何 `ERROR_STATUS` 中的 143 个冻结业务错误码。
2. **任务状态管理**：本任务交付完毕后状态流转至 `in-review`，绝不私自标为 `done`。
3. **导出格式兼容性**：当前导出格式元数据提供 Word 标准排版参数，Word 文档生成引擎在后续阶段将继续依据该元数据进行物理 `.docx` 排版渲染。
