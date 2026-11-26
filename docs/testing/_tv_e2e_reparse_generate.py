# temporary E2E helper: reparse matrix → generate → export
from __future__ import annotations

import collections
import json
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8710"
PID = "project-87155d2134154f66b4af8d6c8a140392"
OUT = Path(r"e:\ICG-CURSOR\if-children-have-been-grown-1\docs\testing\2026-11-05-tv-e2e-evidence.json")


def main() -> None:
    evidence = json.loads(OUT.read_text(encoding="utf-8"))
    c = httpx.Client(timeout=180.0)
    tok = c.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": "alpha-company-admin", "password": "X_2026"},
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    s = c.post(
        f"{BASE}/api/v1/knowledge-base/search",
        headers=h,
        json={"query": "Oracle数据库维保巡检", "limit": 3, "kinds": ["history", "materials"]},
        timeout=90,
    )
    print("search_ok", s.status_code, "items", len((s.json() or {}).get("items") or []), "skip", (s.json() or {}).get("skipped_reason"), flush=True)
    evidence["steps"].append(
        {
            "search_after_rerank_clear": s.status_code,
            "n": len((s.json() or {}).get("items") or []),
            "skip": (s.json() or {}).get("skipped_reason"),
        }
    )

    ws = c.get(f"{BASE}/api/v1/projects/{PID}/workspace", headers=h).json()
    rev = ws["revision"]
    print("reparse rev", rev, flush=True)
    parse = c.post(
        f"{BASE}/api/v1/projects/{PID}/parse",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={},
        timeout=180,
    )
    print("parse", parse.status_code, parse.text[:350], flush=True)
    evidence["steps"].append({"reparse": parse.status_code, "body": parse.text[:400]})
    same_source = parse.status_code == 409 and "SAME_SOURCE" in (parse.text or "")
    if parse.status_code >= 400 and not same_source:
        evidence["bugs"].append(f"reparse fail: {parse.text[:250]}")
        OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(1)
    if same_source:
        print("reparse skipped: already extracted; continue confirm → generate → export", flush=True)
        evidence["reparse_job"] = {"status": "skipped", "message": "SAME_SOURCE_FILES"}
        evidence["bugs"] = [b for b in evidence.get("bugs") or [] if "reparse fail" not in b]
    else:
        jid = parse.json().get("id") or (parse.json().get("job") or {}).get("id")
        for i in range(240):
            j = c.get(f"{BASE}/api/v1/jobs/{jid}", headers=h).json()
            st = j.get("status")
            print(i, st, j.get("progress"), str(j.get("message") or "")[:160], flush=True)
            if st in ("completed", "failed", "cancelled"):
                evidence["reparse_job"] = {k: j.get(k) for k in ("status", "progress", "message", "error")}
                break
            time.sleep(3)

    ws = c.get(f"{BASE}/api/v1/projects/{PID}/workspace", headers=h, timeout=120).json()
    reqs = ws.get("requirements") or []
    tech = [r for r in reqs if r.get("technical_clause")]
    origins = collections.Counter(str(r.get("response_origin")) for r in tech)
    writable = sum(
        1
        for r in tech
        if r.get("response_origin") not in ("", "retrieval_failed", "draft_failed", "no_evidence")
        and str(r.get("response") or "").strip()
    )
    print("origins", origins, "writable", writable, "/", len(tech), flush=True)
    evidence["matrix_after_reparse"] = {"origins": dict(origins), "writable": writable, "total": len(tech)}
    filled = [r for r in tech if r.get("response_origin") == "history"][:3]
    evidence["matrix_samples"] = [
        {k: r.get(k) for k in ("id", "text", "response", "response_origin", "response_type", "history_filename")}
        for r in filled
    ]
    print("samples", json.dumps(evidence["matrix_samples"], ensure_ascii=False)[:800], flush=True)

    if writable == 0:
        # 矩阵不是生成闸门：可继续确认目录与生成（节可能标待补）。
        evidence["bugs"].append("matrix writable=0 (non-blocking; continue generate)")
        print("WARN matrix writable=0; continue anyway", flush=True)

    outline = ws.get("technical_outline") or {}
    if not outline.get("headings") or not outline.get("chapter_id"):
        evidence["bugs"].append("no technical outline after parse")
        OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(2)

    chapter_id = outline["chapter_id"]
    rev = ws["revision"]
    # ensure outline confirmed
    if not ws.get("plan_confirmed"):
        plan = c.post(
            f"{BASE}/api/v1/projects/{PID}/plan",
            headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
            json={
                "scope": "technical",
                "chapters": [
                    {
                        "id": chapter_id,
                        "title": outline.get("title") or "技术方案",
                        "volume": "technical",
                        "fact_ids": [],
                        "writing_points": "",
                    }
                ],
                "outline_title": outline.get("title") or "技术方案",
                "outline_headings": [
                    {
                        "level": i.get("level") or 2,
                        "title": i.get("title"),
                        "requirement_id": i.get("requirement_id"),
                    }
                    for i in outline.get("headings") or []
                ],
                "confirm_outline": True,
            },
            timeout=180,
        )
        print("confirm", plan.status_code, plan.text[:300], flush=True)
        evidence["steps"].append({"reconfirm": plan.status_code, "body": plan.text[:300]})
        if plan.status_code >= 400:
            evidence["bugs"].append(f"reconfirm fail: {plan.text[:250]}")
            OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit(3)
        ws = c.get(f"{BASE}/api/v1/projects/{PID}/workspace", headers=h).json()
        rev = ws["revision"]

    print("generate start writable", writable, flush=True)
    gen = c.post(
        f"{BASE}/api/v1/projects/{PID}/generate",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={},
        timeout=180,
    )
    print("generate", gen.status_code, gen.text[:400], flush=True)
    evidence["steps"].append({"regenerate": gen.status_code, "body": gen.text[:500]})
    if gen.status_code >= 400:
        evidence["bugs"].append(f"regenerate fail: {gen.text[:250]}")
        OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(4)
    gjid = (gen.json().get("job") or {}).get("id") or gen.json().get("id")
    print("gid", gjid, flush=True)
    for i in range(720):
        j = c.get(f"{BASE}/api/v1/jobs/{gjid}", headers=h).json()
        print(i, j.get("status"), j.get("progress"), str(j.get("message") or j.get("error") or "")[:200], flush=True)
        if j.get("status") in ("completed", "failed", "cancelled"):
            evidence["generate_job2"] = {k: j.get(k) for k in ("status", "progress", "message", "error")}
            break
        time.sleep(5)

    ws = c.get(f"{BASE}/api/v1/projects/{PID}/workspace", headers=h, timeout=180).json()
    evidence["technical_quality"] = ws.get("technical_quality")
    evidence["technical_rag_audit"] = ws.get("technical_rag_audit")
    ch = next((x for x in (ws.get("chapters") or []) if x.get("id") == chapter_id), None)
    content = (ch or {}).get("content") or ""
    evidence["content_chars"] = len(content)
    evidence["content_head"] = content[:2500]
    evidence["content_has_table"] = "|" in content
    print("quality", json.dumps(ws.get("technical_quality"), ensure_ascii=False)[:600], flush=True)
    print("chars", len(content), flush=True)
    print("rag_audit_n", len(ws.get("technical_rag_audit") or []), flush=True)

    rev = ws["revision"]
    exp = c.post(
        f"{BASE}/api/v1/projects/{PID}/exports",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
        timeout=300,
    )
    print("export", exp.status_code, exp.text[:400], flush=True)
    evidence["steps"].append({"export_internal": exp.status_code, "body": exp.text[:400]})
    if exp.status_code < 400:
        ej = exp.json()
        evidence["export"] = ej
        body = ej.get("export") if isinstance(ej.get("export"), dict) else ej
        eid = (body or {}).get("id") or ej.get("id")
        urls = [
            row.get("download_url")
            for row in ((body or {}).get("volumes") or [])
            if row.get("download_url")
        ]
        if not urls and eid:
            urls = [f"/api/v1/projects/{PID}/exports/{eid}/technical"]
        for path in urls:
            dl = c.get(BASE + path if path.startswith("/") else path, headers=h, timeout=180)
            print("download", path, dl.status_code, len(dl.content), flush=True)
            evidence["download_status"] = dl.status_code
            evidence["download_bytes"] = len(dl.content)
            if dl.status_code == 200 and len(dl.content) > 1000:
                p = OUT.with_suffix(".docx")
                p.write_bytes(dl.content)
                evidence["saved_docx"] = str(p)
                break
    else:
        evidence["bugs"].append(f"export fail: {exp.text[:250]}")

    # strip stale export fail bugs if later succeeded
    if evidence.get("saved_docx"):
        evidence["bugs"] = [b for b in evidence.get("bugs") or [] if "export fail" not in b]

    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", OUT, flush=True)
    print("BUGS", evidence.get("bugs"), flush=True)


if __name__ == "__main__":
    main()
