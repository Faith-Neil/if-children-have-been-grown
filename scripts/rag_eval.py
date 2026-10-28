# 为什么有这个文件：用合成金标集量化知识库检索质量（召回率、MRR、负例误召回），并扫描检索参数。
# 它解决什么问题：RAG 质量决定生产可用性，但此前没有任何可复现的度量；调阈值、权重、重排模型只能凭感觉。
#
# 用法：
#   离线（进程内假 RAGFlow，只验证脚本与链路，不代表真实质量）：
#     python scripts/rag_eval.py
#   真实 RAGFlow（会新建临时数据集，结束后删除；--keep 保留）：
#     ICG_RAGFLOW_BASE_URL=... ICG_RAGFLOW_API_KEY=... python scripts/rag_eval.py --live [--report docs/testing/xxx.md]
#
# 文档按产品同一渲染函数（library_document / snippet_document）生成，检索参数与 KnowledgeBaseService 一致，
# 因此结论可以直接用于调 ICG_KB_SIMILARITY_THRESHOLD / ICG_KB_KEYWORDS_WEIGHT / ICG_KB_RERANK_ID。

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "bid-core"))
sys.path.insert(0, str(ROOT / "tests" / "backend"))

from icg.domain.knowledge_base import library_document, snippet_document  # noqa: E402
from icg.infra.ragflow_client import RagflowRetrievalClient  # noqa: E402

GOLDEN = ROOT / "tests" / "rag_eval" / "golden_v1.json"
COMPANY = "rag-eval"


def _documents(golden: dict) -> list:
    docs = []
    for row in golden["documents"]:
        if row["type"] == "snippet":
            docs.append(snippet_document({"id": row["id"], "company_id": COMPANY, "product": row["name"],
                                          "snippet_type": "", "published_body": row["content"],
                                          "published_revision": 1, "source_group": "合成"}))
        else:
            docs.append(library_document({"id": row["id"], "company_id": COMPANY, "name": row["name"],
                                          "type": row["type"], "content": row["content"], "revision": 1,
                                          "is_long_term": True}))
    return docs


def _client(live: bool):
    if live:
        base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip()
        key = os.environ.get("ICG_RAGFLOW_API_KEY", "").strip()
        if not base or not key:
            sys.exit("--live 需要 ICG_RAGFLOW_BASE_URL 与 ICG_RAGFLOW_API_KEY")
        return RagflowRetrievalClient(base_url=base, api_key=key, timeout_seconds=120), None
    from fake_ragflow_v1 import FakeRagflowV1
    fake = FakeRagflowV1()
    return fake.client(), fake


def _ingest(client, docs, wait_seconds: int) -> tuple[str, dict[str, str]]:
    dataset = client.create_dataset(f"{COMPANY}-{int(time.time())}", company_id=COMPANY)
    mapping: dict[str, str] = {}
    for doc in docs:
        uploaded = client.upload_document(dataset.id, doc.filename, doc.markdown)
        client.update_document(dataset.id, uploaded.id, meta_fields=doc.meta)
        mapping[uploaded.id] = doc.source_id
    client.trigger_parse(dataset.id, list(mapping))
    deadline = time.time() + wait_seconds
    while True:
        states = {d.id: d.sync_status for d in client.list_documents(dataset.id, page_size=100)}
        pending = [d for d in mapping if states.get(d) == "unsynced"]
        failed = [d for d in mapping if states.get(d) == "failed"]
        print(f"  解析进度：完成 {len(mapping) - len(pending) - len(failed)} / {len(mapping)}，失败 {len(failed)}", flush=True)
        if not pending:
            break
        if time.time() > deadline:
            print(f"  等待超时，{len(pending)} 篇未完成，按已完成部分评测", flush=True)
            break
        time.sleep(10)
    return dataset.id, mapping


