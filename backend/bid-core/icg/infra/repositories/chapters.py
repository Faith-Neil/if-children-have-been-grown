# 为什么有这个文件：章节与章节历史版本的 MySQL 持久化与段落切分。
# 它解决什么问题：管理 demo_chapter 与 demo_chapter_version 表的读取、乐观锁写入与段落拆解。

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from icg.domain.domain import Chapter, DomainError, iso_time
from icg.infra.repositories.common import as_timestamp, utc_naive


def read_chapter(target: Any, chapter_id: str) -> dict | None:
    """读取单个章节及其全量历史版本。"""
    def _execute_read(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, project_id, volume, title, content, revision, assignee_id, updated_at "
                "FROM demo_chapter WHERE id = :id"
            ),
            {"id": chapter_id},
        ).one_or_none()
        if row is None:
            return None

        version_rows = connection.execute(
            text(
                "SELECT id, chapter_id, version_number, content, created_by, created_at "
                "FROM demo_chapter_version WHERE chapter_id = :chapter_id ORDER BY version_number ASC"
            ),
            {"chapter_id": chapter_id},
        ).all()

        versions = [
            {
                "id": v.id,
                "chapter_id": v.chapter_id,
                "revision": int(v.version_number),
                "version_number": int(v.version_number),
                "content": v.content,
                "actor_id": v.created_by,
                "created_by": v.created_by,
                "created_at": iso_time(as_timestamp(v.created_at)) if isinstance(v.created_at, datetime) else str(v.created_at),
            }
            for v in version_rows
        ]

        return {
            "id": row.id,
            "project_id": row.project_id,
            "volume": row.volume,
            "title": row.title,
            "content": row.content,
            "revision": int(row.revision),
            "assignee_id": row.assignee_id,
            "updated_at": row.updated_at,
            "versions": versions,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_read(connection)
    return _execute_read(engine)


def save_chapter(
    target: Any,
    chapter: Chapter | dict,
    expected_revision: int | None = None,
    updated_at: datetime | None = None,
) -> None:
    """保存章节内容与元数据，支持版本冲突检测（乐观并发控制）。"""
    if hasattr(chapter, "id"):
        cid = chapter.id
        pid = chapter.project_id
        volume = chapter.volume
        title = chapter.title
        content = chapter.content
        revision = int(chapter.revision)
        assignee_id = chapter.assignee_id
        versions = list(getattr(chapter, "versions", []))
    else:
        cid = chapter["id"]
        pid = chapter["project_id"]
        volume = chapter["volume"]
        title = chapter["title"]
        content = chapter.get("content", "")
        revision = int(chapter.get("revision", 1))
        assignee_id = chapter.get("assignee_id")
        versions = list(chapter.get("versions", []))

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    def _execute_save(connection) -> None:
        existing = connection.execute(
            text("SELECT revision FROM demo_chapter WHERE id = :id"),
            {"id": cid},
        ).one_or_none()

        payload = {
            "id": cid,
            "project_id": pid,
            "volume": volume,
            "title": title,
            "content": content,
            "revision": revision,
            "assignee_id": assignee_id,
            "updated_at": now,
        }

        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO demo_chapter (id, project_id, volume, title, content, revision, assignee_id, updated_at) "
                    "VALUES (:id, :project_id, :volume, :title, :content, :revision, :assignee_id, :updated_at)"
                ),
                payload,
            )
        else:
            if expected_revision is not None:
                result = connection.execute(
                    text(
                        "UPDATE demo_chapter SET project_id = :project_id, volume = :volume, "
                        "title = :title, content = :content, revision = :revision, "
                        "assignee_id = :assignee_id, updated_at = :updated_at "
                        "WHERE id = :id AND revision = :expected_revision"
                    ),
                    {**payload, "expected_revision": int(expected_revision)},
                )
                if result.rowcount != 1:
                    raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")
            else:
                connection.execute(
                    text(
                        "UPDATE demo_chapter SET project_id = :project_id, volume = :volume, "
                        "title = :title, content = :content, revision = :revision, "
                        "assignee_id = :assignee_id, updated_at = :updated_at "
                        "WHERE id = :id"
                    ),
                    payload,
                )

        for v in versions:
            v_num = int(v.get("revision", v.get("version_number", 1)))
            v_content = v.get("content", "")
            v_actor = v.get("actor_id", v.get("created_by", "system"))
            v_created = v.get("created_at")
            if v_created is None:
                v_time = now
            elif isinstance(v_created, datetime):
                v_time = v_created.astimezone(timezone.utc).replace(tzinfo=None) if v_created.tzinfo else v_created
            else:
                try:
                    v_time = datetime.fromisoformat(str(v_created)).astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    v_time = now

            exists = connection.execute(
                text("SELECT 1 FROM demo_chapter_version WHERE chapter_id = :chapter_id AND version_number = :v_num"),
                {"chapter_id": cid, "v_num": v_num},
            ).scalar()
            if not exists:
                v_id = v.get("id") or f"ver-{uuid4().hex}"
                connection.execute(
                    text(
                        "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
                        "VALUES (:id, :chapter_id, :version_number, :content, :created_by, :created_at)"
                    ),
                    {
                        "id": v_id,
                        "chapter_id": cid,
                        "version_number": v_num,
                        "content": v_content,
                        "created_by": v_actor,
                        "created_at": v_time,
                    },
                )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute_save(connection)
    else:
        _execute_save(engine)


