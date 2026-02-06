#!/usr/bin/env python3
"""
Audit checklist coverage against ADR content.
Identifies potential gaps where ADR decisions aren't reflected in checklists.
"""

import json
import re
from pathlib import Path

ADR_DIR = Path(__file__).parent.parent
CONFIG_FILE = ADR_DIR / ".phase-config.json"

def load_phase_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def find_adr_file(adr_id: str) -> Path | None:
    prefix_map = {
        "FN": ("functional", "ADR-FN"),
        "NF": ("non-functional", "ADR-NF"),
        "UI": ("ui", "ADR-UI"),
    }
    prefix = adr_id.split("-")[0]
    num = adr_id.split("-")[1]
    if prefix not in prefix_map:
        return None
    directory, file_prefix = prefix_map[prefix]
    padded_num = num.zfill(3)
    search_dir = ADR_DIR / directory
    if not search_dir.exists():
        return None
    for file in search_dir.glob(f"{file_prefix}-{padded_num}-*.md"):
        return file
    return None

def extract_section(content: str, section_name: str) -> str:
    pattern = rf"^##\s+{re.escape(section_name)}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_section = re.search(r"^##\s+", content[start:], re.MULTILINE)
    if next_section:
        end = start + next_section.start()
    else:
        end = len(content)
    return content[start:end].strip()

def extract_key_decisions(content: str) -> dict:
    """Extract key decisions from an ADR."""
    decisions = {
        "chosen_option": "",
        "technologies": [],
        "patterns": [],
        "thresholds": [],
        "integrations": [],
    }

    # Get chosen option
    decision_section = extract_section(content, "Decision")
    match = re.search(r"\*\*Chosen Option:\*\*\s*(.+?)(?:\n|$)", decision_section)
    if match:
        decisions["chosen_option"] = match.group(1).strip()

    # Find technologies mentioned
    tech_patterns = [
        r"PostgreSQL\s*\d+\+?", r"pgvector", r"TimescaleDB", r"Redis",
        r"Meilisearch", r"BullMQ", r"NestJS", r"Next\.js\s*\d+\+?",
        r"React Native", r"Expo", r"Socket\.io", r"OpenAPI\s*\d+\.?\d*",
        r"JWT", r"AWS", r"ECS Fargate", r"S3", r"CloudFront",
        r"Azure Document Intelligence", r"OpenAI", r"Claude",
        r"Medusa\.?js?", r"TReDS", r"shadcn/ui", r"Tailwind",
        r"React Query", r"Zustand", r"GitHub Actions",
    ]
    for pattern in tech_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            match = re.search(pattern, content, re.IGNORECASE)
            decisions["technologies"].append(match.group(0))

    # Find architectural patterns
    pattern_keywords = [
        r"modular monolith", r"row[- ]level security", r"RLS",
        r"event[- ]driven", r"saga pattern", r"outbox pattern",
        r"offline[- ]first", r"cache[- ]aside", r"CQRS",
        r"state machine", r"queue[- ]based", r"multi[- ]tenant",
    ]
    for pattern in pattern_keywords:
        if re.search(pattern, content, re.IGNORECASE):
            decisions["patterns"].append(pattern)

    # Find thresholds/numbers
    threshold_patterns = [
        (r"(\d+)%\s*(?:confidence|auto|threshold)", "{}% threshold"),
        (r"(\d+)\s*(?:min|minute|req/min)", "{} rate/time"),
        (r"(\d+)\s*(?:day|hour|d\b|h\b)", "{} duration"),
    ]
    for pattern, template in threshold_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for m in matches:
            decisions["thresholds"].append(template.format(m))

    # Find integrations
    integration_patterns = [
        r"AIS", r"PCS1x", r"VesselFinder", r"Spire",
        r"IMPA", r"ISSA", r"MSG API", r"ERP", r"PMS",
    ]
    for pattern in integration_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            decisions["integrations"].append(pattern)

    return decisions

def audit_adr_coverage(adr_id: str, checklist_items: list[str]) -> dict:
    """Audit a single ADR's checklist coverage."""
    file_path = find_adr_file(adr_id)
    if not file_path:
        return {"error": f"File not found for {adr_id}"}

    with open(file_path) as f:
        content = f.read()

    decisions = extract_key_decisions(content)
    checklist_text = " ".join(checklist_items).lower()

    # Check what's covered vs missing
    coverage = {
        "adr_id": adr_id,
        "chosen_option": decisions["chosen_option"],
        "checklist_count": len(checklist_items),
        "covered": [],
        "potentially_missing": [],
    }

    # Check technologies
    for tech in decisions["technologies"]:
        if tech.lower() in checklist_text or tech.lower().replace(".", "") in checklist_text:
            coverage["covered"].append(f"Tech: {tech}")
        else:
            coverage["potentially_missing"].append(f"Tech: {tech}")

    # Check patterns
    for pattern in decisions["patterns"]:
        pattern_clean = pattern.replace("[- ]", "[ -]?").lower()
        if re.search(pattern_clean, checklist_text):
            coverage["covered"].append(f"Pattern: {pattern}")
        else:
            coverage["potentially_missing"].append(f"Pattern: {pattern}")

    # Check integrations
    for integration in decisions["integrations"]:
        if integration.lower() in checklist_text:
            coverage["covered"].append(f"Integration: {integration}")
        else:
            coverage["potentially_missing"].append(f"Integration: {integration}")

    return coverage

def run_full_audit():
    """Run coverage audit for all phases."""
    config = load_phase_config()

    print("=" * 70)
    print("CHECKLIST COVERAGE AUDIT")
    print("=" * 70)

    total_adrs = 0
    total_missing = 0
    adrs_with_gaps = []

    for phase_id, phase_data in sorted(config["phases"].items()):
        print(f"\n{'─' * 70}")
        print(f"Phase {phase_id}: {phase_data['name']}")
        print(f"{'─' * 70}")

        for adr_id in phase_data["adrs"]:
            total_adrs += 1
            checklist = phase_data.get("validationChecklist", [])

            # Filter checklist items for this specific ADR
            adr_checklist = [item for item in checklist if f"ADR-{adr_id}" in item]

            result = audit_adr_coverage(adr_id, adr_checklist)

            if "error" in result:
                print(f"  ⚠️  {adr_id}: {result['error']}")
                continue

            missing_count = len(result["potentially_missing"])

            if missing_count > 0:
                total_missing += missing_count
                adrs_with_gaps.append((adr_id, result["potentially_missing"]))
                print(f"  ⚠️  {adr_id}: {result['checklist_count']} items, {missing_count} potential gaps")
                for item in result["potentially_missing"][:3]:  # Show first 3
                    print(f"      └─ Missing: {item}")
                if missing_count > 3:
                    print(f"      └─ ... and {missing_count - 3} more")
            else:
                print(f"  ✅ {adr_id}: {result['checklist_count']} items, good coverage")

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total ADRs audited: {total_adrs}")
    print(f"ADRs with potential gaps: {len(adrs_with_gaps)}")
    print(f"Total potential missing items: {total_missing}")

    if adrs_with_gaps:
        print(f"\n⚠️  ADRs needing review:")
        for adr_id, missing in adrs_with_gaps:
            print(f"   • {adr_id}: {len(missing)} items")

if __name__ == "__main__":
    run_full_audit()
