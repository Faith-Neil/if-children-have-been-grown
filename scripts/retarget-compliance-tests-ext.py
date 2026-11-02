from pathlib import Path

mapping = {
    "test_compliance_rules_p3.py": {
        '"rule_id"] == "R05"': '"rule_id"] == "EXT-FINANCIAL-METRICS"',
        '"rule_id"] == "R06"': '"rule_id"] == "EXT-PERFORMANCE-CASE"',
        '"rule_id"] == "R08"': '"rule_id"] == "EXT-DELIVERY-TIMELINE"',
        '"rule_id"] == "R12"': '"rule_id"] == "EXT-SLA-WARRANTY-DEVIATION"',
        '"rule_id"] == "R20"': '"rule_id"] == "EXT-QUOTATION-COLLUSION"',
    },
    "test_compliance_rules_p4.py": {
        '"rule_id"] == "R13"': '"rule_id"] == "EXT-TEAM-STAFFING"',
        '"rule_id"] == "R16"': '"rule_id"] == "EXT-BID-SECURITY"',
        '"rule_id"] == "R18"': '"rule_id"] == "EXT-CONSORTIUM-QUALIFICATION"',
        '"rule_id"] == "R32"': '"rule_id"] == "EXT-BID-VALIDITY"',
    },
    "test_compliance_rules_p5.py": {
        '"rule_id"] == "R17"': '"rule_id"] == "EXT-CONFLICT-INTEREST"',
        '"rule_id"] == "R26"': '"rule_id"] == "EXT-IP-INDEMNITY"',
        '"rule_id"] == "R27"': '"rule_id"] == "EXT-LOCAL-SERVICE"',
        '"rule_id"] == "R28"': '"rule_id"] == "EXT-CRITICAL-TECH-DEVIATION"',
    },
}

root = Path("tests/backend")
for fname, reps in mapping.items():
    path = root / fname
    text = path.read_text(encoding="utf-8")
    for old, new in reps.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("updated", fname)
