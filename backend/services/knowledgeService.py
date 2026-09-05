import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path to the knowledge base directory
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"

# Emergency trigger keywords in English, Tamil, Tanglish, Telugu, and Malayalam
EMERGENCY_TRIGGERS = [
    # English
    "chest pain", "heart attack", "difficulty breathing", "cannot breathe", "stopped breathing",
    "shortness of breath", "stroke", "unconscious", "fainted", "fainting", "collapsed", "convulsion",
    "seizure", "snakebite", "snake bite", "poison", "poisoning", "severe bleeding", "heavy bleeding",
    "paralysis", "stiff neck", "blue lips", "cardiac arrest", "severe allergic reaction", "anaphylaxis",
    "suicide", "self-harm", "severe head injury", "accident on highway",
    # Tamil
    "நெஞ்சு வலி", "மாரடைப்பு", "மூச்சுத்திணறல்", "சுயநினைவின்மை", "வலிப்பு",
    "பாம்புக்கடி", "விஷக்கடி", "விஷம்", "பக்கவாதம்", "கழுத்து விறைப்பு", "தீவிர ரத்தப்போக்கு", "அதிக ரத்தப்போக்கு",
    # Tanglish
    "nenju vali", "maradaipu", "moochu thinaral", "paambu kadi", "visha kadi", "valippu",
    "breathless", "chest tightness", "heart attack", "heavy bleeding", "ratha pokku",
    # Telugu
    "గుండె నొప్పి", "గుండెపోటు", "తీవ్ర శ్వాస సమస్య", "శ్వాస ఆడకపోవడం", "అపస్మారక స్థితి",
    "మూర్ఛ", "పాము కాటు", "విషం", "తీవ్ర రక్తస్రావం", "పక్షవాతం", "ఛాతీ నొప్పి",
    # Malayalam
    "നെഞ്ചുവേദന", "ഹൃദയാഘാതം", "കടുത്ത ശ്വാസതടസ്സം", "ശ്വാസമെടുക്കാൻ ബുദ്ധിമുട്ട്",
    "അബോധാവസ്ഥ", "ഫിറ്റ്സ്", "പാമ്പുകടി", "വിഷബാധ", "കടുത്ത രക്തസ്രാവം", "പക്ഷാഘാതം"
]

# Government scheme intent indicators in English, Tamil, Tanglish, Telugu, and Malayalam
SCHEME_INTENT_INDICATORS = [
    # English
    "scheme", "government scheme", "health scheme", "insurance", "health insurance",
    "eligibility", "eligible", "am i eligible", "how to apply", "where to apply",
    "documents required", "required documents", "benefit", "benefits",
    "pmjay", "pm-jay", "ayushman", "cmchis", "mrmbs", "muthulakshmi", "pmmvy",
    "makkalai thedi", "mtm", "rbsk", "nphce", "nammai kaakkum", "innuyir kaappom",
    "aarogyasri", "aarogya asara", "thalli bidda", "kasp", "medisep", "thalolam", "janani janmaraksha",
    # Tamil
    "திட்டம்", "திட்டங்கள்", "திட்ட", "அரசு திட்டம்", "அரசு திட்டங்கள்",
    "மருத்துவ காப்பீடு", "மருத்துவ காப்பீட்டு", "காப்பீடு", "காப்பீட்டு", "காப்பீட்டு திட்டம்",
    "தகுதி", "தகுதியுடைய", "விண்ணப்பிப்பது எப்படி", "எங்கு விண்ணப்பிப்பது",
    "தேவையான ஆவணங்கள்", "ஆவணங்கள்", "பலன்கள்", "முதலமைச்சர் காப்பீடு",
    "ஆயுஷ்மான்", "முத்துலட்சுமி ரெட்டி", "மாத்ரு வந்தனா",
    "மக்களைத் தேடி மருத்துவம்", "மக்களை தேடி மருத்துவம்", "நம்மைக் காக்கும் 48",
    # Tanglish
    "scheme", "schemes", "thittam", "thittangal", "kaapeedu", "maruthuva kaapeedu", "insurance", "health card",
    "kedaikuma", "eligibility enna", "eligible ah", "apply epdi", "epdi apply panrathu",
    "enga apply panrathu", "documents enna", "enna documents venum", "benefits enna",
    "cmchis", "pmjay", "ayushman card", "muthulakshmi reddy", "pmmvy", "mtm scheme",
    "prasava kaasu", "18000 scheme", "5 lakh card", "accident scheme",
    # Telugu
    "పథకం", "ప్రభుత్వ పథకం", "ఆరోగ్య బీమా", "ఆరోగ్యశ్రీ", "ఆసరా", "తల్లి బిడ్డ ఎక్స్‌ప్రెస్",
    "అర్హత", "దరఖాస్తు", "ప్రయోజనాలు", "కావలసిన పత్రాలు", "ఆయుష్మాన్ భారత్", "ఎలా దరఖాస్తు చేయాలి",
    # Malayalam
    "പദ്ധതി", "സർക്കാർ പദ്ധതി", "ആരോഗ്യ ഇൻഷുറൻസ്", "കാരുണ്യ", "കാസ്പ്", "മെഡിസെപ്",
    "താലോലം", "ജനനി ജന്മരക്ഷ", "യോഗ്യത", "അപേക്ഷിക്കേണ്ട വിധം", "ആനുകൂല്യങ്ങൾ", "ആയുഷ്മാൻ ഭാരത്"
]