def _run(client, dataset_id, mapping, queries, *, threshold, keywords_weight, rerank_id, k):
    per_kind: dict[str, dict] = {}
    details = []
    for query in queries:
        result = client.retrieve(question=query["q"], dataset_ids=[dataset_id], document_ids=list(mapping),
                                 page_size=k * 4, similarity_threshold=threshold,
                                 keywords_similarity_weight=keywords_weight, rerank_id=rerank_id)
        ranked: list[str] = []
        scores: dict[str, float] = {}
        for chunk in result.chunks:
            source = mapping.get(chunk.document_id)
            if source and source not in ranked:
                ranked.append(source)
                scores[source] = chunk.similarity
        top = ranked[:k]
        relevant = set(query["relevant"])
        bucket = per_kind.setdefault(query["kind"], {"n": 0, "recall": 0.0, "mrr": 0.0, "hit1": 0, "false_pos": 0})
        bucket["n"] += 1
        if relevant:
            found = relevant & set(top)
            bucket["recall"] += len(found) / len(relevant)
            rank = next((i + 1 for i, s in enumerate(top) if s in relevant), None)
            bucket["mrr"] += 1 / rank if rank else 0.0
            bucket["hit1"] += 1 if top and top[0] in relevant else 0
        else:
            bucket["false_pos"] += 1 if top else 0
        details.append({"q": query["q"], "kind": query["kind"], "relevant": sorted(relevant),
                        "top": [(s, round(scores[s], 3)) for s in top]})
    summary = {}
    for kind, b in per_kind.items():
        n = b["n"]
        summary[kind] = ({"n": n, "false_positive_rate": round(b["false_pos"] / n, 3)} if kind == "negative" else
                         {"n": n, f"recall@{k}": round(b["recall"] / n, 3), "mrr": round(b["mrr"] / n, 3),
                          "hit@1": round(b["hit1"] / n, 3)})
    return summary, details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--keep", action="store_true", help="保留临时数据集")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--thresholds", default="0.1,0.2,0.3")
    parser.add_argument("--weights", default="0.3,0.5,0.7", help="keywords_similarity_weight 候选")
    parser.add_argument("--rerank-id", default=os.environ.get("ICG_KB_RERANK_ID") or None)
    parser.add_argument("--wait", type=int, default=900, help="等待解析完成的秒数")
    parser.add_argument("--report", help="把结果写成 Markdown")
    args = parser.parse_args()

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    docs = _documents(golden)
    client, _fake = _client(args.live)
    print(f"模式：{'真实 RAGFlow ' + client.base_url if args.live else '离线假服务'}；文档 {len(docs)}，查询 {len(golden['queries'])}")
    dataset_id, mapping = _ingest(client, docs, args.wait)
    rows = []
    try:
        for threshold in [float(x) for x in args.thresholds.split(",")]:
            for weight in [float(x) for x in args.weights.split(",")]:
                summary, details = _run(client, dataset_id, mapping, golden["queries"], threshold=threshold,
                                        keywords_weight=weight, rerank_id=args.rerank_id, k=args.k)
                rows.append({"threshold": threshold, "keywords_weight": weight, "summary": summary, "details": details})
                print(json.dumps({"threshold": threshold, "keywords_weight": weight, **summary}, ensure_ascii=False))
    finally:
        if args.live and not args.keep:
            try:
                client._send_request("DELETE", client.datasets_url, json_body={"ids": [dataset_id]})
                print(f"已删除临时数据集 {dataset_id}")
            except Exception as exc:
                print(f"临时数据集 {dataset_id} 删除失败：{type(exc).__name__}，请手动清理")
    if args.report:
        _write_report(Path(args.report), args, golden, rows, live=args.live)


def _write_report(path: Path, args, golden, rows, *, live: bool) -> None:
    k = args.k
    lines = [f"# RAG 检索评测（{golden['version']}，{'真实 RAGFlow' if live else '离线假服务'}）", "",
             f"- 文档 {len(golden['documents'])} 篇，查询 {len(golden['queries'])} 条；k={k}；rerank={args.rerank_id or '无'}", "",
             f"| 阈值 | 关键词权重 | literal recall@{k} | literal MRR | paraphrase recall@{k} | paraphrase MRR | 负例误召回 |",
             "|---|---|---|---|---|---|---|"]
    for row in rows:
        s = row["summary"]
        lit, par, neg = s.get("literal", {}), s.get("paraphrase", {}), s.get("negative", {})
        lines.append(f"| {row['threshold']} | {row['keywords_weight']} | {lit.get(f'recall@{k}', '-')} | {lit.get('mrr', '-')} | "
                     f"{par.get(f'recall@{k}', '-')} | {par.get('mrr', '-')} | {neg.get('false_positive_rate', '-')} |")
    best = max(rows, key=lambda r: (r["summary"].get("paraphrase", {}).get(f"recall@{k}", 0)
                                    + r["summary"].get("literal", {}).get(f"recall@{k}", 0)
                                    - r["summary"].get("negative", {}).get("false_positive_rate", 0)))
    lines += ["", f"## 最优组合明细（阈值 {best['threshold']}，关键词权重 {best['keywords_weight']}）", "",
              "| 类别 | 查询 | 期望 | 前 k 命中（相似度） |", "|---|---|---|---|"]
    for d in best["details"]:
        lines.append(f"| {d['kind']} | {d['q']} | {', '.join(d['relevant']) or '（无）'} | "
                     f"{', '.join(f'{s}({v})' for s, v in d['top']) or '（无）'} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"报告：{path}")


if __name__ == "__main__":
    main()
