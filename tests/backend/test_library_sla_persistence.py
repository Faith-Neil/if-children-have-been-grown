# 为什么有这个文件：用真实 MySQL 8 核对公司资料库（demo_library_item）、修订履历（demo_library_revision）与服务承诺模板（demo_sla_template）的聚合持久化、JSON 结构存储、多维检索与乐观并发锁。
# 它解决什么问题：确保知识库资料与 SLA 模板原子写入 MySQL，stale revision 无法并发脏写覆盖，修改历史不可变存证，并验证 Alembic 0008 迁移升降级往返与内存仓库多态。

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from icg_demo.adapters import MemoryRepository
from icg_demo.database import (
    commit_library_revision,
    database_url,
    delete_library_item,
    delete_sla_template,
    list_library_items,
    list_library_revisions,
    list_sla_templates,
    mysql_gate,
    read_library_item,
    read_sla_template,
    save_library_item,
    save_sla_template,
)
from icg_demo.domain import DomainError
from icg_demo.main import create_app

pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "backend" / "bid-core" / "alembic"))
    return cfg


def _upgrade() -> None:
    command.upgrade(_alembic_config(), "head")


def _downgrade(revision: str = "base") -> None:
    command.downgrade(_alembic_config(), revision)


@pytest.fixture
def ensure_mysql():
    gate = mysql_gate()
    if gate.action == "skip":
        pytest.skip(gate.reason)
    if gate.action == "fail":
        pytest.fail(gate.reason)


def test_migration_0008_reversibility(ensure_mysql):
    _upgrade()
    cfg = _alembic_config()

    # 降级到 0007_checks_and_exports：三张新表应当被干净移除
    command.downgrade(cfg, "0007_checks_and_exports")
    repository = create_app().state.service.repository
    try:
        with repository.engine.connect() as connection:
            tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
            assert "demo_library_item" not in tables
            assert "demo_library_revision" not in tables
            assert "demo_sla_template" not in tables
            assert "demo_check" in tables
            assert "demo_export" in tables
            assert "demo_chapter" in tables
    finally:
        # 恢复到 head
        _upgrade()

    with repository.engine.connect() as connection:
        tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
        assert "demo_library_item" in tables
        assert "demo_library_revision" in tables
        assert "demo_sla_template" in tables

        # 验证字符集与排序规则为 utf8mb4 / utf8mb4_0900_ai_ci
        table_status = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('demo_library_item', 'demo_library_revision', 'demo_sla_template')"
            )
        ).all()
        for row in table_status:
            assert "utf8mb4" in row.TABLE_COLLATION


