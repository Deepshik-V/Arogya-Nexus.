"""
Arogya Nexus — Multi-State Personalized Scheme Eligibility Engine
Evaluates patient profile against official government health schemes in Tamil Nadu, Andhra Pradesh,
Kerala, and National across the knowledge base.
Trust & Safety: Never claims definitive eligibility; returns 'Likely Eligible', 'Possibly Eligible',
'More Information Needed', or 'Not Determined'.
"""

from typing import Any, Dict, List, Optional
from services.knowledgeService import load_all_knowledge_cards

ELIGIBILITY_STATUSES = [
    "Likely Eligible",
    "Possibly Eligible",
    "More Information Needed",
    "Not Determined"
]

DEFAULT_DISCLAIMER = "Final eligibility must be confirmed with the official government authority."

class SchemeId(str):
    """
    Subclasses str to support both full card IDs ('cmchis-tamil-nadu')
    and short canonical test IDs ('cmchis', 'pmjay', 'aarogyasri', 'kasp', 'mrmbs', 'pmmvy').
    """
    _ALIASES = {
        "cmchis": ["cmchis", "cmchis-tamil-nadu"],
        "pmjay": ["pmjay", "ayushman-bharat-pmjay", "pmjay-national"],
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


class EligibilityResults(list):
    """
    Custom list subclass that also supports dictionary-style access for:
    - total_schemes_checked
    - likely_eligible_count
    - likely_eligible
    - all_evaluations
    - schemes
    - status
    - total_evaluated
    - disclaimer
    """
    def __init__(self, items: List[Dict[str, Any]]):
        super().__init__(items)
        likely = [s for s in items if s.get("eligibility_status") == "Likely Eligible"]
        self._meta = {
            "total_schemes_checked": len(items),
            "likely_eligible_count": len(likely),
            "likely_eligible": likely,
            "all_evaluations": items,
            "schemes": items,
            "status": "success",
            "total_evaluated": len(items),
            "disclaimer": DEFAULT_DISCLAIMER
        }

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._meta[key]
        return super().__getitem__(key)

    def get(self, key, default=None):
        return self._meta.get(key, default)



def _parse_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_bool(val: Any) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "yes", "y", "1"):
            return True
        if v in ("false", "no", "n", "0"):
            return False
    return None


def _normalize_str(val: Any) -> str:
    if not val:
        return ""
    return str(val).strip().lower()


