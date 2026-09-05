"""
Arogya Nexus — Production Matrix Verification & Latency Benchmarks
Executes all 40 core scenarios + AI Health Image Assistant scenarios.
Measures real response times and verifies strict medical safety rules.
"""

import sys
import time
import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from services.intentRouter import classify_intent
from services.llmService import generate_healthcare_response
from services.hospitalService import get_nearby_hospitals
from services.eligibilityService import evaluate_profile_eligibility
from services.schemeComparisonService import compare_schemes
from services.imageService import analyze_health_image

client = TestClient(app)


# =========================================================================
# SCENARIOS 1-5: HIGH-SPEED EMERGENCIES (Short-circuit, deterministic, <100ms)
# =========================================================================
@pytest.mark.parametrize("query,expected_keyword", [
    ("Help! Severe chest pain and sudden sweating!", "108"),
    ("My father collapsed and is unconscious!", "108"),
    ("Emergency: Poisonous snake bite on foot in farm!", "ASV"),
    ("Accident on highway, heavy bleeding from leg!", "108"),
    ("Patient stopped breathing and is fainting!", "108"),
])
def test_scenarios_01_to_05_emergencies(query, expected_keyword):
    start = time.perf_counter()
    res = generate_healthcare_response(query, language_code="en-IN")
    duration_ms = (time.perf_counter() - start) * 1000

    assert res["is_emergency"] is True, f"Failed for {query}"
    assert res["intent"] == "EMERGENCY"
    assert "108" in res["response"]
    assert duration_ms < 100, f"Emergency latency too high: {duration_ms:.2f}ms"
    print(f"\n[LATENCY BENCHMARK] Emergency query {query[:30]!r}: {duration_ms:.2f}ms")


# =========================================================================
# SCENARIOS 6-10: PURE HEALTH SYMPTOM QUERIES (NO UNWANTED SCHEME DUMPING)
# =========================================================================
@pytest.mark.parametrize("query", [
    "I have high fever and shivering since yesterday.",
    "Severe diarrhea and dehydration since morning.",
    "Throbbing headache with sensitivity to light.",
    "Persistent dry cough and sore throat for two days.",
    "Severe generalized body ache and fatigue.",
])
def test_scenarios_06_to_10_symptom_queries_no_schemes(query):
    intent, meta = classify_intent(query, language_code="en-IN")
    assert intent == "HEALTH_QUERY", f"Wrong intent for {query}: {intent}"

    res = generate_healthcare_response(query, language_code="en-IN")
    assert res["is_emergency"] is False
    assert res["intent"] == "HEALTH_QUERY"
    # Verify NO government scheme cards dumped in matched_schemes for pure symptoms
    assert len(res.get("matched_schemes", [])) == 0, f"Scheme dumping detected for pure symptom {query}"

    resp_text = res["response"].lower()
    # Must contain safe clinical guidance elements
    assert any(term in resp_text for term in ["water", "fluid", "rest", "phc", "doctor", "monitor", "warning"])
    # Must NOT contain application instructions for schemes
    assert "where to apply" not in resp_text
    assert "required documents" not in resp_text


# =========================================================================
# SCENARIOS 11-15: EXPLICIT GOVERNMENT SCHEME QUERIES
# =========================================================================
@pytest.mark.parametrize("query,expected_scheme_id", [
    ("What are the benefits and eligibility for CMCHIS in Tamil Nadu?", "cmchis"),
    ("Tell me about Ayushman Bharat PM-JAY 5 lakh hospital cover.", "pmjay"),
    ("How does Dr YSR Aarogyasri scheme work in Andhra Pradesh?", "aarogyasri"),
    ("Explain Karunya Arogya Suraksha Padhathi (KASP) in Kerala.", "kasp"),
    ("Tell me about Dr Muthulakshmi Reddy Maternity Scheme 18000 financial aid.", "mrmbs"),
])
def test_scenarios_11_to_15_scheme_queries(query, expected_scheme_id):
    intent, meta = classify_intent(query, language_code="en-IN")
    assert intent == "SCHEME_QUERY", f"Expected SCHEME_QUERY for {query}, got {intent}"

    res = generate_healthcare_response(query, language_code="en-IN")
    assert res["is_emergency"] is False
    assert len(res["matched_schemes"]) > 0
    matched_ids = [s["id"] for s in res["matched_schemes"]]
    assert expected_scheme_id in matched_ids, f"Expected {expected_scheme_id} in {matched_ids}"


# =========================================================================
# SCENARIOS 16-20: TANGLISH CLINICAL QUERIES (TAMIL INTENT & CONTEXT)
# =========================================================================
@pytest.mark.parametrize("query", [
    "enakku fever irukku enna panrathu",
    "thala vali romba athigama irukku",
    "vayiru vali and vanti varuthu",
    "nenju erichal and mayakkam varuthu",
    "enakku sugar and bp check pannanum hospital enga irukku",
])
def test_scenarios_16_to_20_tanglish_queries(query):
    intent, meta = classify_intent(query, language_code="ta-IN")
    assert intent in ("HEALTH_QUERY", "NEARBY_HEALTHCARE"), f"Unexpected intent {intent} for Tanglish {query}"

    res = generate_healthcare_response(query, language_code="ta-IN")
    assert res["response"] is not None
    assert len(res["response"]) > 20


