"""ISSUE-054 最终真机闭环：既有昆明航空项目全量技术卷生成、导出与实证扫描。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".audit" / "final-round-v2"
OUT.mkdir(parents=True, exist_ok=True)
BUSINESS_WORDS = ["联合体", "转包", "分包", "投标文件份数", "报名材料", "资格条件", "投标有效期", "保证金"]
FOREIGN_WORDS = ["华为", "H3C", "新华三", "浪潮", "曙光", "联想", "Dell", "IBM", "历史做法", "乐山", "甘肃", "农信", "人民医院", "安康", "星河"]


def login(base: str) -> dict[str, str]:
    response = requests.post(base + "/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"}, timeout=15)
    response.raise_for_status()
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def expect_ok(response: requests.Response, label: str) -> requests.Response:
    if response.status_code >= 400:
        raise RuntimeError(f"{label}: HTTP {response.status_code} {response.text[:600]}")
    return response


def stream_generate(base: str, headers: dict[str, str], project_id: str, revision: int) -> dict:
    key = "final-round-v2-" + uuid.uuid4().hex
    h = {**headers, "If-Match": str(revision), "Idempotency-Key": key, "Accept": "text/event-stream"}
    started = time.time()
    events = []
    done = None
    with requests.post(f"{base}/api/v1/projects/{project_id}/technical-volume/stream", headers=h, json={}, stream=True, timeout=(15, 7200)) as response:
        expect_ok(response, "technical stream")
        event = ""
        for raw in response.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.rstrip("\r")
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                kind = payload.get("event") or event
                events.append({"event": kind, **payload})
                if kind in {"volume.done", "volume.failed", "volume.cancelled"}:
                    done = payload
                    break
    elapsed = time.time() - started
    (OUT / "generation-events.json").write_text(json.dumps({"elapsed_seconds": elapsed, "events": events, "done": done}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not done or done.get("event") != "volume.done":
        raise RuntimeError("generation did not finish cleanly: " + json.dumps(done, ensure_ascii=False))
    return {"elapsed_seconds": elapsed, "event_count": len(events), "done": done}


def docx_text(blob: bytes, path: Path) -> str:
    path.write_bytes(blob)
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    return re.sub(r"<[^>]+>", "", xml)


def xlsx_text(blob: bytes, path: Path) -> str:
    path.write_bytes(blob)
    out = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith(".xml") and ("sheet" in name or "sharedStrings" in name):
                out.append(zf.read(name).decode("utf-8", errors="ignore"))
    return re.sub(r"<[^>]+>", "", "\n".join(out))


def scan(label: str, text: str) -> dict:
    dirty = [m for m in ("```", "<br>", "**", "【待确认】") if m in text]
    foreign = [m for m in FOREIGN_WORDS if m in text]
    comma_trunc = bool(re.search(r"[,，、]\s*$", text.strip()))
    return {
        "label": label,
        "chars": len(text),
        "pending_placeholders": text.count("【待补】"),
        "manual_placeholders": text.count("[待人工补充"),
        "dirty_markers": dirty,
        "foreign_or_history_hits": foreign,
        "comma_truncated_tail": comma_trunc,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8710")
    parser.add_argument("--project", default="project-78884aacf9e546fdaa6871ae06510662")
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()
    headers = login(args.base)
    workspace = expect_ok(requests.get(f"{args.base}/api/v1/projects/{args.project}/workspace", headers=headers, timeout=20), "workspace").json()
    pre = {
        "revision": workspace.get("revision"),
        "outline_source": workspace.get("outline_source"),
        "outline_reason": workspace.get("outline_reason"),
        "headings": len((workspace.get("technical_outline") or {}).get("headings") or []),
        "global_fact_sheet": bool(workspace.get("global_fact_sheet")),
        "plan_confirmed": workspace.get("plan_confirmed"),
        "business_intercepted": workspace.get("business_intercepted_requirements") or [],
    }
    heading_text = "\n".join(str(h.get("title") or "") for h in (workspace.get("technical_outline") or {}).get("headings") or [])
    pre["business_heading_hits"] = [word for word in BUSINESS_WORDS if word in heading_text]
    generation = {"skipped": True}
    if not args.skip_generate:
        generation = stream_generate(args.base, headers, args.project, int(workspace["revision"]))
        workspace = expect_ok(requests.get(f"{args.base}/api/v1/projects/{args.project}/workspace", headers=headers, timeout=20), "workspace-after").json()
    revision = int(workspace["revision"])
    # internal 验收导出使用固定 internal check_id；阻断级废标检查另行走 submission 门禁。
    check = {"id": "technical-internal", "revision": revision}
    revision = int(check.get("revision", revision))
    exported = expect_ok(requests.post(f"{args.base}/api/v1/projects/{args.project}/exports", headers={**headers, "If-Match": str(revision), "Idempotency-Key": "final-export-" + uuid.uuid4().hex}, json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"}, timeout=180), "export").json()
    exp = exported.get("export") or {}
    export_id = exp.get("id") or exported.get("id") or ""
    # 下载正文；偏离表接口在导出记录 URL 后加 /deviation（与既有测试一致）。
    tech_url = (exp.get("volumes") or [{}])[0].get("download_url") or f"/api/v1/projects/{args.project}/exports/{export_id}/technical"
    tech_blob = expect_ok(requests.get(args.base + tech_url, headers=headers, timeout=60), "download technical").content
    deviation_url = tech_url.rsplit("/", 1)[0] + "/deviation"
    deviation_resp = requests.get(args.base + deviation_url, headers=headers, timeout=60)
    deviation_blob = deviation_resp.content if deviation_resp.status_code == 200 else b""
    trace_blob = expect_ok(requests.get(f"{args.base}/api/v1/projects/{args.project}/response-trace.xlsx?volume=technical", headers=headers, timeout=60), "response trace").content
    tech_text = docx_text(tech_blob, OUT / "technical.docx")
    deviation_text = docx_text(deviation_blob, OUT / "技术偏离表.docx") if deviation_blob else ""
    trace_text = xlsx_text(trace_blob, OUT / "response-trace-technical.xlsx")
    audits = workspace.get("technical_rag_audit") or []
    history_routes = []
    for audit in audits:
        for route in (audit or {}).get("routes") or []:
            if route.get("route") == "history":
                history_routes.append({"query": route.get("query"), "status": route.get("status"), "post_filter_hits": route.get("post_filter_hits"), "raw_hits": route.get("raw_hits"), "error_detail": route.get("error_detail")})
    report = {
        "project_id": args.project,
        "preflight": pre,
        "generation": generation,
        "workspace": {
            "revision": revision,
            "writer_model": workspace.get("writer_model"),
            "technical_deviation_note": workspace.get("technical_deviation_note"),
            "audit_rows": len(audits),
            "history_route_nonempty_queries": sum(1 for r in history_routes if str(r.get("query") or "").strip()),
            "history_route_ok_positive": sum(1 for r in history_routes if r.get("status") == "ok" and int(r.get("post_filter_hits") or 0) > 0),
        }
        ,
        "history_routes_sample": history_routes[:12],
        "scan": [scan("technical.docx", tech_text), scan("技术偏离表.docx", deviation_text), scan("response-trace-technical.xlsx", trace_text)],
        "files": {"technical_bytes": len(tech_blob), "deviation_bytes": len(deviation_blob), "trace_bytes": len(trace_blob)},
    }
    (OUT / "final-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
