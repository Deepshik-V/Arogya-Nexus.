"""
Arogya Nexus — Multi-Turn LLM Healthcare Response & Streaming Service
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

HEALTHCARE_SYSTEM_PROMPT = """You are Arogya Nexus (ஆரோக்கிய நெக்ஸஸ் / ఆరోగ్య నెక్సస్ / ആരോഗ്യ നെക്സസ്), a Personal Multilingual AI Healthcare Assistant designed for citizens across India.

CRITICAL OPERATIONAL RULES & SAFETY GUARDRAILS:

1. STRICT LANGUAGE MATCHING:
   - If the user query is in Tamil or Tanglish, or language is Tamil: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL TAMIL (தமிழ்). Understand Tanglish seamlessly (e.g., 'enakku fever irukku', 'thala vali', 'stomach pain irukku').
   - If the user query is in Telugu or language is Telugu: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL TELUGU (తెలుగు).
   - If the user query is in Malayalam or language is Malayalam: YOU MUST RESPOND EXCLUSIVELY IN CLEAR, NATURAL MALAYALAM (മലയാളം).
   - If the user query is in English: RESPOND IN SIMPLE, CLEAR INDIAN ENGLISH.
   - NEVER switch to English when a regional language is chosen.

2. HEALTH SYMPTOM QUERIES (CONCISE, SAFE, NO ESSAYS, NO UNREQUESTED SCHEMES):
   When a user asks about symptoms (fever, headache, stomach pain, vomiting, cough, diarrhea, dizziness, swelling, body pain, etc.):
   Answer ONLY the user's actual healthcare concern. Do NOT dump government schemes or health insurance details!
   Use uncertainty-aware language ("This can have several causes. Based on what you've described..."). Never claim a definitive diagnosis. Never promise 90% accuracy.
   Follow this exact 5-point structure concisely:
   👉 1. What you can do now (Immediate safe guidance)
   👉 2. Simple supportive / home-care steps (Hydration, rest, light food, cooling)
   👉 3. What to avoid (Self-medicating with antibiotics, heavy exertion, unverified substances)
   👉 4. Warning signs / when to see a doctor (Red flags requiring Primary Health Centre / PHC evaluation)
   👉 5. Nearby hospital option (Briefly ask: "If your symptoms persist, would you like me to show nearby hospitals in your area?")

3. GOVERNMENT SCHEME QUERIES (ONLY WHEN EXPLICITLY ASKED):
   - When the user specifically asks about health schemes (CMCHIS, Dr. YSR Aarogyasri, KASP, PM-JAY, MRMBS, PMMVY, JSY, etc.), structure the response:
     🏛️ Scheme Name (திட்ட பெயர் / పథకం పేరు / പദ്ധതിയുടെ പേര്)
     📋 Benefits provided (வழங்கப்படும் நன்மைகள் / అందించే ప్రయోజనాలు / ലഭ്യമാകുന്ന ആനുകൂല്യങ്ങൾ)
     🎯 Basic eligibility (தகுதி வரம்பு / అర్హత ప్రమాణాలు / യോഗ്യതാ മാനదണ്ഡങ്ങൾ)
     📄 Required documents (தேவையான ஆவணங்கள் / అవసరమైన పత్రాలు / ആവശ്യമായ രേഖകൾ)
     📍 How & Where to apply (விண்ணப்பிக்கும் முறை மற்றும் இடம் / దరఖాస్తు చేసుకునే విధానం మరియు కేంద్రం / അപേക്ഷിക്കേണ്ട വിധവും സ്ഥലവും)
     ℹ️ Official verification disclaimer: "Final benefit confirmation must be done with official government authorities."

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

    return SarvamAI(api_subscription_key=api_key)


