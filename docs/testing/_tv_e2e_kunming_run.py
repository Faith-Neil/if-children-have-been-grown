# 昆明航空 .doc 主路径冒烟：建项→上传→parse/jobs→确认→整册生成→内部稿导出；过程写入 evidence + blockers。
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
OUT = Path(__file__).with_name("2026-11-05-kunming-oracle-e2e-run.json")
BLOCKERS = Path(__file__).with_name("2026-11-05-kunming-oracle-e2e-blockers.md")


def dump(data: dict) -> None:
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def note(data: dict, severity: str, title: str, detail: str) -> None:
    data.setdefault("blockers", []).append({"severity": severity, "title": title, "detail": detail})
    print(f"[{severity}] {title}: {detail[:200]}", flush=True)


def main() -> None:
    data: dict = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tender": str(TENDER),
        "tender_bytes": TENDER.stat().st_size if TENDER.exists() else 0,
        "steps": [],
        "blockers": [],
        "progress_samples": [],
    }
    if not TENDER.exists():
        note(data, "高", "招标原件不存在", str(TENDER))
        dump(data)
        raise SystemExit(1)

    c = httpx.Client(timeout=httpx.Timeout(900.0, connect=30.0))
    health = c.get(f"{BASE}/health").json()
    data["health"] = health
    print("health", health, flush=True)
    if health.get("effective_model", health.get("model")) == "mock":
        note(data, "高", "当前 effective_model=mock", "分节/大纲 LLM 为替身，正文质量不能当作生产可用")
    elif health.get("model") == "mock" and health.get("effective_model") == "company_real":
        note(data, "中", "进程 model=mock 但公司已配真实模型", "以 effective_model=company_real 为准，勿只看 model")
    if not health.get("persistent"):
        note(data, "高", "非持久化仓储", str(health))

    login = c.post(f"{BASE}/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"})
    data["steps"].append({"login": login.status_code})
    if login.status_code >= 400:
        note(data, "高", "登录失败", login.text[:300])
        dump(data)
        raise SystemExit(2)
    tok = login.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # 知识库探针
    search = c.post(
        f"{BASE}/api/v1/kb-admin/retrieval-test",
        headers=h,
        json={"query": "Oracle数据库维保巡检", "limit": 3, "kinds": ["history", "materials"]},
        timeout=90,
    )
    sj = search.json() if search.status_code == 200 else {}
    data["steps"].append(
        {"kb_search": search.status_code, "n": len(sj.get("items") or []), "skip": sj.get("skipped_reason")}
    )
    print("kb", search.status_code, "n", len(sj.get("items") or []), "skip", sj.get("skipped_reason"), flush=True)
    if search.status_code != 200 or not sj.get("items"):
        note(
            data,
            "高",
            "历史标+材料库检索不可用",
            f"{search.status_code} skip={sj.get('skipped_reason')} body={search.text[:200]}",
        )

    create = c.post(
        f"{BASE}/api/v1/projects",
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
        json={"name": "Kunming-Oracle-E2E-API-1105B", "volume_mode": "technical_only"},
        timeout=60,
    )
    data["steps"].append({"create": create.status_code, "body": create.text[:300]})
    print("create", create.status_code, create.text[:200], flush=True)
    if create.status_code >= 400:
        note(data, "高", "创建项目失败", create.text[:300])
        dump(data)
        raise SystemExit(3)
    cj = create.json()
    pid = cj.get("id") or (cj.get("project") or {}).get("id")
    rev = cj.get("revision") or (cj.get("project") or {}).get("revision") or 1
    data["project_id"] = pid

    patch = c.patch(
        f"{BASE}/api/v1/projects/{pid}",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={"tender_number": "KM-E2E-2026-1105C", "sensitive": False},
        timeout=60,
    )
    data["steps"].append({"patch": patch.status_code})
    if patch.status_code < 400:
        rev = patch.json().get("revision") or rev + 1
    else:
        note(data, "中", "项目补丁失败（标号/涉密）", patch.text[:200])

    up = c.post(
        f"{BASE}/api/v1/projects/{pid}/files/raw",
        headers={
            **h,
            "Idempotency-Key": str(uuid.uuid4()),
            "If-Match": str(rev),
            "Content-Type": "application/msword",
        },
        params={"filename": TENDER.name, "file_role": "tender"},
        content=TENDER.read_bytes(),
        timeout=180,
    )
    data["steps"].append({"upload": up.status_code, "body": up.text[:300]})
    print("upload", up.status_code, flush=True)
    if up.status_code >= 400:
        note(data, "高", "招标文件上传失败", up.text[:300])
        dump(data)
        raise SystemExit(4)
    rev = up.json().get("revision") or rev + 1

    parse = c.post(
        f"{BASE}/api/v1/projects/{pid}/parse/jobs",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={},
        timeout=60,
    )
    data["steps"].append({"parse_jobs": parse.status_code, "body": parse.text[:400]})
    print("parse_jobs", parse.status_code, parse.text[:220], flush=True)
    if parse.status_code >= 400:
        note(data, "高", "启动解析任务失败", parse.text[:300])
        dump(data)
        raise SystemExit(5)
    jid = parse.json()["id"]
    data["parse_job_id"] = jid

    stuck5 = 0
    t0 = time.monotonic()
    for i in range(360):  # 最长约 30 分钟
        j = c.get(f"{BASE}/api/v1/jobs/{jid}", headers=h).json()
        sample = {
            "i": i,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "status": j.get("status"),
            "progress": j.get("progress"),
            "message": (j.get("message") or "")[:200],
        }
        if i < 3 or i % 6 == 0 or j.get("status") in ("completed", "failed", "cancelled"):
            data["progress_samples"].append(sample)
            print(sample["elapsed_s"], sample["status"], sample["progress"], sample["message"], flush=True)
        if j.get("progress") == 5 and "提取文字" in str(j.get("message") or ""):
            stuck5 += 1
        if j.get("status") in ("completed", "failed", "cancelled"):
            data["parse_job"] = {k: j.get(k) for k in ("status", "progress", "message", "error")}
            break
        time.sleep(5)
        if i % 12 == 0:
            dump(data)
    else:
        note(data, "高", "解析超时未完成", f"job={jid}")
        dump(data)
        raise SystemExit(6)

    if stuck5 >= 12:  # ≥约 1 分钟停在 5%
        note(
            data,
            "高",
            "解析进度条长时间停在 5%",
            f"观察到约 {stuck5 * 5}s 停在「正在提取文字与抽取条款」；.doc 走 RAGFlow 时第一次 parse 阻塞不推送中间进度",
        )

    if (data.get("parse_job") or {}).get("status") != "completed":
        note(data, "高", "解析未成功", str(data.get("parse_job")))
        dump(data)
        raise SystemExit(7)

    ws = c.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=120).json()
    reqs = [r for r in (ws.get("requirements") or []) if r.get("technical_clause")]
    origins = collections.Counter(str(r.get("response_origin") or "") for r in reqs)
    writable = sum(
        1
        for r in reqs
        if r.get("response_origin") not in ("", "retrieval_failed", "draft_failed", "no_evidence")
        and str(r.get("response") or "").strip()
    )
    tasks = ws.get("response_tasks") or ws.get("technical_response_tasks") or []
    outline = ws.get("technical_outline") or {}
    headings = outline.get("headings") or []
    data["matrix"] = {
        "req_total": len(reqs),
        "origins": dict(origins),
        "writable": writable,
        "response_tasks": len(tasks) if isinstance(tasks, list) else tasks,
        "outline_headings": len(headings),
        "parse_confirmed": ws.get("parse_confirmed"),
        "facts": len(ws.get("facts") or []),
    }
    print("matrix", data["matrix"], flush=True)
    if writable == 0:
        note(
            data,
            "高",
            "响应矩阵无可写条目（writable=0）",
            f"origins={dict(origins)}；生成易落成「待补/需要核对」壳正文",
        )
    if not headings:
        note(data, "高", "技术大纲 headings 为空", "无法确认方案与分节生成")
        dump(data)
        raise SystemExit(8)

    # 主题标题 vs 原文条款粘贴
    clause_like = 0
    for hdg in headings[:30]:
        title = str(hdg.get("title") or "")
        if len(title) > 40 or title.startswith(("一、", "二、", "三、", "1.", "1、", "（")):
            clause_like += 1
    if clause_like >= 10:
        note(
            data,
            "中",
            "大纲标题仍像原文条款摘抄",
            f"前 30 条中约 {clause_like} 条偏长或像条款编号，未充分主题化",
        )

    rev = ws["revision"]
    chapter_id = outline["chapter_id"]
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
                for i in headings
            ],
            "confirm_outline": True,
        },
        timeout=180,
    )
    data["steps"].append({"confirm_plan": plan.status_code, "body": plan.text[:300]})
    print("confirm", plan.status_code, flush=True)
    if plan.status_code >= 400:
        note(data, "高", "确认大纲失败", plan.text[:300])
        dump(data)
        raise SystemExit(9)

    ws = c.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=120).json()
    rev = ws["revision"]
    t_gen = time.monotonic()
    print("generate whole technical volume…", flush=True)
    gen = c.post(
        f"{BASE}/api/v1/projects/{pid}/generate",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={},
        timeout=900,
    )
    gen_s = round(time.monotonic() - t_gen, 1)
    data["steps"].append({"generate": gen.status_code, "seconds": gen_s, "body": gen.text[:400]})
    print("generate", gen.status_code, f"{gen_s}s", gen.text[:220], flush=True)
    if gen.status_code >= 400:
        note(data, "高", "整册生成失败", gen.text[:300])
    else:
        msg = ((gen.json().get("job") or {}).get("message") or "")
        if "待补" in msg or "需要核对" in msg or "质量八条未全部通过" in msg:
            note(data, "中", "生成完成但质量门未过或含待补提示", msg[:300])

    ws = c.get(f"{BASE}/api/v1/projects/{pid}/workspace", headers=h, timeout=180).json()
    ch = next((x for x in (ws.get("chapters") or []) if x.get("id") == chapter_id), None)
    content = (ch or {}).get("content") or ""
    data["content_chars"] = len(content)
    data["content_head"] = content[:2500]
    data["technical_quality"] = ws.get("technical_quality")
    data["technical_rag_audit_n"] = len(ws.get("technical_rag_audit") or [])
    if len(content) < 500:
        note(data, "高", "生成正文过短", f"chars={len(content)}")
    if content.count("待补") >= 5 or content.count("需要核对") >= 5:
        note(data, "高", "正文大量「待补/需要核对」占位", f"待补={content.count('待补')} 需要核对={content.count('需要核对')}")

    # 检查门禁（如实记录）
    checks = c.post(
        f"{BASE}/api/v1/projects/{pid}/checks",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(ws["revision"])},
        json={"volume": "technical"},
        timeout=120,
    )
    data["steps"].append({"checks": checks.status_code, "body": checks.text[:400]})
    if checks.status_code >= 400:
        note(data, "中", "检查接口失败或未就绪", checks.text[:250])

    rev = ws["revision"]
    exp = c.post(
        f"{BASE}/api/v1/projects/{pid}/exports",
        headers={**h, "Idempotency-Key": str(uuid.uuid4()), "If-Match": str(rev)},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
        timeout=300,
    )
    data["steps"].append({"export": exp.status_code, "body": exp.text[:400]})
    print("export", exp.status_code, exp.text[:250], flush=True)
    if exp.status_code >= 400:
        code = ""
        try:
            code = exp.json().get("code") or ""
        except Exception:
            pass
        if code in ("RULES_INCOMPLETE", "CHECK_BLOCKER_EXISTS"):
            note(data, "高", f"导出门禁拦截 {code}", exp.text[:300])
        else:
            note(data, "高", "内部稿导出失败", exp.text[:300])
    else:
        ej = exp.json()
        data["export"] = ej
        eid = ej.get("id") or (ej.get("export") or {}).get("id")
        if eid:
            for url in (
                f"{BASE}/api/v1/exports/{eid}/download",
                f"{BASE}/api/v1/projects/{pid}/exports/{eid}/technical",
            ):
                dl = c.get(url, headers=h, timeout=180)
                print("download", url.rsplit("/", 1)[-1], dl.status_code, len(dl.content), flush=True)
                if dl.status_code == 200 and len(dl.content) > 1000:
                    docx = OUT.with_name("2026-11-05-kunming-oracle-e2e.docx")
                    docx.write_bytes(dl.content)
                    data["saved_docx"] = str(docx)
                    data["download_bytes"] = len(dl.content)
                    break
            if not data.get("saved_docx"):
                note(data, "中", "导出记录成功但下载失败", f"eid={eid}")

    data["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    dump(data)
    _write_blockers(data)
    print("DONE", OUT, "blockers", len(data["blockers"]), flush=True)
    for b in data["blockers"]:
        print("-", b["severity"], b["title"], flush=True)


def _write_blockers(data: dict) -> None:
    lines = [
        "# 昆明航空 Oracle 招标文件全流程冒烟 — 阻塞与体验问题",
        "",
        "为什么有这个文件：用户要求用真实招标文件 `昆明航空Oracle数据库一体机软硬件维保和DBA服.doc` 跑主路径，并记录阻塞/影响使用的点供后续整改。",
        "",
        f"日期：2026-11-05  ",
        f"项目：`{data.get('project_id')}`  ",
        f"入口：`http://127.0.0.1:8710`（health={json.dumps(data.get('health') or {}, ensure_ascii=False)}）  ",
        "账号：`alpha-manager`  ",
        f"证据：`docs/testing/{OUT.name}`",
        "",
        "## 本轮阻塞 / 体验问题",
        "",
        "| # | 严重度 | 现象 | 详情 |",
        "|---|--------|------|------|",
    ]
    for i, b in enumerate(data.get("blockers") or [], 1):
        detail = (b.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {b.get('severity')} | {b.get('title')} | {detail} |")
    if not data.get("blockers"):
        lines.append("| — | — | 本轮 API 冒烟未记入新阻塞 | 仍须对照 UI 与真实模型再验 |")

    m = data.get("matrix") or {}
    pj = data.get("parse_job") or {}
    lines.extend(
        [
            "",
            "## 主路径执行记录",
            "",
            f"- [{'x' if data.get('project_id') else ' '}] 登录 + 新建项目 `{data.get('project_id')}`",
            f"- [{'x' if any(s.get('upload') == 200 for s in data.get('steps') or []) else ' '}] 上传招标 `.doc`（{data.get('tender_bytes')} bytes）",
            f"- [{'x' if pj.get('status') == 'completed' else ' '}] 解析完成：{pj.get('message')}",
            f"- 矩阵：条款 {m.get('req_total')}，writable={m.get('writable')}，大纲 headings={m.get('outline_headings')}，origins={m.get('origins')}",
            f"- [{'x' if any(s.get('confirm_plan') == 200 for s in data.get('steps') or []) else ' '}] 确认技术大纲",
            f"- [{'x' if any((s.get('generate') or 0) < 400 for s in data.get('steps') or [] if 'generate' in s) else ' '}] 整册生成：chars={data.get('content_chars')}",
            f"- [{'x' if data.get('saved_docx') else ' '}] 内部稿导出下载：{data.get('saved_docx') or '未保存'}（{data.get('download_bytes') or 0} bytes）",
            "",
            "## 进度采样（解析任务）",
            "",
            "```json",
            json.dumps(data.get("progress_samples") or [], ensure_ascii=False, indent=2)[:4000],
            "```",
            "",
            "## 说明",
            "",
            "本记录不把 mock 模型下的「生成成功」写成生产可用。`RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 若出现已写入上表。",
            "UI 侧另见历史记录：解析[进度条](https://vibe-hub.org/progress)长时间停在 5%、浏览器保存密码遮挡、文件选择默认目录等。",
            "",
        ]
    )
    BLOCKERS.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