def commit_chapter_version(
    target: Any,
    chapter_id: str,
    content: str,
    expected_revision: int,
    new_revision: int,
    created_by: str,
    updated_at: datetime | None = None,
) -> dict:
    """原子更新章节正文与提交新版本快照。"""
    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    def _execute_commit(connection) -> dict:
        result = connection.execute(
            text(
                "UPDATE demo_chapter SET content = :content, revision = :new_rev, updated_at = :updated_at "
                "WHERE id = :id AND revision = :old_rev"
            ),
            {
                "id": chapter_id,
                "content": content,
                "new_rev": int(new_revision),
                "old_rev": int(expected_revision),
                "updated_at": now,
            },
        )
        if result.rowcount != 1:
            raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")

        version_id = f"ver-{uuid4().hex}"
        connection.execute(
            text(
                "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
                "VALUES (:id, :chapter_id, :version_number, :content, :created_by, :created_at)"
            ),
            {
                "id": version_id,
                "chapter_id": chapter_id,
                "version_number": int(new_revision),
                "content": content,
                "created_by": created_by,
                "created_at": now,
            },
        )
        return {
            "id": version_id,
            "chapter_id": chapter_id,
            "revision": int(new_revision),
            "version_number": int(new_revision),
            "content": content,
            "actor_id": created_by,
            "created_by": created_by,
            "created_at": iso_time(as_timestamp(now)),
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_commit(connection)
    return _execute_commit(engine)


def decompose_paragraphs(
    content: str,
    chapter_id: str,
    citations: list[dict] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> list[dict]:
    """将章节正文切分为带编号段落，并精准关联引用与时间戳。"""
    if not content:
        return []
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = [p for p in normalized.split("\n") if p.strip()]
    cites = citations or []

    now_iso = datetime.now(timezone.utc).isoformat()
    c_at = created_at or now_iso
    u_at = updated_at or now_iso

    paragraphs = []
    for idx, p_text in enumerate(raw_blocks, start=1):
        p_cites = []
        for c in cites:
            cid = str(c.get("id", ""))
            cname = str(c.get("name", ""))
            ctag = f"[证:{cid}]"
            ctext = str(c.get("cite_text", ""))
            if (ctag in p_text or (cid and cid in p_text) or
                (cname and cname in p_text) or (ctext and ctext in p_text)):
                p_cites.append(c)
        if not p_cites and len(raw_blocks) == 1 and cites:
            p_cites = list(cites)
        paragraphs.append({
            "id": f"{chapter_id}-p{idx}",
            "order": idx,
            "text": p_text,
            "citations": p_cites,
            "created_at": c_at,
            "updated_at": u_at,
        })
    return paragraphs


def chapter_snapshot(state: Any) -> dict[str, tuple]:
    """提取状态中所有章节的快照元组，用于增量脏检查。"""
    return {
        cid: (
            ch.project_id,
            ch.volume,
            ch.title,
            ch.content,
            int(ch.revision),
            ch.assignee_id,
            tuple(
                (int(v.get("revision", v.get("version_number", 1))), v.get("content", ""))
                for v in getattr(ch, "versions", [])
            ),
        )
        for cid, ch in state.chapters.items()
    }


def save_chapters_diff(
    connection: Any,
    before_chapters: dict[str, tuple],
    after_chapters: dict[str, tuple],
    state_chapters: dict[str, Any],
    loaded_chapter_ids: set[str],
) -> None:
    """批量同步事务内变更的章节与版本至 demo_chapter 与 demo_chapter_version。"""
    all_cids = set(before_chapters) | set(after_chapters)
    for cid in all_cids:
        prev = before_chapters.get(cid)
        curr = after_chapters.get(cid)
        if prev == curr:
            continue
        if curr is None:
            if cid in loaded_chapter_ids:
                connection.execute(
                    text("DELETE FROM demo_chapter_version WHERE chapter_id = :id"),
                    {"id": cid},
                )
                connection.execute(
                    text("DELETE FROM demo_chapter WHERE id = :id"),
                    {"id": cid},
                )
        else:
            ch = state_chapters[cid]
            save_chapter(connection, ch)

