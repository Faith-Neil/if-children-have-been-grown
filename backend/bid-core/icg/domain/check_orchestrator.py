# 为什么有这个文件：由 workflow_orchestrator / export_service 解耦抽取的合规检查与门禁子编排服务（BE-TECH-DEBT-03）。
# 它解决什么问题：
# 1. 完整合规规则引擎调用（ComplianceRulesEngine.evaluate_all）与阻断缺陷汇总（CheckBlockerError / aggregate_blockers）；
# 2. 废标（★/废标条款）与星号条款阻断门禁判定；
# 3. 增量复检队列管理（schedule_incremental_recheck）与指纹状态跟踪；
# 4. 保持与 WorkflowService 100% 行为与签名兼容。

from __future__ import annotations

import hashlib

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from icg.domain.domain import DomainError, Principal, iso_time, new_id
from icg.domain.generation_context import evidence_expired, plan_is_current, resolve_fact_variables
from icg.domain.sla import sla_issues
from icg.domain.compliance_rules import ComplianceRulesEngine, ComplianceRulesMixin

SHANGHAI = timezone(timedelta(hours=8))


class CheckBlockerError(DomainError):
    """合规检查存在废标或星号阻断缺陷异常。"""

    def __init__(self, message: str, details: dict | None = None):
        self.status = 400
        self.code = "CHECK_BLOCKER_EXISTS"
        self.message = message
        self.details = details or {}
        Exception.__init__(self, message)


RELEASABLE = ("warning", "info", "hint")


def release_key(issue: dict) -> str:
    details = issue.get("details") or {}
    basis = "|".join(str(x) for x in (issue.get("rule_id") or "", issue.get("code"), issue.get("chapter_id") or "",
                                      issue.get("requirement_id") or "", details.get("paragraph_index", ""),
                                      details.get("quote") or issue.get("message", "")))
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def check_passed(issues: list[dict]) -> bool:
    """提示不挡导出；警告须逐项放行；阻断不能放行。"""
    return not [i for i in issues if i.get("severity") not in ("info", "hint")
                and not (i.get("severity") in RELEASABLE and i.get("released"))]


