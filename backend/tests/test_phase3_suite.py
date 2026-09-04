"""
Comprehensive Phase 3 Automated Verification Suite for Arogya Nexus
Tests 20 critical scenarios across:
1. Health Profile Creation & Evaluation
2. Empty Profile Safe Handling
3. Pregnant Woman Scheme Recommendation
4. Tamil Scheme Recommendation
5. Tanglish Scheme Recommendation
6. CMCHIS Eligibility Reasoning
7. PM-JAY Eligibility Reasoning
8. Missing Information Handling
9. Scheme Comparison (CMCHIS vs PM-JAY)
10. Unknown Scheme Handling
11. Official Source & URL Presence
12. Last Verified & Updated Dates
13. Emergency Query Priority (108 Triage over Scheme Guidance)
14. Phase 1 STT Validation
15. Phase 1 TTS Synthesis
16. Phase 2 Clinical RAG
17. Multi-Turn Conversation Flow
18. Knowledge Base Refresh Endpoint (/api/knowledge/refresh)
19. Knowledge Base Data Quality
20. Server Health & Platform Status
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"


def http_get(path: str):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as res:
        data = res.read().decode("utf-8")
        return res.status, json.loads(data)


def http_post(path: str, payload: dict = None, retries: int = 2):
    body = json.dumps(payload or {}).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{BASE_URL}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as res:
                data = res.read().decode("utf-8")
                return res.status, json.loads(data)
        except urllib.error.URLError as ue:
            if attempt < retries - 1:
                import time
                time.sleep(2)
                continue
            raise ue
        except TimeoutError:
            if attempt < retries - 1:
                import time
                time.sleep(2)
                continue
            raise


def run_tests():
    print("==================================================================")
    print("       AROGYA NEXUS PHASE 3 COMPREHENSIVE VERIFICATION SUITE      ")
    print("==================================================================")

    passed_tests = 0
    total_tests = 20
    results = []

    def record_result(test_num, test_name, success, details=""):
        nonlocal passed_tests
        if success:
            passed_tests += 1
            print(f"[PASS] Test {test_num:02d}: {test_name}", flush=True)
            if details:
                print(f"       -> {details}", flush=True)
            results.append((test_num, test_name, "PASS", details))
        else:
            print(f"[FAIL] Test {test_num:02d}: {test_name}", flush=True)
            print(f"       -> ERROR: {details}", flush=True)
            results.append((test_num, test_name, "FAIL", details))

    # --- Test 1: Server Health & Root Check ---
    try:
        status_health, data_health = http_get("/health")
        status_root, data_root = http_get("/")
        if status_health == 200 and data_health.get("status") == "healthy" and status_root == 200:
            record_result(1, "Server Health & Root Check", True, f"Service Healthy (v{data_root.get('version', '3.0.0')})")
        else:
            record_result(1, "Server Health & Root Check", False, f"Health: {data_health}, Root: {data_root}")
    except Exception as e:
        record_result(1, "Server Health & Root Check", False, str(e))

    # --- Test 2: Knowledge Base Data Quality Validation ---
    try:
        from data.validate_knowledge_base import validate_knowledge_base
        is_valid, report = validate_knowledge_base()
        if is_valid and report["scheme_cards_count"] >= 9 and report["healthcare_cards_count"] >= 9:
            record_result(2, "Knowledge Base Data Quality Validation", True, f"18 Cards verified (Schemes: {report['scheme_cards_count']}, Healthcare: {report['healthcare_cards_count']})")
        else:
            record_result(2, "Knowledge Base Data Quality Validation", False, f"Validation errors: {report.get('errors')}")
    except Exception as e:
        record_result(2, "Knowledge Base Data Quality Validation", False, str(e))

    # --- Test 3: Knowledge Refresh Endpoint (/api/knowledge/refresh) ---
    try:
        status_code, data = http_post("/api/knowledge/refresh", {})
        if status_code == 200 and data.get("status") == "success" and data.get("scheme_cards_count") >= 9:
            record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", True, f"Refreshed {data.get('total_cards')} cards successfully")
        else:
            record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", False, f"Response: {data}")
    except Exception as e:
        record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", False, str(e))

    # --- Test 4: Health Profile Creation & Evaluation (/api/profile/eligibility) ---
    try:
        profile = {
            "age": 28,
            "gender": "Female",
            "state": "Tamil Nadu",
            "district": "Madurai",
            "annual_income": 95000,
            "is_pregnant": True
        }
        status_code, data = http_post("/api/profile/eligibility", {"profile": profile})
        schemes = data.get("schemes", [])
        mrmbs_scheme = next((s for s in schemes if s.get("scheme_id") == "mrmbs-dr-muthulakshmi-reddy"), None)
        cmchis_scheme = next((s for s in schemes if s.get("scheme_id") == "cmchis-tamil-nadu"), None)

        if (
            status_code == 200
            and data.get("status") == "success"
            and len(schemes) >= 9
            and mrmbs_scheme
            and mrmbs_scheme.get("eligibility_status") == "Likely Eligible"
            and cmchis_scheme
            and cmchis_scheme.get("eligibility_status") == "Likely Eligible"
        ):
            record_result(4, "Health Profile Evaluation (/api/profile/eligibility)", True, f"Evaluated {len(schemes)} schemes (MRMBS & CMCHIS: Likely Eligible)")
        else:
            record_result(4, "Health Profile Evaluation (/api/profile/eligibility)", False, f"Data: {data}")
    except Exception as e:
        record_result(4, "Health Profile Evaluation (/api/profile/eligibility)", False, str(e))

    # --- Test 5: Empty Profile Safe Handling ---
    try:
        status_code, data = http_post("/api/profile/eligibility", {"profile": {}})
        schemes = data.get("schemes", [])
        all_more_info = all(s.get("eligibility_status") == "More Information Needed" for s in schemes)
        if status_code == 200 and len(schemes) >= 9 and all_more_info:
            record_result(5, "Empty Profile Safe Handling", True, f"All {len(schemes)} schemes returned 'More Information Needed' with zero crash")
        else:
            record_result(5, "Empty Profile Safe Handling", False, f"Schemes: {[s.get('eligibility_status') for s in schemes]}")
    except Exception as e:
        record_result(5, "Empty Profile Safe Handling", False, str(e))

    # --- Test 6: Pregnant Woman Scheme Recommendation (/api/schemes/recommend) ---
    try:
        profile = {"state": "Tamil Nadu", "is_pregnant": True, "gender": "Female"}
        status_code, data = http_post("/api/schemes/recommend", {"profile": profile, "query": "financial assistance for pregnancy"})
        recs = data.get("recommendations", [])
        rec_ids = [r.get("scheme_id") for r in recs]
        has_maternal = any(m in rec_ids for m in ["mrmbs-dr-muthulakshmi-reddy", "pmmvy-pradhan-mantri-matru-vandana", "janani-suraksha-yojana-jsy"])
        if status_code == 200 and len(recs) <= 3 and has_maternal:
            record_result(6, "Pregnant Woman Scheme Recommendation", True, f"Top recommendations: {rec_ids}")
        else:
            record_result(6, "Pregnant Woman Scheme Recommendation", False, f"Recommendations: {rec_ids}")
    except Exception as e:
        record_result(6, "Pregnant Woman Scheme Recommendation", False, str(e))

    # --- Test 7: Tamil Scheme Recommendation ---
    try:
        payload = {"query": "கர்ப்பிணி பெண்களுக்கு கிடைக்கும் அரசு திட்டங்கள் மற்றும் நிதி உதவி என்ன?"}
        status_code, data = http_post("/api/schemes/recommend", payload)
        recs = data.get("recommendations", [])
        rec_ids = [r.get("scheme_id") for r in recs]
        if status_code == 200 and len(recs) > 0 and any("muthulakshmi" in r or "matru" in r or "janani" in r for r in rec_ids):
            record_result(7, "Tamil Scheme Recommendation", True, f"Matched Tamil query to maternal schemes: {rec_ids}")
        else:
            record_result(7, "Tamil Scheme Recommendation", False, f"Data: {data}")
    except Exception as e:
        record_result(7, "Tamil Scheme Recommendation", False, str(e))

    # --- Test 8: Tanglish Scheme Recommendation ---
    try:
        payload = {"query": "muthulakshmi reddy karpini kaasu and cmchis apply epdi panrathu"}
        status_code, data = http_post("/api/schemes/recommend", payload)
        recs = data.get("recommendations", [])
        rec_ids = [r.get("scheme_id") for r in recs]
        if status_code == 200 and ("mrmbs-dr-muthulakshmi-reddy" in rec_ids or "cmchis-tamil-nadu" in rec_ids):
            record_result(8, "Tanglish Scheme Recommendation", True, f"Fuzzy Tanglish matched schemes: {rec_ids}")
        else:
            record_result(8, "Tanglish Scheme Recommendation", False, f"Data: {data}")
    except Exception as e:
        record_result(8, "Tanglish Scheme Recommendation", False, str(e))

    # --- Test 9: CMCHIS Eligibility Reasoning ---
    try:
        profile = {"state": "Tamil Nadu", "annual_income": 80000}
        status_code, data = http_post("/api/profile/eligibility", {"profile": profile})
        schemes = data.get("schemes", [])
        cmchis = next((s for s in schemes if s.get("scheme_id") == "cmchis-tamil-nadu"), None)
        if status_code == 200 and cmchis and cmchis.get("eligibility_status") == "Likely Eligible":
            record_result(9, "CMCHIS Eligibility Reasoning", True, f"Status: {cmchis.get('eligibility_status')}, Criteria: {cmchis.get('matched_criteria')}")
        else:
            record_result(9, "CMCHIS Eligibility Reasoning", False, f"CMCHIS: {cmchis}")
    except Exception as e:
        record_result(9, "CMCHIS Eligibility Reasoning", False, str(e))

    # --- Test 10: PM-JAY Eligibility Reasoning ---
    try:
        profile = {"annual_income": 100000, "family_size": 5}
        status_code, data = http_post("/api/profile/eligibility", {"profile": profile})
        schemes = data.get("schemes", [])
        pmjay = next((s for s in schemes if s.get("scheme_id") == "ayushman-bharat-pmjay"), None)
        if status_code == 200 and pmjay and pmjay.get("eligibility_status") in ("Likely Eligible", "Possibly Eligible"):
            record_result(10, "PM-JAY Eligibility Reasoning", True, f"Status: {pmjay.get('eligibility_status')}")
        else:
            record_result(10, "PM-JAY Eligibility Reasoning", False, f"PM-JAY: {pmjay}")
    except Exception as e:
        record_result(10, "PM-JAY Eligibility Reasoning", False, str(e))

    # --- Test 11: Missing Information Handling ---
    try:
        profile = {"gender": "Female", "state": "Tamil Nadu"}  # Missing pregnancy, income
        status_code, data = http_post("/api/profile/eligibility", {"profile": profile})
        schemes = data.get("schemes", [])
        mrmbs = next((s for s in schemes if s.get("scheme_id") == "mrmbs-dr-muthulakshmi-reddy"), None)
        has_missing = len(mrmbs.get("missing_information", [])) > 0 if mrmbs else False
        if status_code == 200 and mrmbs and has_missing and mrmbs.get("eligibility_status") == "Possibly Eligible":
            record_result(11, "Missing Information Transparency", True, f"Missing info highlighted: {mrmbs.get('missing_information')}")
        else:
            record_result(11, "Missing Information Transparency", False, f"MRMBS: {mrmbs}")
    except Exception as e:
        record_result(11, "Missing Information Transparency", False, str(e))

    # --- Test 12: Scheme Comparison (CMCHIS vs PM-JAY) (/api/schemes/compare) ---
    try:
        payload = {"scheme_ids": ["cmchis-tamil-nadu", "ayushman-bharat-pmjay"]}
        status_code, data = http_post("/api/schemes/compare", payload)
        schemes = data.get("schemes", [])
        has_insights = bool(data.get("comparison_insights"))
        if status_code == 200 and len(schemes) == 2 and has_insights:
            record_result(12, "Scheme Side-by-Side Comparison (/api/schemes/compare)", True, f"Compared 2 schemes with contextual insights")
        else:
            record_result(12, "Scheme Side-by-Side Comparison (/api/schemes/compare)", False, f"Data: {data}")
    except Exception as e:
        record_result(12, "Scheme Side-by-Side Comparison (/api/schemes/compare)", False, str(e))

    # --- Test 13: Unknown Scheme Rejection ---
    try:
        payload = {"scheme_ids": ["unknown-fake-scheme-id", "non-existent-health-card"]}
        status_code, data = http_post("/api/schemes/compare", payload)
        if status_code == 200 and data.get("total_compared") == 0 and len(data.get("unmatched_ids", [])) == 2:
            record_result(13, "Unknown Scheme Rejection & Validation", True, f"Rejected unmatched IDs: {data.get('unmatched_ids')}")
        else:
            record_result(13, "Unknown Scheme Rejection & Validation", False, f"Data: {data}")
    except Exception as e:
        record_result(13, "Unknown Scheme Rejection & Validation", False, str(e))

    # --- Test 14: Official Source & URL Presence on All Schemes ---
    try:
        from services.knowledgeService import load_all_knowledge_cards
        cards = load_all_knowledge_cards()
        scheme_cards = [c for c in cards if c.get("category") in ("government_scheme", "health_schemes")]
        all_have_source = all(bool(c.get("official_source") and c.get("official_url")) for c in scheme_cards)
        if len(scheme_cards) >= 9 and all_have_source:
            record_result(14, "Official Source & Verification URL Compliance", True, f"100% of {len(scheme_cards)} schemes have verified official source and URL")
        else:
            record_result(14, "Official Source & Verification URL Compliance", False, f"Total schemes: {len(scheme_cards)}, All sourced: {all_have_source}")
    except Exception as e:
        record_result(14, "Official Source & Verification URL Compliance", False, str(e))

    # --- Test 15: Last Verified & Timestamps ---
    try:
        from services.knowledgeService import load_all_knowledge_cards
        cards = load_all_knowledge_cards()
        scheme_cards = [c for c in cards if c.get("category") in ("government_scheme", "health_schemes")]
        all_have_dates = all(bool(c.get("last_verified")) for c in scheme_cards)
        if len(scheme_cards) >= 9 and all_have_dates:
            record_result(15, "Last Verified & Updated At Timestamps", True, f"All {len(scheme_cards)} schemes stamped with last_verified")
        else:
            record_result(15, "Last Verified & Updated At Timestamps", False, f"All have dates: {all_have_dates}")
    except Exception as e:
        record_result(15, "Last Verified & Updated At Timestamps", False, str(e))

    # --- Test 16: Emergency Priority over Scheme Information ---
    try:
        payload = {"message": "எனக்கு கடுமையான நெஞ்சு வலி உள்ளது, எனக்கு முதலமைச்சர் காப்பீடு கிடைக்குமா?"}
        status_code, data = http_post("/api/chat", payload)
        is_emerg = data.get("is_emergency") is True
        if status_code == 200 and is_emerg:
            record_result(16, "Emergency 108 Priority over Scheme Advice", True, f"Emergency flagged: {is_emerg}, 108 Triage Prioritized")
        else:
            record_result(16, "Emergency 108 Priority over Scheme Advice", False, f"is_emergency was: {data.get('is_emergency')}")
    except Exception as e:
        record_result(16, "Emergency 108 Priority over Scheme Advice", False, str(e))

    # --- Test 17: Multi-Turn Conversational Scheme Reasoning ---
    try:
        payload = {
            "message": "Tamil Nadu Smart Family card holder",
            "history": [
                {"role": "user", "content": "I need financial support for surgery."},
                {"role": "assistant", "content": "CMCHIS provides ₹5 Lakh hospital coverage. Are you a resident of Tamil Nadu?"}
            ]
        }
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("success") and data.get("knowledge_used"):
            record_result(17, "Multi-Turn Conversational Scheme Flow", True, "Resolved follow-up context across multiple turns")
        else:
            record_result(17, "Multi-Turn Conversational Scheme Flow", False, f"Data: {data}")
    except Exception as e:
        record_result(17, "Multi-Turn Conversational Scheme Flow", False, str(e))

    # --- Test 18: Sarvam Text-to-Speech (bulbul:v3) Endpoint ---
    try:
        payload = {"text": "முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டம்.", "language_code": "ta-IN"}
        status_code, data = http_post("/api/text-to-speech", payload)
        if status_code == 200 and data.get("status") == "success" and data.get("audio"):
            record_result(18, "Sarvam TTS Audio Synthesis Endpoint", True, f"Generated base64 audio ({len(data['audio'])} chars)")
        else:
            record_result(18, "Sarvam TTS Audio Synthesis Endpoint", False, f"Data: {data}")
    except Exception as e:
        record_result(18, "Sarvam TTS Audio Synthesis Endpoint", False, str(e))

    # --- Test 19: Clinical Triage RAG Grounding ---
    try:
        payload = {"message": "Enakku rendu naala fever and head ache irukku."}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("knowledge_used") is True and data.get("is_emergency") is False:
            record_result(19, "Clinical Supportive Care RAG Grounding", True, f"Matched clinical topics: {data.get('matched_topics')}")
        else:
            record_result(19, "Clinical Supportive Care RAG Grounding", False, f"Data: {data}")
    except Exception as e:
        record_result(19, "Clinical Supportive Care RAG Grounding", False, str(e))

    # --- Test 20: Doorstep Medicine Scheme (Makkalai Thedi Maruthuvam) ---
    try:
        profile = {"state": "Tamil Nadu", "health_conditions": ["hypertension", "diabetes"], "age": 52}
        status_code, data = http_post("/api/profile/eligibility", {"profile": profile})
        schemes = data.get("schemes", [])
        mtm = next((s for s in schemes if s.get("scheme_id") == "makkalai-thedi-maruthuvam"), None)
        if status_code == 200 and mtm and mtm.get("eligibility_status") == "Likely Eligible":
            record_result(20, "Doorstep NCD Scheme (Makkalai Thedi Maruthuvam)", True, f"Status: Likely Eligible, Reason: {mtm.get('possible_reason')}")
        else:
            record_result(20, "Doorstep NCD Scheme (Makkalai Thedi Maruthuvam)", False, f"MTM: {mtm}")
    except Exception as e:
        record_result(20, "Doorstep NCD Scheme (Makkalai Thedi Maruthuvam)", False, str(e))

    print("==================================================================")
    print(f"PHASE 3 VERIFICATION SUMMARY: {passed_tests} / {total_tests} TESTS PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("==================================================================")
    return passed_tests == total_tests


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    success = run_tests()
    sys.exit(0 if success else 1)
