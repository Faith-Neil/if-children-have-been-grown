# 为什么有这个文件：验证章节正文的段落键与逐段来源（APP-M2-T161）。
# 它解决什么问题：改一段、插一段、删一段后其他段落的键不变；改几个字仍是原段落；
# 对话助手写入、粘贴识别、章节循环、系统生成各自标对来源；同一段历史重算得到相同的键；接口返回段落表，MySQL 重新加载后不丢。

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.domain.paragraph_keys import assign, current, ensure, split
from icg_demo.main import create_app

BODY = "# 运维服务方案\n\n本项目提供七乘二十四小时驻场运维。\n\n| 等级 | 响应 |\n|---|---|\n| 一级 | 15 分钟 |\n\n- 巡检每月一次\n- 备份每日一次"


def _chain(*versions):
    chapter = SimpleNamespace(id="ch1", versions=[], content="", revision=0)
    for number, (content, extra) in enumerate(versions, start=1):
        chapter.versions.append({"revision": number, "content": content, **extra})
        chapter.content, chapter.revision = content, number
    return chapter


def test_blocks_follow_export_split_and_skip_blank_lines():
    blocks = split(BODY)
    assert [b["kind"] for b in blocks] == ["heading", "para", "table", "bullet", "bullet"]
    table = blocks[2]
    assert (table["line_start"], table["line_end"]) == (4, 6)
    keys = [p["key"] for p in assign("ch1", None, "", BODY, {"revision": 1})]
    assert len(set(keys)) == 5 and all(k.startswith("pk-ch1-r1-") for k in keys)


def test_edit_insert_and_delete_keep_other_keys():
    edited = BODY.replace("七乘二十四小时驻场运维", "七乘二十四小时驻场运维与远程支持")
    inserted = "前言：以下为服务承诺。\n" + edited
    deleted = inserted.replace("- 备份每日一次", "")
    chapter = _chain((BODY, {}), (edited, {}), (inserted, {}), (deleted, {}))
    ensure(chapter)
    v1, v2, v3, v4 = (v["paragraphs"] for v in chapter.versions)
    assert [p["key"] for p in v2] == [p["key"] for p in v1]          # 改几个字，键不变
    assert [p["key"] for p in v3][1:] == [p["key"] for p in v2]      # 顶部插一段，其余不变
    assert v3[0]["key"].startswith("pk-ch1-r3-")
    assert [p["key"] for p in v4] == [p["key"] for p in v3][:-1]     # 删最后一段，其余不变
    rewritten = deleted.replace("本项目提供七乘二十四小时驻场运维与远程支持。", "完全不同的一段新文字，讲培训安排。")
    chapter.versions.append({"revision": 5, "content": rewritten})
    v5 = ensure(chapter)
    assert v5[2]["key"] != v4[2]["key"]                               # 整段换掉算新段落


def test_sources_follow_the_way_each_version_was_written():
    second = BODY.replace("七乘二十四小时驻场运维。", "七乘二十四小时驻场运维，重大节假日加派值守。")
    third = second + "\n应急预案每季度演练一次。"
    lines = third.split("\n")
    fourth = third.replace("- 巡检每月一次", "- 巡检每两周一次")
    chapter = _chain(
        (BODY, {}),
        (second, {"version_origin": "assistant_edit"}),
        (third, {"paragraph_sources": [{"paragraph_index": len(lines) - 1, "source": "assistant_pasted"}]}),
        (fourth, {"source": "chapter_loop"}),
    )
    latest = ensure(chapter)
    by_kind = {p["kind"] + str(i): p["source"] for i, p in enumerate(latest)}
    assert latest[0]["source"] == "manual"
    assert latest[1]["source"] == "assistant"
    assert latest[3]["source"] == "chapter_loop"
    assert latest[4]["source"] == "manual"
    assert latest[5]["source"] == "assistant_pasted", by_kind
    system = _chain(("| 序号 | 条款 |\n|---|---|\n| 1 | 资格 |", {"source": "system_generated"}))
    assert ensure(system)[0]["source"] == "system"


def test_recomputing_the_same_history_gives_the_same_keys():
    edited = "前言。\n" + BODY.replace("一级 | 15", "一级 | 10")
    first = _chain((BODY, {}), (edited, {"version_origin": "assistant_edit"}))
    again = _chain((BODY, {}), (edited, {"version_origin": "assistant_edit"}))
    assert ensure(first) == ensure(again)
    assert current(first) == ensure(first)


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def _login(client, account="alpha-editor"):
    response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def _commit(client, headers, lease, content, key):
    base = client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()["revision"]
    response = client.post(f"/api/chapters/{CHAPTER}/versions", headers=headers,
                           json={"lease_token": lease, "base_revision": base, "content": content, "idempotency_key": key})
    assert response.status_code == 200, response.text


CHAPTER = "alpha-tech"


def test_chapter_and_versions_return_stable_paragraph_keys(client):
    headers = _login(client)
    lease = client.post(f"/api/chapters/{CHAPTER}/lock", headers=headers, json={"takeover_reason": None}).json()["lease_token"]
    _commit(client, headers, lease, BODY, "paragraph-commit-1")
    first = client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()["paragraphs"]
    assert [p["kind"] for p in first] == ["heading", "para", "table", "bullet", "bullet"]
    assert {p["source_label"] for p in first} == {"人工编写"}
    _commit(client, headers, lease, BODY.replace("每月一次", "每两周一次"), "paragraph-commit-2")
    second = client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()["paragraphs"]
    assert [p["key"] for p in second] == [p["key"] for p in first]
    assert second[3]["hash"] != first[3]["hash"]
    versions = client.get(f"/api/chapters/{CHAPTER}/versions", headers=headers).json()["versions"]
    assert [p["key"] for p in versions[-1]["paragraphs"]] == [p["key"] for p in second]
    assert [p["key"] for p in versions[-2]["paragraphs"]] == [p["key"] for p in first]
    other = _login(client, "alpha-manager")
    assert client.get(f"/api/chapters/{CHAPTER}", headers=other).json()["paragraphs"] == second


@pytest.mark.mysql
def test_version_meta_and_paragraphs_survive_mysql_reload():
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from icg_demo.database import mysql_gate, read_chapter, save_chapter
    from icg_demo.domain import Chapter
    gate = mysql_gate()
    if gate.action == "skip":
        pytest.skip(gate.reason)
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "backend" / "bid-core" / "alembic"))
    command.upgrade(cfg, "head")
    repository = create_app().state.service.repository
    chapter_id = f"ch-{uuid4().hex}"
    edited = BODY.replace("每日一次", "每日两次")
    chapter = Chapter(id=chapter_id, project_id=f"proj-{uuid4().hex}", title="技术方案", volume="technical",
                      content=edited, revision=2, versions=[
                          {"revision": 1, "content": BODY, "actor_id": "alpha-editor", "created_at": "2026-10-30T01:00:00+00:00"},
                          {"revision": 2, "content": edited, "actor_id": "alpha-editor", "created_at": "2026-10-30T02:00:00+00:00",
                           "version_origin": "assistant_edit", "edit_mode": "assistant_replace"}])
    save_chapter(repository.engine, chapter)
    loaded = read_chapter(repository.engine, chapter_id)
    assert loaded["versions"][1]["version_origin"] == "assistant_edit"
    assert loaded["versions"][1]["paragraphs"] == chapter.versions[1]["paragraphs"]
    assert loaded["versions"][1]["paragraphs"][-1]["source"] == "assistant"