# =========================================================================
# SCENARIOS 21-25: TELUGU AND MALAYALAM QUERIES
# =========================================================================
@pytest.mark.parametrize("query,lang,expected_intent", [
    ("నాకు తీవ్రమైన జ్వరం మరియు ఒళ్ళు నొప్పులు ఉన్నాయి", "te-IN", "HEALTH_QUERY"),
    ("తీవ్రమైన కడుపు నొప్పి మరియు విరేచనాలు వస్తున్నాయి", "te-IN", "HEALTH_QUERY"),
    ("ఎన్టీఆర్ లేదా వైఎస్ఆర్ ఆరోగ్యశ్రీ పథకం వివరాలు తెలపండి", "te-IN", "SCHEME_QUERY"),
    ("എനിക്ക് കടുത്ത പനിയും തലവേദനയും ഉണ്ട്", "ml-IN", "HEALTH_QUERY"),
    ("കാരുണ്യ ആരോഗ്യ സുരക്ഷാ പദ്ധതി (KASP) ആനുകൂല്യങ്ങൾ എന്തൊക്കെയാണ്?", "ml-IN", "SCHEME_QUERY"),
])
def test_scenarios_21_to_25_telugu_malayalam(query, lang, expected_intent):
    intent, meta = classify_intent(query, language_code=lang)
    assert intent == expected_intent, f"Failed intent classification for {query}"

    res = generate_healthcare_response(query, language_code=lang)
    assert len(res["response"]) > 10


# =========================================================================
# SCENARIOS 26-28: COMPLEX MULTI-SYMPTOM QUERIES
# =========================================================================
@pytest.mark.parametrize("query", [
    "High fever for 4 days, persistent vomiting, yellow eyes, and dark urine.",
    "Elderly grandmother with diabetes has swollen foot with a non-healing sore.",
    "Pregnant woman in 8th month feeling dizziness, severe headache, and swollen ankles.",
])
def test_scenarios_26_to_28_complex_multi_symptom(query):
    intent, meta = classify_intent(query, language_code="en-IN")
    assert intent == "HEALTH_QUERY"

    res = generate_healthcare_response(query, language_code="en-IN")
    assert res["is_symptom"] is True
    assert res["suggest_nearby_hospitals"] is True
    # Verify no scheme dumping
    assert len(res.get("matched_schemes", [])) == 0


# =========================================================================
# SCENARIOS 29-30: OUT-OF-DOMAIN BOUNDARIES (FAST DETERMINISTIC REJECTION <100ms)
# =========================================================================
@pytest.mark.parametrize("query", [
    "What is the weather forecast for tomorrow in Chennai?",
    "Can you write a Python script or poem about love?",
])
def test_scenarios_29_to_30_out_of_domain_boundaries(query):
    # Warm up regex compilation / GC
    classify_intent("warmup", language_code="en-IN")
    start = time.perf_counter()
    intent, meta = classify_intent(query, language_code="en-IN")
    duration_ms = (time.perf_counter() - start) * 1000

    assert intent == "OUT_OF_DOMAIN"
    assert duration_ms < 100

    res = generate_healthcare_response(query, language_code="en-IN")
    assert res["intent"] == "OUT_OF_DOMAIN"
    assert res["knowledge_used"] is False
    assert "Arogya Nexus" in res["response"]
    print(f"\n[LATENCY BENCHMARK] Out-of-domain query {query[:30]!r}: {duration_ms:.2f}ms")


# =========================================================================
# SCENARIOS 31-33: HOSPITAL DISCOVERY (GPS, PROFILE, MANUAL)
# =========================================================================
def test_scenario_31_hospital_gps():
    # Chennai coordinates
    res = get_nearby_hospitals(latitude=13.0827, longitude=80.2707, limit=3)
    assert res["status"] == "success"
    assert res["user_location"]["type"] == "gps"
    assert len(res["hospitals"]) > 0
    # First hospital should have distance_km calculated
    assert res["hospitals"][0]["distance_km"] is not None


def test_scenario_32_hospital_profile():
    res = get_nearby_hospitals(district="Madurai", limit=3)
    assert res["status"] == "success"
    assert res["user_location"]["type"] in ("profile", "manual")
    assert "madurai" in res["user_location"]["label"].lower()
    assert len(res["hospitals"]) > 0


def test_scenario_33_hospital_manual_city():
    res = get_nearby_hospitals(city="Coimbatore", limit=3)
    assert res["status"] == "success"
    assert "coimbatore" in res["user_location"]["label"].lower()
    assert len(res["hospitals"]) > 0