class CheckOrchestratorMixin(ComplianceRulesMixin):
    """合规检查与缺陷门禁领域编排 Mixin。"""

    @staticmethod
    def _date(value: str) -> date:
        try:
            return date.fromisoformat(value) if len(value) == 10 else CheckOrchestratorMixin._instant(value).astimezone(SHANGHAI).date()
        except (ValueError, TypeError) as error:
            raise DomainError(422, "INVALID_DATE", "日期请使用 YYYY-MM-DD 或包含日期的 ISO 时间格式。") from error

    @staticmethod
    def _instant(value: str) -> datetime:
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (moment.replace(tzinfo=SHANGHAI) if moment.tzinfo is None else moment).astimezone(timezone.utc)
        except (ValueError, TypeError) as error:
            raise DomainError(422, "INVALID_DATE", "截止时间请使用 ISO 时间格式；未带时区时按北京时间理解。") from error

    @staticmethod
    def _is_critical_requirement(row: dict) -> bool:
        text = str(row.get("text", "") or "")
        is_disqual = bool(
            row.get("is_disqualification") is True
            or row.get("category") == "disqualification"
            or "废标" in text
            or "否决" in text
        )
        is_star = bool(
            row.get("importance") == "star"
            or row.get("category") == "star"
            or "★" in text
            or "标星" in text
        )
        return is_disqual or is_star

    @staticmethod
    def _issue(code: str, message: str, severity: str = "blocking", **links) -> dict[str, Any]:
        return {"id": new_id("issue"), "code": code, "severity": severity, "message": message, **links}

    @staticmethod
    def aggregate_blockers(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """从缺陷清单中过滤并汇聚所有废标/阻断级缺陷。"""
        return [i for i in issues if i.get("severity") in ("blocker", "critical") or i.get("is_blocker") is True]

    def schedule_incremental_recheck(
        self, state: Any, project_id: str, changed_chapters: list[str] | None = None
    ) -> dict[str, Any]:
        """增量复检队列管理：针对变更章节与受影响规则标记需增量复核队列。"""
        workflow = self._workflow(state, project_id)
        queue = workflow.setdefault("recheck_queue", {
            "pending_chapters": set(),
            "scheduled_at": None,
            "recheck_count": 0,
        })
        if changed_chapters:
            queue["pending_chapters"].update(changed_chapters)
        queue["scheduled_at"] = iso_time(self.demo._now())
        queue["recheck_count"] += 1
        return {
            "project_id": project_id,
            "pending_chapters": list(queue["pending_chapters"]),
            "scheduled_at": queue["scheduled_at"],
            "recheck_count": queue["recheck_count"],
        }

    def run_check(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        """执行完整合规检查与全规则引擎评估。"""
        def operation(state, project, workflow):
            volume = payload.get("volume", "all")
            from icg.domain.project_access import project_volumes, rule_scope
            scope = rule_scope(state, project_id, volume)  # 只写技术标：全文=技术分册
            issues = []
            add = lambda code, message, severity="blocking", **links: issues.append(self._issue(code, message, severity=severity, **links))
            if not workflow["parse_confirmed"]:
                add("PARSE_NOT_CONFIRMED", "解析结果尚未确认。")
            checked_chapters = [
                c for c in state.chapters.values()
                if c.project_id == project_id and (scope == "all" or c.volume == scope)
            ]
            if not checked_chapters or not all(plan_is_current(state, project_id, c.id) for c in checked_chapters):
                add("PLAN_NOT_CONFIRMED", "写作大纲尚未确认。")
            if not project.tender_number.strip() or not project.deadline:
                add("PROJECT_DETAILS_MISSING", "项目招标编号或投标截止时间未填写。")
            if any(c["status"] != "resolved" for c in workflow["conflicts"].values()):
                add("FACT_CONFLICT", "项目事实仍有未处理冲突。")
            if any(f["status"] == "pending" for f in workflow["facts"].values()):
                add("FACT_PENDING", "项目事实仍待确认。")
            for fact in workflow["facts"].values():
                if fact["status"] != "confirmed":
                    continue
                if fact["key"] == "招标编号" and project.tender_number.strip() != fact["value"].strip():
                    add("PROJECT_FACT_MISMATCH", "已确认招标编号与项目基本信息不一致。")
                if fact["key"] == "投标截止时间" and project.deadline:
                    try:
                        fact_value = fact["value"].strip()
                        matching_date = (
                            self._date(fact_value) == self._date(project.deadline)
                            if len(fact_value) == 10
                            else self._instant(fact_value) == self._instant(project.deadline)
                        )
                    except DomainError:
                        matching_date = False
                    if not matching_date:
                        add("PROJECT_FACT_MISMATCH", "已确认投标截止时间与项目基本信息不一致。")
            if not workflow["requirements"]:
                add("REQUIREMENTS_EMPTY", "没有可核对的招标条款。")
            for row in workflow["requirements"].values():
                if scope != "all" and row["volume"] != scope:
                    continue
                links = {"requirement_id": row["id"]}
                is_crit = self._is_critical_requirement(row)
                crit_sev = "blocker" if is_crit else "blocking"

                if row["status"] == "pending":
                    add("REQUIREMENT_PENDING", "条款尚待确认：" + row["text"][:60], severity=crit_sev, **links)
                if row["status"] == "rejected":
                    if not row["reason"].strip():
                        add("REJECTION_REASON_MISSING", "忽略条款没有理由。", **links)
                    continue
                if row["reference_status"] == "unresolved":
                    add("REFERENCE_UNRESOLVED", "条款引用尚未人工核对。", **links)
                chapter = state.chapters.get(row["chapter_id"] or "")
                if chapter is None or chapter.project_id != project_id or chapter.volume != row["volume"]:
                    add("MATRIX_MAPPING_MISSING", "条款没有映射到本分册有效章节。", severity=crit_sev, **links)
                if not row["response"].strip() or "待补" in row["response"]:
                    add("MATRIX_RESPONSE_MISSING", "条款响应为空或仍有待补。", severity=crit_sev, **links)
                elif chapter is not None:
                    if not chapter.content.strip():
                        add("CHAPTER_CONTENT_EMPTY", "条款映射章节正文为空：" + chapter.title, severity=crit_sev, chapter_id=chapter.id, **links)
                    elif "待补" in chapter.content:
                        add("CHAPTER_CONTENT_PENDING", "条款映射章节正文仍有待补：" + chapter.title, severity=crit_sev, chapter_id=chapter.id, **links)

                need_evidence = any(word in row["text"] for word in ("资质", "证书", "证明", "业绩", "授权")) or row.get("need_evidence") is True
                if need_evidence and not row["evidence_ids"]:
                    add("EVIDENCE_MISSING", "证明类条款缺少已确认的企业证据。", severity=crit_sev, **links)
                for evidence_id in row["evidence_ids"]:
                    evidence = state.library.get(evidence_id)
                    if (
                        evidence is None
                        or evidence["company_id"] != project.company_id
                        or evidence["status"] != "confirmed"
                        or evidence["type"] == "history"
                    ):
                        add("EVIDENCE_NOT_USABLE", "条款引用的证据已失效或不能作为证据。", severity=crit_sev, evidence_id=evidence_id, **links)
                        continue
                    today = datetime.fromtimestamp(self.demo._now(), SHANGHAI).date()
                    if evidence_expired(evidence, project.deadline, today=today):
                        add("EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。", severity=crit_sev, evidence_id=evidence_id, **links)
            chapters = [
                c for c in state.chapters.values()
                if c.project_id == project_id and (scope == "all" or c.volume == scope)
            ]
            required_volumes = set(project_volumes(state, project_id)) if scope == "all" else {scope}
            if {c.volume for c in chapters} != required_volumes:
                add("VOLUME_MISSING", "所检查分册缺少章节。")
            for chapter in chapters:
                if not chapter.content.strip():
                    add("EMPTY_CONTENT", "已提交正文为空：" + chapter.title, chapter_id=chapter.id)
                if "待补" in chapter.content:
                    add("PENDING_CONTENT", "已提交正文仍有待补：" + chapter.title, chapter_id=chapter.id)
                try:
                    resolve_fact_variables(state, project_id, chapter.content)
                except DomainError as error:
                    add(error.code, error.message, chapter_id=chapter.id)
            issues.extend(sla_issues(state, project_id, chapters))
            from icg.domain.system_chapters import stale_system_chapters
            for item in stale_system_chapters(state, project, workflow):
                if scope == "all" or state.chapters[item["chapter_id"]].volume == scope:
                    add("SYSTEM_CHAPTER_STALE", f"系统生成章节《{item['title']}》的数据源已变化，请重新生成。", chapter_id=item["chapter_id"])
            from icg.domain.project_access import in_scope_workflow
            rule_results = ComplianceRulesEngine.evaluate_all(
                state, project, in_scope_workflow(workflow), volume=scope, now_ts=self.demo._now()
            )
            def same(a, b):
                # 段落级规则（R29/R30）同章多段各算一条，按段落下标区分
                return (a.get("code") == b.get("code") and a.get("requirement_id") == b.get("requirement_id")
                        and a.get("chapter_id") == b.get("chapter_id")
                        and (a.get("details") or {}).get("paragraph_index") == (b.get("details") or {}).get("paragraph_index"))

            for r in rule_results:
                for rule_issue in r.issues:
                    duplicate = next((existing for existing in issues if same(existing, rule_issue)), None)
                    if duplicate is None:
                        issues.append(rule_issue)
                    else:
                        duplicate["rule_id"] = r.rule_id
            releases = workflow.get("check_releases", {})
            for issue in issues:
                if issue.get("severity") in RELEASABLE:
                    issue["release_key"] = release_key(issue)
                    if issue["release_key"] in releases:
                        issue["released"] = releases[issue["release_key"]]
            passed = check_passed(issues)
            check_record = {
                "id": new_id("project-check"),
                "volume": volume,
                "passed": passed,
                "status": "passed" if passed else "failed",
                "issues": issues,
                "rules": [r.to_dict() for r in rule_results],
                "coverage": {
                    "implemented_rules": self.IMPLEMENTED_RULES,
                    "unimplemented_rules": self.UNIMPLEMENTED_RULES,
                    "complete": False,
                },
                "fingerprint": self._fingerprint(state, project_id),
                "created_at": iso_time(self.demo._now()),
            }
            workflow["checks"][check_record["id"]] = check_record
            self._job(state, project_id, "check", "已实现的流程检查完成；不代表全部一期合规规则通过。")
            return {"check": check_record}

        return self._write(principal, project_id, "project.check", payload, expected, key, operation)

    def release_check_issue(self, principal: Principal, project_id: str, check_id: str, issue_id: str, payload: dict,
                            expected: str | None, key: str | None):
        """警告逐项放行（PRD §5.8：仅项目负责人或公司管理员，理由必填；阻断不能放行）。

        放行按问题内容（规则、章节、段落与原句）记账：正文改了就是新问题，旧放行自然失效。
        """
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise DomainError(422, "CONFIRMATION_REQUIRED", "放行必须填写理由。")

        def operation(state, project, workflow):
            check = workflow.get("checks", {}).get(check_id)
            if check is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目检查批次。")
            issue = next((i for i in check.get("issues", []) if i.get("id") == issue_id), None)
            if issue is None:
                raise DomainError(404, "NOT_FOUND", "检查批次中没有这个问题。")
            if issue.get("severity") not in RELEASABLE:
                raise DomainError(409, "BLOCKER_NOT_REJECTABLE", "阻断级问题不能放行，须在正文或矩阵中修正。")
            record = {"reason": reason[:500], "by": principal.user.id, "by_name": principal.user.name,
                      "at": iso_time(self.demo._now()), "decision": payload.get("decision") or "keep"}
            key_value = issue.get("release_key") or release_key(issue)
            workflow.setdefault("check_releases", {})[key_value] = record
            issue["release_key"], issue["released"] = key_value, record
            check["passed"] = check_passed(check["issues"])
            check["status"] = "passed" if check["passed"] else "failed"
            self._audit(state, principal, project_id, "check.release",
                        {"check_id": check_id, "issue_id": issue_id, "code": issue.get("code"), "reason": reason[:200]})
            return {"check": check}

        return self._write(principal, project_id, f"check.release:{check_id}", {**payload, "issue_id": issue_id},
                           expected, key, operation)

    def check(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        """run_check 的直接方法别名，保持与 WorkflowService 统一调用风格。"""
        return self.run_check(principal, project_id, payload, expected, key)

    def checks(self, principal: Principal, project_id: str):
        workspace = self.workspace(principal, project_id)
        return {"revision": workspace["revision"], "checks": workspace["checks"]}


class CheckOrchestrator(CheckOrchestratorMixin):
    """合规检查与门禁独立领域编排服务。"""

    def __init__(self, workflow: Any = None):
        self._workflow_service = workflow

    def __getattr__(self, name: str) -> Any:
        if hasattr(self, "_workflow_service") and self._workflow_service is not None and hasattr(self._workflow_service, name):
            return getattr(self._workflow_service, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