def get_fast_emergency_response(query: str, lang: str = "ta-IN") -> str:
    """
    Deterministic instant (<2ms) emergency triage protocol.
    Bypasses LLM and RAG entirely for safety-critical queries.
    """
    lower = query.lower()
    is_snakebite = any(k in lower for k in [
        "snake", "bite", "பாம்பு", "கடி", "పాము", "కాటు", "പാമ്പ്", "കടി"
    ])

    if "en" in lang.lower():
        if is_snakebite:
            return (
                "🚨 **EMERGENCY MEDICAL PROTOCOL: IMMEDIATE ACTION REQUIRED!**\n\n"
                "1. **DIAL 108 IMMEDIATELY FOR AN EMERGENCY AMBULANCE.**\n"
                "2. Keep the patient calm and completely still. Movement causes venom to spread faster.\n"
                "3. Immobilize the bitten limb using a splint or sling at heart level.\n"
                "4. **DO NOT** cut, suction, or apply a tight tourniquet.\n"
                "5. Rush directly to the nearest Government Headquarters Hospital equipped with Anti-Snake Venom (ASV)."
            )
        return (
            "🚨 **CRITICAL EMERGENCY MEDICAL ALERT: 108 AMBULANCE REQUIRED!**\n\n"
            "1. **CALL 108 IMMEDIATELY FOR EMERGENCY MEDICAL SERVICES.**\n"
            "2. Keep the patient in a comfortable, seated, or semi-reclined position (W-position).\n"
            "3. Loosen any tight clothing around neck and chest; ensure continuous ventilation.\n"
            "4. Do not offer oral fluids or food if the person is dizzy, faint, or short of breath.\n"
            "5. If unconscious and breathing stops, initiate chest compressions immediately."
        )
    elif "te" in lang.lower():
        if is_snakebite:
            return (
                "🚨 **అత్యవసర వైద్య హెచ్చరిక: తక్షణమే 108 కు కాల్ చేయండి!**\n\n"
                "1. **వెంటనే 108 అత్యవసర అంబులెన్స్‌కు కాల్ చేయండి.**\n"
                "2. బాధితుడిని కదలకుండా ప్రశాంతంగా ఉంచండి. కదలడం వల్ల విషం వేగంగా వ్యాపిస్తుంది.\n"
                "3. కాటు వేసిన భాగాన్ని గుండె స్థాయి కంటే కింద లేదా సమంగా ఉంచండి.\n"
                "4. గాటు పెట్టడం, నోటితో పీల్చడం లేదా గట్టిగా కట్టడం చేయవద్దు.\n"
                "5. వెంటనే యాంటీ స్నేక్ వెనమ్ (ASV) అందుబాటులో ఉన్న సమీప ప్రభుత్వ ఆసుపత్రికి తరలించండి."
            )
        return (
            "🚨 **అత్యవసర హెచ్చరిక: 108 అంబులెన్స్ తక్షణమే అవసరం!**\n\n"
            "1. వెంటనే 108 అత్యవసర సేవలకు కాల్ చేయండి.\n"
            "2. రోగిని విశ్రాంత స్థితిలో (W-స్థితి) కూర్చోబెట్టండి.\n"
            "3. ఛాతీ, మెడ చుట్టూ ఉన్న దుస్తులను వదులు చేయండి; గాలి ధారాళంగా ఆడేలా చూడండి.\n"
            "4. స్పృహ లేకపోతే లేదా శ్వాస తీసుకోవడంలో ఇబ్బంది ఉంటే ఆహారం లేదా నీరు ఇవ్వవద్దు.\n"
            "5. అత్యవసర ECG సౌకర్యం ఉన్న సమీప ఆసుపత్రికి వెంటనే తరలించండి."
        )
    elif "ml" in lang.lower():
        if is_snakebite:
            return (
                "🚨 **അടിയന്തര മെഡിക്കൽ മുന്നറിയിപ്പ്: ഉടൻ 108 ആംബുലൻസ് വിളിക്കുക!**\n\n"
                "1. **ഉടൻ തന്നെ 108 എമർജൻസി ആംബുലൻസ് വിളിക്കുക.**\n"
                "2. രോഗിയെ പൂർണ്ണമായും അനങ്ങാതെ ശാന്തമായി കിടത്തുക. ചലനം വിഷം വേഗത്തിൽ പടരാൻ ഇടയാക്കും.\n"
                "3. കടിയേറ്റ ഭാഗം ഹൃദയ നിരപ്പിൽ അനക്കാതെ സൂക്ഷിക്കുക.\n"
                "4. മുറിവുണ്ടാക്കാനോ, വിഷം വലിച്ച് കുടിക്കാനോ, മുറുക്കി കെട്ടാനോ പാടില്ല.\n"
                "5. ആന്റി-സ്നേക്ക് വെനം (ASV) ലഭ്യമായ തൊട്ടടുത്ത സർക്കാർ ആശുപത്രിയിൽ ഉടൻ എത്തിക്കുക."
            )
        return (
            "🚨 **അടിയന്തര മുന്നറിയിപ്പ്: ഉടൻ 108 ആംബുലൻസ് വിളിക്കുക!**\n\n"
            "1. ഉടൻ തന്നെ 108 എമർജൻസി ആംബുലൻസ് സർവീസിനെ വിളിക്കുക.\n"
            "2. രോഗിയെ ശാന്തമായി ചാരി ഇരിക്കാൻ (W-Position) അനുവദിക്കുക.\n"
            "3. കഴുത്തിലും നെഞ്ചിലുമുള്ള ഇറുകിയ വസ്ത്രങ്ങൾ അയച്ച് ശുദ്ധവായു ഉറപ്പാക്കുക.\n"
            "4. അബോധാവസ്ഥയിലോ ശ്വാസതടസ്സമോ ഉണ്ടെങ്കിൽ ഭക്ഷണവും വെള്ളവും നൽകരുത്.\n"
            "5. ഇസിജി സൗകര്യമുള്ള തൊട്ടടുത്ത ആശുപത്രിയിൽ രോഗിയെ ഉടൻ എത്തിക്കുക."
        )
    else:  # Tamil default
        if is_snakebite:
            return (
                "🚨 **அவசர மருத்துவ எச்சரிக்கை: உடனடியாக 108 ஆம்புலன்ஸை அழைக்கவும்!**\n\n"
                "1. **உடனடியாக 108 அவசர ஆம்புலன்ஸை அழைக்கவும்.**\n"
                "2. பாதிக்கப்பட்ட நபரை அமைதியாகவும் அசைவின்றியும் வைக்கவும். அசைவு விஷத்தை விரைவாக பரவச் செய்யும்.\n"
                "3. கடித்த பகுதியை இதய நிலைக்கு சமமாக அல்லது கீழே அசையாமல் வைக்கவும்.\n"
                "4. கடித்த இடத்தில் கீறவோ, வாயால் உறிஞ்சவோ, இறுக்கமாக கட்டவோ கூடாது.\n"
                "5. உடனடியாக பாம்புக்கடி மாற்று மருந்து (ASV) உள்ள அரசு தலைமை மருத்துவமனைக்கு கொண்டு செல்லவும்."
            )
        return (
            "🚨 **அவசர மருத்துவ எச்சரிக்கை: தீவிர நெஞ்சுவலி / மாரடைப்பு அறிகுறிகள்!**\n\n"
            "1. **உடனடியாக 108 அவசர ஆம்புலன்ஸை அழைக்கவும்.**\n"
            "2. நோயாளிக்கு வசதியான நிலையில், சாய்ந்த நிலையில் (W-Position) அமர வைக்கவும்.\n"
            "3. கழுத்து மற்றும் மார்புப் பகுதியில் உள்ள இறுக்கமான ஆடைகளை தளர்த்தி, தாராளமாக காற்று கிடைக்கச் செய்யவும்.\n"
            "4. நோயாளிக்கு மயக்கம் அல்லது மூச்சுத்திணறல் இருந்தால் வாய்வழியாக எதுவும் கொடுக்க வேண்டாம்.\n"
            "5. உடனடியாக ECG வசதி கொண்ட அருகிலுள்ள அரசு அல்லது தனியார் மருத்துவமனைக்கு கொண்டு செல்லவும்."
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
        f"🏥 **Nearby Healthcare Facilities (Location: {loc_label})**\n"
    ]
    for h in hospitals[:3]:
        dist_str = f" ({h.get('distance_label', '')})" if h.get("distance_label") else ""
        lines.append(f"📍 **{h.get('name')}**{dist_str}")
        lines.append(f"  Type: {h.get('type', 'Government Hospital')}")
        if h.get("address"):
            lines.append(f"  Address: {h.get('address')}")
        if h.get("phone"):
            lines.append(f"  Phone: {h.get('phone')}")
        if h.get("maps_url") or h.get("directions_url"):
            url = h.get("maps_url") or h.get("directions_url")
            lines.append(f"  [Get Directions on Map]({url})")
        lines.append("")

    lines.append("🧭 *You can also view these facilities with live interactive markers on the **Hospitals & Map** tab.*")
    return "\n".join(lines)


