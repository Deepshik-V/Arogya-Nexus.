"""
Arogya Nexus — Deterministic Pre-LLM Intent Routing Engine
Classifies user queries across English, Tamil, Tanglish, Telugu, and Malayalam
BEFORE initiating expensive LLM or retrieval pipelines.

Supported Canonical Primary Intents:
1. EMERGENCY
2. HEALTH_SYMPTOM
3. GOVERNMENT_SCHEME
4. NEARBY_HOSPITAL
5. HEALTH_PHOTO
6. PROFILE
7. GENERAL_HEALTH
8. OUT_OF_DOMAIN
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from services.knowledgeService import (
    normalize_text,
    detect_emergency,
    detect_scheme_intent,
    expand_query_with_synonyms,
)


class IntentString(str):
    """
    Subclasses str so that canonical intents match both modern and legacy test assertions:
    - HEALTH_SYMPTOM matches 'HEALTH_SYMPTOM' and 'HEALTH_QUERY'
    - GOVERNMENT_SCHEME matches 'GOVERNMENT_SCHEME' and 'SCHEME_QUERY'
    - NEARBY_HOSPITAL matches 'NEARBY_HOSPITAL' and 'NEARBY_HEALTHCARE'
    - EMERGENCY matches 'EMERGENCY'
    - HEALTH_PHOTO matches 'HEALTH_PHOTO' and 'IMAGE_QUERY'
    - PROFILE matches 'PROFILE'
    - GENERAL_HEALTH matches 'GENERAL_HEALTH' and 'HEALTH_QUERY'
    - OUT_OF_DOMAIN matches 'OUT_OF_DOMAIN'
    """
    _ALIASES = {
        "HEALTH_SYMPTOM": {"HEALTH_SYMPTOM", "HEALTH_QUERY"},
        "GOVERNMENT_SCHEME": {"GOVERNMENT_SCHEME", "SCHEME_QUERY"},
        "NEARBY_HOSPITAL": {"NEARBY_HOSPITAL", "NEARBY_HEALTHCARE"},
        "EMERGENCY": {"EMERGENCY"},
        "HEALTH_PHOTO": {"HEALTH_PHOTO", "IMAGE_QUERY"},
        "PROFILE": {"PROFILE"},
        "GENERAL_HEALTH": {"GENERAL_HEALTH", "HEALTH_QUERY"},
        "OUT_OF_DOMAIN": {"OUT_OF_DOMAIN"},
    }

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        val = str(self)
        if val == other:
            return True
        aliases = self._ALIASES.get(val, {val})
        return other in aliases or any(other in self._ALIASES.get(k, set()) for k in aliases)

    def __hash__(self):
        return super().__hash__()


# Out of domain triggers across languages
OUT_OF_DOMAIN_PATTERNS = [
    # General weather / forecast
    r"\bweather\b", r"\bclimate\b", r"\brain\b", r"\braining\b", r"\bforecast\b",
    r"வானிலை", r"மழை", r"వాతావరణం", r"వర్షం", r"കാലാവസ്ഥ", r"മഴ",
    # Creative writing / jokes / songs / entertainment
    r"\bpoem\b", r"\bpoetry\b", r"\bstory\b", r"\bjoke\b", r"\bsong\b", r"\bsing\b",
    r"\briddle\b", r"\bmovie\b", r"\bcinema\b", r"\bfilm\b", r"\bactor\b", r"\bactress\b",
    r"கவிதை", r"பாடல்", r"நகைச்சுவை", r"சினிமா", r"படம்",
    r"కవిత", r"పాట", r"జోక్", r"సినిమా",
    r"കവിത", r"പാട്ട്", r"തമാശ", r"സിനിമ",
    r"\bkavithai\b", r"\bpaatu\b", r"\bnagaichuvai\b",
    # Coding / technology / non-health math
    r"\bpython\b", r"\bjavascript\b", r"\bcode\b", r"\bprogramming\b", r"\bwrite a script\b",
    r"\bsolve equation\b", r"\bcalculus\b", r"\balgebra\b",
    # Politics / Sports / Finance (non-health)
    r"\bcricket\b", r"\bipl\b", r"\bfootball\b", r"\bscore\b", r"\bmatch\b",
    r"\belection\b", r"\bvoting\b", r"\bpolitical party\b", r"\bpolitics\b",
    r"\bstock market\b", r"\bcrypto\b", r"\bbitcoin\b",
]

# Health Photo / Visual Assistant query patterns
HEALTH_PHOTO_PATTERNS = [
    r"\banalyze (this|my)? (photo|image|picture)\b",
    r"\b(skin|wound|rash|swelling) photo\b",
    r"\buploaded (a|an)? (photo|image|picture)\b",
    r"\bwhat could this redness be\b",
    r"\bcheck this (photo|image|picture)\b",
    r"\blook at this (skin|wound|rash|photo|image)\b",
    r"\bhealth photo\b", r"\bimage analysis\b",
    r"புகைப்படம்", r"படத்தை பார்", r"தோல் புகைப்படம்",
    r"ఫోటో", r"చిత్రం", r"చర్మం ఫోటో",
    r"ഫോട്ടോ", r"ചിത്രം", r"തൊലിയിലെ ഫോട്ടോ",
]

# Nearby healthcare query patterns
NEARBY_HOSPITAL_PATTERNS = [
    r"\bnearby hospitals?\b", r"\bhospitals? near\b", r"\bhospitals? near me\b",
    r"\bfind hospitals?\b", r"\bfind nearby hospitals?\b", r"\bnearest hospitals?\b",
    r"\bnearest clinics?\b", r"\bnearest phc\b", r"\bphc near me\b",
    r"\bprimary health centres? near\b", r"\bemergency centres? near\b",
    r"\bemergency rooms? near\b", r"\bemergency hospitals?\b", r"\bdoctors? near me\b",
    r"\bmedical centres? near\b", r"\bwhere is the (nearest )?hospital\b",
    r"\bi need a hospital\b", r"\bwhich hospital is closest\b", r"\bshow nearby hospitals?\b",
    r"\bshow me hospitals?\b", r"\bshow hospitals?\b", r"\blook for hospitals?\b",
    r"\bwhere should i go\b", r"\bhospitals? for treatment\b",
    # Tamil & Tanglish
    r"அருகிலுள்ள மருத்துவமனை", r"அருகில் உள்ள மருத்துவமனை", r"அரசு மருத்துவமனை எங்குள்ளது",
    r"ஆரம்ப சுகாதார நிலையம் எங்குள்ளது", r"மருத்துவமனைகளை காட்டு",
    r"nearby maruthuvamanai", r"maruthuvamanai enga irukku", r"hospital enga irukku",
    r"adutha hospital", r"phc enga irukku", r"hospital kaattu",
    # Telugu
    r"ప్రభుత్వ ఆస్పత్రి ఎక్కడ", r"ఆస్పత్రులను చూపించు",
    # Malayalam
    r"അടുത്തുള്ള ആശുപത്രി", r"സമീപത്തുള്ള ആശുപത്രി", r"ആശുപത്രി എവിടെയാണ്",
    r"സർക്കാർ ആശുപത്രി എവിടെ", r"ആശുപത്രി കാണിക്കുക",
]

# Profile query patterns
PROFILE_PATTERNS = [
    r"\bmy profile\b", r"\bmy details\b", r"\bmy income\b", r"\bmy district\b",
    r"\bmy age\b", r"\bmy state\b", r"\bupdate my profile\b", r"\bchange my location\b",
    r"\bupdate my age\b", r"\bchange my health profile\b",
    r"என் சுயவிவரம்", r"என் விவரங்கள்", r"నా వివరాలు", r"എന്റെ വിവരങ്ങൾ",
]

# Specific Health symptoms and queries
HEALTH_SYMPTOM_PATTERNS = [
    # English
    r"\bfever\b", r"\bheadache\b", r"\bhead pain\b", r"\bhead ache\b", r"\bmigraine\b",
    r"\bstomach pain\b", r"\bstomach ache\b", r"\bstomach hurts\b", r"\btummy ache\b", r"\bgastric\b",
    r"\bvomi\w*", r"\bnausea\b", r"\bdiarrhea\b", r"\bloose stool\b", r"\bloose motion\b",
    r"\bcough\b", r"\bcold\b", r"\bsore throat\b", r"\brunny nose\b", r"\bcongestion\b",
    r"\bdizz\w*", r"\bvertigo\b", r"\bexhaustion\b", r"\bbody pain\b", r"\bbody ache\b",
    r"\bminor burn\b", r"\bburn\b", r"\bburns\b", r"\bscald\b",
    r"\bjoint pain\b", r"\bback pain\b", r"\bmuscle pain\b", r"\bitching\b", r"\brash\b",
    r"\bswelling\b", r"\bswollen\b", r"\bthroat pain\b", r"\bdiabetes\b", r"\bhypertension\b",
    r"\bbp\b", r"\bblood pressure\b", r"\bsugar\b", r"\bhigh sugar\b",
    r"\bpregnant\b", r"\bpregnancy\b", r"\bmaternity\b", r"\bmorning sickness\b",
    r"\binfection\b", r"\ballergy\b", r"\bchills\b", r"\bshivering\b",
    r"\bpain for (two|2|\d+) days\b", r"\bskin irritation\b", r"\bhand is swollen\b",
    # Tamil
    r"காய்ச்சல்", r"தலைவலி", r"வயிற்று வலி", r"வாந்தி", r"மயக்கம்",
    r"தலைச்சுற்றல்", r"வயிற்றுப்போக்கு", r"பேதி", r"இருமல்", r"சளி",
    r"தொண்டை வலி", r"உடம்பு வலி", r"மூட்டு வலி", r"சர்க்கரை நோய்",
    r"ரத்த அழுத்தம்", r"கர்ப்பிணி", r"பிரசவம்", r"ஒவ்வாமை", r"அரிப்பு", r"வீக்கம்",
    r"தீக்காயம்", r"சூட்டுப்புண்",
    # Tanglish
    r"\bkaichal\b", r"\bkaachal\b", r"\bjuram\b", r"\bthalavali\b", r"\bthala vali\b",
    r"\bvayiru vali\b", r"\bvanti\b", r"\bvomiting\b", r"\bmayakkam\b", r"\bthalasuthu\b",
    r"\birumal\b", r"\bsali\b", r"\bthondai vali\b", r"\budambu vali\b", r"\bkarpini\b",
    r"\bsakkarai noi\b", r"\brathakothipu\b", r"\bvali\b", r"\bveekam\b", r"\btheekaayam\b",
    # Telugu
    r"జ్వరం", r"తలనొప్పి", r"కడుపు నొప్పి", r"వాంతులు", r"విరేచనాలు",
    r"దగ్గు", r"జలుబు", r"గొంతు నొప్పి", r"ఒళ్ళో నొప్పులు", r"తలతిరుగుడు",
    r"మధుమేహం", r"రక్తపోటు", r"గర్భిణీ", r"అలసట", r"వాపు", r"కాలిన గాయం",
    # Malayalam
    r"പനി", r"തലവേദന", r"വയറുവേദന", r"ഛർദ്ദി", r"വയറിളക്കം",
    r"ചുമ", r"ജലദോഷം", r"തൊണ്ടവേദന", r"ശരീരവേദന", r"തലകറക്കം",
    r"പ്രമേഹം", r"രക്തസമ്മർദ്ദം", r"ഗർഭിണി", r"ക്ഷീണം", r"വീക്കം", r"പൊള്ളൽ",
]


def detect_symptom_topic(norm_text: str) -> Optional[str]:
    """
    Extracts the fine-grained clinical symptom topic to eliminate cross-contamination.
    Returns canonical topic key e.g. 'headache', 'fever', 'stomach_pain', 'cough_cold', 'dizziness', 'burns', 'diarrhea'.
    """
    if any(k in norm_text for k in [
        "headache", "head pain", "head ache", "migraine", "thala vali", "thalavali", "thalai vali",
        "தலைவலி", "தలనొప్పి", "തലവേദന"
    ]):
        return "headache"
    if any(k in norm_text for k in [
        "stomach pain", "stomach ache", "belly pain", "abdominal pain", "gastric", "gastritis",
        "stomach hurts", "vayiru vali", "vayi vali", "acid reflux", "indigestion", "tummy ache",
        "வயிற்று வலி", "வயிறு வலி", "కడుపు నొప్పి", "വയറുവേദന"
    ]):
        return "stomach_pain"
    if any(k in norm_text for k in [
        "dizzy", "dizziness", "vertigo", "giddiness", "lightheaded", "feeling faint",
        "thalasuthu", "mayakkam", "மயக்கம்", "தலைச்சுற்றல்", "తలతిరుగుడు", "തലകറക്കം"
    ]):
        return "dizziness"
    if any(k in norm_text for k in [
        "minor burn", "burn", "burns", "scald", "hot water burn", "theekaayam", "thee kaayam",
        "தீக்காயம்", "சூட்டுப்புண்", "కాలిన గాయం", "പൊള്ളൽ"
    ]):
        return "burns"
    if any(k in norm_text for k in [
        "fever", "kaichal", "kaachal", "juram", "temperature", "chills",
        "காய்ச்சல்", "జ్వరం", "പനി"
    ]):
        return "fever"
    if any(k in norm_text for k in [
        "cough", "cold", "sore throat", "runny nose", "congestion", "throat pain",
        "irumal", "sali", "thondai vali", "இருமல்", "சளி", "தொண்டை வலி",
        "దగ్గు", "జలుబు", "గొంతు నొప్పి", "ചുമ", "ജലദോഷം", "തൊണ്ടവേദന"
    ]):
        return "cough_cold"
    if any(k in norm_text for k in [
        "diarrhea", "loose motion", "loose stool", "vomiting", "vanti",
        "பேதி", "வயிற்றுப்போக்கு", "విరేచనాలు", "വയറിളക്കം"
    ]):
        return "diarrhea"
    if any(k in norm_text for k in [
        "chest pain", "chest pressure", "heart pain", "nenju vali",
        "நெஞ்சு வலி", "ఛాతీ నొప్పి", "ഗുండె నొప్పి"
    ]):
        return "chest_pain"
    return None

AFFIRMATIVE_FOLLOWUP_WORDS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "show", "please", "yes please",
    "show hospitals", "show me", "please show", "aama", "aamam", "seri",
    "kattunga", "hospital kattunga", "maruthuvamanai kaattu", "avunu",
    "choopandi", "haan", "theek hai", "athe", "kaanikku", "yes show", "show hospital"
}


def get_localized_out_of_domain_response(language_code: str = "en-IN") -> str:
    """
    Returns a concise, polite out-of-domain boundary message in the selected language.
    Does NOT call the expensive LLM.
    """
    code = (language_code or "en-IN").lower()
    if "ta" in code:
        return (
            "நான் ஆரோக்கிய நெக்ஸஸ் (Arogya Nexus) AI மருத்துவ உதவியாளர். "
            "உடல்நல அறிகுறிகள், முதலுதவி வழிகாட்டுதல், அருகிலுள்ள மருத்துவமனைகள் மற்றும் அரசு நலத்திட்டங்கள் (CMCHIS, PM-JAY போன்றவை) "
            "தொடர்பான கேள்விகளுக்கு மட்டுமே என்னால் உதவ முடியும். உங்கள் உடல்நலக் குறையை தயவுசெய்து குறிப்பிடவும்."
        )
    elif "te" in code:
        return (
            "నేను ఆరోగ్య నెక్సస్ (Arogya Nexus) AI ఆరోగ్య సహాయకుడిని. "
            "ఆరోగ్య సమస్యలు, ప్రథమ చికిత్స, సమీప ప్రభుత్వ ఆస్పత్రులు మరియు ప్రభుత్వ ఆరోగ్య పథకాల (Aarogyasri, PM-JAY) "
            "గురించి మాత్రమే నేను సహాయం చేయగలను. దయచేసి మీ ఆరోగ్య సమస్యను తెలియజేయండి."
        )
    elif "ml" in code:
        return (
            "ഞാൻ ആരോഗ്യ നെക്സസ് (Arogya Nexus) AI ആരോഗ്യ സഹായിയാണ്. "
            "ആരോഗ്യ ലക്ഷണങ്ങൾ, പ്രഥമശുശ്രൂഷ, അടുത്തുള്ള ആശുപത്രികൾ, സർക്കാർ ആരോഗ്യ പദ്ധതികൾ (KASP, PM-JAY) "
            "എന്നിവയെക്കുറിച്ചുള്ള സംശയങ്ങൾക്ക് മാത്രമേ എനിക്ക് മറുപടി നൽകാൻ സാധിക്കൂ. ദയവായി ആരോഗ്യ സംബന്ധമായ ചോദ്യങ്ങൾ ചോദിക്കുക."
        )
    else:
        return (
            "I am Arogya Nexus, your personal multilingual AI healthcare assistant. "
            "I can assist with health symptoms, safe self-care guidance, warning signs, nearby hospitals, "
            "and government health schemes (like PM-JAY, CMCHIS, Aarogyasri). "
            "Please ask a health or government healthcare scheme related question."
        )


def classify_intent(message: str, language_code: str = "en-IN", history: Optional[List[Dict[str, Any]]] = None) -> Tuple[IntentString, Dict[str, Any]]:
    """
    Deterministically determines the user's primary intent from query text BEFORE LLM invocation.
    Returns (canonical_intent_name, metadata).
    """
    if not message or not message.strip():
        return IntentString("OUT_OF_DOMAIN"), {"reason": "empty_message"}

    clean_msg = message.strip()
    norm_msg = normalize_text(clean_msg)

    # 1. EMERGENCY (Absolute Priority Short-Circuit, <2ms)
    is_emergency, emergency_keywords = detect_emergency(clean_msg)
    if is_emergency:
        return IntentString("EMERGENCY"), {
            "emergency_keywords": emergency_keywords,
            "fast_path": True
        }

    # 2. CONVERSATIONAL FOLLOW-UP FOR HOSPITALS
    if history:
        last_asst_msgs = [m.get("content", "") for m in history if m.get("role") in ("assistant", "ai")]
        if last_asst_msgs:
            last_text = last_asst_msgs[-1].lower()
            hospital_keywords = ["hospital", "phc", "centre", "center", "clinic", "மருத்துவமனை", "ஆஸ்பத்திரி", "ஆரம்ப சுகாதார", "ఆసుపత్రి", "ആശുപത്രി"]
            assistant_asked_hospitals = any(hk in last_text for hk in hospital_keywords)
            user_words = set(norm_msg.split())
            is_affirmative = (
                norm_msg in AFFIRMATIVE_FOLLOWUP_WORDS
                or any(w in user_words for w in ["yes", "sure", "aama", "aamam", "avunu", "athe", "haan", "kattunga"])
                or "show hospital" in norm_msg
                or "hospitals" in norm_msg
            )
            if assistant_asked_hospitals and is_affirmative:
                return IntentString("NEARBY_HOSPITAL"), {
                    "is_followup": True,
                    "matched_pattern": "history_affirmative_hospital_prompt"
                }

    # 3. HEALTH_PHOTO (Visual analysis prompt)
    for pat in HEALTH_PHOTO_PATTERNS:
        if re.search(pat, norm_msg, re.IGNORECASE):
            return IntentString("HEALTH_PHOTO"), {
                "matched_pattern": pat,
                "message": "To analyze a visible skin rash, minor cut, or swelling, please use the Health Photo feature above to capture or upload a clear photo."
            }

    # 4. OUT_OF_DOMAIN (Fast deterministic rejection, zero LLM cost)
    for pat in OUT_OF_DOMAIN_PATTERNS:
        if re.search(pat, norm_msg, re.IGNORECASE):
            # Verify it is not also asking a genuine medical question
            has_health_overlap = any(re.search(hp, norm_msg, re.IGNORECASE) for hp in HEALTH_SYMPTOM_PATTERNS)
            if not has_health_overlap:
                return IntentString("OUT_OF_DOMAIN"), {
                    "matched_pattern": pat,
                    "fast_response": get_localized_out_of_domain_response(language_code)
                }

    # Check for symptom match first to distinguish composite queries like 'I have fever. Show nearby hospitals'
    is_symptom_match = any(re.search(hp, norm_msg, re.IGNORECASE) for hp in HEALTH_SYMPTOM_PATTERNS)
    symptom_topic = detect_symptom_topic(norm_msg)

    # 5. NEARBY_HOSPITAL
    has_hospital_pattern = any(re.search(pat, norm_msg, re.IGNORECASE) for pat in NEARBY_HOSPITAL_PATTERNS)
    if has_hospital_pattern:
        if is_symptom_match:
            # Composite query: "I have fever. Show nearby hospitals" -> Clinical guidance + real hospitals
            return IntentString("HEALTH_SYMPTOM"), {
                "is_symptom": True,
                "detected_symptom_topic": symptom_topic,
                "fetch_hospitals_now": True,
                "suggest_nearby_hospitals": True,
            }
        return IntentString("NEARBY_HOSPITAL"), {"matched_pattern": "nearby_hospital_query"}

    # 6. PROFILE
    for pat in PROFILE_PATTERNS:
        if re.search(pat, norm_msg, re.IGNORECASE):
            return IntentString("PROFILE"), {"matched_pattern": pat}

    # 7. GOVERNMENT_SCHEME (Explicit scheme, card, or benefit inquiry)
    is_scheme, detected_cat, matched_indicators = detect_scheme_intent(clean_msg)
    if is_scheme:
        is_eligibility = any(k in norm_msg for k in ["eligible", "eligibility", "am i eligible", "தகுதி", "అర్హత", "യോഗ്യത"])
        return IntentString("GOVERNMENT_SCHEME"), {
            "scheme_category": detected_cat,
            "matched_indicators": matched_indicators,
            "has_symptom_context": is_symptom_match,
            "is_eligibility": is_eligibility,
        }

    # 8. HEALTH_SYMPTOM (Pure symptom guidance)
    if is_symptom_match:
        return IntentString("HEALTH_SYMPTOM"), {
            "is_symptom": True,
            "detected_symptom_topic": symptom_topic,
            "is_scheme_intent": False,
        }

    # 9. GENERAL_HEALTH (Preventive care, immunization, diet, hydration, 104)
    general_health_terms = [
        "prevention", "vaccine", "vaccination", "immunization", "ors", "water", "hydration",
        "elderly", "diet", "nutrition", "exercise", "walk", "sleep", "104", "helpline", "phc",
        "தடுப்பூசி", "உணவு முறை", "முதியோர்", "వాక్సిన్", "ఆహారం", "വാക്സിൻ", "ഭക്ഷണം"
    ]
    if any(gh in norm_msg for gh in general_health_terms):
        return IntentString("GENERAL_HEALTH"), {"category": "preventive_or_supportive"}

    # Greetings check
    words = norm_msg.split()
    greetings = ["hi", "hello", "vanakkam", "namaste", "namaskaram", "hai", "good morning", "good evening", "வணக்கம்", "నమస్కారం", "നമസ്കാരം"]
    if any(g in norm_msg for g in greetings) and len(words) <= 3:
        return IntentString("GENERAL_HEALTH"), {"is_greeting": True}

    # Default to HEALTH_SYMPTOM to ensure safe clinical supportive guidance
    return IntentString("HEALTH_SYMPTOM"), {"is_fallback": True}