_CACHED_KNOWLEDGE_BASE: Optional[List[Dict[str, Any]]] = None


def load_all_knowledge_cards() -> List[Dict[str, Any]]:
    """
    Loads all verified knowledge cards from JSON files in the knowledge_base directory.
    """
    global _CACHED_KNOWLEDGE_BASE
    if _CACHED_KNOWLEDGE_BASE is not None:
        return _CACHED_KNOWLEDGE_BASE

    cards: List[Dict[str, Any]] = []
    if not KNOWLEDGE_BASE_DIR.exists():
        return cards

    for json_file in KNOWLEDGE_BASE_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cards.extend(data)
        except Exception as e:
            print(f"[WARN] Error loading knowledge file {json_file.name}: {e}")

    _CACHED_KNOWLEDGE_BASE = cards
    return cards


def reload_knowledge_base() -> Dict[str, Any]:
    """
    Forces a cache reset and reloads knowledge cards from disk.
    Used for safe runtime refresh (e.g. n8n automation webhook).
    """
    global _CACHED_KNOWLEDGE_BASE
    _CACHED_KNOWLEDGE_BASE = None
    cards = load_all_knowledge_cards()

    scheme_count = sum(1 for c in cards if c.get("category") in ("government_scheme", "health_schemes"))
    healthcare_count = len(cards) - scheme_count

    return {
        "status": "success",
        "total_cards": len(cards),
        "scheme_cards_count": scheme_count,
        "healthcare_cards_count": healthcare_count
    }


def normalize_text(text: str) -> str:
    """
    Normalizes input text for case-insensitive and punctuation-agnostic matching
    while preserving Tamil (0B80-0BFF), Telugu (0C00-0C7F), and Malayalam (0D00-0D7F) unicode characters.
    """
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = re.sub(r"[^\w\s\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F]", " ", cleaned)
    return " ".join(cleaned.split())


def detect_emergency(text: str) -> Tuple[bool, List[str]]:
    """
    Checks if the user query contains genuine emergency red flag triggers across English, Tamil, Tanglish, Telugu, and Malayalam.
    Considers the COMPLETE user message, not isolated keywords.
    Avoids false positives for mild headache, fever, minor body pain, or negated triggers.
    Returns (is_emergency, detected_keywords).
    """
    if not text or not text.strip():
        return (False, [])

    norm_text = normalize_text(text)

    # Check for common negation phrases in English, Tamil, etc.
    negation_patterns = [
        r"\bno chest pain\b", r"\bwithout chest pain\b", r"\bnot having chest pain\b",
        r"\bno breathing difficulty\b", r"\bno bleeding\b",
        r"நெஞ்சு வலி இல்லை", r"வலி இல்லை", r"నొప్పి లేదు"
    ]
    is_negated = any(re.search(pat, norm_text) for pat in negation_patterns)

    # Mild/common symptoms alone are NOT emergencies
    mild_patterns = [
        r"\bmild headache\b", r"\bheadache for (two|2|\d+) days\b", r"\bhead pain for (two|2|\d+) days\b",
        r"\bmild fever\b", r"\bfever for (two|2|\d+) days\b", r"\bmild stomach pain\b", r"\bmild cough\b"
    ]
    is_explicitly_mild = any(re.search(pat, norm_text) for pat in mild_patterns)

    detected: List[str] = []
    for trigger in EMERGENCY_TRIGGERS:
        norm_trigger = normalize_text(trigger)
        if not norm_trigger:
            continue
        
        # For English, enforce strict whole word boundaries.
        # For Indic scripts (Tamil \u0B80-\u0BFF, Telugu \u0C00-\u0C7F, Malayalam \u0D00-\u0D7F),
        # words take agglutinative suffixes (e.g. -വും, -உம், -తో), so substring containment is required.
        is_indic = any("\u0B80" <= c <= "\u0D7F" for c in norm_trigger)
        if is_indic:
            matched = norm_trigger in norm_text
        else:
            pattern = rf"(?<!\w){re.escape(norm_trigger)}(?!\w)"
            matched = bool(re.search(pattern, norm_text))

        if matched:
            # If negated or explicitly mild non-emergency query, ignore this trigger
            if is_negated and any(k in norm_trigger for k in ["chest", "breath", "bleeding", "vali", "నొప్పి", "വേദന"]):
                continue
            if is_explicitly_mild and any(k in norm_trigger for k in ["chest pain", "head injury", "convulsion"]):
                continue
            detected.append(trigger)

    return (len(detected) > 0, detected)


