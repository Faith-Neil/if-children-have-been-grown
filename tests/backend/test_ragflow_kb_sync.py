# 为什么有这个文件：自动化测试 RAGFlow 知识库摄入与同步闭环（dataset/kb_sync，落实用户拍板 B5/B6）。
# 它解决什么问题：验证多租户数据集强隔离、方案片段结构化摄入、文档解析状态轮询、run 到 kb_sync_status 映射、异常优雅降级与真实内网门控。

from __future__ import annotations

from uuid import uuid4
from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from fake_ragflow import (
    FakeRagflow,
    MODE_BUSINESS_ERROR,
    MODE_CHUNKS,
    MODE_EMPTY,
    MODE_HTTP_ERROR,
    MODE_TIMEOUT,
    real_ragflow_skip_reason,
)
from icg.domain.domain import Account, DomainError, Principal
from icg_demo.main import create_app
from icg_demo.model_config_storage import ICG_SECRET_KEY_ENV
from icg_demo.ragflow_client import (
    RagflowBusinessError,
    RagflowClient,
    RagflowDataset,
    RagflowDocument,
    RagflowRetrievalClient,
    ragflow_run_to_kb_sync_status,
)
from icg.domain.ragflow_config import RagflowConfigService
from test_demo import login


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv(ICG_SECRET_KEY_ENV, key)
    return key


@pytest.fixture
def fake_ragflow_fixture():
    fake = FakeRagflow()
    try:
        yield fake
    finally:
        fake.close()


@pytest.fixture
def client(secret_key):
    with TestClient(create_app()) as test_client:
        yield test_client


def make_principal(user_id: str, company_id: str, role: str = "project_manager") -> Principal:
    user = Account(
        id=user_id,
        company_id=company_id,
        name=f"User {user_id}",
        role=role,
    )
    return Principal(user=user, session_token=f"token-{user_id}")


# ---------------------------------------------------------------------------
# 1. 客户端层：多租户数据集隔离与生命周期
# ---------------------------------------------------------------------------

def test_client_dataset_crud_and_tenant_isolation(fake_ragflow_fixture):
    client = RagflowRetrievalClient(base_url=fake_ragflow_fixture.base_url)

    # 1. 为 company-alpha 创建数据集 -> 自动注入 company-alpha:: 前缀
    ds_alpha = client.create_dataset("方案片段库", company_id="company-alpha")
    assert isinstance(ds_alpha, RagflowDataset)
    assert ds_alpha.company_id == "company-alpha"
    assert ds_alpha.name == "company-alpha::方案片段库"
    assert ds_alpha.id.startswith("ds-")

    # 2. 为 company-beta 创建数据集 -> 自动注入 company-beta:: 前缀
    ds_beta = client.create_dataset("方案片段库", company_id="company-beta")
    assert isinstance(ds_beta, RagflowDataset)
    assert ds_beta.company_id == "company-beta"
    assert ds_beta.name == "company-beta::方案片段库"

    # 3. 租户隔离查询：指定 company-alpha 只看到 alpha 的数据集
    alpha_datasets = client.list_datasets(company_id="company-alpha")
    alpha_names = [d.name for d in alpha_datasets]
    assert "company-alpha::方案片段库" in alpha_names
    assert "company-beta::方案片段库" not in alpha_names

    # 4. 租户隔离查询：指定 company-beta 只看到 beta 的数据集
    beta_datasets = client.list_datasets(company_id="company-beta")
    beta_names = [d.name for d in beta_datasets]
    assert "company-beta::方案片段库" in beta_names
    assert "company-alpha::方案片段库" not in beta_names

    # 5. 单数据集查询隔离：跨租户查询阻断
    alpha_fetched = client.get_dataset(ds_alpha.id, company_id="company-alpha")
    assert alpha_fetched.id == ds_alpha.id

    with pytest.raises(RagflowBusinessError) as exc_info:
        client.get_dataset(ds_beta.id, company_id="company-alpha")
    assert "does not belong to company" in str(exc_info.value) or "not found" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. 客户端层：文档摄入、切块解析触发与状态轮询
