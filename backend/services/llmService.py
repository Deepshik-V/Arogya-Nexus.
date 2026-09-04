"""
Arogya Nexus �� Multi-Turn LLM Healthcare Response & Streaming Service
Integrates Sarvam AI (sarvam-105b) with deterministic intent routing,
intent-aware RAG, instant token streaming, and response relevance guarding.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from dotenv import load_dotenv
from sarvamai import SarvamAI

from services.knowledgeService import (
    search_knowledge_base,
    format_knowledge_context_for_llm,
    detect_emergency,
)
from services.intentRouter import (
    classify_intent,
    get_localized_out_of_domain_response,
)
from services.hospitalService import get_nearby_hospitals
from services.schemeComparisonService import SchemeId

# Base project paths
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

HEALTHCARE_SYSTEM_PROMPT = """You are Arogya Nexus (鉈�扇鉒肀�鉒温�鉈賴悖 鉈兒�鉈𨫼�鉈詮捂鉒� / 鈰�偽鈺肀�鈺温偺 鈰兒�鈰𨫼�鈰詮偶鈺� / 鉥�敦鉞肀�鉞温敞 鉥兒�鉥𨫼�鉥詮晴鉞�), a Personal Multilingual AI Healthcare Assistant designed for citizens across India.

CRITICAL OPERATIONAL RULES & SAFETY GUARDRAILS:

1. STRICT LANGUAGE MATCHING:
   - If the user query is in Tamil or Tanglish, or language is Tamil: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL TAMIL (鉈戈悅鉈賴捎鉒�). Understand Tanglish seamlessly (e.g., 'enakku fever irukku', 'thala vali', 'stomach pain irukku').
   - If the user query is in Telugu or language is Telugu: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL TELUGU (鈰戈�鈰耜�鈰鉮�).
   - If the user query is in Malayalam or language is Malayalam: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL MALAYALAM (鉥桌散鉥能晷鉥喪�).
   - If the user query is in English: RESPOND IN SIMPLE, CLEAR INDIAN ENGLISH.
   - NEVER switch to English when a regional language is chosen.

2. HEALTH SYMPTOM QUERIES (CONCISE, SAFE, NO ESSAYS, NO UNREQUESTED SCHEMES):
   When a user asks about symptoms (fever, headache, stomach pain, vomiting, cough, diarrhea, dizziness, swelling, body pain, etc.):
   Answer ONLY the user's actual healthcare concern. Do NOT dump government schemes or health insurance details!
   Use uncertainty-aware language ("This can have several causes. Based on what you've described..."). Never claim a definitive diagnosis. Never promise 90% accuracy.
   Follow this exact 5-point structure concisely:
   �� 1. What you can do now (Immediate safe guidance)
   �� 2. Simple supportive / home-care steps (Hydration, rest, light food, cooling)
   �� 3. What to avoid (Self-medicating with antibiotics, heavy exertion, unverified substances)
   �� 4. Warning signs / when to see a doctor (Red flags requiring Primary Health Centre / PHC evaluation)
   �� 5. Nearby hospital option (Briefly ask: "If your symptoms persist, would you like me to show nearby hospitals in your area?")

3. GOVERNMENT SCHEME QUERIES (ONLY WHEN EXPLICITLY ASKED):
   - When the user specifically asks about health schemes (CMCHIS, Dr. YSR Aarogyasri, KASP, PM-JAY, MRMBS, PMMVY, JSY, etc.), structure the response:
     ��儭� Scheme Name (鉈戈挪鉈颴�鉈颴悅鉒� / 鈰芹陞鈰𨫼� / 鉥芹揭鉞温揮鉥戈曾)
     �� Benefits provided (鉈芹悖鉈拈�鉈𨫼拿鉒� / 鈰芹�鈰啤偺鈺肀�鈰兒偏鈰耜� / 鉥�捶鉞��鉞�散鉞温敞鉥跃�鉥跃翔)
     �𪈠 Basic eligibility (鉈戈�鉒�恕鉈� / 鈰�偽鈺温偎鈰� / 鉥能�鉥鉮�鉥能握)
     �� Required documents (鉈�挾鉈␡�鉒温�鉈喪� / 鈰芹陘鈺温偽鈰擒假鈺� / 鉥啤�鉥遤�鉞�)
     �� How & Where to apply (鉈菽挪鉈␡�鉈␡悚鉒温悚鉈賴�鉒温�鉒�悅鉒� 鉈桌�鉈晤� / 鈰舟偽鈰遤偏鈰詮�鈰戈� 鈰菽倏鈰抉偏鈰兒� / 鉥�揪鉞��鉞温晰鉥賴�鉞温�鉞�提鉞温� 鉥菽曾鉥抉�)
     �𩤃� Official verification disclaimer: "Final benefit confirmation must be done with official government authorities."

4. SOURCE-GROUNDING & ZERO FABRICATION:
   - Ground all guidance strictly in verified public health standards.
   - Never invent prescription drug dosages, never prescribe antibiotics, never claim diagnosis certainty, never invent hospitals or phone numbers.
   - Never expose internal reasoning or chain-of-thought.
