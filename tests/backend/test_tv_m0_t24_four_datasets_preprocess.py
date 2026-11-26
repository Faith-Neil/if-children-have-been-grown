# 为什么有这个文件：验证 TV-M0-T24 RAGFlow 物理四库管道、历史标书入库去实体化清洗、多型号参数表按型号带表头拆块与 Metadata 精确过滤。
from __future__ import annotations

import base64
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app
from icg.domain.kb_preprocess import preprocess_history_upload
from test_reference_flow import login


def _b64(data: str | bytes) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return base64.b64encode(raw).decode()


def _make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        zf.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


@pytest.fixture()
def fake():
    return FakeRagflowV1()


@pytest.fixture()
def client(fake):
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as tc:
        yield tc


def test_deploy_four_physical_datasets_with_specialized_pipelines(client, fake):
    admin = login(client, "alpha-company-admin")
    resp = client.post(
        "/api/v1/kb-admin/pipelines/deploy",
        headers=admin,
        json={"kinds": ["history", "manuals", "fault_cases", "products"]},
    )
    assert resp.status_code == 200, resp.text
    datasets = resp.json()["datasets"]
    assert set(datasets) == {"history", "manuals", "fault_cases", "products"}

    ds_names = {fake.datasets[info["dataset_id"]]["name"] for info in datasets.values()}
    assert ds_names == {
        "alpha::icg-history",
        "alpha::icg-manuals",
        "alpha::icg-fault-cases",
        "alpha::icg-products",
    }

    # fault_cases 开启 Auto-question (top_n=3)；products 限制 chunk_token_cap=640 防跨型号混切
    fc_comp = fake.agents[datasets["fault_cases"]["pipeline_id"]]["dsl"]["components"]
    fc_ext = next(v for k, v in fc_comp.items() if k.startswith("Extractor"))["obj"]["params"]
    assert fc_ext["questions"]["enabled"] is True and fc_ext["questions"]["top_n"] == 3

    prod_comp = fake.agents[datasets["products"]["pipeline_id"]]["dsl"]["components"]
    prod_chunker = next(v for k, v in prod_comp.items() if k.startswith("TitleChunker"))["obj"]["params"]
    assert prod_chunker["chunk_token_cap"] == 640


def test_history_bid_docx_and_text_desensitized_before_ragflow_ingestion(client, fake):
    # 1. 验证真实 DOCX XML 内旧甲方、旧项目、编号与金额被替换为占位符
    docx_bytes = _make_docx([
        "采购人：乐山市人民医院",
        "项目名称：乐山市人民医院Oracle核心库三年维保项目",
        "项目编号：LSYY-2024-019",
        "投标总价：186.50万元",
        "第五章 应急响应方案：我司承诺为乐山市人民医院提供7×24小时数据库应急保障。",
    ])
    scrubbed_docx, info = preprocess_history_upload("历史标书.docx", docx_bytes)
    assert info["desensitized"] is True and info["mode"] == "docx_xml"
    with ZipFile(BytesIO(scrubbed_docx), "r") as zf:
        xml_text = zf.read("word/document.xml").decode("utf-8")
    assert "乐山市人民医院" not in xml_text
    assert "LSYY-2024-019" not in xml_text
    assert "186.50万元" not in xml_text
    assert "[某甲方]" in xml_text and "[某项目]" in xml_text and "[项目编号]" in xml_text and "[合同金额]" in xml_text

    # 2. 验证通过 API 上传进 icg-history 后，分块里不含旧甲方/旧金额，且审计元数据仍保留
    admin = login(client, "alpha-company-admin")
    client.post("/api/v1/kb-admin/datasets/history/ensure", headers=admin, json={})
    raw_history = (
        "# 第五章 售后服务方案\n\n"
        "## 5.1 应急预案\n"
        "采购人：甘肃省农村信用社联合社\n"
        "项目编号：GSNX-2025-008，合同金额 320万元。\n"
        "针对甘肃省农村信用社联合社核心数据库突发宕机，启动三级应急切换流程。"
    )
    up = client.post(
        "/api/v1/kb-admin/datasets/history/documents",
        headers=admin,
        json={
            "filename": "甘肃农信投标书.docx",
            "content_base64": _b64(raw_history),
            "metadata": {"purchaser": "甘肃省农村信用社联合社", "is_winner": "true"},
        },
    )
    assert up.status_code == 200, up.text
    doc_id = up.json()["document_id"]
    stored_chunks = fake.documents[doc_id]["chunks"]
    assert all("甘肃省农村信用社联合社" not in c["content"] and "320万元" not in c["content"] for c in stored_chunks)
    assert any("[某甲方]" in c["content"] and "三级应急切换流程" in c["content"] for c in stored_chunks)
    assert fake.documents[doc_id]["meta_fields"]["purchaser"] == "甘肃省农村信用社联合社"


