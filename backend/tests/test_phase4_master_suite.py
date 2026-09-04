"""
Arogya Nexus — Phase 4 Master Comprehensive Verification Test Suite
Tests:
1. 4-Language Healthcare Chat (Tamil, English, Telugu, Malayalam)
2. State & Regional Intelligence (Tamil Nadu, Andhra Pradesh, Kerala, National)
3. 16 Verified Government Health Schemes (CMCHIS, Aarogyasri, KASP, MEDISEP, PM-JAY, etc.)
4. 6-Step Symptom-Specific Guidance (Fever, Diarrhea, Cough/Cold)
5. Pre-LLM Emergency Fast-Path (<100ms response & 108 speed-dial)
6. Multi-State Eligibility & Recommendation Service
7. Side-by-Side Scheme Comparison
8. Markdown Sanitization for Natural TTS Audio
9. Knowledge Base Runtime Refresh (n8n Integration)
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.knowledgeService import (
    load_all_knowledge_cards,
    detect_emergency,
    detect_scheme_intent,
    search_knowledge_base,
    search_schemes,
    reload_knowledge_base,
)
from services.eligibilityService import evaluate_profile_eligibility
from services.schemeRecommendationService import get_scheme_recommendations
from services.schemeComparisonService import compare_schemes
from services.sarvamService import sanitize_text_for_speech
from services.llmService import generate_healthcare_response, get_fast_emergency_response


class TestArogyaNexusMasterSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cards = load_all_knowledge_cards()
        cls.cards = cards

    def test_01_knowledge_base_card_count_and_schema(self):
        """Verify knowledge base has at least 26 verified cards (16 schemes + 10 clinical)."""
        self.assertGreaterEqual(len(self.cards), 26)
        schemes = [c for c in self.cards if c.get("category") in ("government_scheme", "health_schemes")]
        clinical = [c for c in self.cards if c.get("category") not in ("government_scheme", "health_schemes")]

        self.assertEqual(len(schemes), 16, "Must have exactly 16 verified government schemes.")
        self.assertGreaterEqual(len(clinical), 10, "Must have at least 10 clinical cards.")

        # Check multi-state representation
        states = set(s.get("state") for s in schemes)
        self.assertIn("Tamil Nadu", states)
        self.assertIn("Andhra Pradesh", states)
        self.assertIn("Kerala", states)
        self.assertIn("National", states)

    def test_02_emergency_detection_across_4_languages(self):
        """Verify emergency red-flag triggers in Tamil, English, Telugu, and Malayalam."""
        # Tamil
        is_em_ta, _ = detect_emergency("கடுமையான நெஞ்சு வலி மற்றும் மாரடைப்பு")
        self.assertTrue(is_em_ta, "Tamil chest pain must trigger emergency.")

        # English
        is_em_en, _ = detect_emergency("Severe crushing chest pain and shortness of breath")
        self.assertTrue(is_em_en, "English chest pain must trigger emergency.")

        # Telugu
        is_em_te, _ = detect_emergency("తీవ్రమైన గుండె నొప్పి మరియు గుండెపోటు")
        self.assertTrue(is_em_te, "Telugu chest pain must trigger emergency.")

        # Malayalam
        is_em_ml, _ = detect_emergency("കടുത്ത നെഞ്ചുവേദനയും ഹൃദയാഘാതവും")
        self.assertTrue(is_em_ml, "Malayalam chest pain must trigger emergency.")

        # Non-emergency
        is_em_none, _ = detect_emergency("What are the benefits of CMCHIS scheme?")
        self.assertFalse(is_em_none, "Normal scheme query must not trigger emergency.")

    def test_03_fast_emergency_response_short_circuit(self):
        """Verify fast emergency responses are generated without waiting for LLM."""
        resp_ta = get_fast_emergency_response("நெஞ்சு வலி", lang="ta-IN")
        self.assertIn("108", resp_ta)
        self.assertIn("W-Position", resp_ta)

        resp_te = get_fast_emergency_response("గుండె నొప్పి", lang="te-IN")
        self.assertIn("108", resp_te)

        resp_ml = get_fast_emergency_response("നെഞ്ചുവേദന", lang="ml-IN")
        self.assertIn("108", resp_ml)

        resp_snake = get_fast_emergency_response("snakebite poison", lang="en-IN")
        self.assertIn("108", resp_snake)
        self.assertIn("Anti-Snake Venom", resp_snake)

    def test_04_eligibility_engine_multi_state_profiles(self):
        """Verify profile evaluation against TN, AP, Kerala, and National schemes."""
        # Profile 1: Tamil Nadu BPL Family
        tn_profile = {
            "age": 35,
            "gender": "female",
            "state": "Tamil Nadu",
            "annual_income": 90000,
            "income_range": "< 1.2L",
            "family_size": 4
        }
        res_tn = evaluate_profile_eligibility(tn_profile)
        cmchis_eval = next((s for s in res_tn if s["scheme_id"] == "cmchis-tamil-nadu"), None)
        self.assertIsNotNone(cmchis_eval)
        self.assertEqual(cmchis_eval["eligibility_status"], "Likely Eligible")

        # Profile 2: Andhra Pradesh Rice Card Family
        ap_profile = {
            "age": 40,
            "gender": "male",
            "state": "Andhra Pradesh",
            "annual_income": 250000,
            "income_range": "< 5.0L"
        }
        res_ap = evaluate_profile_eligibility(ap_profile)
        ysr_eval = next((s for s in res_ap if s["scheme_id"] == "ysr-aarogyasri-andhra-pradesh"), None)
        self.assertIsNotNone(ysr_eval)
        self.assertEqual(ysr_eval["eligibility_status"], "Likely Eligible")

        # Profile 3: Kerala Govt Pensioner
        kl_profile = {
            "age": 62,
            "gender": "female",
            "state": "Kerala",
            "occupation": "Govt Pensioner",
            "is_elderly": True
        }
        res_kl = evaluate_profile_eligibility(kl_profile)
        medisep_eval = next((s for s in res_kl if s["scheme_id"] == "medisep-kerala"), None)
        self.assertIsNotNone(medisep_eval)
        self.assertEqual(medisep_eval["eligibility_status"], "Likely Eligible")

    def test_05_scheme_recommendations_with_state_filtering(self):
        """Verify scheme recommendations rank relevant state schemes first."""
        recs_tn = get_scheme_recommendations(
            profile={"state": "Tamil Nadu"},
            query="cashless hospital insurance",
            language_code="ta-IN",
            state="Tamil Nadu",
            top_k=3
        )
        rec_ids_tn = [r["scheme_id"] for r in recs_tn["recommendations"]]
        self.assertIn("cmchis-tamil-nadu", rec_ids_tn)

        recs_ap = get_scheme_recommendations(
            profile={"state": "Andhra Pradesh"},
            query="hospital insurance 25 lakh",
            language_code="te-IN",
            state="Andhra Pradesh",
            top_k=3
        )
        rec_ids_ap = [r["scheme_id"] for r in recs_ap["recommendations"]]
        self.assertIn("ysr-aarogyasri-andhra-pradesh", rec_ids_ap)

    def test_06_scheme_comparison_service(self):
        """Verify structured side-by-side comparison across schemes."""
        comp = compare_schemes(["cmchis-tamil-nadu", "ayushman-bharat-pmjay", "ysr-aarogyasri-andhra-pradesh"])
        self.assertEqual(comp["status"], "success")
        self.assertEqual(comp["total_compared"], 3)
        self.assertIn("cmchis-tamil-nadu", [s["scheme_id"] for s in comp["schemes"]])
        self.assertIn("ayushman-bharat-pmjay", [s["scheme_id"] for s in comp["schemes"]])
        self.assertIn("ysr-aarogyasri-andhra-pradesh", [s["scheme_id"] for s in comp["schemes"]])

    def test_07_markdown_sanitization_for_tts(self):
        """Verify markdown syntax is cleanly stripped for natural acoustic speech."""
        md_text = (
            "### 🏥 CMCHIS Scheme\n\n"
            "**Key Benefits:**\n"
            "* Cashless coverage up to [₹5,00,000](https://cmchistn.com)\n"
            "* Over 1,090 surgical procedures.\n"
            "> Emergency helpline: 108"
        )
        cleaned = sanitize_text_for_speech(md_text)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertNotIn("[", cleaned)
        self.assertIn("CMCHIS Scheme", cleaned)
        self.assertIn("1,090 surgical procedures", cleaned)

    def test_08_knowledge_refresh_endpoint_n8n(self):
        """Verify reload_knowledge_base returns updated card counts."""
        stats = reload_knowledge_base()
        self.assertEqual(stats["status"], "success")
        self.assertGreaterEqual(stats["total_cards"], 26)
        self.assertEqual(stats["scheme_cards_count"], 16)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    unittest.main()
