# temporary E2E: new project → parse (RAG matrix) → confirm → section generate → export
from __future__ import annotations

import collections
import json
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8710"
TENDER = Path(
    r"C:\Users\徐佳馨\xwechat_files\wxid_pa7w4dqzpwsr22_4002\msg\attach"
    r"\9e20f478899dc29eb19741386f9343c8\2026-11\Rec\139f784a39cf362f\F\1"
    r"\昆明航空Oracle数据库一体机软硬件维保和DBA服.doc"
)
OUT = Path(r"e:\ICG-CURSOR\if-children-have-been-grown-1\docs\testing\2026-11-05-tv-e2e-evidence.json")
PROGRESS = Path(r"e:\ICG-CURSOR\if-children-have-been-grown-1\docs\testing\_tv_e2e_progress.json")


def save(evidence: dict) -> None:
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    evidence = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"steps": [], "bugs": []}
    evidence.setdefault("steps", [])
    evidence.setdefault("bugs", [])
    c = httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0))
    tok = c.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": "alpha-company-admin", "password": "X_2026"},
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # model configs
    mc = c.get(f"{BASE}/api/v1/model-configs", headers=h).json()
    print("models", json.dumps(mc, ensure_ascii=False)[:500], flush=True)
    evidence["model_configs"] = mc

    # Matrix/generation use history+materials via kb.search; knowledge-base/search
    # defaults to evidence+snippet+history and mixes datasets (RagflowBusinessError).
    s = c.post(
        f"{BASE}/api/v1/kb-admin/retrieval-test",
        headers=h,
        json={"query": "Oracle数据库维保巡检", "limit": 3, "kinds": ["history", "materials"]},
        timeout=90,
    )
    sj = s.json() if s.status_code == 200 else {}
    print("search", s.status_code, "n", len(sj.get("items") or []), "skip", sj.get("skipped_reason"), flush=True)
    evidence["steps"].append(
        {
            "search_v2": s.status_code,
            "n": len(sj.get("items") or []),
            "skip": sj.get("skipped_reason"),
            "note": "kb-admin retrieval-test history+materials",
        }
    )
    if s.status_code != 200 or not sj.get("items"):
        evidence["bugs"].append(f"dual-kb search still broken: {s.status_code} {s.text[:200]}")
        save(evidence)
        raise SystemExit(1)

    create = c.post(
        f"{BASE}/api/v1/projects",
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
        json={"name": "昆明航空Oracle一体机维保-E2E重跑", "volume_mode": "technical_only"},
        timeout=60,
    )
    print("create", create.status_code, create.text[:300], flush=True)
    evidence["steps"].append({"create2": create.status_code, "body": create.text[:300]})
    if create.status_code >= 400:
        evidence["bugs"].append(f"create fail: {create.text[:200]}")
        save(evidence)
        raise SystemExit(1)
    cj = create.json()
    pid = cj.get("id") or (cj.get("project") or {}).get("id")
    rev = cj.get("revision") or (cj.get("project") or {}).get("revision") or 1
    evidence["project_id_v2"] = pid
    print("pid", pid, flush=True)

    patch = c.patch(
        f"{BASE}/api/v1/projects/{pid}",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={"tender_number": "KM-E2E-2026-1105B", "sensitive": False},
        timeout=60,
    )
    print("patch", patch.status_code, flush=True)
    evidence["steps"].append({"patch2": patch.status_code})
    if patch.status_code < 400:
        rev = patch.json().get("revision") or rev + 1

    raw = TENDER.read_bytes()
    up = c.post(
        f"{BASE}/api/v1/projects/{pid}/files/raw",
        headers={
            **h,
            "Idempotency-Key": str(uuid.uuid4()),
            "If-Match": str(rev),
            "Content-Type": "application/msword",
        },
        params={"filename": TENDER.name, "role": "tender"},
        content=raw,
        timeout=180,
    )
    print("upload", up.status_code, up.text[:250], flush=True)
    evidence["steps"].append({"tender_upload2": up.status_code, "body": up.text[:300]})
    if up.status_code >= 400:
        evidence["bugs"].append(f"tender upload2 fail: {up.text[:200]}")
        save(evidence)
        raise SystemExit(1)
    rev = up.json().get("revision") or rev + 1

    parse = c.post(
        f"{BASE}/api/v1/projects/{pid}/parse",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={},
        timeout=180,
    )
    print("parse", parse.status_code, parse.text[:300], flush=True)
    evidence["steps"].append({"parse2": parse.status_code, "body": parse.text[:300]})
    if parse.status_code >= 400:
        evidence["bugs"].append(f"parse2 fail: {parse.text[:200]}")
        save(evidence)
        raise SystemExit(1)
    jid = parse.json().get("id") or (parse.json().get("job") or {}).get("id")
    for i in range(600):
        j = c.get(f"{BASE}/api/v1/jobs/{jid}", headers=h).json()
        print(i, j.get("status"), j.get("progress"), str(j.get("message") or "")[:180], flush=True)
        if j.get("status") in ("completed", "failed", "cancelled"):
            evidence["parse_job2"] = {k: j.get(k) for k in ("status", "progress", "message", "error")}
            break
        time.sleep(5)
    if (evidence.get("parse_job2") or {}).get("status") != "completed":
        evidence["bugs"].append("parse2 not completed")
        save(evidence)
        raise SystemExit(2)

    ws = c.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=120).json()
    reqs = [r for r in (ws.get("requirements") or []) if r.get("technical_clause")]
    origins = collections.Counter(str(r.get("response_origin")) for r in reqs)
    writable = sum(
        1
        for r in reqs
        if r.get("response_origin") not in ("", "retrieval_failed", "draft_failed", "no_evidence")
        and str(r.get("response") or "").strip()
    )
    print("origins", origins, "writable", writable, "/", len(reqs), flush=True)
    evidence["matrix_v2"] = {"origins": dict(origins), "writable": writable, "total": len(reqs)}
    evidence["matrix_samples_v2"] = [
        {k: r.get(k) for k in ("text", "response", "response_origin", "response_type", "history_filename")}
        for r in reqs
        if r.get("response_origin") == "history"
    ][:5]
    save(evidence)
    if writable == 0:
        evidence["bugs"].append("matrix still unwritable after fresh parse with search working")
        save(evidence)
        raise SystemExit(3)

    outline = ws.get("technical_outline") or {}
    chapter_id = outline["chapter_id"]
    leaves = [h for h in (outline.get("headings") or []) if h.get("requirement_id")]
    rev = ws["revision"]
    plan = c.post(
        f"{BASE}/api/v1/projects/{pid}/plan",
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
    print("confirm", plan.status_code, plan.text[:250], flush=True)
    evidence["steps"].append({"confirm2": plan.status_code, "body": plan.text[:300]})
    if plan.status_code >= 400:
        evidence["bugs"].append(f"confirm2 fail: {plan.text[:200]}")
        save(evidence)
        raise SystemExit(4)

    # section-by-section generate (sync HTTP, long timeout each)
    done_titles: list[str] = []
    failed_titles: list[str] = []
    gen_client = httpx.Client(timeout=httpx.Timeout(900.0, connect=30.0))
    for idx, leaf in enumerate(leaves):
        title = leaf.get("title") or ""
        ws = gen_client.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=120).json()
        rev = ws["revision"]
        print(f"GEN {idx+1}/{len(leaves)} {title}", flush=True)
        t0 = time.time()
        try:
            gen = gen_client.post(
                f"{BASE}/api/v1/projects/{pid}/generate",
                headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
                json={"section": title},
                timeout=900,
            )
        except Exception as exc:
            print("  EXC", type(exc).__name__, exc, flush=True)
            failed_titles.append(title)
            evidence["bugs"].append(f"generate section timeout/err: {title}: {exc}")
            save(evidence)
            continue
        elapsed = round(time.time() - t0, 1)
        print("  ", gen.status_code, f"{elapsed}s", gen.text[:220], flush=True)
        if gen.status_code >= 400:
            failed_titles.append(title)
            evidence["bugs"].append(f"generate section fail {title}: {gen.text[:180]}")
        else:
            done_titles.append(title)
            msg = ((gen.json().get("job") or {}).get("message") or "")[:160]
            print("  msg", msg, flush=True)
        PROGRESS.write_text(
            json.dumps(
                {"pid": pid, "done": len(done_titles), "failed": failed_titles, "total": len(leaves), "last": title},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if (idx + 1) % 5 == 0:
            ws = gen_client.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=120).json()
            ch = next((x for x in (ws.get("chapters") or []) if x.get("id") == chapter_id), None)
            print("  interim chars", len((ch or {}).get("content") or ""), flush=True)
            evidence["content_chars_v2"] = len((ch or {}).get("content") or "")
            evidence["gen_progress"] = {"done": len(done_titles), "failed": len(failed_titles), "total": len(leaves)}
            save(evidence)

    ws = gen_client.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=180).json()
    evidence["technical_quality_v2"] = ws.get("technical_quality")
    evidence["technical_rag_audit_v2"] = ws.get("technical_rag_audit")
    evidence["gen_progress"] = {"done": len(done_titles), "failed": failed_titles, "total": len(leaves)}
    ch = next((x for x in (ws.get("chapters") or []) if x.get("id") == chapter_id), None)
    content = (ch or {}).get("content") or ""
    evidence["content_chars_v2"] = len(content)
    evidence["content_head_v2"] = content[:3000]
    evidence["content_has_table_v2"] = "|" in content
    print("quality", json.dumps(ws.get("technical_quality"), ensure_ascii=False)[:700], flush=True)
    print("chars", len(content), "rag_audit", len(ws.get("technical_rag_audit") or []), flush=True)

    rev = ws["revision"]
    exp = gen_client.post(
        f"{BASE}/api/v1/projects/{pid}/exports",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
        timeout=300,
    )
    print("export", exp.status_code, exp.text[:400], flush=True)
    evidence["steps"].append({"export_v2": exp.status_code, "body": exp.text[:400]})
    if exp.status_code < 400:
        ej = exp.json()
        evidence["export_v2"] = ej
        eid = ej.get("id") or (ej.get("export") or {}).get("id")
        ejid = (ej.get("job") or {}).get("id")
        if ejid:
            for i in range(120):
                j = gen_client.get(f"{BASE}/api/v1/jobs/{ejid}", headers=h).json()
                print("expjob", i, j.get("status"), flush=True)
                if j.get("status") in ("completed", "failed", "cancelled"):
                    break
                time.sleep(2)
            ws = gen_client.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h).json()
            exports = ws.get("exports") or []
            if exports and not eid:
                eid = exports[-1].get("id")
        if eid:
            for url in (
                f"{BASE}/api/v1/exports/{eid}/download",
                f"{BASE}/api/v1/projects/{pid}/exports/{eid}/technical",
            ):
                dl = gen_client.get(url, headers=h, timeout=180)
                print("download", url.rsplit("/", 1)[-1], dl.status_code, len(dl.content), flush=True)
                if dl.status_code == 200 and len(dl.content) > 1000:
                    p = OUT.with_suffix(".docx")
                    p.write_bytes(dl.content)
                    evidence["saved_docx"] = str(p)
                    evidence["download_bytes"] = len(dl.content)
                    break
    else:
        evidence["bugs"].append(f"export_v2 fail: {exp.text[:250]}")

    if evidence.get("saved_docx"):
        evidence["bugs"] = [b for b in evidence.get("bugs") or [] if "export" not in b.lower()]

    save(evidence)
    print("WROTE", OUT, flush=True)
    print("BUGS", evidence.get("bugs"), flush=True)


if __name__ == "__main__":
    main()