def detect_scheme_intent(text: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Detects if the user query is asking about government schemes, eligibility, documents, or benefits.
    Returns (is_scheme_intent, detected_category, matched_indicators).
    """
    norm_text = normalize_text(text)
    matched_indicators: List[str] = []

    for indicator in SCHEME_INTENT_INDICATORS:
        norm_ind = normalize_text(indicator)
        if norm_ind and (norm_ind in norm_text or norm_text in norm_ind):
            matched_indicators.append(indicator)

    # Category inference
    detected_cat = None
    if any(k in norm_text for k in [
        "insurance", "kaapeedu", "cmchis", "pmjay", "ayushman", "5 lakh", "25 lakh",
        "aarogyasri", "kasp", "medisep", "బీమా", "ఇన్సూరెన్స్", "ഇൻഷുറൻസ്"
    ]):
        detected_cat = "health_insurance"
    elif any(k in norm_text for k in [
        "maternal", "pregnancy", "karpini", "prasavam", "delivery", "muthulakshmi",
        "pmmvy", "jsy", "18000", "thalli bidda", "janani janmaraksha", "గర్భిణీ", "പ്രസവം"
    ]):
        detected_cat = "maternal_pregnancy"
    elif any(k in norm_text for k in [
        "child", "kulanthai", "rbsk", "newborn", "deic", "school", "palli",
        "thalolam", "పిల్లలు", "കുട്ടികൾ"
    ]):
        detected_cat = "child_health"
    elif any(k in norm_text for k in [
        "elderly", "muthiyor", "senior", "bp", "sugar", "diabetes", "makkalai thedi",
        "mtm", "nphce", "doorstep", "aarogya asara", "వృద్ధులు", "മുതിർന്ന"
    ]):
        detected_cat = "elderly_chronic"
    elif any(k in norm_text for k in [
        "accident", "vibhathu", "trauma", "48 hours", "nammai kaakkum", "innuyir",
        "ప్రమాదం", "അപകടം"
    ]):
        detected_cat = "emergency_services"

    is_intent = len(matched_indicators) > 0
    return is_intent, detected_cat, matched_indicators


# Common Tanglish, Tamil, Telugu, and Malayalam synonym mappings for robust fuzzy retrieval
SYNONYM_MAP = {
    # Symptoms: Fever
    "kaachal": ["kaichal", "juram", "fever", "காய்ச்சல்", "kaychal", "జ్వరం", "പനി"],
    "kaichal": ["kaachal", "juram", "fever", "காய்ச்சல்", "kaychal", "జ్వరం", "പനി"],
    "juram": ["kaichal", "kaachal", "fever", "காய்ச்சல்", "జ్వరం", "പനി"],
    "fever": ["kaichal", "kaachal", "juram", "காய்ச்சல்", "జ్వరం", "പനി", "high temperature"],

    # Symptoms: Headache / Head Pain
    "thalavali": ["thala vali", "thalai vali", "headache", "head pain", "தலைவலி", "తలనొప్పి", "തലവേദന"],
    "thala": ["thalai", "head", "headache", "head pain", "தலைவலி", "తలనొప్పి", "തല"],
    "head": ["headache", "head pain", "thala", "தலைவலி", "తలనొప్పి", "തല"],
    "headache": ["head pain", "thala vali", "thalavali", "migraine", "தலைவலி", "తలనొప్పి", "തലവേദന"],
    "migraine": ["headache", "head pain", "othai thalavali", "ஒற்றைத் தலைவலி", "తలనొప్పి"],
    
    # Generic Pain
    "vali": ["pain", "வலி", "ache", "నొప్పి", "வேദന"],

    # Symptoms: Stomach / Gastric
    "vayiru": ["vayi", "stomach", "வயிறு", "stomach pain", "vayiru vali", "gastric", "కడుపు", "വയർ"],
    "vayi": ["vayiru", "stomach", "வயிறு", "vayiru vali"],
    "stomach": ["stomach pain", "stomach ache", "vayiru", "gastric", "gastritis", "abdomen", "కడుపు", "വയർ"],
    "gastric": ["stomach pain", "vayiru vali", "gastritis", "acidity", "indigestion"],
    "belly": ["stomach", "vayiru", "stomach pain"],
    "abdomen": ["stomach", "abdominal pain", "vayiru"],

    # Symptoms: Dizziness / Vertigo
    "dizzy": ["dizziness", "vertigo", "lightheaded", "thalasuthu", "mayakkam", "తలతిరుగుడు", "തലകറക്കം"],
    "dizziness": ["dizzy", "vertigo", "lightheaded", "thalasuthu", "mayakkam", "తలతిరుగుడు", "തലകറക്കം"],
    "mayakkam": ["dizzy", "dizziness", "vertigo", "thalasuthu", "மயக்கம்"],
    "thalasuthu": ["dizzy", "dizziness", "vertigo", "mayakkam", "தலைச்சுற்றல்"],
    "vertigo": ["dizzy", "dizziness", "thalasuthu", "தலைச்சுற்றல்"],

    # Symptoms: Burns / Scalds
    "burn": ["minor burn", "scald", "theekaayam", "தீக்காயம்", "காலిన గాయం", "പൊള്ളൽ"],
    "burns": ["minor burn", "scald", "theekaayam", "தீக்காயம்", "కాలిన గాయం", "പൊള്ളൽ"],
    "theekaayam": ["burn", "minor burn", "scald", "தீக்காயம்"],

    # Symptoms: Cough & Cold
    "cough": ["irumal", "sali", "cold", "இருமல்", "దగ్గు", "ചുമ"],
    "cold": ["sali", "cough", "runny nose", "சளி", "జలుబు", "ജലദോഷം"],
    "irumal": ["cough", "இருமல்"],
    "sali": ["cold", "cough", "runny nose", "சளி"],

    # Symptoms: Cardiac / Chest
    "nenju": ["chest", "நெஞ்சு", "heart", "nenju vali", "chest pain", "ఛాతీ", "గుండె", "നെഞ്ച്"],
    "chest": ["nenju", "heart", "cardiac", "nenju vali", "chest pain", "நெஞ்சு", "గుండె", "നെഞ്ച്"],
    "moochu": ["breath", "breathing", "மூச்சு", "moochu thinaral", "శ్వాస", "ശ്വാസം"],
    "thinaral": ["difficulty", "breathless", "திணறல்", "ఆయాసం", "തടസ്സം"],

    # Chronic
    "sugar": ["diabetes", "sakkarai", "சர்க்கரை", "sugar noi", "మధుమేహం", "പ്രമേഹം"],
    "sakkarai": ["sugar", "diabetes", "சர்க்கரை", "మధుమేహం"],
    "bp": ["blood pressure", "rathakothipu", "ரத்த அழுத்தம்", "రక్తపోటు", "രക്തസമ്മർദ്ദം"],
    "rathakothipu": ["bp", "blood pressure", "ரத்த அழுத்தம்"],
    "karpini": ["pregnant", "pregnancy", "கர்ப்பிணி", "maternity", "thaai", "గర్భిణీ", "ഗർഭിണി"],
    "maruthuvamanai": ["hospital", "phc", "மருத்துவமனை", "clinic", "ఆసుపత్రి", "ആശുപത്രി"],
    
    # Scheme Synonyms
    "thittam": ["scheme", "திட்டம்", "yojana", "పథకం", "പദ്ധതി"],
    "scheme": ["thittam", "திட்டம்", "yojana", "పథకం", "പദ്ധതി"],
    "kaapeedu": ["insurance", "காப்பீடு", "bima", "health card", "బీమా", "ഇൻഷുറൻസ്"],
    "insurance": ["kaapeedu", "காப்பீடு", "bima", "health card", "బీమా", "ഇൻഷുറൻസ്"],
    "kedaikuma": ["eligibility", "available", "கிடைக்குமா", "eligible", "లభిస్తుందా", "ലഭിക്കുമോ"],
    "apply": ["vinnappam", "விண்ணப்பம்", "register", "eppadi", "దరఖాస్తు", "അപേക്ഷ"],
    "documents": ["aavanam", "சான்றிதழ்", "ஆவணங்கள்", "proof", "card", "పత్రాలు", "രേഖകൾ"],
    "muthulakshmi": ["mrmbs", "முத்துலட்சுமி", "maternity assistance", "18000"],
    "cmchis": ["chief minister insurance", "kalaignar kaapeedu", "முதலமைச்சர் காப்பீடு"],
    "aarogyasri": ["ysr aarogyasri", "ఆరోగ్యశ్రీ", "ap health scheme", "25 lakh"],
    "kasp": ["karunya", "കരുണ്യ", "കാസ്പ്", "kerala health scheme", "5 lakh"],
    "medisep": ["മെഡിസെപ്", "kerala employee insurance"],
    "thalolam": ["താലോലം", "child illness scheme kerala"],
    "pmjay": ["ayushman bharat", "ஆயுஷ்மான் பாரத்", "ఆయుష్మాన్", "ആയുഷ്മാൻ", "5 lakh"],
    "mtm": ["makkalai thedi maruthuvam", "மக்களைத் தேடி மருத்துவம்", "doorstep medicine"],
    "rbsk": ["rashtriya bal swasthya", "ராஷ்ட்ரிய பால ஸ்வஸ்திய", "child screening"],
    "accident": ["vibhathu", "விபத்து", "nammai kaakkum 48", "innuyir kaappom", "ప్రమాదం", "അപകടം"]
}


def expand_query_with_synonyms(norm_query: str) -> List[str]:
    """Expands query terms with common Tamil, Tanglish, Telugu, and Malayalam synonyms."""
    tokens = norm_query.split()
    expanded = set(tokens)
    for token in tokens:
        if token in SYNONYM_MAP:
            for syn in SYNONYM_MAP[token]:
                expanded.add(normalize_text(syn))
    return list(expanded)


def search_schemes(query: str, state: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Dedicated scheme search ranking government scheme cards based on eligibility,
    benefits, state relevance, keyword overlap, and category intent.
    """
    all_cards = load_all_knowledge_cards()
    scheme_cards = [c for c in all_cards if c.get("category") in ("government_scheme", "health_schemes")]

    norm_query = normalize_text(query)
    expanded_tokens = set(expand_query_with_synonyms(norm_query))
    _, detected_cat, _ = detect_scheme_intent(query)

    scored_schemes: List[Tuple[float, Dict[str, Any]]] = []

    for card in scheme_cards:
        score = 0.0
        card_state = card.get("state", "National")

        # State filter relevance boost
        if state:
            norm_target_state = state.strip().lower()
            if card_state.lower() == norm_target_state:
                score += 20.0  # Significant priority for selected state
            elif card_state.lower() == "national":
                score += 10.0  # National schemes remain accessible
            else:
                score -= 15.0  # Deprioritize schemes from other states

        keywords_en = [normalize_text(k) for k in card.get("keywords_en", [])]
        keywords_ta = [normalize_text(k) for k in card.get("keywords_ta", [])]
        keywords_te = [normalize_text(k) for k in card.get("keywords_te", [])]
        keywords_ml = [normalize_text(k) for k in card.get("keywords_ml", [])]
        keywords_tanglish = [normalize_text(k) for k in card.get("keywords_tanglish", [])]
        all_keywords = keywords_en + keywords_ta + keywords_te + keywords_ml + keywords_tanglish

        title_en = normalize_text(card.get("title_en", ""))
        title_ta = normalize_text(card.get("title_ta", ""))
        title_te = normalize_text(card.get("title_te", ""))
        title_ml = normalize_text(card.get("title_ml", ""))
        card_id = normalize_text(card.get("id", ""))
        scheme_cat = card.get("scheme_category", "")

        # 1. Exact match with card id or scheme names
        if card_id and (card_id in norm_query or norm_query in card_id):
            score += 30.0

        # 2. Category intent boost
        if detected_cat and scheme_cat == detected_cat:
            score += 15.0

        # 3. Exact keyword match
        for kw in all_keywords:
            if kw and (kw in norm_query or norm_query in kw):
                score += 12.0
            elif kw and any(t in kw for t in expanded_tokens if len(t) > 2):
                score += 4.0

        # 4. Token overlap
        for kw in all_keywords:
            kw_tokens = set(kw.split())
            overlap = expanded_tokens.intersection(kw_tokens)
            if overlap:
                score += len(overlap) * 3.5

        # 5. Title matches
        for token in expanded_tokens:
            if len(token) > 2:
                if token in title_en or token in title_ta or token in title_te or token in title_ml:
                    score += 6.0

        if score > 0:
            scored_schemes.append((score, card))

    scored_schemes.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in scored_schemes[:top_k]]