# ---------------------------------------------------------------------------

def test_client_document_upload_and_parse_lifecycle(fake_ragflow_fixture):
    client = RagflowRetrievalClient(base_url=fake_ragflow_fixture.base_url)
    ds = client.create_dataset("资质证明库", company_id="company-alpha")

    # 1. 上传文档 -> 初始状态 UNSTART
    doc_content = "甲级资质证明文件：具备机房工程专业承包一级资质，有效期至 2028-12-31。"
    doc = client.upload_document(
        dataset_id=ds.id,
        name="qualification_cert.txt",
        content=doc_content,
        company_id="company-alpha",
    )
    assert isinstance(doc, RagflowDocument)
    assert doc.id.startswith("doc-")
    assert doc.run == "UNSTART"
    assert doc.progress == 0.0

    # 2. 查询文档列表与单个状态
    docs = client.list_documents(ds.id)
    assert len(docs) >= 1
    assert any(d.id == doc.id for d in docs)

    status_before = client.get_document_status(ds.id, doc.id)
    assert status_before.run == "UNSTART"
    assert ragflow_run_to_kb_sync_status(status_before.run) == "unsynced"

    # 3. 触发解析
    parse_ok = client.trigger_parse(ds.id, [doc.id])
    assert parse_ok is True

    # 4. 解析完成状态轮询校验
    status_after = client.get_document_status(ds.id, doc.id)
    assert status_after.run == "DONE"
    assert status_after.progress == 1.0
    assert ragflow_run_to_kb_sync_status(status_after.run) == "synced"


def test_client_document_sync_fail_handling(fake_ragflow_fixture):
    client = RagflowRetrievalClient(base_url=fake_ragflow_fixture.base_url)
    ds = client.create_dataset("故障测试库", company_id="company-alpha")

    # 上传带 [[sync-fail]] 的特殊文档
    doc = client.upload_document(
        dataset_id=ds.id,
        name="fail_doc.txt",
        content="本段包含 [[sync-fail]]，模拟解析拒绝。",
        company_id="company-alpha",
    )
    client.trigger_parse(ds.id, [doc.id])
    status = client.get_document_status(ds.id, doc.id)
    assert status.run == "FAIL"
    assert ragflow_run_to_kb_sync_status(status.run) == "failed"


# ---------------------------------------------------------------------------
# 3. 领域服务层：RagflowConfigService 知识库摄入与同步闭环
# ---------------------------------------------------------------------------

def test_service_dataset_management_with_tenant_prefix(client, fake_ragflow_fixture):
    service = client.app.state.service
    config_service = RagflowConfigService(service)
    p_alpha = make_principal("user-alpha", "alpha")
    p_beta = make_principal("user-beta", "beta")

    # 1. 更新为测试桩地址
    cfg_a = config_service.get(p_alpha)
    config_service.update(
        p_alpha,
        {"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-alpha-123"},
        if_match=f'"{cfg_a["revision"]}"',
    )
    cfg_b = config_service.get(p_beta)
    config_service.update(
        p_beta,
        {"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-beta-456"},
        if_match=f'"{cfg_b["revision"]}"',
    )

    # 2. Alpha 创建数据集
    ds_alpha = config_service.create_dataset(p_alpha, "服务承诺库")
    assert ds_alpha["company_id"] == "alpha"
    assert ds_alpha["name"].startswith("alpha::")

    # 3. Beta 创建数据集
    ds_beta = config_service.create_dataset(p_beta, "历史方案库")
    assert ds_beta["company_id"] == "beta"
    assert ds_beta["name"].startswith("beta::")

    # 4. 隔离列表校验
    list_alpha = config_service.list_datasets(p_alpha)
    alpha_names = [d["name"] for d in list_alpha]
    assert any("alpha::" in name for name in alpha_names)
    assert not any("beta::" in name for name in alpha_names)