# =========================================================================
# SCENARIOS 34-36: SCHEME ELIGIBILITY EVALUATION
# =========================================================================
def test_scenario_34_low_income_bpl_tamil_nadu():
    profile = {
        "state": "Tamil Nadu",
        "district": "Salem",
        "annual_income": 72000,
        "ration_card_type": "PHH",
        "age": 35,
        "gender": "male"
    }
    eval_res = evaluate_profile_eligibility(profile)
    assert eval_res["total_schemes_checked"] >= 16
    assert eval_res["likely_eligible_count"] > 0
    likely_ids = [s["id"] for s in eval_res["likely_eligible"]]
    assert "cmchis" in likely_ids or "pmjay" in likely_ids


def test_scenario_35_high_income_ineligible_for_subsidized_care():
    profile = {
        "state": "Tamil Nadu",
        "district": "Chennai",
        "annual_income": 1500000,  # 15 Lakhs
        "ration_card_type": "None",
        "age": 42,
        "gender": "male"
    }
    eval_res = evaluate_profile_eligibility(profile)
    # Income exceeds 1.2L limit for CMCHIS
    cmchis_eval = next((s for s in eval_res["all_evaluations"] if s["id"] == "cmchis"), None)
    assert cmchis_eval is not None
    assert cmchis_eval["status"] != "Likely Eligible"


def test_scenario_36_pregnant_mother_eligibility():
    profile = {
        "state": "Tamil Nadu",
        "district": "Salem",
        "annual_income": 60000,
        "age": 24,
        "gender": "female",
        "is_pregnant": True,
        "ration_card_type": "PHH"
    }
    eval_res = evaluate_profile_eligibility(profile)
    likely_ids = [s["id"] for s in eval_res["likely_eligible"]]
    assert "mrmbs" in likely_ids or "pmmvy" in likely_ids


# =========================================================================
# SCENARIOS 37-38: SCHEME COMPARISON
# =========================================================================
def test_scenario_37_compare_cmchis_vs_pmjay():
    comp = compare_schemes(["cmchis", "pmjay"])
    assert comp["status"] == "success"
    assert len(comp["schemes"]) == 2
    ids = [s["id"] for s in comp["schemes"]]
    assert "cmchis" in ids and "pmjay" in ids


def test_scenario_38_compare_aarogyasri_vs_pmjay():
    comp = compare_schemes(["aarogyasri", "pmjay"])
    assert comp["status"] == "success"
    assert len(comp["schemes"]) == 2


# =========================================================================
# SCENARIOS 39-40: ROBUST EDGE CASES (EMPTY & VERY LONG MESSAGES)
# =========================================================================
def test_scenario_39_empty_message_validation():
    with pytest.raises(ValueError):
        generate_healthcare_response("   ")


def test_scenario_40_long_message_stability():
    long_msg = "Doctor, " + "I have had a mild headache and fever for two days. " * 40
    res = generate_healthcare_response(long_msg, language_code="en-IN")
    assert res is not None
    assert len(res["response"]) > 0


# =========================================================================
# SCENARIOS 41-45: AI HEALTH IMAGE ASSISTANT & MEDICAL SAFETY RULES
# =========================================================================
def test_scenario_41_image_validation_empty():
    res = analyze_health_image(b"")
    assert res["status"] == "error"
    assert res["error_code"] == "EMPTY_IMAGE"
    assert res["suitable_for_analysis"] is False


def test_scenario_42_image_validation_poor_quality_dark():
    # 300 bytes of solid black zeros
    dark_image = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 300
    res = analyze_health_image(dark_image, filename="dark_photo.jpg")
    assert res["status"] == "error"
    assert res["error_code"] == "POOR_QUALITY"
    assert res["suitable_for_analysis"] is False


def test_scenario_43_image_observation_redness():
    valid_image = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x88" * 300
    res = analyze_health_image(
        valid_image,
        filename="arm_rash.jpg",
        user_notes="Redness and mild itching on my arm",
        language_code="en-IN"
    )
    assert res["status"] == "success"
    assert res["suitable_for_analysis"] is True
    assert res["pattern_category"] == "redness"
    assert "Superficial Redness" in res["title"]
    assert len(res["safe_immediate_care"]) > 0
    assert len(res["warning_signs"]) > 0
    # Must have disclaimer and nearby healthcare
    assert "Not a medical diagnosis" in res["disclaimer"]
    assert len(res["nearby_healthcare"]) > 0


def test_scenario_44_image_observation_wound():
    valid_image = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x88" * 300
    res = analyze_health_image(
        valid_image,
        filename="scraped_knee.jpg",
        user_notes="Minor scrape and bleeding after tripping on road",
        language_code="en-IN"
    )
    assert res["status"] == "success"
    assert res["pattern_category"] == "superficial_wound"
    assert "Wound" in res["title"]


def test_scenario_45_medical_safety_no_fake_accuracy_percentages():
    valid_image = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x88" * 300
    res = analyze_health_image(valid_image, filename="photo.jpg")
    serialized = str(res)
    # Medical safety rule: No fake certainty or accuracy claims
    assert "90%" not in serialized
    assert "guaranteed diagnosis" not in serialized.lower()
    assert "accuracy" not in serialized.lower()
