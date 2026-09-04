"""
Arogya Nexus — Multi-State Scheme Recommendation Engine
Combines natural language intent (Tamil, English, Tanglish, Telugu, Malayalam) with patient health profile
and state location to rank and recommend the top verified government health schemes.
"""

from typing import Any, Dict, List, Optional
from services.knowledgeService import (
    load_all_knowledge_cards,
    detect_scheme_intent,
    normalize_text,
    expand_query_with_synonyms,
)
from services.eligibilityService import evaluate_profile_eligibility


def get_scheme_recommendations(
    profile: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    language_code: Optional[str] = "ta-IN",
    state: Optional[str] = None,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Returns top recommended schemes based on natural query intent, patient profile, and state.
    """
    profile = profile or {}
    user_state = state or profile.get("state")
    clean_query = (query or "").strip()
    norm_query = normalize_text(clean_query)
    expanded_tokens = set(expand_query_with_synonyms(norm_query)) if norm_query else set()
    is_scheme_intent, detected_cat, matched_indicators = detect_scheme_intent(clean_query) if clean_query else (False, None, [])

    # Determine language tag
    lang_tag = "en"
    if language_code:
        if "ta" in language_code.lower():
            lang_tag = "ta"
        elif "te" in language_code.lower():
            lang_tag = "te"
        elif "ml" in language_code.lower():
            lang_tag = "ml"

    # 1. Run eligibility evaluation on profile
    eligibility_evals = evaluate_profile_eligibility(profile)
    eval_by_id = {item["scheme_id"]: item for item in eligibility_evals}

    # 2. Score each scheme
    all_cards = load_all_knowledge_cards()
    scheme_cards = [c for c in all_cards if c.get("category") in ("government_scheme", "health_schemes")]

    scored_schemes: List[Dict[str, Any]] = []

    for card in scheme_cards:
        sid = card.get("id", "")
        eval_info = eval_by_id.get(sid, {})
        status = eval_info.get("eligibility_status", "More Information Needed")
        card_cat = card.get("scheme_category", "")
        card_state = card.get("state", "National")

        score = 0.0

        # State filter relevance boost
        if user_state:
            norm_ustate = user_state.strip().lower()
            if card_state.lower() == norm_ustate:
                score += 25.0
            elif card_state.lower() == "national":
                score += 12.0
            else:
                score -= 15.0

        # Eligibility status weights
        if status == "Likely Eligible":
            score += 40.0
        elif status == "Possibly Eligible":
            score += 20.0
        elif status == "More Information Needed":
            score += 5.0

        # Matched criteria bonus
        matched_crits = eval_info.get("matched_criteria", [])
        score += len(matched_crits) * 10.0

        # Query semantic relevance
        if norm_query:
            keywords_en = [normalize_text(k) for k in card.get("keywords_en", [])]
            keywords_ta = [normalize_text(k) for k in card.get("keywords_ta", [])]
            keywords_te = [normalize_text(k) for k in card.get("keywords_te", [])]
            keywords_ml = [normalize_text(k) for k in card.get("keywords_ml", [])]
            keywords_tanglish = [normalize_text(k) for k in card.get("keywords_tanglish", [])]
            all_kws = keywords_en + keywords_ta + keywords_te + keywords_ml + keywords_tanglish

            title_en = normalize_text(card.get("title_en", ""))
            title_ta = normalize_text(card.get("title_ta", ""))
            title_te = normalize_text(card.get("title_te", ""))
            title_ml = normalize_text(card.get("title_ml", ""))

            # Exact ID or name match
            if sid in norm_query or norm_query in sid:
                score += 35.0

            # Category match
            if detected_cat and card_cat == detected_cat:
                score += 25.0

            # Keyword match
            for kw in all_kws:
                if kw and (kw in norm_query or norm_query in kw):
                    score += 15.0
                elif kw and any(t in kw for t in expanded_tokens if len(t) > 2):
                    score += 5.0

            # Title matches
            for token in expanded_tokens:
                if len(token) > 2 and (token in title_en or token in title_ta or token in title_te or token in title_ml):
                    score += 8.0

        # Build recommendation card
        name_obj = card.get("scheme_name", {})
        benefits_list = card.get("benefits", {}).get(lang_tag) or card.get("benefits", {}).get("en", [])
        how_apply_list = card.get("how_to_apply", {}).get(lang_tag) or card.get("how_to_apply", {}).get("en", [])
        next_step = how_apply_list[0] if how_apply_list else "Visit your nearest Primary Health Centre (PHC) or Government Portal."
        src = card.get("official_source", "Government Health Authority")
        url = card.get("official_url", "")
        last_ver = card.get("last_verified", "2026-08-25")

        why_rec = eval_info.get("possible_reason") or "Matched based on official eligibility criteria and health priorities."

        scored_schemes.append({
            "score": score,
            "scheme_id": sid,
            "scheme_name": name_obj,
            "state": card_state,
            "why_recommended": why_rec,
            "key_benefits": benefits_list[:3],
            "practical_next_step": next_step,
            "official_source": src,
            "official_url": url,
            "last_verified": last_ver,
            "eligibility_status": status,
            "disclaimer": "Official government verification required for final sanction."
        })

    # Sort descending by score
    scored_schemes.sort(key=lambda x: x["score"], reverse=True)
    top_recommendations = scored_schemes[:top_k]

    return {
        "recommendations": top_recommendations,
        "query_detected_category": detected_cat,
        "matched_indicators": matched_indicators,
        "total_evaluated": len(scheme_cards),
        "user_state": user_state or "All-India"
    }