def test_multi_model_comparison_csv_splits_by_model_with_headers_and_filters_by_metadata(client, fake):
    admin = login(client, "alpha-company-admin")
    client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={"kinds": ["products", "fault_cases"]})

    # A/B 两款型号横向对比参数表：拆行后 Model-X800 与 Model-S200 分属独立 ## 章节块，互不串参数
    comparison_csv = (
        "参数项,Model-X800,Model-S200\n"
        "最大并发TPS,50万TPS,8万TPS\n"
        "双活热备切换,原生RPO=0秒级切换,不支持双活\n"
    )
    up_x = client.post(
        "/api/v1/kb-admin/datasets/products/documents",
        headers=admin,
        json={
            "filename": "数据库一体机彩页对比表.csv",
            "content_base64": _b64(comparison_csv),
            "metadata": {"brand": "星河数据"},
        },
    )
    assert up_x.status_code == 200, up_x.text
    prod_doc = fake.documents[up_x.json()["document_id"]]
    assert prod_doc["meta_fields"]["doc_type"] == "product_spec"
    assert "Model-X800" in prod_doc["meta_fields"]["model"]
    assert len(prod_doc["chunks"]) == 2
    x800_chunk = next(c["content"] for c in prod_doc["chunks"] if "Model-X800" in c["content"])
    s200_chunk = next(c["content"] for c in prod_doc["chunks"] if "Model-S200" in c["content"])
    assert "50万TPS" in x800_chunk and "8万TPS" not in x800_chunk
    assert "8万TPS" in s200_chunk and "50万TPS" not in s200_chunk

    # 再上传两份单型号规格：Model-X800 单值文档可被精确锁定；Model-Legacy 绝不混入。
    # 真实 RAGFlow 1.0 实测语义：contains/is 均为标量精确匹配（非子串），
    # 逗号拼接的多型号串（"Model-X800,Model-S200"）无法被任何单值条件命中——
    # 多型号对比表文档在型号精确级会落空，由放宽阶梯降到 doc_type 级召回（见 T25 阶梯测试），
    # 单型号文档才是精确检索的推荐上传粒度。
    client.post(
        "/api/v1/kb-admin/datasets/products/documents",
        headers=admin,
        json={
            "filename": "X800专项规格.md",
            "content_base64": _b64("# X800专项\n\n## 双活热备\nModel-X800 最大并发TPS为50万TPS，原生双活热备秒级切换。"),
            "metadata": {"model": "Model-X800"},
        },
    )
    client.post(
        "/api/v1/kb-admin/datasets/products/documents",
        headers=admin,
        json={
            "filename": "旧款一体机参数.md",
            "content_base64": _b64("# 旧款参数\n\n## 双活热备\nModel-Legacy 最大并发TPS为1万TPS，双活热备需外置网关。"),
            "metadata": {"model": "Model-Legacy"},
        },
    )
    filtered = client.post(
        "/api/v1/kb-admin/retrieval-test",
        headers=admin,
        json={
            "query": "最大并发TPS 双活热备",
            "kinds": ["products"],
            "metadata_condition": {
                "logic": "and",
                "conditions": [{"name": "model", "comparison_operator": "is", "value": "Model-X800"}],
            },
        },
    )
    assert filtered.status_code == 200, filtered.text
    items = filtered.json()["items"]
    assert len(items) == 1
    assert "Model-Legacy" not in items[0]["content"]
    assert "Model-X800" in items[0]["content"]

    # 真机语义锚定：逗号拼接多型号串在精确级不命中（防止误以为 contains 是子串匹配而误设计）
    comma_filtered = client.post(
        "/api/v1/kb-admin/retrieval-test",
        headers=admin,
        json={
            "query": "最大并发TPS 双活热备",
            "kinds": ["products"],
            "metadata_condition": {
                "logic": "and",
                "conditions": [{"name": "model", "comparison_operator": "is", "value": "Model-S200"}],
            },
        },
    )
    assert comma_filtered.status_code == 200
    assert comma_filtered.json()["items"] == []


def test_history_desensitize_keeps_brand_and_our_company_allowlist():
    """厂商品牌词与我方公司名不得被误脱敏；旧甲方名仍替换为占位，Markdown 标题层级保持。"""
    from icg.domain.kb_preprocess import desensitize_history_text

    text = (
        "# 项目经验\n我方与陕西数联科技有限责任公司、中国移动通信集团有限公司联合交付，"
        "为安康市人民医院提供核心运维服务。"
    )
    cleaned, _ = desensitize_history_text(text, {"bidder_name": "陕西数联科技有限责任公司"})
    assert "陕西数联科技有限责任公司" in cleaned
    assert "中国移动通信集团有限公司" in cleaned
    assert "安康市人民医院" not in cleaned and "[某甲方]" in cleaned
    assert cleaned.startswith("# 项目经验")
