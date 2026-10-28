# 为什么有这个文件：验证内部响应追溯表 Excel（APP-M2-T201，PRD v1.8 §5.9.1 规则 12）。
# 它解决什么问题：每条条款的文件页码、响应、分册章节段落、证据版本、负责人与确认人全列；
# 标明内部用；项目负责人导出全部，只读与编写人不能导出，跨公司看不到。

from icg.infra.xlsx import read_xlsx_rows
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def test_trace_lists_every_requirement_with_full_columns(client):
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    flow.write("/requirements/" + reqs[0]["id"], {"status": "confirmed"}, "PATCH")
    resp = client.get(f"{flow.path}/response-trace.xlsx", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rows = read_xlsx_rows(resp.content)
    assert "内部用" in rows[0][0]
    assert rows[3] == ["序号", "招标条款", "所属文件", "页码", "条款类别", "响应方式与要点", "所在分册", "对应章节", "段落",
                       "证据（版本）", "知识片段来源", "负责人", "确认人", "条款状态"]
    body = rows[4:]
    assert len(body) == len(reqs)
    by_text = {r[1]: r for r in body}
    first = by_text[reqs[0]["text"]]
    assert first[2] == "合成招标.txt" and first[3] and first[5] == "经核对满足要求。"
    assert first[12] == "甲公司项目经理（合成）" and first[13] == "已确认"
    business = next(r for r in body if r[6] == "商务分册")
    assert "合成企业资质（v1）" in business[9]
    assert all(r[7] != "未对应章节" for r in body)


def test_trace_scope_and_permissions(client):
    flow = ProjectFlow(client).ready()
    technical = read_xlsx_rows(client.get(f"{flow.path}/response-trace.xlsx?volume=technical", headers=flow.headers).content)
    assert all(r[6] == "技术分册" for r in technical[4:]) and "技术分册" in technical[1][0]
    for account in ("alpha-viewer", "alpha-editor"):
        assert client.get(f"{flow.path}/response-trace.xlsx", headers=login(client, account)).status_code == 403
    assert client.get(f"{flow.path}/response-trace.xlsx", headers=login(client, "beta-manager")).status_code == 404
    assert client.get(f"{flow.path}/response-trace.xlsx?volume=x", headers=flow.headers).status_code == 422