def test_save_and_read_library_item_with_optimistic_locking(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    item_id = f"lib-{uuid4().hex}"
    company_id = "alpha-corp"
    payload = {
        "title": "CMMI 5级认证证书",
        "cert_no": "CMMI-2026-9999",
        "valid_to": "2028-12-31",
        "issuer": "SEI / ISACA",
        "keywords": ["软件成熟度", "质量保障体系"],
    }

    item_data = {
        "id": item_id,
        "company_id": company_id,
        "category": "qualification",
        "name": "企业CMMI5级证书",
        "status": "confirmed",
        "is_starred": True,
        "can_insert": True,
        "is_sensitive": False,
        "payload_json": payload,
        "revision": 1,
    }

    save_library_item(repository.engine, item_data)

    loaded = read_library_item(repository.engine, item_id)
    assert loaded is not None
    assert loaded["id"] == item_id
    assert loaded["company_id"] == company_id
    assert loaded["category"] == "qualification"
    assert loaded["name"] == "企业CMMI5级证书"
    assert loaded["status"] == "confirmed"
    assert loaded["is_starred"] is True
    assert loaded["can_insert"] is True
    assert loaded["is_sensitive"] is False
    assert loaded["revision"] == 1
    assert loaded["payload_json"]["cert_no"] == "CMMI-2026-9999"

    # 乐观并发锁测试：带正确期望版本成功更新
    update_data = dict(loaded)
    update_data["name"] = "企业CMMI5级证书（已年审）"
    update_data["revision"] = 2
    save_library_item(repository.engine, update_data, expected_revision=1)

    updated = read_library_item(repository.engine, item_id)
    assert updated["revision"] == 2
    assert updated["name"] == "企业CMMI5级证书（已年审）"

    # 乐观并发锁冲突拦截：提供旧版本 expected_revision=1，抛出 409 REVISION_CONFLICT
    conflict_data = dict(updated)
    conflict_data["name"] = "并发脏写更新"
    with pytest.raises(DomainError) as exc_info:
        save_library_item(repository.engine, conflict_data, expected_revision=1)
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"


def test_commit_library_revision_in_transaction(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    item_id = f"lib-rev-item-{uuid4().hex}"
    company_id = "beta-corp"

    # 1. 初始化资料条目
    save_library_item(repository.engine, {
        "id": item_id,
        "company_id": company_id,
        "category": "person",
        "name": "首席架构师履历",
        "status": "confirmed",
        "payload_json": {"experience_years": 15, "skills": ["Python", "FastAPI", "MySQL"]},
        "revision": 1,
    })

    # 2. 提交新修订版本（同一事务原子写 item 与 revision 表）
    new_payload = {"experience_years": 16, "skills": ["Python", "FastAPI", "MySQL", "K8s"]}
    rev_record = commit_library_revision(
        repository.engine,
        item_id=item_id,
        payload=new_payload,
        expected_revision=1,
        new_revision=2,
        changed_by="hr-admin",
        change_reason="增加云原生认证与经验年限更新",
    )
    assert rev_record["version_number"] == 2
    assert rev_record["changed_by"] == "hr-admin"

    # 验证主表版本已推进
    item_after = read_library_item(repository.engine, item_id)
    assert item_after["revision"] == 2
    assert item_after["payload_json"]["experience_years"] == 16

    # 验证历史履历表
    history = list_library_revisions(repository.engine, item_id)
    assert len(history) == 1
    assert history[0]["version_number"] == 2
    assert history[0]["change_reason"] == "增加云原生认证与经验年限更新"

    # 3. 冲突拦截验证
    with pytest.raises(DomainError) as exc_info:
        commit_library_revision(
            repository.engine,
            item_id=item_id,
            payload={"skills": ["Conflict"]},
            expected_revision=1,
            new_revision=3,
            changed_by="other-user",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"


def test_list_and_delete_library_items(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    cid = f"comp-list-{uuid4().hex}"
    it1 = {"id": f"lib1-{uuid4().hex}", "company_id": cid, "category": "qualification", "name": "资质A", "status": "confirmed"}
    it2 = {"id": f"lib2-{uuid4().hex}", "company_id": cid, "category": "qualification", "name": "资质B", "status": "draft"}
    it3 = {"id": f"lib3-{uuid4().hex}", "company_id": cid, "category": "case", "name": "案例A", "status": "confirmed"}

    save_library_item(repository.engine, it1)
    save_library_item(repository.engine, it2)
    save_library_item(repository.engine, it3)

    # 全公司检索
    all_items, total = list_library_items(repository.engine, cid)
    assert total == 3
    assert len(all_items) == 3

    # 按分类检索
    quals, q_total = list_library_items(repository.engine, cid, category="qualification")
    assert q_total == 2
    assert all(i["category"] == "qualification" for i in quals)

    # 按分类和状态检索
    confirmed_quals, cq_total = list_library_items(repository.engine, cid, category="qualification", status="confirmed")
    assert cq_total == 1
    assert confirmed_quals[0]["id"] == it1["id"]

    # 删除条目
    deleted = delete_library_item(repository.engine, it1["id"])
    assert deleted is True
    assert read_library_item(repository.engine, it1["id"]) is None
    _, remaining_total = list_library_items(repository.engine, cid)
    assert remaining_total == 2


def test_sla_template_persistence_and_optimistic_locking(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    tid = f"sla-{uuid4().hex}"
    company_id = "gamma-corp"
    rules = {
        "service_hours": "7x24",
        "response_time_minutes": 15,
        "resolution_time_hours": 2,
        "availability_pct": 99.99,
        "variables": [
            {"var_key": "response_time", "label": "响应时长", "unit": "minute", "default_value": "15"},
        ],
    }

    template_data = {
        "id": tid,
        "company_id": company_id,
        "level": "gold",
        "name": "金牌级服务保障承诺模板",
        "rules_json": rules,
        "revision": 1,
    }

    save_sla_template(repository.engine, template_data)

    loaded = read_sla_template(repository.engine, tid)
    assert loaded is not None
    assert loaded["id"] == tid
    assert loaded["company_id"] == company_id
    assert loaded["level"] == "gold"
    assert loaded["name"] == "金牌级服务保障承诺模板"
    assert loaded["revision"] == 1
    assert loaded["rules_json"]["response_time_minutes"] == 15

    # 等级检索
    gold_tmpls = list_sla_templates(repository.engine, company_id, level="gold")
    assert len(gold_tmpls) >= 1
    assert any(t["id"] == tid for t in gold_tmpls)

    silver_tmpls = list_sla_templates(repository.engine, company_id, level="silver")
    assert not any(t["id"] == tid for t in silver_tmpls)

    # 乐观锁成功更新
    update_tmpl = dict(loaded)
    update_tmpl["name"] = "金牌级服务保障承诺模板（增强版）"
    update_tmpl["revision"] = 2
    save_sla_template(repository.engine, update_tmpl, expected_revision=1)

    updated = read_sla_template(repository.engine, tid)
    assert updated["revision"] == 2
    assert updated["name"] == "金牌级服务保障承诺模板（增强版）"

    # 乐观锁冲突拦截
    with pytest.raises(DomainError) as exc_info:
        save_sla_template(repository.engine, update_tmpl, expected_revision=1)
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 删除
    del_ok = delete_sla_template(repository.engine, tid)
    assert del_ok is True
    assert read_sla_template(repository.engine, tid) is None


def test_memory_repository_polymorphism_library_and_sla():
    # 纯内存模式纯洁性测试：未设置数据库连接串时，MemoryRepository 具备完全一致的接口与乐观锁冲突拦截行为
    repo = MemoryRepository()
    cid = "mem-comp-1"
    item_id = "mem-item-01"

    # 1. 资料条目 CRUD 与乐观锁
    repo.save_library_item({
        "id": item_id,
        "company_id": cid,
        "category": "qualification",
        "name": "内存ISO27001证书",
        "status": "confirmed",
        "payload_json": {"cert_name": "ISO27001"},
        "revision": 1,
    })

    item = repo.read_library_item(item_id)
    assert item is not None
    assert item["revision"] == 1
    assert item["payload_json"]["cert_name"] == "ISO27001"

    # 乐观并发锁拦截
    with pytest.raises(DomainError) as exc_info:
        repo.save_library_item(
            {"id": item_id, "company_id": cid, "name": "冲突更新", "payload_json": {}},
            expected_revision=99,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 修订履历提交
    rev = repo.commit_library_revision(
        item_id=item_id,
        payload={"cert_name": "ISO27001-2026"},
        expected_revision=1,
        new_revision=2,
        changed_by="mem-admin",
        change_reason="换证更新",
    )
    assert rev["version_number"] == 2
    assert repo.read_library_item(item_id)["revision"] == 2
    assert len(repo.list_library_revisions(item_id)) == 1

    # 列表与删除
    items, total = repo.list_library_items(cid, category="qualification")
    assert total == 1
    assert items[0]["id"] == item_id

    assert repo.delete_library_item(item_id) is True
    assert repo.read_library_item(item_id) is None

    # 2. SLA 模板 CRUD 与乐观锁
    sla_id = "mem-sla-01"
    repo.save_sla_template({
        "id": sla_id,
        "company_id": cid,
        "level": "silver",
        "name": "内存银牌SLA",
        "rules_json": {"uptime": "99.9%"},
        "revision": 1,
    })

    tmpl = repo.read_sla_template(sla_id)
    assert tmpl is not None
    assert tmpl["level"] == "silver"

    with pytest.raises(DomainError) as exc_info:
        repo.save_sla_template(
            {"id": sla_id, "company_id": cid, "name": "冲突SLA"},
            expected_revision=88,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    assert len(repo.list_sla_templates(cid, level="silver")) == 1
    assert repo.delete_sla_template(sla_id) is True
    assert repo.read_sla_template(sla_id) is None