def search_knowledge_base(
    query: str,
    state: Optional[str] = None,
    top_k: int = 3,
    is_symptom_only: bool = False
) -> Dict[str, Any]:
    """
    Searches and ranks knowledge cards matching the query in English, Tamil, Tanglish, Telugu, or Malayalam
    using multi-factor scoring, substring matches, and state awareness.
    When is_symptom_only is True, government scheme cards are excluded so clinical guidance remains strictly health-focused.
    Returns matched cards, matched scheme structures, sources, and emergency status.
    """
    is_emergency, emergency_keywords = detect_emergency(query)
    is_scheme_intent, detected_cat, scheme_indicators = detect_scheme_intent(query)
    if is_symptom_only:
        is_scheme_intent = False

    all_cards = load_all_knowledge_cards()
    norm_query = normalize_text(query)
    expanded_tokens = set(expand_query_with_synonyms(norm_query))

    # Token groups for precise body-part and symptom affinity
    generic_clinical_tokens = {
        "pain", "vali", "ache", "about", "days", "have", "feel", "having", "since",
        "two", "three", "four", "mild", "severe", "problem", "issue", "for", "with",
        "from", "and", "the", "what", "should", "get", "help", "feeling", "care",
        "support", "treat", "cure", "வந்து", "இருந்து", "வலி", "நோவு", "నొప్పి", "వేదన"
    }
    head_tokens = {"head", "headache", "forehead", "migraine", "thala", "thalavali", "thalai", "தல", "தலைவலி", "తలనొప్పి", "తల", "തലവേദന", "തല"}
    chest_tokens = {"chest", "heart", "cardiac", "nenju", "இதய", "நெஞ்சு", "மாரடைப்பு", "గుండె", "ఛాతీ", "ഗുండె", "നെഞ്ച്"}
    stomach_tokens = {"stomach", "abdomen", "belly", "gastric", "gastritis", "vayiru", "vayi", "வயிறு", "కడుపు", "വയർ", "വയറുവേദന"}
    dizzy_tokens = {"dizzy", "dizziness", "vertigo", "giddiness", "lightheaded", "thalasuthu", "mayakkam", "மயக்கம்", "தலைச்சுற்றல்", "తలతిరుగుడు", "തലകറക്കം"}
    burn_tokens = {"burn", "burns", "scald", "theekaayam", "தீக்காயம்", "சூட்டுப்புண்", "కాలిన", "గాయం", "പൊള്ളൽ"}
    fever_tokens = {"fever", "kaichal", "kaachal", "juram", "காய்ச்சல்", "జ్వరం", "പനി", "temperature", "chills"}
    cough_tokens = {"cough", "cold", "sore throat", "throat", "runny nose", "sneeze", "congestion", "irumal", "sali", "இருமல்", "சளி", "தொண்டை", "దగ్గు", "జలుబు", "గొంతు", "ചുമ"}

    has_head = any(t in norm_query for t in head_tokens)
    has_chest = any(t in norm_query for t in chest_tokens)
    has_stomach = any(t in norm_query for t in stomach_tokens)
    has_dizzy = any(t in norm_query for t in dizzy_tokens)
    has_burn = any(t in norm_query for t in burn_tokens)
    has_fever = any(t in norm_query for t in fever_tokens)
    has_cough = any(t in norm_query for t in cough_tokens)

    meaningful_expanded = {t for t in expanded_tokens if t not in generic_clinical_tokens and len(t) > 2}

    scored_cards: List[Tuple[float, Dict[str, Any]]] = []

    for card in all_cards:
        card_cat = card.get("category", "")
        card_id = card.get("id", "").lower()
        title_en_lower = card.get("title_en", "").lower()

        # RULE 1: Never score or inject government scheme cards for pure symptom queries
        if is_symptom_only and card_cat in ("government_scheme", "health_schemes"):
            continue

        # RULE 2: NEVER retrieve emergency protocol cards for non-emergency queries
        if not is_emergency and card_cat == "emergency_protocols":
            continue

        # RULE 3: Strict Cross-Contamination Guardrails (Anatomy isolation)
        if has_head and not has_chest and ("chest" in card_id or "chest" in title_en_lower or "cardiac" in card_id):
            continue
        if has_stomach and not has_chest and ("chest" in card_id or "chest" in title_en_lower or "cardiac" in card_id):
            continue
        if has_dizzy and not has_chest and ("chest" in card_id or "chest" in title_en_lower or "cardiac" in card_id):
            continue
        if has_burn and not has_chest and ("chest" in card_id or "chest" in title_en_lower or "cardiac" in card_id):
            continue

        score = 0.0
        card_state = card.get("state", "National")

        # If scheme and state specified, apply state weighting
        if card_cat in ("government_scheme", "health_schemes") and state:
            if card_state.lower() == state.strip().lower():
                score += 15.0
            elif card_state.lower() == "national":
                score += 8.0
            else:
                score -= 10.0

        # Combine all searchable keywords
        keywords_en = [normalize_text(k) for k in card.get("keywords_en", [])]
        keywords_ta = [normalize_text(k) for k in card.get("keywords_ta", [])]
        keywords_te = [normalize_text(k) for k in card.get("keywords_te", [])]
        keywords_ml = [normalize_text(k) for k in card.get("keywords_ml", [])]
        keywords_tanglish = [normalize_text(k) for k in card.get("keywords_tanglish", [])]
        all_keywords = keywords_en + keywords_ta + keywords_te + keywords_ml + keywords_tanglish

        title_en = normalize_text(card.get("title_en", ""))
        title_ta = normalize_text(card.get("title_ta", ""))
        title_te = normalize_text(card.get("title_te", ""))
        title_ml = normalize_text(card.get("title_ml", ""))
        norm_card_id = normalize_text(card_id)
        scheme_cat = card.get("scheme_category", "")

        # 1. Exact phrase match in query or keywords (excluding generic tokens)
        for kw in all_keywords:
            if not kw or kw in generic_clinical_tokens:
                continue
            if kw in norm_query:
                score += 15.0
            elif len(norm_query) >= 4 and norm_query in kw:
                score += 10.0
            else:
                # Token subset match for non-generic words
                if any(t in kw for t in meaningful_expanded):
                    score += 4.0

        # 2. Token overlap with meaningful expanded synonyms
        for kw in all_keywords:
            kw_tokens = set(kw.split()) - generic_clinical_tokens
            overlap = meaningful_expanded.intersection(kw_tokens)
            if overlap:
                score += len(overlap) * 3.5

        # 3. Title matches
        for token in meaningful_expanded:
            if token in title_en or token in title_ta or token in title_te or token in title_ml:
                score += 5.0

        # 4. Emergency priority boost
        if is_emergency and card_cat == "emergency_protocols":
            score += 25.0

        # 5. Symptom card direct topic affinity boosts
        if has_head and "headache" in card_id:
            score += 35.0
        if has_stomach and ("stomach" in card_id or "diarrhea" in card_id):
            score += 35.0
        if has_dizzy and "dizziness" in card_id:
            score += 35.0
        if has_burn and "burn" in card_id:
            score += 35.0
        if has_fever and "fever" in card_id:
            score += 35.0
        if has_cough and "cough" in card_id:
            score += 35.0

        # 6. Scheme intent boost (only when not is_symptom_only)
        if not is_symptom_only and is_scheme_intent and card_cat in ("government_scheme", "health_schemes"):
            score += 15.0
            if detected_cat and scheme_cat == detected_cat:
                score += 10.0

        if score > 0:
            scored_cards.append((score, card))

    scored_cards.sort(key=lambda x: x[0], reverse=True)
    top_cards = [c[1] for c in scored_cards[:top_k]]

    # If scheme intent is strong and not is_symptom_only, ensure top scheme cards are populated
    matched_schemes = []
    if not is_symptom_only:
        matched_schemes = [c for c in top_cards if c.get("category") in ("government_scheme", "health_schemes")]
        if is_scheme_intent and len(matched_schemes) < 2:
            extra_schemes = search_schemes(query, state=state, top_k=top_k)
            for es in extra_schemes:
                if es["id"] not in [c["id"] for c in matched_schemes]:
                    matched_schemes.append(es)
            matched_schemes = matched_schemes[:top_k]

    # Collect source citations
    sources: List[Dict[str, str]] = []
    seen_urls = set()

    for c in (top_cards + matched_schemes):
        src_name = c.get("official_source") or c.get("source") or "National Health Mission"
        src_url = c.get("official_url") or c.get("source_url") or "https://mohfw.gov.in/"
        card_title = c.get("title_en") or c.get("id")

        if src_url not in seen_urls:
            seen_urls.add(src_url)
            sources.append({
                "title": f"{card_title} ({src_name})",
                "url": src_url,
                "scheme_id": c.get("id")
            })

    matched_topics = [c.get("title_en", c.get("id")) for c in top_cards]

    return {
        "matched_cards": top_cards,
        "matched_schemes": matched_schemes,
        "matched_topics": matched_topics,
        "sources": sources,
        "is_emergency": is_emergency,
        "emergency_keywords": emergency_keywords,
        "is_scheme_intent": is_scheme_intent,
        "has_matches": len(top_cards) > 0 or len(matched_schemes) > 0
    }


