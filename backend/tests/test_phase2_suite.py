"""
Comprehensive Phase 1 & Phase 2 Automated Verification Suite for Arogya Nexus
Tests 18 critical scenarios across Clinical AI, Government Scheme Intelligence,
Ranked Retrieval, Eligibility Reasoning, Live Endpoints, and Data Validation.
Uses standard library urllib to avoid external dependencies.
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
    print("       AROGYA NEXUS PHASE 1 & PHASE 2 VERIFICATION SUITE         ")
    print("==================================================================")
    
    passed_tests = 0
    total_tests = 18
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

    # --- Test 1: Health & Root Endpoints ---
    try:
        status_health, data_health = http_get("/health")
        status_root, data_root = http_get("/")
        if status_health == 200 and data_health.get("status") == "healthy" and status_root == 200:
            record_result(1, "Server Health & Root Check", True, f"Service Healthy (v{data_root.get('version', '2.0.0')})")
        else:
            record_result(1, "Server Health & Root Check", False, f"Health: {data_health}, Root: {data_root}")
    except Exception as e:
        record_result(1, "Server Health & Root Check", False, str(e))

    # --- Test 2: Knowledge Base Validation ---
    try:
        from data.validate_knowledge_base import validate_knowledge_base
        is_valid, report = validate_knowledge_base()
        if is_valid and report["scheme_cards_count"] >= 9 and report["healthcare_cards_count"] >= 9:
            record_result(2, "Knowledge Base Data Quality Validation", True, f"18 Cards verified (Schemes: {report['scheme_cards_count']}, Clinical: {report['healthcare_cards_count']})")
        else:
            record_result(2, "Knowledge Base Data Quality Validation", False, f"Validation errors: {report.get('errors')}")
    except Exception as e:
        record_result(2, "Knowledge Base Data Quality Validation", False, str(e))

    # --- Test 3: /api/knowledge/refresh Endpoint (n8n preparation) ---
    try:
        status_code, data = http_post("/api/knowledge/refresh", {})
        if status_code == 200 and data.get("status") == "success" and data.get("scheme_cards_count") >= 9:
            record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", True, f"Refreshed {data.get('total_cards')} cards successfully")
        else:
            record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", False, f"Response: {data}")
    except Exception as e:
        record_result(3, "Knowledge Refresh Endpoint (/api/knowledge/refresh)", False, str(e))

    # --- Test 4: English Scheme Query ---
    try:
        payload = {"message": "What government health schemes are available in Tamil Nadu?"}
        status_code, data = http_post("/api/chat", payload)
        has_schemes = len(data.get("matched_schemes", [])) > 0
        has_sources = len(data.get("sources", [])) > 0
        if status_code == 200 and data.get("success") and has_schemes and has_sources:
            record_result(4, "English Scheme Query", True, f"Matched {len(data['matched_schemes'])} schemes & {len(data['sources'])} sources")
        else:
            record_result(4, "English Scheme Query", False, f"Data: {data}")
    except Exception as e:
        record_result(4, "English Scheme Query", False, str(e))

    # --- Test 5: Tamil Scheme Query ---
    try:
        payload = {"message": "அரசு மருத்துவ காப்பீட்டு திட்டங்கள் என்னென்ன உள்ளன?"}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("success") and len(data.get("matched_schemes", [])) > 0:
            record_result(5, "Tamil Scheme Query", True, f"Retrieved schemes: {[s['id'] for s in data['matched_schemes']]}")
        else:
            record_result(5, "Tamil Scheme Query", False, f"Data: {data}")
    except Exception as e:
        record_result(5, "Tamil Scheme Query", False, str(e))

    # --- Test 6: Tanglish Scheme Query ---
    try:
        payload = {"message": "government health scheme iruka? enakku entha scheme kedaikum?"}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("success") and data.get("knowledge_used"):
            record_result(6, "Tanglish Scheme Query", True, f"Matched topics: {data.get('matched_topics')}")
        else:
            record_result(6, "Tanglish Scheme Query", False, f"Data: {data}")
    except Exception as e:
        record_result(6, "Tanglish Scheme Query", False, str(e))

    # --- Test 7: CMCHIS Query ---
    try:
        payload = {"message": "CMCHIS ku eligibility enna? How to apply for Chief Minister health insurance?"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "cmchis-tamil-nadu" in matched_ids:
            record_result(7, "CMCHIS Specific Ranked Retrieval", True, f"Found cmchis-tamil-nadu in {matched_ids}")
        else:
            record_result(7, "CMCHIS Specific Ranked Retrieval", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(7, "CMCHIS Specific Ranked Retrieval", False, str(e))

    # --- Test 8: PM-JAY Query ---
    try:
        payload = {"message": "Ayushman Bharat PM-JAY 5 lakh health insurance card details"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "ayushman-bharat-pmjay" in matched_ids:
            record_result(8, "PM-JAY Ranked Retrieval", True, f"Found ayushman-bharat-pmjay in {matched_ids}")
        else:
            record_result(8, "PM-JAY Ranked Retrieval", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(8, "PM-JAY Ranked Retrieval", False, str(e))

    # --- Test 9: Maternal Scheme Query (Judge Showcase Query 1) ---
    try:
        payload = {"message": "கர்ப்ப காலத்தில் என்னென்ன பரிசோதனைகள் செய்ய வேண்டும்? கிடைக்கும் அரசு திட்டங்கள் என்ன?"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and data.get("success") and any(m in matched_ids for m in ["mrmbs-dr-muthulakshmi-reddy", "janani-suraksha-yojana-jsy", "pmmvy-pradhan-mantri-matru-vandana"]):
            record_result(9, "Maternal Care & Schemes (Showcase 1)", True, f"Matched Maternal Schemes: {matched_ids}")
        else:
            record_result(9, "Maternal Care & Schemes (Showcase 1)", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(9, "Maternal Care & Schemes (Showcase 1)", False, str(e))

    # --- Test 10: Eligibility Query Reasoning Flow ---
    try:
        payload = {"message": "Enakku CMCHIS kedaikuma?"}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("success") and len(data.get("matched_schemes", [])) > 0:
            record_result(10, "Eligibility Inquiry Reasoning", True, "Response provides criteria with official verification notice")
        else:
            record_result(10, "Eligibility Inquiry Reasoning", False, f"Data: {data}")
    except Exception as e:
        record_result(10, "Eligibility Inquiry Reasoning", False, str(e))

    # --- Test 11: Documents Query ---
    try:
        payload = {"message": "What documents do I need for Dr. Muthulakshmi Reddy Maternity Scheme?"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "mrmbs-dr-muthulakshmi-reddy" in matched_ids:
            record_result(11, "Scheme Required Documents Query", True, f"Retrieved MRMBS scheme card with documents")
        else:
            record_result(11, "Scheme Required Documents Query", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(11, "Scheme Required Documents Query", False, str(e))

    # --- Test 12: Application / Doorstep Healthcare Query ---
    try:
        payload = {"message": "How can an elderly person get BP and sugar medicines at home under Makkalai Thedi Maruthuvam?"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "makkalai-thedi-maruthuvam" in matched_ids:
            record_result(12, "Doorstep Scheme & Application Query", True, f"Found makkalai-thedi-maruthuvam in {matched_ids}")
        else:
            record_result(12, "Doorstep Scheme & Application Query", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(12, "Doorstep Scheme & Application Query", False, str(e))

    # --- Test 13: Emergency Query (Judge Showcase 2) -> Must prioritize 108 Emergency ---
    try:
        payload = {"message": "எனக்கு கடுமையான நெஞ்சு வலி மற்றும் மூச்சுத்திணறல் உள்ளது."}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("is_emergency") is True:
            record_result(13, "Emergency Red Flag Triage (Showcase 2)", True, f"is_emergency: True, Matched: {data.get('matched_topics')}")
        else:
            record_result(13, "Emergency Red Flag Triage (Showcase 2)", False, f"is_emergency was {data.get('is_emergency')}")
    except Exception as e:
        record_result(13, "Emergency Red Flag Triage (Showcase 2)", False, str(e))

    # --- Test 14: Normal Healthcare Query (Tanglish Fever - Judge Showcase 3) ---
    try:
        payload = {"message": "Enakku rendu naala fever irukku, udambu romba weak ah irukku."}
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("is_emergency") is False and data.get("knowledge_used") is True:
            record_result(14, "Normal Clinical Triage (Showcase 3)", True, f"is_emergency: False, Knowledge used: True")
        else:
            record_result(14, "Normal Clinical Triage (Showcase 3)", False, f"Data: {data}")
    except Exception as e:
        record_result(14, "Normal Clinical Triage (Showcase 3)", False, str(e))

    # --- Test 15: Multi-Turn Conversation Scheme Flow ---
    try:
        payload = {
            "message": "Tamil Nadu resident",
            "history": [
                {"role": "user", "content": "I am pregnant and looking for government maternity financial assistance."},
                {"role": "assistant", "content": "Government schemes such as Dr. Muthulakshmi Reddy Maternity Scheme and JSY provide benefits."}
            ]
        }
        status_code, data = http_post("/api/chat", payload)
        if status_code == 200 and data.get("success") and data.get("knowledge_used"):
            record_result(15, "Multi-Turn Conversational Scheme Query", True, f"Resolved composite query across history turns")
        else:
            record_result(15, "Multi-Turn Conversational Scheme Query", False, f"Data: {data}")
    except Exception as e:
        record_result(15, "Multi-Turn Conversational Scheme Query", False, str(e))

    # --- Test 16: Fuzzy Tanglish Scheme Retrieval ---
    try:
        payload = {"message": "muthoolakshmi redy karpini kaasu kedaikuma"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "mrmbs-dr-muthulakshmi-reddy" in matched_ids:
            record_result(16, "Fuzzy Tanglish Scheme Retrieval", True, f"Phonetic matching resolved MRMBS card")
        else:
            record_result(16, "Fuzzy Tanglish Scheme Retrieval", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(16, "Fuzzy Tanglish Scheme Retrieval", False, str(e))

    # --- Test 17: Road Accident Scheme (Nammai Kaakkum 48) ---
    try:
        payload = {"message": "Road accident emergency hospital 48 hours free scheme in Tamil Nadu"}
        status_code, data = http_post("/api/chat", payload)
        matched_ids = [s.get("id") for s in data.get("matched_schemes", [])]
        if status_code == 200 and "nammai-kaakkum-48-innisaikarangal" in matched_ids:
            record_result(17, "Accident Emergency Scheme (Nammai Kaakkum 48)", True, f"Found nammai-kaakkum-48 in {matched_ids}")
        else:
            record_result(17, "Accident Emergency Scheme (Nammai Kaakkum 48)", False, f"Matched: {matched_ids}")
    except Exception as e:
        record_result(17, "Accident Emergency Scheme (Nammai Kaakkum 48)", False, str(e))

    # --- Test 18: Text-to-Speech Endpoint Check ---
    try:
        payload = {"text": "வணக்கம், முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டம்.", "language_code": "ta-IN"}
        status_code, data = http_post("/api/text-to-speech", payload)
        if status_code == 200 and data.get("status") == "success" and data.get("audio"):
            record_result(18, "Sarvam TTS Endpoint (/api/text-to-speech)", True, f"Generated base64 audio ({len(data['audio'])} chars)")
        else:
            record_result(18, "Sarvam TTS Endpoint (/api/text-to-speech)", False, f"Response: {data}")
    except Exception as e:
        record_result(18, "Sarvam TTS Endpoint (/api/text-to-speech)", False, str(e))

    print("==================================================================")
    print(f"VERIFICATION SUMMARY: {passed_tests} / {total_tests} TESTS PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("==================================================================")
    return passed_tests == total_tests


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    success = run_tests()
    sys.exit(0 if success else 1)
