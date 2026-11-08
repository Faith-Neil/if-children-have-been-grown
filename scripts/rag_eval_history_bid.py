# 为什么有这个文件：对五份脱敏历史标书走 history_bid 管道，在真实 RAGFlow 上算 Recall@5 / MRR@10。
# 它解决什么问题：解析验收只证明切块可用，不能证明检索大盘；本脚本按文档级金标复现字面/同义/负例指标。
#
# 用法：
#   离线冒烟（假服务，不算质量验收）：
#     python scripts/rag_eval_history_bid.py
#   真实 RAGFlow：
#     ICG_RAGFLOW_BASE_URL=... ICG_RAGFLOW_API_KEY=... \\
#       python scripts/rag_eval_history_bid.py --live --report docs/testing/rag-eval-history-bid-v1.md

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "bid-core"))
sys.path.insert(0, str(ROOT / "tests" / "backend"))

from icg.infra.ragflow_client import RagflowRetrievalClient  # noqa: E402
from icg.infra.ragflow_pipelines import PROFILES, PipelineOptions, build_dsl  # noqa: E402

GOLDEN = ROOT / "tests" / "rag_eval" / "golden_history_bid_v1.json"
FIXTURE_DIR = ROOT / "tests" / "backend" / "fixtures" / "history-bid-golden"
COMPANY = "rag-eval-hb"
CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _client(live: bool):
    if live:
        base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip()
        key = os.environ.get("ICG_RAGFLOW_API_KEY", "").strip()
        if not base or not key:
            sys.exit("--live 需要 ICG_RAGFLOW_BASE_URL 与 ICG_RAGFLOW_API_KEY")
        return RagflowRetrievalClient(base_url=base, api_key=key, timeout_seconds=180), None
    from fake_ragflow_v1 import FakeRagflowV1

    fake = FakeRagflowV1()
    return fake.client(), fake


def _load_docs(golden: dict, *, live: bool) -> list[dict]:
    docs = []
    for row in golden["documents"]:
        path = FIXTURE_DIR / row["fixture"]
        if not path.is_file():
            raise SystemExit(f"缺少金标文件 {path}")
        if live:
            data = path.read_bytes()
        else:
            # 离线假服务只冒烟链路：用短合成正文，不把百兆原件灌进 MockTransport。
            data = (
                f"# {row.get('name') or row['id']}\n\n"
                f"synthetic body for {row['id']} offline smoke.\n"
            ).encode("utf-8")
        docs.append({
            "id": row["id"],
            "name": row.get("name") or row["id"],
            "filename": f"{row['id']}-{row['fixture']}",
            "data": data,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if live else "offline",
        })
    return docs


def _wait_parsed(client, dataset_id: str, mapping: dict[str, str], wait_seconds: int) -> None:
    deadline = time.time() + wait_seconds
    while True:
        listed = client.list_documents(dataset_id, page_size=100)
        states = {d.id: d.sync_status for d in listed}
        pending = [d for d in mapping if states.get(d) == "unsynced"]
        failed = [d for d in mapping if states.get(d) == "failed"]
        print(
            f"  解析进度：完成 {len(mapping) - len(pending) - len(failed)} / {len(mapping)}，失败 {len(failed)}",
            flush=True,
        )
        if failed and len(failed) == len(mapping):
            reason = next((d.progress_msg for d in listed if d.id in failed and d.progress_msg), "")
            raise SystemExit(f"全部文档解析失败：{reason[:300]}")
        if not pending:
            return
        if time.time() > deadline:
            print(f"  等待超时，{len(pending)} 篇未完成，按已完成部分评测", flush=True)
            return
        time.sleep(15)


def _ingest(client, docs: list[dict], wait_seconds: int, embedding_model: str | None, llm_id: str):
    title = f"icg:history_bid:v1:{hashlib.sha1(COMPANY.encode()).hexdigest()[:8]}"
    if len(title) > 32:
        title = title[:32]
    dsl = build_dsl(PROFILES["history_bid"], PipelineOptions(llm_id=llm_id or ""))
    agent = client.create_agent(
        title,
        dsl,
        description=f"[{COMPANY}] history bid eval",
        canvas_category="dataflow_canvas",
    )
    pipeline_id = agent["id"]
    name = f"{COMPANY}-{int(time.time())}"
    try:
        dataset = client.create_pipeline_dataset(
            name, pipeline_id, company_id=COMPANY, embedding_model=embedding_model
        )
    except Exception:
        client.delete_agent(pipeline_id)
        raise
    mapping: dict[str, str] = {}
    try:
        for doc in docs:
            uploaded = client.upload_file(dataset.id, doc["filename"], doc["data"], CONTENT_TYPE)
            client.update_document(
                dataset.id,
                uploaded.id,
                meta_fields={"company_id": COMPANY, "source_id": doc["id"], "knowledge_kind": "history"},
            )
            mapping[uploaded.id] = doc["id"]
        client.trigger_parse(dataset.id, list(mapping))
        _wait_parsed(client, dataset.id, mapping, wait_seconds)
        return dataset.id, pipeline_id, mapping
    except BaseException:
        try:
            client._send_request("DELETE", client.datasets_url, json_body={"ids": [dataset.id]})
        except Exception:
            pass
        try:
            client.delete_agent(pipeline_id)
        except Exception:
            pass
        raise


