# 为什么有这个文件：解析决策/后处理/文件版本链三组测试共用的合成数据与小工具。
# 它解决什么问题：避免三个测试文件各写一遍上传、解析、按条件取条目的样板代码。

import base64

from test_reference_flow import TENDER, ProjectFlow


def upload_role(flow: ProjectFlow, content: str, filename: str, role: str = "tender") -> dict:
    payload = {"filename": filename, "content_base64": base64.b64encode(content.encode()).decode(), "file_role": role}
    return flow.write("/files", payload)["file"]


def parsed_flow(client, content: str = TENDER, filename: str = "t.txt") -> ProjectFlow:
    flow = ProjectFlow(client)
    upload_role(flow, content, filename)
    flow.write("/parse", {})
    return flow


def fact_values(flow: ProjectFlow, key: str) -> list[tuple[str, str]]:
    return [(f["value"], f["status"]) for f in flow.state()["facts"] if f["key"] == key]


def settle_pending(flow: ProjectFlow) -> None:
    """把剩下的待确认条款和事实逐条确认（星号/废标/资格也逐条）。"""
    for row in flow.state()["requirements"]:
        if row["status"] == "pending" and not row.get("merged_into"):
            flow.write("/requirements/" + row["id"], {"status": "confirmed", "reason": "合成测试已人工核对"}, "PATCH")
    for fact in flow.state()["facts"]:
        if fact["status"] == "pending" and not fact.get("merged_into"):
            flow.write("/facts/" + fact["id"], {"status": "confirmed"}, "PATCH")
