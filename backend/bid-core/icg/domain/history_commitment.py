# 历史投标承诺片段：当技术领域未在企业权威资料中覆盖时，在写作快照上给出固定提示（不改动正文）。

from __future__ import annotations

from typing import Any

NOTICE_MESSAGE = (
    "本节有内容来自历史投标承诺，尚未在企业权威资料中核到。"
    "历史承诺不代表公司当前一定具备该能力。"
)

_TRIGGER_ROLES = frozenset({
    "bidder_response",
    "project_specific_commitment",
    "enterprise_fact",
})


def commitment_notice(chunks: list[dict[str, Any]]) -> dict[str, list[str] | str] | None:
    material_domains = {
        str(chunk.get("technical_domain") or "").strip()
        for chunk in chunks
        if str(chunk.get("dataset_kind") or "") == "materials"
        and str(chunk.get("technical_domain") or "").strip()
    }

    filenames: list[str] = []
    seen: set[str] = set()
    uncovered = False
    for chunk in chunks:
        if str(chunk.get("dataset_kind") or "") != "history":
            continue
        if str(chunk.get("content_role") or "") not in _TRIGGER_ROLES:
            continue
        domain = str(chunk.get("technical_domain") or "").strip()
        if domain and domain in material_domains:
            continue
        uncovered = True
        name = str(chunk.get("name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            filenames.append(name)

    if not uncovered:
        return None
    return {"message": NOTICE_MESSAGE, "filenames": filenames}