def _attach(client, dataset_id: str, docs: list[dict], wait_seconds: int):
    by_name = {d["filename"]: d["id"] for d in docs}
    listed = client.list_documents(dataset_id, page_size=100)
    mapping = {d.id: by_name[d.name] for d in listed if d.name in by_name}
    if not mapping:
        raise SystemExit(f"数据集 {dataset_id} 里没有金标文档")
    print(f"  接续数据集 {dataset_id}：{len(mapping)} 篇", flush=True)
    _wait_parsed(client, dataset_id, mapping, wait_seconds)
    return mapping


def _run(client, dataset_id, mapping, queries, *, threshold, keywords_weight, rerank_id, k_recall, k_mrr):
    k_fetch = max(k_recall, k_mrr)
    per_kind: dict[str, dict] = {}
    details = []
    for query in queries:
        result = client.retrieve(
            question=query["q"],
            dataset_ids=[dataset_id],
            document_ids=list(mapping),
            page_size=max(k_fetch * 4, 20),
            similarity_threshold=threshold,
            keywords_similarity_weight=keywords_weight,
            rerank_id=rerank_id,
        )
        ranked: list[str] = []
        scores: dict[str, float] = {}
        for chunk in result.chunks:
            source = mapping.get(chunk.document_id)
            if source and source not in ranked:
                ranked.append(source)
                scores[source] = chunk.similarity
        top_recall = ranked[:k_recall]
        top_mrr = ranked[:k_mrr]
        relevant = set(query["relevant"])
        bucket = per_kind.setdefault(
            query["kind"],
            {"n": 0, "recall": 0.0, "mrr": 0.0, "hit1": 0, "false_pos": 0},
        )
        bucket["n"] += 1
        if relevant:
            found = relevant & set(top_recall)
            bucket["recall"] += len(found) / len(relevant)
            rank = next((i + 1 for i, s in enumerate(top_mrr) if s in relevant), None)
            bucket["mrr"] += 1 / rank if rank else 0.0
            bucket["hit1"] += 1 if top_mrr and top_mrr[0] in relevant else 0
        else:
            bucket["false_pos"] += 1 if top_mrr else 0
        details.append({
            "q": query["q"],
            "kind": query["kind"],
            "relevant": sorted(relevant),
            "top": [(s, round(scores[s], 3)) for s in top_mrr],
        })
    summary = {}
    for kind, b in per_kind.items():
        n = b["n"]
        if kind == "negative":
            summary[kind] = {"n": n, "false_positive_rate": round(b["false_pos"] / n, 3)}
        else:
            summary[kind] = {
                "n": n,
                f"recall@{k_recall}": round(b["recall"] / n, 3),
                f"mrr@{k_mrr}": round(b["mrr"] / n, 3),
                "hit@1": round(b["hit1"] / n, 3),
            }
    return summary, details