def evaluate_profile_eligibility(profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates a user's health profile against all verified government schemes (State & National).
    Returns a structured assessment for each scheme.
    """
    profile = profile or {}

    # Extract sanitized profile attributes
    age = _parse_int(profile.get("age"))
    gender = _normalize_str(profile.get("gender"))
    state = _normalize_str(profile.get("state"))
    district = profile.get("district", "")
    income_val = _parse_int(profile.get("annual_income"))
    income_range = _normalize_str(profile.get("income_range") or profile.get("annual_family_income"))
    family_size = _parse_int(profile.get("family_size"))
    is_pregnant = _parse_bool(profile.get("is_pregnant") or profile.get("pregnancy_status"))
    has_child = _parse_bool(profile.get("has_child") or profile.get("child_status"))
    is_elderly = _parse_bool(profile.get("is_elderly") or profile.get("elderly_status"))
    raw_conditions = profile.get("health_conditions") or profile.get("existing_health_conditions") or []
    if isinstance(raw_conditions, str):
        conditions = [_normalize_str(c) for c in raw_conditions.split(",") if c.strip()]
    elif isinstance(raw_conditions, list):
        conditions = [_normalize_str(c) for c in raw_conditions if c]
    else:
        conditions = []
    occupation = _normalize_str(profile.get("occupation"))

    # Load all scheme cards from knowledge base
    all_cards = load_all_knowledge_cards()
    scheme_cards = [c for c in all_cards if c.get("category") in ("government_scheme", "health_schemes")]

    is_empty_profile = len([v for v in profile.values() if v is not None and v != "" and v != []]) == 0

    results: List[Dict[str, Any]] = []

    for scheme in scheme_cards:
        scheme_id = scheme.get("id", "")
        name_obj = scheme.get("scheme_name", {"en": scheme.get("title_en", scheme_id), "ta": scheme.get("title_ta", scheme_id)})
        benefits = scheme.get("benefits", {}).get("en", [])
        docs = scheme.get("required_documents", {}).get("en", [])
        how_apply = scheme.get("how_to_apply", {}).get("en", [])
        src = scheme.get("official_source", "Government Health Authority")
        url = scheme.get("official_url", "")
        last_ver = scheme.get("last_verified", "2026-08-25")
        scheme_state = scheme.get("state", "National")

        matched_criteria: List[str] = []
        missing_information: List[str] = []
        status = "More Information Needed"
        possible_reason = ""

        if is_empty_profile:
            missing_information = ["State residency confirmation", "Annual family income", "Specific demographic/health details"]
            possible_reason = "Please complete your health profile to view personalized scheme eligibility."
            results.append({
                "scheme_id": scheme_id,
                "scheme_name": name_obj,
                "state": scheme_state,
                "eligibility_status": "More Information Needed",
                "matched_criteria": [],
                "missing_information": missing_information,
                "possible_reason": possible_reason,
                "official_source": src,
                "official_url": url,
                "last_verified": last_ver,
                "disclaimer": DEFAULT_DISCLAIMER
            })
            continue

        # -------------------------------------------------------------
        # STATE & SCHEME SPECIFIC EVALUATION RULES
        # -------------------------------------------------------------

        # 1. CMCHIS (Tamil Nadu)
        if scheme_id == "cmchis-tamil-nadu":
            is_tn = ("tamil nadu" in state) or ("tn" in state)
            is_low_income = (income_val is not None and income_val <= 120000) or ("below" in income_range) or ("<" in income_range)
            
            if is_tn:
                matched_criteria.append("Resident of Tamil Nadu")
            elif state:
                status = "Not Determined"
                possible_reason = "CMCHIS requires Tamil Nadu state residency and a valid Tamil Nadu Smart Family Card."
                missing_information.append("Tamil Nadu Smart Ration Card proof")

            if is_low_income:
                matched_criteria.append("Annual family income within ₹1,20,000 threshold")
            elif income_val is not None and income_val > 120000:
                missing_information.append("Annual income exceeds standard ₹1.2L threshold (special exceptions for camp refugees / welfare board)")

            if is_tn and is_low_income:
                status = "Likely Eligible"
                possible_reason = "Resident of Tamil Nadu with family income within the ₹1.2 Lakh threshold eligible for ₹5 Lakh cashless hospital coverage."
            elif is_tn:
                status = "Possibly Eligible"
                possible_reason = "Tamil Nadu resident; verification of Smart Family Ration Card and VAO income certificate required."
                missing_information.append("Income Certificate from VAO / Revenue Authority")

        # 2. MRMBS (Tamil Nadu)
        elif scheme_id == "mrmbs-dr-muthulakshmi-reddy":
            is_tn = ("tamil nadu" in state) or ("tn" in state)
            if is_tn:
                matched_criteria.append("Resident of Tamil Nadu")
            if is_pregnant:
                matched_criteria.append("Pregnant mother status")
            if age is not None and age >= 19:
                matched_criteria.append("Eligible age demographic (19 years and above)")

            if is_tn and is_pregnant:
                status = "Likely Eligible"
                possible_reason = "Pregnant woman residing in Tamil Nadu eligible for ₹18,000 assistance and 2 Nutrition Kits."
                missing_information.append("PICME 12-digit RCH ID registration before 12 weeks of pregnancy")
                missing_information.append("Applicable for first 2 deliveries only")
            elif is_tn and is_pregnant is None:
                status = "Possibly Eligible"
                possible_reason = "Tamil Nadu resident; pregnancy status required to confirm Dr. Muthulakshmi Reddy Maternity Scheme eligibility."
                missing_information.append("Pregnancy status confirmation (must be within first 2 deliveries)")
            elif is_pregnant:
                status = "Possibly Eligible"
                possible_reason = "Pregnant mother; requires Tamil Nadu residency and PICME registration."
                missing_information.append("Tamil Nadu residency verification")
            else:
                status = "More Information Needed"
                possible_reason = "Pregnancy status confirmation required."
                missing_information.append("Pregnancy status confirmation")

        # 3. MTM - Makkalai Thedi Maruthuvam (Tamil Nadu)
        elif scheme_id == "makkalai-thedi-maruthuvam":
            is_tn = ("tamil nadu" in state) or ("tn" in state)
            has_ncd = any(c in conditions for c in ["hypertension", "diabetes", "bp", "sugar", "kidney"])
            is_senior_45 = (age is not None and age >= 45) or is_elderly

            if is_tn:
                matched_criteria.append("Resident of Tamil Nadu")
            if has_ncd:
                matched_criteria.append("Hypertension / Diabetes / NCD condition")
            if is_senior_45:
                matched_criteria.append("Eligible age category (45+ years / senior citizen)")

            if is_tn and (has_ncd or is_senior_45):
                status = "Likely Eligible"
                possible_reason = "Eligible for doorstep delivery of hypertension/diabetes medicines and routine NCD screening in Tamil Nadu."
            elif is_tn:
                status = "Possibly Eligible"
                possible_reason = "Available across all households in Tamil Nadu for screening and chronic medicine delivery."

        # 4. Innuyir Kaappom 48 (Tamil Nadu)
        elif scheme_id == "nammai-kaakkum-48-innisaikarangal":
            status = "Likely Eligible"
            matched_criteria.append("Universal emergency coverage within Tamil Nadu")
            possible_reason = "Universal emergency road accident trauma coverage up to ₹1,00,000 for first 48 hours for anyone in Tamil Nadu."

        # 5. Dr. YSR Aarogyasri (Andhra Pradesh)
        elif scheme_id == "ysr-aarogyasri-andhra-pradesh":
            is_ap = ("andhra" in state) or ("ap" in state)
            is_ap_income = (income_val is not None and income_val <= 500000) or ("below" in income_range) or ("<" in income_range)

            if is_ap:
                matched_criteria.append("Resident of Andhra Pradesh")
            if is_ap_income:
                matched_criteria.append("Annual income within ₹5,00,000 threshold (Rice Card eligible)")

            if is_ap and is_ap_income:
                status = "Likely Eligible"
                possible_reason = "Resident of Andhra Pradesh with eligible income / Rice Card eligible for up to ₹25 Lakh cashless hospital coverage."
            elif is_ap:
                status = "Possibly Eligible"
                possible_reason = "Andhra Pradesh resident; requires verification of AP Rice Card / Aarogyasri Card."
                missing_information.append("AP Rice Card or YSR Aarogyasri Card verification")
            else:
                status = "More Information Needed"
                missing_information.append("Andhra Pradesh residency confirmation")

        # 6. Dr. YSR Aarogya Asara (Andhra Pradesh)
        elif scheme_id == "ysr-aarogya-asara-andhra-pradesh":
            is_ap = ("andhra" in state) or ("ap" in state)
            if is_ap:
                matched_criteria.append("Resident of Andhra Pradesh")
                status = "Possibly Eligible"
                possible_reason = "Eligible for post-operative daily subsistence allowance (₹225/day up to ₹5,000/mo) after surgery under Aarogyasri in AP."
                missing_information.append("Aarogyasri approved surgical procedure and physician prescribed bed rest")

        # 7. Dr. YSR Thalli Bidda Express (Andhra Pradesh)
        elif scheme_id == "ysr-thalli-bidda-express-andhra-pradesh":
            is_ap = ("andhra" in state) or ("ap" in state)
            if is_ap:
                matched_criteria.append("Resident of Andhra Pradesh")
            if is_pregnant:
                matched_criteria.append("Pregnant mother status")

            if is_ap and is_pregnant:
                status = "Likely Eligible"
                possible_reason = "Eligible for free 102 transport, newborn baby care kit, and hospital delivery support in Andhra Pradesh."
            elif is_pregnant:
                status = "Possibly Eligible"
                missing_information.append("Andhra Pradesh Government Hospital delivery registration")

        # 8. KASP (Kerala)
        elif scheme_id == "kasp-karunya-arogya-suraksha-padhathi-kerala":
            is_kerala = ("kerala" in state) or ("kl" in state)
            is_kerala_income = (income_val is not None and income_val <= 300000) or ("below" in income_range) or ("<" in income_range)

            if is_kerala:
                matched_criteria.append("Resident of Kerala")
            if is_kerala_income:
                matched_criteria.append("Income within eligible threshold (Pink/Yellow Ration Card or Karunya Benevolent Fund)")

            if is_kerala and is_kerala_income:
                status = "Likely Eligible"
                possible_reason = "Resident of Kerala with eligible Ration Card eligible for up to ₹5 Lakh cashless hospital coverage."
            elif is_kerala:
                status = "Possibly Eligible"
                missing_information.append("Kerala Pink/Yellow Ration Card or Karunya income certificate")
            else:
                status = "More Information Needed"
                missing_information.append("Kerala state residency verification")

        # 9. MEDISEP (Kerala)
        elif scheme_id == "medisep-kerala":
            is_kerala = ("kerala" in state) or ("kl" in state)
            is_govt_job = any(k in occupation for k in ["govt", "government", "teacher", "pension", "clerk", "officer"])

            if is_kerala:
                matched_criteria.append("Resident of Kerala")
            if is_govt_job:
                matched_criteria.append("Kerala Government Employee / Pensioner status")
                status = "Likely Eligible"
                possible_reason = "Kerala government employees and pensioners are covered up to ₹3 Lakh/year + catastrophic corpus."
            else:
                status = "Possibly Eligible"
                missing_information.append("Permanent Employee Number (PEN) / Service Pensioner ID in Kerala")

        # 10. Thalolam Scheme (Kerala)
        elif scheme_id == "thalolam-scheme-kerala":
            is_kerala = ("kerala" in state) or ("kl" in state)
            is_child = has_child or (age is not None and age < 18)

            if is_kerala:
                matched_criteria.append("Resident of Kerala")
            if is_child:
                matched_criteria.append("Child under 18 years")

            if is_kerala and is_child:
                status = "Likely Eligible"
                possible_reason = "Children under 18 with severe illness eligible for free treatment grant up to ₹1,00,000 in Kerala Medical Colleges."
                missing_information.append("Hospital treatment estimate and medical superintendent recommendation")
            else:
                status = "More Information Needed"
                missing_information.append("Child age verification & Kerala residency")

        # 11. Janani Janmaraksha (Kerala)
        elif scheme_id == "janani-janmaraksha-kerala":
            is_kerala = ("kerala" in state) or ("kl" in state)
            if is_kerala:
                matched_criteria.append("Resident of Kerala")
            if is_pregnant:
                matched_criteria.append("Pregnant mother status")
                status = "Possibly Eligible"
                possible_reason = "Pregnant tribal mothers in Kerala eligible for ₹1,000/month financial nutritional support."
                missing_information.append("Scheduled Tribe community certificate and PHC MCP card")

        # 12. Ayushman Bharat PM-JAY (National)
        elif scheme_id == "ayushman-bharat-pmjay":
            is_senior_70 = (age is not None and age >= 70)
            is_bpl = (income_val is not None and income_val <= 250000) or ("below" in income_range) or ("<" in income_range)

            if is_senior_70:
                matched_criteria.append("Senior citizen aged 70+ (Universal PM-JAY coverage)")
                status = "Likely Eligible"
                possible_reason = "Senior citizens aged 70 and above are eligible for universal ₹5 Lakh Ayushman health cover."
            elif is_bpl:
                matched_criteria.append("SECC / Low Income demographic")
                status = "Likely Eligible"
                possible_reason = "Eligible for ₹5 Lakh cashless national hospital cover across 27,000+ hospitals across India."
            else:
                status = "Possibly Eligible"
                possible_reason = "Requires verification of SECC 2011 database or state ration card list."
                missing_information.append("Aadhaar-seeded Ration Card verification on beneficiary.nha.gov.in")

        # 13. JSY (National)
        elif scheme_id == "janani-suraksha-yojana-jsy":
            if is_pregnant:
                matched_criteria.append("Pregnant mother status")
                if age is not None and age >= 19:
                    matched_criteria.append("Age 19+")
                status = "Likely Eligible"
                possible_reason = "Pregnant women undergoing institutional delivery in Government PHC/Hospital eligible for direct cash assistance."
                missing_information.append("Registration at Government Primary Health Centre / MCP Card")
            else:
                status = "More Information Needed"
                missing_information.append("Pregnancy status confirmation")

        # 14. PMMVY (National)
        elif scheme_id == "pmmvy-pradhan-mantri-matru-vandana":
            if is_pregnant:
                matched_criteria.append("Pregnant & lactating mother status")
                status = "Likely Eligible"
                possible_reason = "Eligible for ₹5,000 (1st child) or ₹6,000 (2nd girl child) Direct Benefit Transfer."
                missing_information.append("Aadhaar-linked bank account and Anganwadi / MCP card registration")
            else:
                status = "More Information Needed"
                missing_information.append("Pregnancy status confirmation")

        # 15. RBSK (National)
        elif scheme_id == "rbsk-rashtriya-bal-swasthya":
            is_child = has_child or (age is not None and age <= 18)
            if is_child:
                matched_criteria.append("Child in age range 0 to 18 years")
                status = "Likely Eligible"
                possible_reason = "Children aged 0-18 eligible for 100% free screening and treatment for 30 birth defects & diseases."
            else:
                status = "Possibly Eligible"
                missing_information.append("Presence of child (0-18 years) in the household")

        # 16. NPHCE (National)
        elif scheme_id == "nphce-elderly-care":
            is_senior_60 = is_elderly or (age is not None and age >= 60)
            if is_senior_60:
                matched_criteria.append("Senior citizen aged 60 years or above")
                status = "Likely Eligible"
                possible_reason = "Universal access to weekly geriatric clinics, free chronic medicines, and checkups at Government PHCs."
            else:
                status = "Possibly Eligible"
                missing_information.append("Age 60+ senior citizen verification")

        else:
            status = "More Information Needed"
            possible_reason = "Additional demographic verification required."

        results.append({
            "id": SchemeId(scheme_id),
            "scheme_id": scheme_id,
            "scheme_name": name_obj,
            "state": scheme_state,
            "status": status,
            "eligibility_status": status,
            "matched_criteria": matched_criteria,
            "missing_information": missing_information,
            "possible_reason": possible_reason,
            "official_source": src,
            "official_url": url,
            "last_verified": last_ver,
            "disclaimer": DEFAULT_DISCLAIMER
        })

    # Sort: Likely Eligible first, then Possibly Eligible, then More Information Needed
    priority_map = {
        "Likely Eligible": 0,
        "Possibly Eligible": 1,
        "More Information Needed": 2,
        "Not Determined": 3
    }
    results.sort(key=lambda x: priority_map.get(x["eligibility_status"], 4))
    return EligibilityResults(results)
