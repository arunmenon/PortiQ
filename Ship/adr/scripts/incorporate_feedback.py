#!/usr/bin/env python3
"""
Incorporate feedback from feedback files into corresponding ADRs.
Adds an 'Operational Considerations' section to each ADR addressing the feedback items.
"""

import re
from pathlib import Path
from typing import Optional

ADR_DIR = Path(__file__).parent.parent
FEEDBACK_DIR = ADR_DIR / "feedback"


def find_adr_file(feedback_filename: str) -> Optional[Path]:
    """Find the ADR file corresponding to a feedback file."""
    # Extract ADR ID from feedback filename
    # e.g., ADR-FN-001-impa-issa-primary-identifier.md -> FN-001
    match = re.match(r"ADR-([A-Z]+-\d+)", feedback_filename)
    if not match:
        return None

    adr_id = match.group(1)  # e.g., "FN-001"
    prefix = adr_id.split("-")[0]  # e.g., "FN"

    prefix_map = {
        "FN": "functional",
        "NF": "non-functional",
        "UI": "ui",
    }

    if prefix not in prefix_map:
        return None

    directory = prefix_map[prefix]
    search_dir = ADR_DIR / directory

    if not search_dir.exists():
        return None

    # Find file matching pattern ADR-{prefix}-{num}-*.md
    for file in search_dir.glob(f"ADR-{adr_id}-*.md"):
        return file

    return None


def parse_feedback(content: str) -> dict:
    """Parse feedback file to extract feedback items and questions."""
    result = {
        "feedback": [],
        "questions": []
    }

    # Extract feedback section
    feedback_match = re.search(r"## Feedback\s*\n([\s\S]*?)(?=## Questions|$)", content)
    if feedback_match:
        feedback_text = feedback_match.group(1).strip()
        # Parse bullet points
        for line in feedback_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                result["feedback"].append(line[2:])

    # Extract questions section
    questions_match = re.search(r"## Questions\s*\n([\s\S]*?)$", content)
    if questions_match:
        questions_text = questions_match.group(1).strip()
        for line in questions_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                result["questions"].append(line[2:])
            elif line and not line.startswith("#"):
                result["questions"].append(line)

    return result


def generate_operational_section(feedback_data: dict, adr_id: str) -> str:
    """Generate the Operational Considerations section content."""
    lines = [
        "",
        "---",
        "",
        "## Operational Considerations",
        "",
    ]

    # Add feedback items as subsections with responses
    if feedback_data["feedback"]:
        for i, item in enumerate(feedback_data["feedback"], 1):
            # Convert feedback item to a subsection header
            lines.append(f"### {item}")
            lines.append("")
            lines.append("*To be addressed during implementation planning.*")
            lines.append("")

    # Add questions section
    if feedback_data["questions"]:
        lines.append("### Open Questions")
        lines.append("")
        for q in feedback_data["questions"]:
            lines.append(f"- **Q:** {q}")
            lines.append("  - **A:** *To be determined during implementation.*")
        lines.append("")

    return "\n".join(lines)


def has_operational_section(content: str) -> bool:
    """Check if ADR already has an Operational Considerations section."""
    return "## Operational Considerations" in content


def insert_section_before_references(content: str, new_section: str) -> str:
    """Insert the new section before the References section, or at the end."""
    # Try to find References section
    ref_match = re.search(r"\n---\s*\n\n## References", content)
    if ref_match:
        insert_pos = ref_match.start()
        return content[:insert_pos] + new_section + content[insert_pos:]

    # No References section, append at end
    return content.rstrip() + "\n" + new_section


def process_adr(feedback_file: Path) -> dict:
    """Process a single feedback file and update the corresponding ADR."""
    result = {
        "feedback_file": feedback_file.name,
        "status": "unknown",
        "message": ""
    }

    # Find corresponding ADR
    adr_file = find_adr_file(feedback_file.name)
    if not adr_file:
        result["status"] = "error"
        result["message"] = "ADR file not found"
        return result

    result["adr_file"] = adr_file.name

    # Read feedback
    feedback_content = feedback_file.read_text()
    feedback_data = parse_feedback(feedback_content)

    if not feedback_data["feedback"] and not feedback_data["questions"]:
        result["status"] = "skipped"
        result["message"] = "No feedback or questions found"
        return result

    # Read ADR
    adr_content = adr_file.read_text()

    # Check if already has operational section
    if has_operational_section(adr_content):
        result["status"] = "skipped"
        result["message"] = "Already has Operational Considerations section"
        return result

    # Generate new section
    adr_id = re.match(r"ADR-([A-Z]+-\d+)", feedback_file.name).group(1)
    new_section = generate_operational_section(feedback_data, adr_id)

    # Insert section
    updated_content = insert_section_before_references(adr_content, new_section)

    # Write updated ADR
    adr_file.write_text(updated_content)

    result["status"] = "updated"
    result["message"] = f"Added {len(feedback_data['feedback'])} feedback items, {len(feedback_data['questions'])} questions"
    result["feedback_count"] = len(feedback_data["feedback"])
    result["question_count"] = len(feedback_data["questions"])

    return result


def main():
    """Process all feedback files."""
    print("=" * 70)
    print("INCORPORATING FEEDBACK INTO ADRs")
    print("=" * 70)
    print()

    if not FEEDBACK_DIR.exists():
        print(f"Error: Feedback directory not found at {FEEDBACK_DIR}")
        return

    feedback_files = sorted(FEEDBACK_DIR.glob("ADR-*.md"))
    print(f"Found {len(feedback_files)} feedback files\n")

    stats = {
        "updated": 0,
        "skipped": 0,
        "error": 0
    }

    results = []

    for feedback_file in feedback_files:
        result = process_adr(feedback_file)
        results.append(result)
        stats[result["status"]] = stats.get(result["status"], 0) + 1

        # Print status
        status_icon = {"updated": "✅", "skipped": "⏭️", "error": "❌"}.get(result["status"], "?")
        print(f"{status_icon} {result['feedback_file']}")
        if result["status"] == "updated":
            print(f"   → {result.get('adr_file', 'N/A')}: {result['message']}")
        elif result["status"] == "error":
            print(f"   → Error: {result['message']}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors:  {stats['error']}")
    print()

    if stats['updated'] > 0:
        total_feedback = sum(r.get('feedback_count', 0) for r in results)
        total_questions = sum(r.get('question_count', 0) for r in results)
        print(f"Total feedback items added: {total_feedback}")
        print(f"Total questions documented: {total_questions}")


if __name__ == "__main__":
    main()