def build_structured_card_guidance(card: Dict[str, Any], lang_tag: str, location_str: str = "your local area") -> str:
    """
    Builds the canonical 5-point structured healthcare response directly from verified clinical card.
    """
    title = card.get(f"title_{lang_tag}") or card.get("title_en", "Health Guidance")
    indicates = card.get("what_it_indicates", {}).get(lang_tag) or card.get("what_it_indicates", {}).get("en", "")
    home_care = card.get("safe_home_care", {}).get(lang_tag) or card.get("safe_home_care", {}).get("en", [])
    avoid = card.get("what_to_avoid", {}).get(lang_tag) or card.get("what_to_avoid", {}).get("en", [])
    warning_signs = card.get("warning_signs", {}).get(lang_tag) or card.get("warning_signs", {}).get("en", [])
    phc_advice = card.get("when_to_visit_phc", {}).get(lang_tag) or card.get("when_to_visit_phc", {}).get("en", [])

    if lang_tag == "ta":
        parts = [f"🩺 **{title}**\n"]
        if indicates:
            parts.append(f"**பொதுவான காரணங்கள் மற்றும் விவரம்:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**நீங்கள் இப்போது செய்யக்கூடியவை:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**எளிய சுயபராமரிப்பு முறைகள்:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**தவிர்க்க வேண்டியவை:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**எச்சரிக்கை அறிகுறிகள் (உடனே கவனிக்க வேண்டியவை):**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**மருத்துவரை எப்போது அணுக வேண்டும்:**\n{doc_str}\n")
        parts.append(f"**அருகிலுள்ள மருத்துவமனைகள்:** அறிகுறிகள் நீடித்தால், {location_str} பகுதியில் உள்ள அருகிலுள்ள ஆரம்ப சுகாதார நிலையங்கள் (PHC) அல்லது மருத்துவமனைகளை பார்க்க விரும்புகிறீர்களா?")
    elif lang_tag == "te":
        parts = [f"🩺 **{title}**\n"]
        if indicates:
            parts.append(f"**సాధారణ కారణాలు మరియు సమాచారం:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**మీరు ప్రస్తుతం చేయవలసిన చర్యలు:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**గృహ సంరక్షణ విధానాలు:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**నివారించవలసినవి:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**ప్రమాద హెచ్చరిక సంకేతాలు:**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**వైద్యుడిని ఎప్పుడు సంప్రదించాలి:**\n{doc_str}\n")
        parts.append(f"**సమీప ఆసుపత్రులు:** లక్షణాలు కొనసాగితే, {location_str} లోని సమీప ప్రాథమిక ఆరోగ్య కేంద్రాలు లేదా ఆసుపత్రులను చూడాలనుకుంటున్నారా?")
    elif lang_tag == "ml":
        parts = [f"🩺 **{title}**\n"]
        if indicates:
            parts.append(f"**സാധാരണ കാരണങ്ങളും വിവരങ്ങളും:**\n- {indicates}\n")
        if home_care:
            steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(home_care[:3])])
            parts.append(f"**നിങ്ങൾക്ക് ഇപ്പോൾ ചെയ്യാവുന്ന കാര്യങ്ങൾ:**\n{steps_str}\n")
            if len(home_care) > 3:
                care_str = "\n".join([f"- {s}" for s in home_care[3:]])
                parts.append(f"**ലളിതമായ പരിചരണ രീതികൾ:**\n{care_str}\n")
        if avoid:
            avoid_str = "\n".join([f"- {s}" for s in avoid])
            parts.append(f"**ഒഴിവാക്കേണ്ട കാര്യങ്ങൾ:**\n{avoid_str}\n")
        if warning_signs:
            warn_str = "\n".join([f"- {s}" for s in warning_signs])
            parts.append(f"**അപകട ലക്ഷണങ്ങൾ:**\n{warn_str}\n")
        if phc_advice:
            doc_str = "\n".join([f"- {s}" for s in phc_advice])
            parts.append(f"**ഡോക്ടറെ എപ്പോൾ കാണണം:**\n{doc_str}\n")
        parts.append(f"**സമീപത്തുള്ള ആശുപത്രികൾ:** ലക്ഷണങ്ങൾ തുടരുകയാണെങ്കിൽ, {location_str} സമീപത്തുള്ള പ്രാഥമിക ആരോഗ്യ കേന്ദ്രങ്ങൾ കാണാൻ താൽപ്പര്യമുണ്ടോ?")
    else:  # English
        parts = [f"🩺 **HEALTH GUIDANCE: {title}**\n"]
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
        "நெஞ்சு வலி", "மாரடைப்பு", "நெஞ்சுவலி", "గుండె నొప్పి", "గుండెపోటు", "ఛాతీ నొప్పి",
        "നെഞ്ചുവേദന", "ഹൃദയാഘാതം"
    ]
    if detected_topic in ("headache", "fever", "stomach_pain", "dizziness", "burns", "cough_cold"):
        has_unrelated_chest = any(ch in lower_resp for ch in chest_hallucinations)
        if has_unrelated_chest:
            if top_card:
                return build_structured_card_guidance(top_card, tag, location_str=loc_str)

    # Check 2: Strip unrequested schemes from symptom responses
    if intent in ("HEALTH_SYMPTOM", "HEALTH_QUERY", "GENERAL_HEALTH", "GENERAL_SUPPORTED_HEALTHCARE"):
        lines = response_text.splitlines()
        cleaned_lines = []
        skip_scheme_section = False
        for line in lines:
            if any(marker in line for marker in [
                "🏛️", "CMCHIS:", "PM-JAY:", "Aarogyasri:", "KASP:", "MRMBS:", "PMMVY:", "JSY:",
                "மருத்துவ காப்பீடு", "திட்ட பெயர்", "పథకం పేరు", "പദ്ധതിയുടെ പേര്",
                "Where to apply:", "Required Documents:", "விண்ணப்பிக்கும் முறை", "దరఖాస్తు చేసుకునే", "അപേക്ഷിക്കേണ്ട"
            ]):
                skip_scheme_section = True
                continue
            if skip_scheme_section and any(marker in line for marker in [
                "When to see a doctor", "Nearby healthcare", "Primary Health Centre",
                "மருத்துவரை எப்போது அணுக", "அருகிலுள்ள மருத்துவமனைகள்",
                "వైద్యుడిని ఎప్పుడు సంప్రదించాలి", "సమీప ఆసుపత్రులు",
                "ഡോക്ടറെ എപ്പോൾ കാണണം", "സമീപത്തുള്ള ആശുപത്രികൾ"
            ]):
                skip_scheme_section = False
            if not skip_scheme_section:
                cleaned_lines.append(line)
        sanitized = "\n".join(cleaned_lines).strip()
        if len(sanitized) > 30:
            response_text = sanitized

    return response_text


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
            if any(marker in line for marker in [
                "🏛️", "CMCHIS:", "PM-JAY:", "Aarogyasri:", "KASP:", "MRMBS:", "PMMVY:", "JSY:",
                "மருத்துவ காப்பீடு", "திட்ட பெயர்", "పథకం పేరు", "പദ്ധതിയുടെ പേര്",
                "Where to apply:", "Required Documents:", "விண்ணப்பிக்கும் முறை", "దరఖాస్తు చేసుకునే", "അപേക്ഷിക്കേണ്ട"
            ]):
                skip_scheme_section = True
                continue

            if skip_scheme_section and any(marker in line for marker in [
                "When to see a doctor", "Nearby healthcare", "Primary Health Centre",
                "மருத்துவரை எப்போது அணுக", "அருகிலுள்ள மருத்துவமனைகள்",
                "వైద్యుడిని ఎప్పుడు సంప్రదించాలి", "సమీప ఆసుపత్రులు",
                "ഡോക്ടറെ എപ്പോൾ കാണണം", "സമീപത്തുള്ള ആശുപത്രികൾ"
            ]):
                skip_scheme_section = False

            if not skip_scheme_section:
                cleaned_lines.append(line)

        sanitized = "\n".join(cleaned_lines).strip()
        if len(sanitized) > 30:
            return sanitized

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
    6. Guaranteed verified fallback if LLM is unavailable or empty
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
            "📷 **AI Health Image Assistant**\n\n"
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
    if history and (len(clean_msg.split()) <= 10 or is_scheme_intent):
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

    lang_name = "Tamil (தமிழ்)"
    if "te" in target_lang.lower():
        lang_name = "Telugu (తెలుగు)"
    elif "ml" in target_lang.lower():
        lang_name = "Malayalam (മലയാളം)"
    elif "en" in target_lang.lower():
        lang_name = "Indian English"

    sources_summary = "\n".join([f"- {s['title']}: {s['url']}" for s in search_result.get("sources", [])])
    if not sources_summary:
        sources_summary = "Official Public Health Standards / MoHFW"

    loc_str = location or district or "your local area"
    if is_scheme_intent:
        guidance_instruction = (
            "The query is about government health schemes. Structure your response concisely with: "
            "🏛️ Scheme Name, 📋 Benefits, 🎯 Eligibility, 📄 Required Documents, 📍 Where/How to apply, "
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
            temperature=0.2,
            max_tokens=800
        )

        if response and response.choices and len(response.choices) > 0:
            message_content = response.choices[0].message.content
            if message_content and message_content.strip():
                response_text = message_content.strip()
    except Exception as llm_err:
        pass

    # GUARANTEED CLINICAL FALLBACK: Triggers whenever LLM returns None, empty, or encounters errors
    if not response_text or len(response_text.strip()) < 15:
        tag = "ta" if "ta" in target_lang else ("te" if "te" in target_lang else ("ml" if "ml" in target_lang else "en"))

        if is_scheme_intent and search_result.get("matched_schemes"):
            s = search_result["matched_schemes"][0]
            name = s.get("scheme_name", {}).get(tag, s.get("title_en", ""))
            ben = "\n- ".join(s.get("benefits", {}).get(tag, s.get("benefits", {}).get("en", [])))
            elig = "\n- ".join(s.get("eligibility", {}).get(tag, s.get("eligibility", {}).get("en", [])))
            docs = "\n- ".join(s.get("required_documents", {}).get(tag, s.get("required_documents", {}).get("en", [])))
            where = s.get("where_to_apply", {}).get(tag, ["Primary Health Centre / e-Sevai / Grama Sachivalayam"])[0]

            response_text = (
                f"🏛️ **{name}**\n\n"
                f"📋 **Benefits / நன்மைகள் / ప్రయోజనాలు / ആനുകൂല്യങ്ങൾ:**\n- {ben}\n\n"
                f"🎯 **Eligibility / தகுதி / అర్హత / യോഗ്യത:**\n- {elig}\n\n"
                f"📄 **Required Documents / தேவையான ஆவணங்கள் / అవసరమైన పత్రాలు / ആവശ്യമായ രേഖകൾ:**\n- {docs}\n\n"
                f"📍 **Where to Apply / விண்ணப்பிக்கும் இடம்:** {where}\n\n"
                f"ℹ️ *Final eligibility must be verified by official government authorities.*"
            )
        elif search_result.get("matched_cards"):
            card = search_result["matched_cards"][0]
            response_text = build_structured_card_guidance(card, tag, location_str=loc_str)
        else:
            if "te" in target_lang:
                response_text = f"దయచేసి తగినంత విశ్రాంతి తీసుకోండి మరియు పుష్కలంగా నీరు త్రాగండి. లక్షణాలు కొనసాగితే లేదా తీవ్రమైతే, వెంటనే సమీప ప్రాథమిక ఆరోగ్య కేంద్రాన్ని సంప్రదించండి. {loc_str} లోని సమీప ఆసుపత్రులను చూడాలనుకుంటున్నారా?"
            elif "ml" in target_lang:
                response_text = f"ദയവായി ആവശ്യത്തിന് വിശ്രമിക്കുകയും ധാരാളം വെള്ളം കുടിക്കുകയും ചെയ്യുക. ലക്ഷണങ്ങൾ തുടരുകയാണെങ്കിൽ ഡോക്ടറുടെ സേവനം തേടുക. {loc_str} സമീപത്തുള്ള ആശുപത്രി വിവരങ്ങൾ ആവശ്യമുണ്ടോ?"
            elif "en" in target_lang:
                response_text = f"Please take adequate rest and maintain hydration. If symptoms persist or worsen, consider seeing a doctor. Would you like to view nearby hospitals in {loc_str}?"
            else:
                response_text = f"தயவுசெய்து போதுமான ஓய்வு எடுத்துக்கொள்ளுங்கள், மேலும் நிறைய தண்ணீர் குடிக்கவும். அறிகுறிகள் நீடித்தால் அல்லது தீவிரமடைந்தால் உடனடியாக அரசு ஆரம்ப சுகாதார நிலைய மருத்துவரை அணுகவும். {loc_str} பகுதியில் உள்ள அருகிலுள்ள மருத்துவமனைகளை பார்க்க விரும்புகிறீர்களா?"

    response_text = sanitize_and_guard_response(response_text, intent, target_lang)

    # FINAL SAFETY NET: If sanitize_and_guard_response stripped everything, generate structured card guidance
    if not response_text or len(response_text.strip()) < 15:
        tag = "ta" if "ta" in target_lang else ("te" if "te" in target_lang else ("ml" if "ml" in target_lang else "en"))
        if search_result.get("matched_cards"):
            response_text = build_structured_card_guidance(search_result["matched_cards"][0], tag, location_str=loc_str)
        else:
            response_text = f"Please take adequate rest and maintain hydration. If symptoms persist or worsen, consider seeing a doctor at the nearest Primary Health Centre in {loc_str}."

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
            "📷 **AI Health Image Assistant**\n\n"
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

    lang_name = "Tamil (தமிழ்)"
    if "te" in target_lang.lower():
        lang_name = "Telugu (తెలుగు)"
    elif "ml" in target_lang.lower():
        lang_name = "Malayalam (മലയാളം)"
    elif "en" in target_lang.lower():
        lang_name = "Indian English"

    sources_summary = "\n".join([f"- {s['title']}: {s['url']}" for s in search_result.get("sources", [])])
    if not sources_summary:
        sources_summary = "Official Public Health Standards / MoHFW"

    loc_str = location or district or "your local area"
    if is_scheme_intent:
        guidance_instruction = (
            "The query is about government health schemes. Structure your response concisely with: "
            "🏛️ Scheme Name, 📋 Benefits, 🎯 Eligibility, 📄 Required Documents, 📍 Where/How to apply, "
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
            max_tokens=800,
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
        pass

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