def _write_report(path: Path, args, golden, rows, *, live: bool, parse_note: str) -> None:
    k_r, k_m = args.k_recall, args.k_mrr
    lines = [
        f"# 历史标书 RAG 检索评测（{golden['version']}，{'真实 RAGFlow' if live else '离线假服务'}，history_bid）",
        "",
        f"- 文档 {len(golden['documents'])} 篇，查询 {len(golden['queries'])} 条；"
        f"Recall@{k_r} / MRR@{k_m}；rerank={args.rerank_id or '无'}",
        f"- {parse_note}",
        f"- 假服务结果不算质量验收。" if not live else "- 本报告为真实 RAGFlow 跑盘结果。",
        "",
        f"| 阈值 | 关键词权重 | literal recall@{k_r} | literal MRR@{k_m} | "
        f"paraphrase recall@{k_r} | paraphrase MRR@{k_m} | 负例误召回 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        s = row["summary"]
        lit, par, neg = s.get("literal", {}), s.get("paraphrase", {}), s.get("negative", {})
        lines.append(
            f"| {row['threshold']} | {row['keywords_weight']} | "
            f"{lit.get(f'recall@{k_r}', '-')} | {lit.get(f'mrr@{k_m}', '-')} | "
            f"{par.get(f'recall@{k_r}', '-')} | {par.get(f'mrr@{k_m}', '-')} | "
            f"{neg.get('false_positive_rate', '-')} |"
        )

    def score(r):
        s = r["summary"]
        return (
            s.get("paraphrase", {}).get(f"recall@{k_r}", 0)
            + s.get("literal", {}).get(f"recall@{k_r}", 0)
            - s.get("negative", {}).get("false_positive_rate", 0)
        )

    best = max(rows, key=score)
    lines += [
        "",
        f"## 最优组合明细（阈值 {best['threshold']}，关键词权重 {best['keywords_weight']}）",
        "",
        "| 类别 | 查询 | 期望 | 前 k 命中（相似度） |",
        "|---|---|---|---|",
    ]
    for d in best["details"]:
        lines.append(
            f"| {d['kind']} | {d['q']} | {', '.join(d['relevant']) or '（无）'} | "
            f"{', '.join(f'{s}({v})' for s, v in d['top']) or '（无）'} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"报告：{path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--k-recall", type=int, default=5)
    parser.add_argument("--k-mrr", type=int, default=10)
    parser.add_argument("--thresholds", default="0.3,0.45")
    parser.add_argument("--weights", default="0.3,0.5")
    parser.add_argument("--rerank-id", default=os.environ.get("ICG_KB_RERANK_ID") or None)
    parser.add_argument("--wait", type=int, default=3600)
    parser.add_argument("--report", help="Markdown 报告路径")
    parser.add_argument("--llm-id", default=os.environ.get("ICG_KB_LLM_ID", ""))
    parser.add_argument("--embedding-model", default=os.environ.get("ICG_KB_EMBEDDING_MODEL") or None)
    parser.add_argument("--dataset-id", default="")
    parser.add_argument("--pipeline-id", default="")
    args = parser.parse_args()

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    docs = _load_docs(golden, live=args.live)
    client, _fake = _client(args.live)
    print(
        f"模式：{'真实 RAGFlow ' + client.base_url if args.live else '离线假服务'}；"
        f"文档 {len(docs)}，查询 {len(golden['queries'])}；"
        f"Recall@{args.k_recall} / MRR@{args.k_mrr}",
        flush=True,
    )

    pipeline_id = args.pipeline_id
    if args.dataset_id:
        dataset_id = args.dataset_id
        mapping = _attach(client, dataset_id, docs, args.wait)
    else:
        dataset_id, pipeline_id, mapping = _ingest(
            client, docs, args.wait, args.embedding_model, args.llm_id
        )

    synced = len(mapping)
    listed = client.list_documents(dataset_id, page_size=100)
    failed = sum(1 for d in listed if d.id in mapping and d.sync_status == "failed")
    parse_note = f"摄入映射 {synced} 篇；远端失败标记 {failed} 篇"

    rows = []
    try:
        for threshold in [float(x) for x in args.thresholds.split(",")]:
            for weight in [float(x) for x in args.weights.split(",")]:
                summary, details = _run(
                    client,
                    dataset_id,
                    mapping,
                    golden["queries"],
                    threshold=threshold,
                    keywords_weight=weight,
                    rerank_id=args.rerank_id,
                    k_recall=args.k_recall,
                    k_mrr=args.k_mrr,
                )
                rows.append({
                    "threshold": threshold,
                    "keywords_weight": weight,
                    "summary": summary,
                    "details": details,
                })
                print(json.dumps({"threshold": threshold, "keywords_weight": weight, **summary}, ensure_ascii=False))
    finally:
        if args.live and not args.keep and not args.dataset_id:
            try:
                client._send_request("DELETE", client.datasets_url, json_body={"ids": [dataset_id]})
                print(f"已删除临时数据集 {dataset_id}")
                if pipeline_id:
                    client.delete_agent(pipeline_id)
                    print(f"已删除临时摄入流程 {pipeline_id}")
            except Exception as exc:
                print(f"清理失败：{type(exc).__name__}，请手动清理 {dataset_id}")

    if args.report:
        _write_report(Path(args.report), args, golden, rows, live=args.live, parse_note=parse_note)


if __name__ == "__main__":
    main()