"""


def get_llm_client() -> SarvamAI:
    """
    Initializes and returns the SarvamAI client using LLM_API_KEY or SARVAM_API_KEY.
    """
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)

    api_key = (os.getenv("LLM_API_KEY") or "").strip()
    if not api_key:
        api_key = (os.getenv("SARVAM_API_KEY") or "").strip()

    if not api_key:
        raise ValueError(
            "LLM_API_KEY (or SARVAM_API_KEY) is missing or empty. Please set it in the root .env file."
        )

    return SarvamAI(api_key=api_key)


def get_fast_emergency_response(query: str, lang: str = "ta-IN") -> str:
    """
    Deterministic instant (<2ms) emergency triage protocol.
    Bypasses LLM and RAG entirely for safety-critical queries.
    """
    lower = query.lower()
    is_snakebite = any(k in lower for k in ["snake", "bite", "鉈芹挽鉈桌�鉈芹�", "鉈𨫼�鉈�", "鈰芹偏鈰桌�", "鈰𨫼偏鈰颴�", "鉥芹晷鉥桌�鉥芹�"])

    if "en" in lang.lower():
        if is_snakebite:
            return (
                "�辶 **EMERGENCY MEDICAL PROTOCOL: IMMEDIATE ACTION REQUIRED!**\n\n"
                "1. **DIAL 108 IMMEDIATELY FOR AN EMERGENCY AMBULANCE.**\n"
                "2. Keep the patient calm and completely still. Movement causes venom to spread faster.\n"
                "3. Immobilize the bitten limb using a splint or sling at heart level.\n"
                "4. **DO NOT** cut, suction, or apply a tight tourniquet.\n"
                "5. Rush directly to the nearest Government Headquarters Hospital equipped with Anti-Snake Venom (ASV)."
            )
        return (
            "辶 **CRITICAL EMERGENCY MEDICAL ALERT: 108 AMBULANCE REQUIRED!**\n\n"
            "1. **CALL 108 IMMEDIATELY FOR EMERGENCY MEDICAL SERVICES.**\n"
            "2. Keep the patient in a comfortable, seated, or semi-reclined position (W-position).\n"
            "3. Loosen any tight clothing around neck and chest; ensure continuous ventilation.\n"
            "4. Do not offer oral fluids or food if the person is dizzy, faint, or short of breath.\n"
            "5. If unconscious and breathing stops, initiate chest compressions immediately."
        )
    elif "te" in lang.lower():
        if is_snakebite:
            return (
                "�辶 **鈰�陘鈺温偺鈰菽偶鈰� 鈰菽�鈰舟�鈰� 鈰嫩�鈰𠼭�鈰𠼭偽鈰賴�: 鈰戈�鈺温健鈰␡乾鈺� 108 鈰𨫼倏 鈰𨫼偏鈰耜� 鈰𠼭�鈰能�鈰﹤倏!**\n\n"
                "1. **鈰菽�鈰��鈰兒� 108 鈰��鈰眇�鈰耜�鈰兒�鈰詮��䓃�鈺� 鈰𨫼偏鈰耜� 鈰𠼭�鈰能�鈰﹤倏.**\n"
                "2. 鈰眇偏鈰抉倏鈰戈�鈰﹤倏鈰兒倏 鈰𨫼隻鈰耜�鈺��鈰﹤偏 鈰芹�鈰啤偉鈰擒�鈰戈�鈰鉮偏 鈰凼�鈰𠼭�鈰﹤倏.\n"
                "3. 鈰𨫼偏鈰颴� 鈰菽�鈰詮倏鈰� 鈰冢偏鈰鉮偏鈰兒�鈰兒倏 鈰𨫼隻鈰耜�鈺��鈰﹤偏 鈰𨫼偽鈺温偽 鈰耜�鈰舟偏 鈰鉮�鈰﹤�鈰﹤陘鈺� 鈰𨫼�鈺温�鈰�陛鈰�.\n"
                "4. 鈰鉮偏鈰颴� 鈰芹�鈰颴�鈰颴陛鈰� 鈰耜�鈰舟偏 鈰鉮�鈺温�鈰賴�鈰� 鈰𨫼�鈺温�鈰﹤� 鈰𠼭�鈰能做鈰舟�鈰舟�.\n"
                "5. 鈰菽�鈰��鈰兒� 鈰能偏鈰��鈺�-鈰詮�鈰兒�鈰𨫼� 鈰菽�鈰兒乾鈺� (ASV) 鈰凼馬鈺温馬 鈰詮乾鈺�鈰� 鈰芹�鈰啤鬼鈺�陘鈺温做 鈰�偶鈺�高鈰戈�鈰啤倏鈰𨫼倏 鈰戈偽鈰耜倏鈰��鈰�陛鈰�."
            )
        return (
            "🚨 **Emergency Alert: 108 Ambulance!**\n\n"
            "1. Call 108 emergency ambulance immediately.\n"
            "2. Keep patient seated in W-position.\n"
            "3. Loosen tight clothing and ensure ventilation.\n"
            "4. Do not give food or water.\n"
            "5. Transport immediately to nearest hospital with ECG."
        )
    else:  # Tamil default
        if is_snakebite:
            return (
                "�辶 **鉈�挾鉈𠼭扇 鉈桌扇鉒�恕鉒温恕鉒�挾 鉈兒�鉈晤挪鉈桌�鉈晤�: 鉈凼�鉈拈�鉈賴悖鉈擒� 108 鉈�悅鉒温悚鉒�挈鉈拈�鉈詮� 鉈�捎鉒��鉒温�鉈菽�鉈桌�!**\n\n"
                "1. **鉈凼�鉈拈�鉈賴悖鉈擒� 108 鉈�挾鉈𠼭扇 鉈�悅鉒温悚鉒�挈鉈拈�鉈詮� 鉈�捎鉒��鉒温�鉈菽�鉈桌�.**\n"
                "2. 鉈芹挽鉈戈挪鉈𨫼�鉈𨫼悚鉒温悚鉈颴�鉈颴挾鉈啤� 鉈芹悖鉈芹�鉈芹�鉈擒悅鉈耜� 鉈�悅鉒�恕鉈賴悖鉈擒�, 鉈芹�鉒��鉒温� 鉈菽�鉈𨫼�鉈𨫼挽鉈桌挈鉒� 鉈菽�鉈𨫼�鉈𨫼挾鉒�悅鉒�.\n"
                "3. 鉈𨫼�鉈賴悚鉈颴�鉈� 鉈凼拳鉒�悚鉒温悚鉒� 鉈��鉒��鉒温�鉈擒悅鉈耜� 鉈桌扇鉈𨫼�鉈𨫼�鉒温�鉒� 鉈菽�鉈戈�鉈戈� 鉈𨫼�鉒温�鉈菽�鉈桌�.\n"
                "4. 鉈𨫼�鉈賴恕鉒温恕 鉈��鉈戈�鉈戈挪鉈耜� 鉈菽�鉈颴�鉈颴�鉈菽恕鉒�, 鉈菽挽鉈能挽鉈耜� 鉈凼拳鉈賴�鉒温�鉒�挾鉈戈�, 鉈𨫼悖鉈賴拳鉒� 鉈𨫼�鉒温�鉒�挾鉈戈� 鉈𨫼�鉈颴挽鉈戈�.\n"
                "5. 鉈菽挪鉈� 鉈桌�鉈晤挪鉈菽� 鉈桌扇鉒�悄鉒温恕鉒� (ASV) 鉈凼拿鉒温拿 鉈�扇鉈𠼭� 鉈戈挈鉒�悅鉒� 鉈桌扇鉒�恕鉒温恕鉒�挾鉈桌悟鉒��鉒温�鉒� 鉈凼�鉈拈� 鉈𠼭�鉈耜�鉈耜挾鉒�悅鉒�."
            )
        return (
            "�辶 **鉈�挾鉈𠼭扇 鉈桌扇鉒�恕鉒温恕鉒�挾 鉈脚�鉒温�鉈啤挪鉈𨫼�鉈𨫼�: 鉈𨫼�鉒�悅鉒�悖鉈擒悟 鉈兒�鉈𠒎�鉈𠼭� 鉈菽挈鉈� / 鉈桌挽鉈啤�鉒�悚鉒温悚鉒� 鉈�拳鉈賴�鉒�拳鉈�!**\n\n"
            "1. **鉈凼�鉈拈�鉈賴悖鉈擒� 108 鉈�挾鉈𠼭扇 鉈�悅鉒温悚鉒�挈鉈拈�鉈詮� 鉈�捎鉒��鉒温�鉈菽�鉈桌�.**\n"
            "2. 鉈兒�鉈能挽鉈喪挪鉈能� 鉈芹�鉒��鉒温� 鉈菽�鉈𨫼�鉈𨫼挽鉈桌挈鉒�, 鉈𠼭挽鉈能�鉈兒�鉈� 鉈兒挪鉈耜�鉈能挪鉈耜� (W-Position) 鉈�悅鉈� 鉈菽�鉈𨫼�鉈𨫼挾鉒�悅鉒�.\n"
            "3. 鉈�拳鉒��鉒温�鉈桌挽鉈� 鉈��鉒��鉈喪�鉈戈� 鉈戈拿鉈啤�鉈戈�鉈戈挪, 鉈�悅鉒�恕鉈賴悖鉈擒� 鉈�扇鉒��鉒温�鉈𠼭� 鉈𠼭�鉈能�鉈能挾鉒�悅鉒�.\n"
            "4. 鉈兒�鉈能挽鉈喪挪鉈能� 鉈兒�鉈𨫼�鉈� 鉈菽挪鉈颴挽鉈桌挈鉒� ECG 鉈菽�鉈戈挪鉈能�鉈喪�鉈� 鉈�扇鉒��鉈賴挈鉒�拿鉒温拿 鉈桌扇鉒�恕鉒温恕鉒�挾鉈桌悟鉒��鉒温�鉒� 鉈菽挪鉈啤�鉈兒�鉈戈� 鉈𠼭�鉈耜�鉈耜挾鉒�悅鉒�."
        )


def format_nearby_hospitals_text(hospitals_result: Dict[str, Any], lang: str = "en-IN") -> str:
    """
    Formats nearby hospital search results into a clean markdown block.
    """
    hospitals = hospitals_result.get("hospitals", [])
    loc_label = hospitals_result.get("user_location", {}).get("label", "your location")

    if not hospitals:
        return f"Currently, no verified public healthcare facilities were found directly matching {loc_label}. Please visit the nearest Primary Health Centre or dial 108 in an emergency."

    lines = [
        f"�蘂 **Nearby Healthcare Facilities (Location: {loc_label})**\n"
    ]
    for h in hospitals[:3]:
        dist_str = f" ({h.get('distance_label', '')})" if h.get("distance_label") else ""
        lines.append(f"�� **{h.get('name')}**{dist_str}")
        lines.append(f"  Type: {h.get('type', 'Government Hospital')}")
        if h.get("address"):
            lines.append(f"  Address: {h.get('address')}")
        if h.get("phone"):
            lines.append(f"  Phone: {h.get('phone')}")
        if h.get("maps_url") or h.get("directions_url"):
            url = h.get("maps_url") or h.get("directions_url")
            lines.append(f"  [Get Directions on Map]({url})")
        lines.append("")

    lines.append("�働 *You can also view these facilities with live interactive markers on the **Hospitals & Map** tab.*")
    return "\n".join(lines)


def build_structured_card_guidance(card: Dict[str, Any], lang_tag: str, location_str: str = "your local area") -> str:
    """
    Builds the canonical 5-point structured healthcare response directly from verified clinical card.
    Format:
    - What it may commonly relate to: Short non-diagnostic explanation
    - What you can do now: Practical safe steps (1, 2, 3)
    - Home care: Low-risk supportive care
    - Avoid: Important things to avoid
    - Warning signs: Clearly identify red flags
    - When to see a doctor: PHC recommendation
    - Nearby healthcare: Safe option to view facilities
    """
    title = card.get(f"title_{lang_tag}") or card.get("title_en", "Health Guidance")
    indicates = card.get("what_it_indicates", {}).get(lang_tag) or card.get("what_it_indicates", {}).get("en", "")
    home_care = card.get("safe_home_care", {}).get(lang_tag) or card.get("safe_home_care", {}).get("en", [])
    avoid = card.get("what_to_avoid", {}).get(lang_tag) or card.get("what_to_avoid", {}).get("en", [])
    warning_signs = card.get("warning_signs", {}).get(lang_tag) or card.get("warning_signs", {}).get("en", [])
    phc_advice = card.get("when_to_visit_phc", {}).get(lang_tag) or card.get("when_to_visit_phc", {}).get("en", [])

    if lang_tag == "ta":
        parts = [f"�征 **{title}**\n"]
        if indicates:
            parts.append(f"**鉈𠼭挽鉈戈�鉈戈挪鉈能悅鉈擒悟 鉈芹�鉈戈�鉈菽挽鉈� 鉈𨫼挽鉈啤恐鉈桌�:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**鉈兒�鉈跃�鉈𨫼拿鉒� 鉈�悚鉒温悚鉒肀恕鉒� 鉈𠼭�鉈能�鉈能�鉒温�鉒��鉈賴悖鉈菽�:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**鉈菽�鉈颴�鉈颴�鉈芹� 鉈芹扇鉈擒悅鉈啤挪鉈芹�鉈芹�:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**鉈戈挾鉈賴扇鉒温�鉒温� 鉈菽�鉈␡�鉈颴挪鉈能挾鉒�:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**鉈脚�鉒温�鉈啤挪鉈𨫼�鉈𨫼� 鉈�拳鉈賴�鉒�拳鉈賴�鉈喪� (鉈𠼭挪鉈菽悚鉒温悚鉒��鉒� 鉈𨫼�鉈颴挪鉈𨫼拿鉒�):**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**鉈桌扇鉒�恕鉒温恕鉒�挾鉈啤� 鉈脚悚鉒温悚鉒肀恕鉒� 鉈�恐鉒�� 鉈菽�鉈␡�鉈颴�鉈桌�:**\n{doc_str}\n")
        parts.append(f"**鉈�扇鉒��鉈賴挈鉒�拿鉒温拿 鉈桌扇鉒�恕鉒温恕鉒�挾鉈桌悟鉒�:** 鉈�拳鉈賴�鉒�拳鉈賴�鉈喪� 鉈戈�鉈颴扇鉒温悄鉒温恕鉈擒挈鉒�, {location_str} 鉈芹�鉒�恕鉈賴悖鉈賴挈鉒� 鉈凼拿鉒温拿 鉈�扇鉒��鉈賴挈鉒�拿鉒温拿 鉈�扇鉈𠼭� 鉈桌扇鉒�恕鉒温恕鉒�挾鉈桌悟鉒��鉈喪� 鉈�挈鉒温挈鉈戈� 鉈�扇鉈桌�鉈� 鉈𠼭�鉈𨫼挽鉈戈挽鉈� 鉈兒挪鉈耜�鉈能�鉒温�鉈喪� (PHC) 鉈芹挽鉈啤�鉈𨫼�鉈� 鉈菽挪鉈啤�鉈桌�鉈芹�鉈𨫼挪鉈晤�鉈啤�鉈𨫼拿鉈�?")
    elif lang_tag == "te":
        parts = [f"�征 **{title}**\n"]
        if indicates:
            parts.append(f"**鈰詮偏鈰抉偏鈰啤除 鈰𨫼偏鈰啤除鈰�:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**鈰桌�鈰啤� 鈰�高鈺温高鈺�陛鈺� 鈰𠼭�鈰能做鈰耜偶鈰賴馬鈰菽倏:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**鈰��鈰颴倏 鈰詮�鈰啤�鈺温健鈰�:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**鈰兒倏鈰菽偏鈰啤倏鈰��鈰菽假鈰詮倏鈰兒做鈰�:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**鈰嫩�鈰𠼭�鈰𠼭偽鈰賴� 鈰詮�鈰𨫼�鈰戈偏鈰耜�:**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**鈰菽�鈰舟�鈰能�鈰﹤倏鈰兒倏 鈰脚高鈺温高鈺�陛鈺� 鈰詮�鈰芹�鈰啤隻鈰賴�鈰𠼭偏鈰耜倏:**\n{doc_str}\n")
        parts.append(f"**鈰詮乾鈺�鈰� 鈰�偽鈺肀�鈺温偺 鈰𨫼�鈰�隻鈺温偽鈰擒假鈺�:** 鈰耜�鈺温健鈰␡偏鈰耜� 鈰戈�鈺温�鈰𨫼高鈺肀陘鈺�, {location_str} 鈰耜�鈰兒倏 鈰詮乾鈺�鈰� 鈰�偶鈺温高鈰戈�鈰啤�鈰耜馬鈺� 鈰𠼭�鈰﹤偏鈰耜馬鈺��鈺��鈰颴�鈰兒�鈰兒偏鈰啤偏?")
    elif lang_tag == "ml":
        parts = [f"�征 **{title}**\n"]
        if indicates:
            parts.append(f"**鉥詮晷鉥抉晷鉥啤提 鉥𨫼晷鉥啤提鉥�:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**鉥兒曾鉥跃�鉥跃翔鉥𨫼�鉥𨫼� 鉥�揪鉞温揪鉞肀翔 鉥𠼭�鉥能�鉥能晷鉞� 鉥𨫼斐鉥賴敞鉞�捶鉞温捶 鉥𨫼晷鉥啤�鉥能�鉞温�鉞�:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**鉥菽�鉥颴�鉥颴�鉥芹敦鉥賴�鉥啤提鉥�:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**鉥响斐鉥賴斯鉥擒�鉞温�鉞�提鉞温� 鉥𨫼晷鉥啤�鉥能�鉞温�鉞�:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**鉥�揪鉥𨫼� 鉥詮�鉥𠼭捶鉥𨫼翔:**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**鉥脚揪鉞温揪鉞肀斐鉥擒提鉞� 鉥﹤�鉥𨫼�鉥颴敢鉞� 鉥𨫼晷鉥␡�鉥␡�鉥颴握鉞�:**\n{doc_str}\n")
        parts.append(f"**鉥��鉞�握鉞温握鉞�斑鉞温斑 鉥�普鉞�揪鉥戈�鉥啤曾鉥𨫼翔:** 鉥耜�鉞温晰鉥␡�鉞温�鉞� 鉥戈�鉥颴敦鉞��鉥能晷鉥␡�鉥跃�鉥𨫼曾鉞�, {location_str} 鉥��鉞�握鉞温握鉞�斑鉞温斑 鉥�普鉞�揪鉥戈�鉥啤曾 鉥菽曾鉥菽敦鉥跃�鉥跃翔 鉥𨫼晷鉥␡曾鉥𨫼�鉥𨫼提鉥桌�?")
    else:  # English
        parts = [f"�征 **HEALTH GUIDANCE: {title}**\n"]
        if indicates:
            parts.append(f"**What it may commonly relate to:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**What you can do now:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**Home care:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**Avoid:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**Warning signs:**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**When to see a doctor:**\n{doc_str}\n")
        parts.append(f"**Nearby healthcare:** If your symptoms persist or worsen, would you like to view verified nearby hospitals in {location_str}?")

    return "\n".join(parts).strip()


def validate_and_guard_response(
    response_text: str,
    intent: str,
    detected_topic: Optional[str],
    query: str,
    target_lang: str,
    top_card: Optional[Dict[str, Any]] = None,
    loc_str: str = "your local area"
) -> str:
    """
    Section 27 Semantic Validation & Guardrail:
    1. Checks if response addresses user's actual topic.
    2. If headache/fever/stomach query accidentally contains chest pain or heart attack,
       REJECT and replace with verified clinical card guidance!
    3. Strips unrequested scheme dumps for pure symptom queries.
    4. Guarantees safe, non-diagnostic guidance in user's target language.
    """
    tag = "ta" if "ta" in target_lang else ("te" if "te" in target_lang else ("ml" if "ml" in target_lang else "en"))

    if not response_text or len(response_text.strip()) < 15:
        if top_card:
            return build_structured_card_guidance(top_card, tag, location_str=loc_str)
        return response_text

    lower_resp = response_text.lower()

    # Check 1: Cross-contamination detection
    chest_hallucinations = [
        "chest pain", "heart attack", "coronary", "myocardial", "cardiac event",
        "鉈兒�鉈𠒎�鉈𠼭� 鉈菽挈鉈�", "鉈桌挽鉈啤�鉒�悚鉒温悚鉒�", "鉈�恕鉈� 鉈菽挈鉈�", "鉈𨫼�鈰�陛鈺� 鈰兒�鈰芹�鈰芹倏", "鈰鉮�鈰�陛鈺�高鈺肀�鈺�", "鈰𥔿偏鈰戈� 鈰兒�鈰芹�鈰芹倏",
        "鉥兒�鉥𠒎�鉥𠼭�鉥菽�鉥舟捶", "鉥嫩�鉥舟敞鉥擒�鉥擒握鉥�"
    ]
    if detected_topic in ("headache", "fever", "stomach_pain", "dizziness", "burns", "cough_cold"):
        # If the user did NOT ask about chest, but response mentions chest pain or heart attack:
        has_unrelated_chest = any(ch in lower_resp for ch in chest_hallucinations)
        if has_unrelated_chest:
            print(f"[GUARD TRIGGERED] Unrelated chest pain hallucination detected for topic '{detected_topic}'. Replacing with pristine card guidance.")
            if top_card:
                return build_structured_card_guidance(top_card, tag, location_str=loc_str)

    # Check 2: Strip unrequested schemes from symptom responses
    if intent in ("HEALTH_SYMPTOM", "HEALTH_QUERY", "GENERAL_HEALTH", "GENERAL_SUPPORTED_HEALTHCARE"):
        lines = response_text.splitlines()
        cleaned_lines = []
        skip_scheme_section = False
        for line in lines:
            if any(marker in line for marker in [
                "��儭�", "CMCHIS:", "PM-JAY:", "Aarogyasri:", "鉈𨫼挽鉈芹�鉈芹�鉈颴�鉈颴� 鉈戈挪鉈颴�鉈颴悅鉒�", "鈰芹陞鈰𨫼�", "鉥芹揭鉞温揮鉥戈曾",
                "Where to apply:", "Required Documents:", "鉈菽挪鉈␡�鉈␡悚鉒温悚鉈賴�鉒温�鉒�悅鉒� 鉈桌�鉈晤�:"
            ]):
                skip_scheme_section = True
                continue
            if skip_scheme_section and any(marker in line for marker in [
                "When to see a doctor", "Nearby healthcare", "Primary Health Centre",
                "鉈�扇鉈桌�鉈� 鉈𠼭�鉈𨫼挽鉈戈挽鉈�", "鉈桌扇鉒�恕鉒温恕鉒�挾鉈啤� 鉈�恐鉒��鉈菽�鉈桌�", "鈰菽�鈰舟�鈰能�鈰﹤倏鈰兒倏", "鉥﹤�鉥𨫼�鉥颴敢鉞�"
            ]):
                skip_scheme_section = False
            if not skip_scheme_section:
                cleaned_lines.append(line)
        sanitized = "\n".join(cleaned_lines).strip()
        if len(sanitized) > 40:
            response_text = sanitized

    return response_text


def format_nearby_hospitals_text(hospitals_result: Dict[str, Any], lang: str = "en-IN") -> str:
    """
    Formats nearby hospital search results into a clean markdown block.
    """
    hospitals = hospitals_result.get("hospitals", [])
    loc_label = hospitals_result.get("user_location", {}).get("label", "your location")
    loc_type = hospitals_result.get("user_location", {}).get("type", "profile")

    if not hospitals:
        return f"Currently, no verified public healthcare facilities were found directly matching {loc_label}. Please visit the nearest Primary Health Centre or dial 108 in an emergency."

    lines = [
        f"�蘂 **Nearby Healthcare Facilities (Location: {loc_label})**\n"
    ]
    for h in hospitals[:3]:
        dist_str = f" ({h.get('distance_label', '')})" if h.get("distance_label") else ""
        lines.append(f"�� **{h.get('name')}**{dist_str}")
        lines.append(f"  Type: {h.get('type', 'Government Hospital')}")
        if h.get("address"):
            lines.append(f"  Address: {h.get('address')}")
        if h.get("phone"):
            lines.append(f"  Phone: {h.get('phone')}")
        if h.get("maps_url") or h.get("directions_url"):
            url = h.get("maps_url") or h.get("directions_url")
            lines.append(f"  [Get Directions on Map]({url})")
        lines.append("")

    lines.append("�働 *You can also view these facilities with live interactive markers on the **Hospitals & Map** tab.*")
    return "\n".join(lines)


def sanitize_and_guard_response(response_text: str, intent: str, target_lang: str) -> str:
    """
    Response Relevance Guard:
    1. For pure HEALTH_SYMPTOM queries, strips any unrequested government scheme sections.
    2. Ensures no dangerous ungrounded medical prescriptions or definitive diagnosis claims.
    """
    if not response_text:
        return ""

    if intent in ("HEALTH_SYMPTOM", "HEALTH_QUERY", "GENERAL_HEALTH", "GENERAL_SUPPORTED_HEALTHCARE"):
        lines = response_text.splitlines()
        cleaned_lines = []
        skip_scheme_section = False

        for line in lines:
            # Detect start of unwanted scheme dump in health response
            if any(marker in line for marker in [
                "��儭�", "CMCHIS:", "PM-JAY:", "Aarogyasri:", "鉈𨫼挽鉈芹�鉈芹�鉈颴�鉈颴� 鉈戈挪鉈颴�鉈颴悅鉒�", "鈰芹陞鈰𨫼�", "鉥芹揭鉞温揮鉥戈曾",
                "Where to apply:", "Required Documents:", "鉈菽挪鉈␡�鉈␡悚鉒温悚鉈賴�鉒温�鉒�悅鉒� 鉈桌�鉈晤�:"
            ]):
                skip_scheme_section = True
                continue

            if skip_scheme_section and any(marker in line for marker in [
                "When to see a doctor", "Nearby healthcare", "Primary Health Centre",
                "鉈�扇鉈桌�鉈� 鉈𠼭�鉈𨫼挽鉈戈挽鉈�", "鉈桌扇鉒�恕鉒温恕鉒�挾鉈啤� 鉈�恐鉒��鉈菽�鉈桌�", "鈰菽�鈰舟�鈰能�鈰﹤倏鈰兒倏", "鉥﹤�鉥𨫼�鉥颴敢鉞�"
            ]):
                skip_scheme_section = False

            if not skip_scheme_section:
                cleaned_lines.append(line)

        sanitized = "\n".join(cleaned_lines).strip()
        if len(sanitized) > 40:
            response_text = sanitized

    return response_text


def generate_healthcare_response(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    language_code: Optional[str] = "ta-IN",
    state: Optional[str] = None,
    district: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronous entry point for Arogya Nexus AI Assistant:
    1. Deterministic Intent Routing (EMERGENCY, OUT_OF_DOMAIN, HEALTH_SYMPTOM, GOVERNMENT_SCHEME, NEARBY_HOSPITAL, etc.)
    2. Fast emergency short-circuit (<2ms)
    3. Fast out-of-domain short-circuit (<2ms)
    4. Nearby hospital retrieval
    5. Health-focused RAG with Sarvam AI LLM invocation
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty.")

    clean_msg = user_message.strip()
    target_lang = language_code or "ta-IN"

    intent, intent_meta = classify_intent(clean_msg, language_code=target_lang, history=history)

    # 1. EMERGENCY FAST-PATH (<2ms)
    if intent == "EMERGENCY":
        fast_resp = get_fast_emergency_response(clean_msg, lang=target_lang)
        return {
            "response": fast_resp,
            "intent": "EMERGENCY",
            "knowledge_used": True,
            "matched_topics": ["108 Emergency Medical Protocol"],
            "matched_schemes": [],
            "sources": [{"title": "108 Emergency Medical Protocol", "url": "https://mohfw.gov.in/"}],
            "is_emergency": True,
            "is_symptom": True,
            "suggest_nearby_hospitals": True,
        }

    # 2. OUT-OF-DOMAIN FAST-PATH (<2ms)
    if intent == "OUT_OF_DOMAIN":
        out_of_domain_resp = intent_meta.get("fast_response") or get_localized_out_of_domain_response(target_lang)
        return {
            "response": out_of_domain_resp,
            "intent": "OUT_OF_DOMAIN",
            "knowledge_used": False,
            "matched_topics": ["General Healthcare Scope"],
            "matched_schemes": [],
            "sources": [],
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": False,
        }

    # 3. HEALTH_PHOTO INTENT
    if intent == "HEALTH_PHOTO":
        resp_msg = (
            "�𤦉 **AI Health Image Assistant**\n\n"
            "To analyze a visible skin rash, minor superficial wound, redness, or swelling, please click the **Health Photo** tab above or use the camera icon. "
            "You can take a photo in good lighting for supportive visual observation, safe first-aid care, and red-flag alerts.\n\n"
            "*Notice: AI visual guidance is for educational first-aid support, not a definitive medical diagnosis.*"
        )
        return {
            "response": resp_msg,
            "intent": "HEALTH_PHOTO",
            "knowledge_used": True,
            "matched_topics": ["Visual Health Observation"],
            "matched_schemes": [],
            "sources": [],
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": False,
        }

    # 4. NEARBY_HOSPITAL INTENT
    if intent in ("NEARBY_HOSPITAL", "NEARBY_HEALTHCARE"):
        hosp_res = get_nearby_hospitals(district=district, location=location, limit=3)
        hosp_text = format_nearby_hospitals_text(hosp_res, lang=target_lang)
        return {
            "response": hosp_text,
            "intent": "NEARBY_HOSPITAL",
            "knowledge_used": True,
            "matched_topics": ["Hospital Directory"],
            "matched_schemes": [],
            "sources": [{"title": "Verified Public Healthcare Directory", "url": "https://tnhealth.tn.gov.in/"}],
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": True,
            "nearby_hospitals": hosp_res.get("hospitals", []),
            "user_location": hosp_res.get("user_location"),
        }

    # 5. RAG KNOWLEDGE RETRIEVAL
    is_scheme_intent = intent in ("GOVERNMENT_SCHEME", "SCHEME_QUERY")
    is_symptom_only = intent in ("HEALTH_SYMPTOM", "HEALTH_QUERY", "GENERAL_HEALTH", "GENERAL_SUPPORTED_HEALTHCARE")

    search_query = clean_msg
    if history and len(clean_msg.split()) <= 4:
        prev_user_msgs = [m.get("content", "") for m in history if m.get("role") == "user"]
        if prev_user_msgs:
            search_query = f"{prev_user_msgs[-1]} {clean_msg}"

    search_result = search_knowledge_base(
        search_query,
        state=state,
        top_k=3,
        is_symptom_only=is_symptom_only
    )
    knowledge_context = format_knowledge_context_for_llm(search_result, lang=target_lang)

    lang_name = "Tamil"
    if "te" in target_lang.lower():
        lang_name = "Telugu (鈰戈�鈰耜�鈰鉮�)"
    elif "ml" in target_lang.lower():
        lang_name = "Malayalam (鉥桌散鉥能晷鉥喪�)"
    elif "en" in target_lang.lower():
        lang_name = "Indian English"

    sources_summary = "\n".join([f"- {s['title']}: {s['url']}" for s in search_result.get("sources", [])])
    if not sources_summary:
        sources_summary = "Official Public Health Standards / MoHFW"

    loc_str = location or district or "your local area"
    if is_scheme_intent:
        guidance_instruction = (
            "The query is about government health schemes. Structure your response concisely with: "
            "��儭� Scheme Name, �� Benefits, �𪈠 Eligibility, �� Required Documents, �� Where/How to apply, "
            "and official verification disclaimer."
        )
    else:
        guidance_instruction = (
            "The query is about health symptoms/conditions. Prioritize safe, concise health guidance. "
            "DO NOT discuss government schemes or health insurance. "
            "Follow this exact 5-point structure using concise bullet points: "
            "1. What you can do now, "
            "2. Simple supportive / home-care steps, "
            "3. What to avoid, "
            "4. Warning signs / when to see a doctor, "
            f"5. Nearby hospital option (ask briefly: 'If your symptoms persist, would you like to view nearby hospitals in {loc_str}?')"
        )

    user_prompt = (
        f"[USER QUERY]\n{clean_msg}\n\n"
        f"[SELECTED USER LANGUAGE]\n{lang_name}\n\n"
        f"[USER STATE / REGION]\n{state or 'All-India'}\n\n"
        f"[VERIFIED KNOWLEDGE BASE CONTEXT]\n{knowledge_context}\n\n"
        f"[OFFICIAL SOURCES]\n{sources_summary}\n\n"
        f"[INSTRUCTION]\n"
        f"Respond EXCLUSIVELY in {lang_name}. "
        f"Ground your answer strictly in the verified context. "
        f"{guidance_instruction}"
    )

    messages_payload = [{"role": "system", "content": HEALTHCARE_SYSTEM_PROMPT}]
    if history:
        recent_history = history[-4:]
        for h in recent_history:
            role = h.get("role")
            content = h.get("content", "")
            if role in ("user", "assistant") and content.strip():
                clean_content = content.replace("[VERIFIED KNOWLEDGE BASE CONTEXT]", "").strip()
                messages_payload.append({"role": role, "content": clean_content})

    messages_payload.append({"role": "user", "content": user_prompt})

    response_text = ""
    try:
        client = get_llm_client()
        response = client.chat.completions(
            model="sarvam-105b",
            messages=messages_payload,
            temperature=0.2
        )

        if response and response.choices and len(response.choices) > 0:
            message_content = response.choices[0].message.content
            if message_content:
                response_text = message_content.strip()
    except Exception as llm_err:
        print(f"[WARN] Sarvam LLM API call error: {llm_err}. Using verified knowledge card fallback.")
        tag = "ta" if "ta" in target_lang else ("te" if "te" in target_lang else ("ml" if "ml" in target_lang else "en"))

        if is_scheme_intent and search_result.get("matched_schemes"):
            s = search_result["matched_schemes"][0]
            name = s.get("scheme_name", {}).get(tag, s.get("title_en", ""))
            ben = "\n- ".join(s.get("benefits", {}).get(tag, s.get("benefits", {}).get("en", [])))
            elig = "\n- ".join(s.get("eligibility", {}).get(tag, s.get("eligibility", {}).get("en", [])))
            docs = "\n- ".join(s.get("required_documents", {}).get(tag, s.get("required_documents", {}).get("en", [])))
            where = s.get("where_to_apply", {}).get(tag, ["Primary Health Centre / e-Sevai / Grama Sachivalayam"])[0]

            response_text = (
                f"��儭� **{name}**\n\n"
                f"�� **Benefits / 鉈芹悖鉈拈�鉈𨫼拿鉒� / 鈰芹�鈰啤偺鈺肀�鈰兒偏鈰耜�:**\n- {ben}\n\n"
                f"�𪈠 **Eligibility / 鉈戈�鉒�恕鉈� / 鈰�偽鈺温偎鈰�:**\n- {elig}\n\n"
                f"�� **Required Documents / 鉈戈�鉈菽�鉈能挽鉈� 鉈�挾鉈␡�鉒温�鉈喪�:**\n- {docs}\n\n"
                f"�� **Where to Apply:** {where}\n\n"
                f"�𩤃� *Final eligibility must be verified by official government authorities.*"
            )
        elif search_result.get("matched_cards"):
            card = search_result["matched_cards"][0]
            card_title = card.get(f"title_{tag}", card.get("title_en", "Health Guidance"))
            indicates = card.get("what_it_indicates", {}).get(tag, card.get("what_it_indicates", {}).get("en", ""))
            home_care = "\n- ".join(card.get("safe_home_care", {}).get(tag, card.get("safe_home_care", {}).get("en", [])))
            avoid = "\n- ".join(card.get("what_to_avoid", {}).get(tag, card.get("what_to_avoid", {}).get("en", [])))
            red_flags = "\n- ".join(card.get("warning_signs", {}).get(tag, card.get("warning_signs", {}).get("en", [])))

            parts = [f"**{card_title}**"]
            parts.append(f"**1. What You Can Do Now:** {indicates or 'Rest and keep hydrated.'}")
            if home_care:
                parts.append(f"**2. Simple Supportive Steps:**\n- {home_care}")
            if avoid:
                parts.append(f"**3. What to Avoid:**\n- {avoid}")
            if red_flags:
                parts.append(f"**4. Warning Signs / When to See a Doctor:**\n- {red_flags}")
            parts.append(f"**5. Nearby Healthcare:** If symptoms persist or worsen, would you like me to show nearby hospitals in {loc_str}?")

            response_text = "\n\n".join(parts)
        else:
            if "te" in target_lang:
                response_text = f"鈰芹�鈰啤�鈰戈倏 鈰菽倏鈰嗣�鈰啤偏鈰�陘鈰� 鈰戈�鈰詮�鈰𨫼�鈰�陛鈰�, 鈰芹�鈰獅�鈰𨫼假鈰��鈰� 鈰兒�鈰啤� 鈰戈偏鈰鉮�鈰﹤倏. 鈰耜�鈺温健鈰␡偏鈰耜� 鈰戈�鈺温�鈰𨫼高鈺肀陘鈺� 鈰詮乾鈺�鈰芹�鈰耜�鈰兒倏 鈰�偽鈺肀�鈺温偺 鈰𨫼�鈰�隻鈺温偽鈰擒馬鈺温馬鈰� 鈰詮�鈰芹�鈰啤隻鈰賴�鈰𠼭�鈰﹤倏."
            elif "ml" in target_lang:
                response_text = f"鉥兒捶鉞温捶鉥擒敞鉥� 鉥菽曾鉥嗣�鉥啤揹鉥賴�鉞温�鉞��, 鉥抉晷鉥啤晷鉥喪� 鉥菽�鉥喪�鉥喪� 鉥𨫼�鉥颴曾鉥𨫼�鉥𨫼�鉥�. 鉥耜�鉞温晰鉥␡�鉞温�鉞� 鉥戈�鉥颴敦鉞��鉥能晷鉥␡�鉥跃�鉥𨫼曾鉞� 鉥��鉞�握鉞温握鉞�斑鉞温斑 鉥�普鉞�揪鉥戈�鉥啤曾 鉥詮捶鉞温揭鉞潼普鉥賴�鉞温�鉞��."
            elif "en" in target_lang:
                response_text = f"Please take adequate rest and maintain hydration. If symptoms persist or worsen, consider seeing a doctor. Would you like to view nearby hospitals in {loc_str}?"
            else:
                response_text = f"鉈兒悟鉒温拳鉈擒� 鉈㮙悖鉒温挾鉒��鉒��鉒温�鉈菽�鉈桌�, 鉈芹�鉈戈�鉈桌挽鉈� 鉈�拿鉈菽� 鉈𨫼挽鉈能�鉈𠼭�鉈𠼭挪鉈� 鉈兒�鉈啤� 鉈芹扇鉒��鉈菽�鉈桌�. 鉈�拳鉈賴�鉒�拳鉈賴�鉈喪� 鉈戈�鉈颴扇鉒温悄鉒温恕鉈擒挈鉒� 鉈桌扇鉒�恕鉒温恕鉒�挾鉈啤� 鉈�恐鉒��鉈菽�鉈桌�. 鉈�扇鉒��鉈賴挈鉒�拿鉒温拿 鉈桌扇鉒�恕鉒温恕鉒�挾鉈桌悟鉒��鉈喪� 鉈芹挽鉈啤�鉈𨫼�鉈� 鉈菽挪鉈啤�鉈桌�鉈芹�鉈𨫼挪鉈晤�鉈啤�鉈𨫼拿鉈�?"

    response_text = sanitize_and_guard_response(response_text, intent, target_lang)

    clean_matched_schemes = []
    if not is_symptom_only:
        for s in search_result.get("matched_schemes", []):
            cid = s.get("id", "")
            clean_matched_schemes.append({
                "id": SchemeId(cid),
                "scheme_id": cid,
                "scheme_name": s.get("scheme_name", {"en": s.get("title_en", ""), "ta": s.get("title_ta", "")}),
                "state": s.get("state", "National"),
                "official_source": s.get("official_source", "Government Authority"),
                "official_url": s.get("official_url", ""),
                "benefits": s.get("benefits", {}),
                "eligibility": s.get("eligibility", {}),
                "required_documents": s.get("required_documents", {}),
                "how_to_apply": s.get("how_to_apply", {}),
                "where_to_apply": s.get("where_to_apply", {}),
                "last_verified": s.get("last_verified", "2026-08-25")
            })

    return {
        "response": response_text,
        "intent": intent,
        "knowledge_used": bool(search_result.get("has_matches")),
        "matched_topics": search_result.get("matched_topics", []),
        "matched_schemes": clean_matched_schemes,
        "sources": search_result.get("sources", []),
        "is_emergency": bool(search_result.get("is_emergency", False)),
        "is_symptom": is_symptom_only,
        "suggest_nearby_hospitals": is_symptom_only,
    }


def generate_healthcare_response_stream(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    language_code: Optional[str] = "ta-IN",
    state: Optional[str] = None,
    district: Optional[str] = None,
    location: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming generator for Arogya Nexus AI Assistant.
    Yields Server-Sent Events (SSE) formatted chunks:
    1. 'metadata' event with intent, is_emergency, suggest_nearby_hospitals, etc.
    2. 'token' events containing incremental text chunks.
    3. '[DONE]' event marking stream completion.
    """
    if not user_message or not user_message.strip():
        yield f"data: {json.dumps({'error': 'User message cannot be empty.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    clean_msg = user_message.strip()
    target_lang = language_code or "ta-IN"

    intent, intent_meta = classify_intent(clean_msg, language_code=target_lang, history=history)

    # 1. EMERGENCY SHORT-CIRCUIT (<2ms)
    if intent == "EMERGENCY":
        fast_resp = get_fast_emergency_response(clean_msg, lang=target_lang)
        meta = {
            "intent": "EMERGENCY",
            "is_emergency": True,
            "is_symptom": True,
            "suggest_nearby_hospitals": True,
            "matched_topics": ["108 Emergency Medical Protocol"],
            "matched_schemes": [],
        }
        yield f"data: {json.dumps({'metadata': meta})}\n\n"
        yield f"data: {json.dumps({'token': fast_resp})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 2. OUT-OF-DOMAIN SHORT-CIRCUIT (<2ms)
    if intent == "OUT_OF_DOMAIN":
        out_of_domain_resp = intent_meta.get("fast_response") or get_localized_out_of_domain_response(target_lang)
        meta = {
            "intent": "OUT_OF_DOMAIN",
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": False,
            "matched_topics": ["General Healthcare Scope"],
            "matched_schemes": [],
        }
        yield f"data: {json.dumps({'metadata': meta})}\n\n"
        yield f"data: {json.dumps({'token': out_of_domain_resp})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 3. HEALTH_PHOTO SHORT-CIRCUIT
    if intent == "HEALTH_PHOTO":
        resp_msg = (
            "�𤦉 **AI Health Image Assistant**\n\n"
            "To analyze a visible skin rash, minor superficial wound, redness, or swelling, please navigate to the **Health Photo** tab above. "
            "You can take a photo in good lighting for supportive visual observation, safe first-aid care, and red-flag alerts.\n\n"
            "*Notice: AI visual guidance is for educational first-aid support, not a definitive medical diagnosis.*"
        )
        meta = {
            "intent": "HEALTH_PHOTO",
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": False,
            "matched_topics": ["Visual Health Observation"],
            "matched_schemes": [],
        }
        yield f"data: {json.dumps({'metadata': meta})}\n\n"
        yield f"data: {json.dumps({'token': resp_msg})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 4. NEARBY_HOSPITAL SHORT-CIRCUIT
    if intent in ("NEARBY_HOSPITAL", "NEARBY_HEALTHCARE"):
        hosp_res = get_nearby_hospitals(district=district, location=location, limit=3)
        hosp_text = format_nearby_hospitals_text(hosp_res, lang=target_lang)
        meta = {
            "intent": "NEARBY_HOSPITAL",
            "is_emergency": False,
            "is_symptom": False,
            "suggest_nearby_hospitals": True,
            "matched_topics": ["Hospital Directory"],
            "matched_schemes": [],
            "nearby_hospitals": hosp_res.get("hospitals", []),
            "user_location": hosp_res.get("user_location"),
        }
        yield f"data: {json.dumps({'metadata': meta})}\n\n"
        yield f"data: {json.dumps({'token': hosp_text})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 5. KNOWLEDGE RETRIEVAL & LLM STREAMING
    is_scheme_intent = intent in ("GOVERNMENT_SCHEME", "SCHEME_QUERY")
    is_symptom_only = intent in ("HEALTH_SYMPTOM", "HEALTH_QUERY", "GENERAL_HEALTH", "GENERAL_SUPPORTED_HEALTHCARE")

    search_query = clean_msg
    if history and len(clean_msg.split()) <= 4:
        prev_user_msgs = [m.get("content", "") for m in history if m.get("role") == "user"]
        if prev_user_msgs:
            search_query = f"{prev_user_msgs[-1]} {clean_msg}"

    search_result = search_knowledge_base(
        search_query,
        state=state,
        top_k=3,
        is_symptom_only=is_symptom_only
    )
    knowledge_context = format_knowledge_context_for_llm(search_result, lang=target_lang)

    stream_schemes = []
    if not is_symptom_only:
        stream_schemes = search_result.get("matched_schemes", [])

    meta = {
        "intent": intent,
        "is_emergency": False,
        "is_symptom": is_symptom_only,
        "suggest_nearby_hospitals": is_symptom_only,
        "knowledge_used": bool(search_result.get("has_matches")),
        "matched_topics": search_result.get("matched_topics", []),
        "matched_schemes": stream_schemes,
    }
    yield f"data: {json.dumps({'metadata': meta})}\n\n"

    lang_name = "Tamil"
    if "te" in target_lang.lower():
        lang_name = "Telugu (鈰戈�鈰耜�鈰鉮�)"
    elif "ml" in target_lang.lower():
        lang_name = "Malayalam (鉥桌散鉥能晷鉥喪�)"
    elif "en" in target_lang.lower():
        lang_name = "Indian English"

    sources_summary = "\n".join([f"- {s['title']}: {s['url']}" for s in search_result.get("sources", [])])
    if not sources_summary:
        sources_summary = "Official Public Health Standards / MoHFW"

    loc_str = location or district or "your local area"
    if is_scheme_intent:
        guidance_instruction = (
            "The query is about government health schemes. Structure your response concisely with: "
            "��儭� Scheme Name, �� Benefits, �𪈠 Eligibility, �� Required Documents, �� Where/How to apply, "
            "and official verification disclaimer."
        )
    else:
        guidance_instruction = (
            "The query is about health symptoms/conditions. Prioritize safe, concise health guidance. "
            "DO NOT discuss government schemes or health insurance. "
            "Follow this exact 5-point structure using concise bullet points: "
            "1. What you can do now, "
            "2. Simple supportive / home-care steps, "
            "3. What to avoid, "
            "4. Warning signs / when to see a doctor, "
            f"5. Nearby hospital option (ask briefly: 'If your symptoms persist, would you like to view nearby hospitals in {loc_str}?')"
        )

    user_prompt = (
        f"[USER QUERY]\n{clean_msg}\n\n"
        f"[SELECTED USER LANGUAGE]\n{lang_name}\n\n"
        f"[USER STATE / REGION]\n{state or 'All-India'}\n\n"
        f"[VERIFIED KNOWLEDGE BASE CONTEXT]\n{knowledge_context}\n\n"
        f"[OFFICIAL SOURCES]\n{sources_summary}\n\n"
        f"[INSTRUCTION]\n"
        f"Respond EXCLUSIVELY in {lang_name}. "
        f"Ground your answer strictly in the verified context. "
        f"{guidance_instruction}"
    )

    messages_payload = [{"role": "system", "content": HEALTHCARE_SYSTEM_PROMPT}]
    if history:
        recent_history = history[-4:]
        for h in recent_history:
            role = h.get("role")
            content = h.get("content", "")
            if role in ("user", "assistant") and content.strip():
                clean_content = content.replace("[VERIFIED KNOWLEDGE BASE CONTEXT]", "").strip()
                messages_payload.append({"role": role, "content": clean_content})

    messages_payload.append({"role": "user", "content": user_prompt})

    token_streamed = False
    try:
        client = get_llm_client()
        stream = client.chat.completions(
            model="sarvam-105b",
            messages=messages_payload,
            temperature=0.2,
            stream=True
        )

        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = getattr(chunk.choices[0], "delta", None)
                if delta and getattr(delta, "content", None):
                    token = delta.content
                    token_streamed = True
                    yield f"data: {json.dumps({'token': token})}\n\n"

    except Exception as stream_err:
        print(f"[WARN] Streaming error: {stream_err}. Using verified fallback.")
        if not token_streamed:
            fallback_res = generate_healthcare_response(
                clean_msg,
                history=history,
                language_code=target_lang,
                state=state,
                district=district,
                location=location
            )
            yield f"data: {json.dumps({'token': fallback_res.get('response', '')})}\n\n"

    yield "data: [DONE]\n\n"