def test_service_sync_knowledge_base_published_snippet(client, fake_ragflow_fixture):
    service = client.app.state.service
    config_service = RagflowConfigService(service)
    p_alpha = make_principal("alpha-lead", "alpha")

    # 设置 RAGFlow 服务桩地址
    cfg = config_service.get(p_alpha)
    config_service.update(
        p_alpha,
        {"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-alpha-key"},
        if_match=f'"{cfg["revision"]}"',
    )

    # 1. 在系统中创建并发布一个方案片段
    headers = login(client, "alpha-manager")
    create_res = client.post(
        "/api/v1/snippet-publications",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "product": "巡检产品",
            "snippet_type": "solution",
            "source_group": "机房运维方案",
            "draft_body": "每周巡检一次机房，SLA 达到 99.99%。",
            "variables": ["uptime"],
        },
    )
    assert create_res.status_code == 200
    snippet = create_res.json()

    # 发布草稿
    pub_res = client.post(
        f"/api/v1/snippet-publications/{snippet['id']}/publish",
        headers={**headers, "If-Match": f'"{snippet["draft_revision"]}"', "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert pub_res.status_code == 200
    published_item = pub_res.json()["item"]
    assert published_item["kb_sync_status"] == "unsynced"

    # 2. 调用 sync_knowledge_base 将方案片段摄入至对应公司的 RAGFlow 知识库
    sync_result = config_service.sync_knowledge_base(p_alpha, snippet["id"])
    assert sync_result["synced"] is True
    assert sync_result["kb_sync_status"] == "synced"
    assert sync_result["dataset_id"].startswith("ds-") or sync_result["dataset_id"].startswith("dataset-")
    assert sync_result["document_id"].startswith("doc-")
    assert sync_result["run"] == "DONE"

    # 3. 验证片段发布存储记录中的 kb_sync_status 已被同步更新为 synced
    detail_res = client.get(f"/api/v1/snippet-publications/{snippet['id']}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["kb_sync_status"] == "synced"


def test_service_sync_knowledge_base_with_sync_fail_marker(client, fake_ragflow_fixture):
    service = client.app.state.service
    config_service = RagflowConfigService(service)
    p_alpha = make_principal("alpha-lead", "alpha")

    cfg = config_service.get(p_alpha)
    config_service.update(
        p_alpha,
        {"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-alpha-key"},
        if_match=f'"{cfg["revision"]}"',
    )

    headers = login(client, "alpha-manager")
    create_res = client.post(
        "/api/v1/snippet-publications",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "product": "巡检产品",
            "snippet_type": "solution",
            "source_group": "拒绝测试片段",
            "draft_body": "知识库拒绝这段 [[sync-fail]]，变量为 {{uptime}}。",
            "variables": ["uptime"],
        },
    )
    snippet = create_res.json()
    client.post(
        f"/api/v1/snippet-publications/{snippet['id']}/publish",
        headers={**headers, "If-Match": f'"{snippet["draft_revision"]}"', "Idempotency-Key": str(uuid4())},
        json={},
    )

    # 同步含有 [[sync-fail]] 的片段
    sync_result = config_service.sync_knowledge_base(p_alpha, snippet["id"])
    assert sync_result["synced"] is False
    assert sync_result["kb_sync_status"] == "failed"

    # 验证存储中状态也更新为 failed
    detail_res = client.get(f"/api/v1/snippet-publications/{snippet['id']}", headers=headers)
    assert detail_res.json()["kb_sync_status"] == "failed"


def test_service_sync_knowledge_base_graceful_degradation_on_http_error(client, fake_ragflow_fixture):
    service = client.app.state.service
    config_service = RagflowConfigService(service)
    p_alpha = make_principal("alpha-lead", "alpha")

    # 模拟上游服务端 500 故障
    fake_ragflow_fixture.mode = MODE_HTTP_ERROR

    cfg = config_service.get(p_alpha)
    config_service.update(
        p_alpha,
        {"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-alpha-key"},
        if_match=f'"{cfg["revision"]}"',
    )

    result = config_service.sync_knowledge_base(
        p_alpha,
        "mock_snippet_01",
        payload={"title": "紧急故障处理方案", "content": "SLA 响应时限 30 分钟。"},
    )
    # 优雅降级：不抛出未捕获 500 崩溃，返回清晰失败状态
    assert result["synced"] is False
    assert result["kb_sync_status"] == "failed"
    assert "失败" in result["message"] or "异常" in result["message"]


def test_service_sync_cross_tenant_isolation(client, fake_ragflow_fixture):
    service = client.app.state.service
    config_service = RagflowConfigService(service)
    p_alpha = make_principal("alpha-lead", "alpha")
    p_beta = make_principal("beta-lead", "beta")

    # Alpha 创建并拥有一个片段
    headers_alpha = login(client, "alpha-manager")
    create_res = client.post(
        "/api/v1/snippet-publications",
        headers={**headers_alpha, "Idempotency-Key": str(uuid4())},
        json={
            "product": "巡检产品",
            "snippet_type": "solution",
            "source_group": "Alpha机密方案",
            "draft_body": "仅供 Alpha 内部使用。",
            "variables": [],
        },
    )
    assert create_res.status_code == 200
    snippet_alpha_id = create_res.json()["id"]

    # Beta 用户尝试同步 Alpha 的方案片段 -> 触发 404 NOT_FOUND 强拦截
    with pytest.raises(DomainError) as exc_info:
        config_service.sync_knowledge_base(p_beta, snippet_alpha_id)
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


# ---------------------------------------------------------------------------
# 4. HTTP API 契约与运行时端点集成验证
# ---------------------------------------------------------------------------

def test_ragflow_sync_api_endpoints_integration(client, fake_ragflow_fixture):
    headers = login(client, "alpha-manager")

    # 1. 配置基础地址
    client.put(
        "/api/v1/ragflow-config",
        headers={**headers, "If-Match": '"1"'},
        json={"base_url": fake_ragflow_fixture.base_url, "api_key": "sec-alpha-api-key"},
    )

    # 2. 调用 POST /api/v1/ragflow/datasets 创建数据集
    create_ds_res = client.post(
        "/api/v1/ragflow/datasets",
        headers=headers,
        json={"name": "API集成测试库", "parser_id": "general"},
    )
    assert create_ds_res.status_code == 200
    ds = create_ds_res.json()
    assert ds["name"].startswith("alpha::")

    # 3. 调用 GET /api/v1/ragflow/datasets 检索列表
    list_ds_res = client.get("/api/v1/ragflow/datasets", headers=headers)
    assert list_ds_res.status_code == 200
    items = list_ds_res.json()["items"]
    assert any(d["id"] == ds["id"] for d in items)

    # 4. 调用 POST /api/v1/ragflow/sync 同步知识库
    sync_res = client.post(
        "/api/v1/ragflow/sync",
        headers=headers,
        json={
            "snippet_id": "manual_snippet_01",
            "title": "API同步测试方案",
            "content": "API 测试方案内容：支持多租户强隔离摄入。",
            "dataset_id": ds["id"],
        },
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["synced"] is True
    assert sync_data["kb_sync_status"] == "synced"
    assert sync_data["dataset_id"] == ds["id"]


# ---------------------------------------------------------------------------
# 5. 真实环境隔离门控核验
# ---------------------------------------------------------------------------

@pytest.mark.live_ragflow
def test_real_ragflow_kb_sync_skipped_without_env_flag(fake_ragflow_fixture):
    reason = real_ragflow_skip_reason()
    if reason is not None:
        pytest.skip(reason)

    # 仅在设置 ICG_RUN_REAL_RAGFLOW_TESTS=1 时运行真实端点测试
    real_url = "http://127.0.0.1:9380"
    client = RagflowRetrievalClient(base_url=real_url)
    health = client.health()
    assert health.get("status") == "ok"
