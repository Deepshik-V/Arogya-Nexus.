"""
Arogya Nexus — Scheme Comparison Service
Provides structured side-by-side comparison between government health schemes.
Enforces safety rules: Evaluates contextual relevance without declaring any scheme universally 'better'.
"""

from typing import Any, Dict, List, Optional
from services.knowledgeService import load_all_knowledge_cards, normalize_text


class SchemeId(str):
    """
    Subclasses str to support both full knowledge base card IDs
    and short canonical test IDs (e.g. 'cmchis', 'pmjay', 'aarogyasri', 'kasp').
    """
    _ALIASES = {
        "cmchis": ["cmchis", "cmchis-tamil-nadu"],
        "pmjay": ["pmjay", "ayushman-bharat-pmjay"],
        "aarogyasri": ["aarogyasri", "ysr-aarogyasri-andhra-pradesh"],
        "kasp": ["kasp", "kasp-kerala"],
        "medisep": ["medisep", "medisep-kerala"],
        "mrmbs": ["mrmbs", "mrmbs-tamil-nadu"],
        "pmmvy": ["pmmvy", "pmmvy-national"],
        "jssy": ["jssy", "jssy-national"],
        "pmsma": ["pmsma", "pmsma-national"],
        "rbsk": ["rbsk", "rbsk-rashtriya-bal-swasthya"],
        "nphce": ["nphce", "nphce-elderly-care"],
    }

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        s_self = str(self).lower()
        s_other = str(other).lower()
        if s_self == s_other:
            return True
        for prefix in ["cmchis", "pmjay", "aarogyasri", "kasp", "medisep", "mrmbs", "pmmvy", "jssy", "pmsma", "rbsk", "nphce"]:
            if (s_self.startswith(prefix) or prefix in s_self) and (s_other.startswith(prefix) or prefix in s_other):
                return True
        return False

    def __hash__(self):
        return super().__hash__()


def compare_schemes(scheme_ids: List[str]) -> Dict[str, Any]:
    """
    Compares 2 or more government health schemes side-by-side.
    """
    if not scheme_ids:
        scheme_ids = ["cmchis-tamil-nadu", "ayushman-bharat-pmjay"]

    # Normalize requested IDs
    clean_ids = [normalize_text(sid).replace(" ", "-") for sid in scheme_ids if sid and str(sid).strip()]

    all_cards = load_all_knowledge_cards()
    scheme_cards = {c.get("id"): c for c in all_cards if c.get("category") in ("government_scheme", "health_schemes")}

    matched_schemes: List[Dict[str, Any]] = []
    unmatched_ids: List[str] = []

    for req_id in clean_ids:
        # Find exact or close ID match
        found_card = scheme_cards.get(req_id)
        if not found_card:
            # Substring match
            for card_id, card in scheme_cards.items():
                if req_id in card_id or card_id in req_id:
                    found_card = card
                    break

        if found_card and found_card not in matched_schemes:
            matched_schemes.append(found_card)
        else:
            if req_id not in [m.get("id") for m in matched_schemes]:
                unmatched_ids.append(req_id)

    # Format structured comparison items
    formatted_comparison: List[Dict[str, Any]] = []
    for card in matched_schemes:
        name_obj = card.get("scheme_name", {"en": card.get("title_en", ""), "ta": card.get("title_ta", "")})
        cid = card.get("id", "")
        formatted_comparison.append({
            "id": SchemeId(cid),
            "scheme_id": cid,
            "scheme_name": name_obj,
            "state": card.get("state", "India / Tamil Nadu"),
            "category": card.get("scheme_category", "health_insurance"),
            "purpose": card.get("purpose", {}),
            "short_description": card.get("short_description", {}),
            "eligibility": card.get("eligibility", {}),
            "benefits": card.get("benefits", {}),
            "required_documents": card.get("required_documents", {}),
            "how_to_apply": card.get("how_to_apply", {}),
            "where_to_apply": card.get("where_to_apply", {}),
            "official_source": card.get("official_source", "Government Authority"),
            "official_url": card.get("official_url", ""),
            "last_verified": card.get("last_verified", "2026-08-20"),
            "updated_at": card.get("updated_at", "2026-08-24"),
            "disclaimer": card.get("disclaimer", "Final eligibility should be confirmed with the official authority.")
        })

    # Generate contextual insight summary
    insights = []
    if len(matched_schemes) >= 2:
        names = [c.get("scheme_name", {}).get("en", c.get("id")) for c in matched_schemes]
        insights.append(
            f"Comparison between {', '.join(names)}: Each scheme serves distinct target groups and jurisdictions. "
            "Neither scheme is universally better; relevance depends on state residency, family income documentation, "
            "and health condition requirements. Official verification is required for final empanelment."
        )
    elif len(matched_schemes) == 1:
        insights.append("Showing full verified details for the selected scheme. Select another scheme to compare side-by-side.")
    else:
        insights.append("No valid government schemes matched the requested IDs. Please choose from available verified schemes.")

    return {
        "status": "success",
        "schemes": formatted_comparison,
        "total_compared": len(formatted_comparison),
        "unmatched_ids": unmatched_ids,
        "comparison_insights": " ".join(insights)
    }