def format_knowledge_context_for_llm(search_result: Dict[str, Any], lang: str = "ta-IN") -> str:
    """
    Formats the matched knowledge cards and official scheme records into a structured,
    compact context string for grounding the LLM response without token bloat.
    """
    cards = search_result.get("matched_cards", [])
    schemes = search_result.get("matched_schemes", [])

    all_items = []
    seen_ids = set()
    for item in (cards + schemes):
        if item.get("id") not in seen_ids:
            seen_ids.add(item.get("id"))
            all_items.append(item)

    if not all_items:
        return "No specific verified knowledge card matched this query. Provide general safe supportive guidance and advise consulting the local Primary Health Centre (PHC)."

    # Determine language tag
    lang_tag = "en"
    if "ta" in lang.lower():
        lang_tag = "ta"
    elif "te" in lang.lower():
        lang_tag = "te"
    elif "ml" in lang.lower():
        lang_tag = "ml"

    blocks = []
    for item in all_items:
        card_id = item.get("id")
        category = item.get("category", "")
        title = item.get(f"title_{lang_tag}") or item.get("title_en") or card_id
        src = item.get("official_source") or item.get("source") or "Government Authority"
        url = item.get("official_url") or item.get("source_url") or ""

        if category in ("government_scheme", "health_schemes"):
            # Extract multilingual scheme fields with fallback
            def get_field_list(field_name):
                field_obj = item.get(field_name, {})
                if isinstance(field_obj, dict):
                    return field_obj.get(lang_tag) or field_obj.get("en") or []
                elif isinstance(field_obj, list):
                    return field_obj
                return [str(field_obj)]

            def get_field_str(field_name):
                field_obj = item.get(field_name, {})
                if isinstance(field_obj, dict):
                    return field_obj.get(lang_tag) or field_obj.get("en") or ""
                return str(field_obj)

            benefits = "\n  - ".join(get_field_list("benefits"))
            eligibility = "\n  - ".join(get_field_list("eligibility"))
            documents = "\n  - ".join(get_field_list("required_documents"))
            where = "\n  - ".join(get_field_list("where_to_apply"))
            desc = get_field_str("short_description")
            state_val = item.get("state", "National")

            block = (
                f"[GOVERNMENT SCHEME CARD: {title}]\n"
                f"State / Jurisdiction: {state_val}\n"
                f"Summary: {desc}\n"
                f"Official Source: {src} ({url})\n"
                f"Key Benefits:\n  - {benefits}\n"
                f"Eligibility Requirements:\n  - {eligibility}\n"
                f"Required Documents:\n  - {documents}\n"
                f"Where to Apply:\n  - {where}\n"
                f"Official Verification Note: Final eligibility must be confirmed with the official authority."
            )
            blocks.append(block)
        else:
            # Clinical symptom or emergency card
            def get_clin_list(field_name):
                field_obj = item.get(field_name, {})
                if isinstance(field_obj, dict):
                    return field_obj.get(lang_tag) or field_obj.get("en") or []
                elif isinstance(field_obj, list):
                    return field_obj
                return []

            def get_clin_str(field_name):
                field_obj = item.get(field_name, {})
                if isinstance(field_obj, dict):
                    return field_obj.get(lang_tag) or field_obj.get("en") or ""
                return str(field_obj) if field_obj else ""

            home_care = "\n  - ".join(get_clin_list("safe_home_care") or get_clin_list("immediate_safe_steps"))
            what_avoid = "\n  - ".join(get_clin_list("what_to_avoid"))
            warning_signs = "\n  - ".join(get_clin_list("warning_signs") or get_clin_list("emergency_red_flags"))
            when_phc = "\n  - ".join(get_clin_list("when_to_visit_phc"))
            indicates = get_clin_str("what_it_indicates")

            block = (
                f"[CLINICAL GUIDANCE CARD: {title}]\n"
                f"Source: {src}\n"
                f"What it Indicates: {indicates}\n"
                f"Safe Supportive Steps:\n  - {home_care}\n"
            )
            if what_avoid:
                block += f"What to Avoid:\n  - {what_avoid}\n"
            if warning_signs:
                block += f"Warning Red Flags:\n  - {warning_signs}\n"
            if when_phc:
                block += f"When to Visit PHC / Doctor:\n  - {when_phc}\n"

            blocks.append(block)

    return "\n\n".join(blocks)
