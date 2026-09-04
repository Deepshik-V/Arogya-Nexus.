"""
Arogya Nexus Knowledge Base Validator
Validates JSON structure, required fields, unique IDs, official sources, and data integrity
across all verified clinical and government scheme knowledge cards.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Path to knowledge base directory
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent / "knowledge_base"


def validate_knowledge_base() -> Tuple[bool, Dict[str, Any]]:
    """
    Validates all JSON files in the knowledge base.
    Returns (is_valid, report_summary).
    """
    report = {
        "is_valid": True,
        "total_files": 0,
        "total_cards": 0,
        "scheme_cards_count": 0,
        "healthcare_cards_count": 0,
        "files_validated": [],
        "errors": [],
        "warnings": [],
        "all_card_ids": set(),
        "duplicate_ids": [],
    }

    if not KNOWLEDGE_BASE_DIR.exists():
        report["is_valid"] = False
        report["errors"].append(f"Knowledge base directory not found at: {KNOWLEDGE_BASE_DIR}")
        return False, report

    json_files = sorted(list(KNOWLEDGE_BASE_DIR.glob("*.json")))
    report["total_files"] = len(json_files)

    seen_ids = set()

    # Core required fields for all cards
    BASE_REQUIRED_FIELDS = ["id", "category", "title_en", "title_ta", "last_verified"]
    
    # Specific fields expected for government schemes
    SCHEME_REQUIRED_FIELDS = [
        "id", "category", "scheme_category", "scheme_name",
        "short_description", "purpose", "eligibility", "benefits",
        "required_documents", "how_to_apply", "where_to_apply",
        "state", "official_source", "official_url", "last_verified", "disclaimer"
    ]

    for json_file in json_files:
        file_info = {
            "filename": json_file.name,
            "cards_count": 0,
            "status": "PASS",
            "errors": [],
        }

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                cards = json.load(f)
        except json.JSONDecodeError as jde:
            report["is_valid"] = False
            err_msg = f"Malformed JSON in {json_file.name}: {jde}"
            file_info["status"] = "FAIL"
            file_info["errors"].append(err_msg)
            report["errors"].append(err_msg)
            report["files_validated"].append(file_info)
            continue
        except Exception as e:
            report["is_valid"] = False
            err_msg = f"Error reading {json_file.name}: {e}"
            file_info["status"] = "FAIL"
            file_info["errors"].append(err_msg)
            report["errors"].append(err_msg)
            report["files_validated"].append(file_info)
            continue

        if not isinstance(cards, list):
            report["is_valid"] = False
            err_msg = f"Root element in {json_file.name} must be a JSON array (list)."
            file_info["status"] = "FAIL"
            file_info["errors"].append(err_msg)
            report["errors"].append(err_msg)
            report["files_validated"].append(file_info)
            continue

        file_info["cards_count"] = len(cards)
        report["total_cards"] += len(cards)

        for idx, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                report["is_valid"] = False
                err_msg = f"{json_file.name} [Card #{idx}]: Card must be a JSON object (dict)."
                file_info["errors"].append(err_msg)
                report["errors"].append(err_msg)
                continue

            card_id = card.get("id")
            category = card.get("category", "")

            # Check ID existence and uniqueness
            if not card_id or not str(card_id).strip():
                report["is_valid"] = False
                err_msg = f"{json_file.name} [Card #{idx}]: Missing or empty 'id'."
                file_info["errors"].append(err_msg)
                report["errors"].append(err_msg)
            else:
                card_id_str = str(card_id).strip()
                if card_id_str in seen_ids:
                    report["is_valid"] = False
                    report["duplicate_ids"].append(card_id_str)
                    err_msg = f"Duplicate Card ID '{card_id_str}' found in {json_file.name}."
                    file_info["errors"].append(err_msg)
                    report["errors"].append(err_msg)
                else:
                    seen_ids.add(card_id_str)
                    report["all_card_ids"].add(card_id_str)

            # Count categories
            if category in ("government_scheme", "health_schemes"):
                report["scheme_cards_count"] += 1
                # Check government scheme required fields
                for field in SCHEME_REQUIRED_FIELDS:
                    if field not in card or card[field] is None or (isinstance(card[field], str) and not card[field].strip()):
                        report["is_valid"] = False
                        err_msg = f"{json_file.name} [Card '{card_id}']: Missing required scheme field '{field}'."
                        file_info["errors"].append(err_msg)
                        report["errors"].append(err_msg)
            else:
                report["healthcare_cards_count"] += 1
                # Check standard healthcare card fields
                for field in BASE_REQUIRED_FIELDS:
                    if field not in card or card[field] is None or (isinstance(card[field], str) and not card[field].strip()):
                        report["is_valid"] = False
                        err_msg = f"{json_file.name} [Card '{card_id}']: Missing required healthcare field '{field}'."
                        file_info["errors"].append(err_msg)
                        report["errors"].append(err_msg)

            # Check official URL format if present
            url = card.get("official_url") or card.get("source_url")
            if url and not (url.startswith("http://") or url.startswith("https://")):
                report["is_valid"] = False
                err_msg = f"{json_file.name} [Card '{card_id}']: Invalid official URL '{url}'."
                file_info["errors"].append(err_msg)
                report["errors"].append(err_msg)

        if file_info["errors"]:
            file_info["status"] = "FAIL"

        report["files_validated"].append(file_info)

    return report["is_valid"], report


def print_validation_report(is_valid: bool, report: Dict[str, Any]) -> None:
    """Prints a human-readable console report."""
    print("==================================================================")
    print("           AROGYA NEXUS KNOWLEDGE BASE VALIDATION REPORT          ")
    print("==================================================================")
    status_str = "PASSED [OK]" if is_valid else "FAILED [ERROR]"
    print(f"Overall Status: {status_str}")
    print(f"Total Files Validated: {report['total_files']}")
    print(f"Total Knowledge Cards: {report['total_cards']}")
    print(f"  - Scheme Intelligence Cards: {report['scheme_cards_count']}")
    print(f"  - Clinical / Healthcare Cards: {report['healthcare_cards_count']}")
    print("------------------------------------------------------------------")
    print("File Breakdown:")
    for f in report["files_validated"]:
        print(f"  * {f['filename']:<25} | Cards: {f['cards_count']:<3} | Status: {f['status']}")

    if report["duplicate_ids"]:
        print("------------------------------------------------------------------")
        print(f"[!] Duplicate IDs Detected: {report['duplicate_ids']}")

    if report["errors"]:
        print("------------------------------------------------------------------")
        print(f"[X] Validation Errors ({len(report['errors'])}):")
        for err in report["errors"]:
            print(f"    - {err}")
    else:
        print("------------------------------------------------------------------")
        print("[V] All knowledge cards comply with schema, unique IDs, and source standards.")
    print("==================================================================")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    is_valid, report = validate_knowledge_base()
    print_validation_report(is_valid, report)
    sys.exit(0 if is_valid else 1)
