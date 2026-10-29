# 为什么有这个文件：手动运行的真实环境验收：把真实扫描件经应用 API 上传、交给真实 RAGFlow 解析并抽取条款。
# 它解决什么问题：假 RAGFlow 只能证明流程通，识别质量和页码只能在真实服务上看。不进 CI（需要 ICG_RAGFLOW_*）。
# 运行：ICG_RAGFLOW_BASE_URL=… ICG_RAGFLOW_API_KEY=… ICG_KB_EMBEDDING_MODEL=… python tests/backend/live_scan_e2e.py

import os
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("ICG_TENDER_REMOTE_WAIT", "1500")
os.environ.setdefault("ICG_KB_SYNC_INLINE", "1")

from fastapi.testclient import TestClient  # noqa: E402

from icg_demo.main import create_app  # noqa: E402
from test_reference_flow import ProjectFlow  # noqa: E402

SCAN = Path(__file__).parents[1] / "fixtures" / "tenders" / "guiyang-2025-scan.pdf"


def main() -> None:
    with TestClient(create_app()) as client:
        flow = ProjectFlow(client)
        data = SCAN.read_bytes()
        headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4()),
                   "Content-Type": "application/octet-stream"}
        started = time.time()
        resp = client.post(f"{flow.path}/files/raw", params={"filename": SCAN.name}, content=data, headers=headers)
        print("upload", resp.status_code, f"{len(data) / 1024 / 1024:.1f}MB", flush=True)
        for attempt in range(3):
            result = client.post(f"{flow.path}/parse", json={}, headers={
                **flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
            record = flow.state()["files"][0]
            print("parse", attempt, result.status_code, record["status"], record["warnings"][:1], f"{time.time() - started:.0f}s", flush=True)
            if record["status"] != "parsing_remote":
                break
        state = flow.state()
        print("pages", record.get("page_count"), "pagination", record.get("pagination"), "extraction", record.get("extraction"))
        kinds = {}
        for row in state["requirements"]:
            kinds[row["category"]] = kinds.get(row["category"], 0) + 1
        print("requirements", len(state["requirements"]), kinds)
        print("facts", [(f["key"], f["value"]) for f in state["facts"]])
        for row in state["requirements"][:12]:
            print(" ", row["source"]["page"], row["category"], row["text"][:70].replace("\n", " "))
        kb = client.app.state.service.knowledge_base
        index = client.app.state.service.repository.read().service_stores.get("kb_index", {}).get("alpha", {})
        info = index.get("tender_dataset") or {}
        print("tender dataset", info)
        if os.environ.get("KEEP") != "1" and info.get("dataset_id"):
            c = kb.client_for("alpha")
            c.delete_datasets([info["dataset_id"]])
            if info.get("pipeline_id"):
                c.delete_agent(info["pipeline_id"])
            print("cleaned up remote dataset and pipeline")


if __name__ == "__main__":
    main()
