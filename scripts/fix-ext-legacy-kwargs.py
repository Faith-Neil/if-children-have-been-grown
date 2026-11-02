import re
from pathlib import Path

p = Path("backend/bid-core/icg/domain/compliance_rules.py")
text = p.read_text(encoding="utf-8")
pattern = re.compile(
    r"        legacy_kwargs = \{\"volume\": volume\}\n"
    r"        if \"\d+\" in \(\"06\", \"15\"\):\n"
    r"            legacy_kwargs\[\"now_ts\"\] = now_ts\n"
    r"        legacy = cls\._legacy_misaligned_r(\d+)\(state, project, workflow, \*\*legacy_kwargs\)",
    re.M,
)


def repl(m: re.Match) -> str:
    num = m.group(1)
    if num in ("06", "15"):
        return (
            f"        legacy = cls._legacy_misaligned_r{num}"
            f"(state, project, workflow, volume=volume, now_ts=now_ts)"
        )
    return f"        legacy = cls._legacy_misaligned_r{num}(state, project, workflow, volume=volume)"


text2, n = pattern.subn(repl, text)
print("fixed", n)
p.write_text(text2, encoding="utf-8")
