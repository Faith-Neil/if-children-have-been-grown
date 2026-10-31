# 为什么有这个文件：验证导出命名（PRD v1.8 §5.1.4 第 9 项、§5.9.1 第 11 条与验收⑤；APP-M2-T086）。
# 它解决什么问题：内部稿默认“{编写人}_{版本}_{日期}_{项目名称}”，版本随本分册内部稿导出次数递增；递交版默认“{项目名称}_{分册名称}”，
# 规则含 {编写人} 或不认识的变量时不能保存；只有项目负责人能改；下载响应头带中文文件名。

import re
from urllib.parse import unquote
from uuid import uuid4

from test_merge_checklist import _submission
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _put(flow, body, expected=200, headers=None):
    resp = flow.client.put(f"{flow.path}/export-settings", json=body,
                           headers=headers or {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert resp.status_code == expected, resp.text
    return resp.json()


def _internal(flow):
    check = flow.write("/checks", {"volume": "all"})["check"]
    return flow.write("/exports", {"check_id": check["id"], "kind": "internal", "volume": "all"})["export"]


def test_internal_names_use_writer_version_date_and_project(client):
    flow = ProjectFlow(client).ready()
    first = {v["volume"]: v["filename"] for v in _internal(flow)["volumes"]}
    second = {v["volume"]: v["filename"] for v in _internal(flow)["volumes"]}
    pattern = r"^(.+)_V(\d)\.0_(\d{8})_合成双册验收项目(_技术分册|_商务分册)?\.docx$"
    assert all(re.match(pattern, name) for name in first.values()), first
    assert {re.match(pattern, n).group(2) for n in first.values()} == {"1"}
    assert {re.match(pattern, n).group(2) for n in second.values()} == {"2"}
    assert len(set(first.values())) == 2  # 两册同一负责人时自动补分册名称避免重名
    export = flow.state()["exports"][-1]
    response = client.get(export["volumes"][0]["download_url"], headers=flow.headers)
    disposition = response.headers["content-disposition"]
    assert unquote(disposition.split("filename*=UTF-8''", 1)[1]) == export["volumes"][0]["filename"]
    assert export["naming_rule"] == "{编写人}_{版本}_{日期}_{项目名称}"


def test_submission_rule_cannot_contain_the_writer_and_only_leads_change_it(client):
    flow = ProjectFlow(client).ready()
    current = client.get(f"{flow.path}/export-settings", headers=flow.headers).json()
    assert current["submit_rule"] == "{项目名称}_{分册名称}" and {v["name"] for v in current["variables"]} >= {"编写人", "版本"}
    refused = _put(flow, {"submit_rule": "{编写人}_{项目名称}"}, expected=422)
    assert "不能含 {编写人}" in refused["message"]
    unknown = _put(flow, {"internal_template": "{作者}_{项目名称}"}, expected=422)
    assert "不认识的变量" in unknown["message"]
    editor = login(client, "alpha-editor")
    _put(flow, {"submit_rule": "{招标编号}_{分册名称}"}, expected=403,
         headers={**editor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    saved = _put(flow, {"submit_rule": "{招标编号}_{分册名称}", "internal_template": "{项目名称}_{分册名称}_{版本}"})
    assert saved["submit_rule"] == "{招标编号}_{分册名称}" and saved["updated_by"]


def test_submission_files_never_carry_the_writer_name(client):
    flow, _, export = _submission(client)
    owner_names = {a["name"] for a in client.get(f"{flow.path}", headers=flow.headers).json().get("team", {}).get("available_accounts", [])}
    for volume in export["volumes"]:
        assert volume["filename"] in ("合成双册验收项目_技术分册.docx", "合成双册验收项目_商务分册.docx")
        assert not any(name and name in volume["filename"] for name in owner_names)
