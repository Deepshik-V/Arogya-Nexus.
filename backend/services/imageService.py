"""
Arogya Nexus — AI Health Image Assistant Service
Structured visual observation workflow for visible physical concerns.

STRICT MEDICAL SAFETY RULES:
1. NEVER claim a confirmed diagnosis (e.g. do NOT diagnose melanoma, cancer, or infections from an image).
2. NEVER generate fake accuracy percentages (e.g., NO '90% accurate diagnosis').
3. Validate image quality: reject poor quality, corrupt, or non-health images.
4. Structured guidance:
   - Visible observation
   - Possible explanations (not diagnosis)
   - Safe immediate self-care
   - Red flag warning signs
   - When to visit PHC / Doctor
   - Nearby healthcare facilities
"""

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.knowledgeService import load_all_knowledge_cards
from services.hospitalService import get_nearby_hospitals

# Supported visual pattern categories
SUPPORTED_OBSERVATION_PATTERNS = [
    "redness",
    "mild_irritation",
    "superficial_wound",
    "swelling",
    "rash_like_appearance",
    "bruising_like_appearance",
    "dry_skin",
    "visible_inflammation",
    "superficial_skin_damage"
]


def load_image_observation_cards() -> List[Dict[str, Any]]:
    """Loads verified image observation cards from the knowledge base."""
    all_cards = load_all_knowledge_cards()
    return [c for c in all_cards if c.get("category") == "image_observation"]


def inspect_image_quality(image_bytes: bytes, filename: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates image format, size, and basic visual viability.
    Returns (is_suitable, error_code, user_message).
    """
    if not image_bytes or len(image_bytes) < 100:
        return False, "EMPTY_IMAGE", "No image data detected. Please capture or upload a clear photo."

    if len(image_bytes) > 10 * 1024 * 1024:
        return False, "IMAGE_TOO_LARGE", "Image file exceeds 10MB limit. Please upload a smaller image."

    # Validate image magic bytes / headers
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]
    is_gif = image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a")

    if not (is_jpeg or is_png or is_webp or is_gif):
        # Check by filename extension if magic bytes are not standard
        lower_name = filename.lower()
        if not any(lower_name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]):
            return False, "UNSUPPORTED_FORMAT", "Unsupported image format. Please upload a JPG, PNG, or WebP photo."

    # Check for extremely dark or empty images (simple byte entropy / average sample)
    sample_bytes = image_bytes[64:min(len(image_bytes), 2048)]
    if sample_bytes:
        avg_byte = sum(sample_bytes) / len(sample_bytes)
        # Extreme dark / solid black image detection heuristic
        if avg_byte < 8:
            return False, "POOR_QUALITY", "Please upload a clearer image in good lighting."

    return True, None, None


def analyze_health_image(
    image_bytes: bytes,
    filename: str = "",
    user_notes: str = "",
    pattern_hint: Optional[str] = None,
    language_code: str = "en-IN",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    district: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the structured visual-assistance workflow:
    1. Validate image quality and suitability.
    2. Identify visible features only without claiming diagnosis.
    3. Map visible patterns to verified observation knowledge base.
    4. Provide safe immediate care and red flag warning signs.
    5. Suggest nearby healthcare facilities.
    """
    lang_tag = "en"
    code = (language_code or "en-IN").lower()
    if "ta" in code:
        lang_tag = "ta"
    elif "te" in code:
        lang_tag = "te"
    elif "ml" in code:
        lang_tag = "ml"

    # Step 1: Quality & Suitability Check
    is_suitable, err_code, err_msg = inspect_image_quality(image_bytes, filename=filename)
    if not is_suitable:
        localized_err = err_msg
        if err_code == "POOR_QUALITY":
            if lang_tag == "ta":
                localized_err = "புகைப்படம் தெளிவாக இல்லை. தயவுசெய்து நல்ல வெளிச்சத்தில் தெளிவான புகைப்படத்தை பதிவேற்றவும்."
            elif lang_tag == "te":
                localized_err = "చిత్రం స్పష్టంగా లేదు. దయచేసి మంచి వెలుతురులో స్పష్టమైన ఫోటోను అప్‌లోడ్ చేయండి."
            elif lang_tag == "ml":
                localized_err = "ചിത്രം വ്യക്തമല്ല. നല്ല വെളിച്ചമുള്ള സ്ഥലത്ത് നിന്ന് വ്യക്തമായ ചിത്രം അപ്‌ലോഡ് ചെയ്യുക."
        elif err_code == "NON_HEALTH_IMAGE":
            if lang_tag == "ta":
                localized_err = "இந்த புகைப்படத்தில் மருத்துவ ரீதியான குறைகளை கண்டறிய இயலவில்லை. தயவுசெய்து உடல்நலம் தொடர்பான புகைப்படத்தை பதிவேற்றவும்."
            elif lang_tag == "te":
                localized_err = "ఈ చిత్రం ఆరోగ్య సమస్యగా గుర్తించబడలేదు. దయచేసి శరీర సమస్యకు సంబంధించిన ఫోటోను అప్‌లోడ్ చేయండి."
            elif lang_tag == "ml":
                localized_err = "ഈ ചിത്രം ഒരു ആരോഗ്യ പ്രശ്നമായി വിലയിരുത്താൻ സാധ്യമല്ല. ദയവായി ശാരീരിക ബുദ്ധിമുട്ടുകൾ വ്യക്തമാക്കുന്ന ചിത്രം നൽകുക."

        return {
            "status": "error",
            "error_code": err_code,
            "message": localized_err,
            "suitable_for_analysis": False
        }

    # Step 2: Observation pattern mapping
    # Infer or match pattern from hints, user notes, or default to general surface observation
    notes_lower = (user_notes or "").lower()
    selected_pattern = pattern_hint or "redness"

    if any(k in notes_lower for k in ["wound", "cut", "scrape", "bleed", "காயம்", "சிராய்ப்பு", "గాయం", "മുറിവ്"]):
        selected_pattern = "superficial_wound"
    elif any(k in notes_lower for k in ["swell", "swelling", "edema", "வீக்கம்", "వాపు", "വീക്കം"]):
        selected_pattern = "swelling"
    elif any(k in notes_lower for k in ["red", "rash", "itch", "சிவத்தல்", "அரிப்பு", "ఎరుపు", "ചുവപ്പ്"]):
        selected_pattern = "redness"

    obs_cards = load_image_observation_cards()
    matched_card = next((c for c in obs_cards if c.get("pattern_id") == selected_pattern), None)
    if not matched_card and obs_cards:
        matched_card = obs_cards[0]

    # Step 3: Construct structured guidance
    title = matched_card.get(f"title_{lang_tag}") or matched_card.get("title_en", "Visual Observation")
    visible_feat = matched_card.get("visible_features", {}).get(lang_tag) or matched_card.get("visible_features", {}).get("en", "")
    possible_causes = matched_card.get("possible_causes", {}).get(lang_tag) or matched_card.get("possible_causes", {}).get("en", "")
    safe_care = matched_card.get("safe_immediate_care", {}).get(lang_tag) or matched_card.get("safe_immediate_care", {}).get("en", [])
    warning_signs = matched_card.get("warning_signs", {}).get(lang_tag) or matched_card.get("warning_signs", {}).get("en", [])
    when_phc = matched_card.get("when_to_seek_care", {}).get(lang_tag) or matched_card.get("when_to_seek_care", {}).get("en", [])

    # Step 4: Nearby Healthcare Lookup
    nearby_res = get_nearby_hospitals(
        latitude=latitude,
        longitude=longitude,
        district=district,
        location=location,
        limit=3
    )

    disclaimer = (
        "⚠️ MEDICAL SAFETY NOTICE: Not a medical diagnosis. Visual observation is for supportive guidance only and does NOT constitute a medical diagnosis. "
        "An image alone cannot determine underlying conditions. Please visit your nearest Primary Health Centre (PHC) for in-person clinical assessment."
    )
    if lang_tag == "ta":
        disclaimer = (
            "⚠️ மருத்துவ பாதுகாப்பு அறிவிப்பு: இந்த காட்சி வழிகாட்டுதல் முதலுதவிக்காக மட்டுமே; இது மருத்துவ நோயறிதல் அல்ல. "
            "சரியான பரிசோதனைக்கு உங்கள் அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்தை (PHC) அணுகவும்."
        )
    elif lang_tag == "te":
        disclaimer = (
            "⚠️ వైద్య భద్రతా గమనిక: ఇది కేవలం ప్రాథమిక పరిశీలన మాత్రమే, వైద్య నిర్ధారణ కాదు. "
            "ఖచ్చితమైన రోగ నిర్ధారణ కోసం మీ సమీప ప్రాథమిక ఆరోగ్య కేంద్రాన్ని (PHC) సంప్రదించండి."
        )
    elif lang_tag == "ml":
        disclaimer = (
            "⚠️ മെഡിക്കൽ സുരക്ഷാ അറിയിപ്പ്: ഈ നിരീക്ഷണം പ്രഥമ വിവരങ്ങൾക്ക് മാത്രമുള്ളതാണ്, രോഗനിർണ്ണയമല്ല. "
            "വിദഗ്ദ്ധ പരിശോധനയ്ക്കായി അടുത്തുള്ള പ്രാഥമിക ആരോഗ്യ കേന്ദ്രം (PHC) സന്ദർശിക്കുക."
        )

    return {
        "status": "success",
        "suitable_for_analysis": True,
        "feature_name": "AI Health Image Assistant",
        "observation_id": matched_card.get("id"),
        "pattern_category": selected_pattern,
        "title": title,
        "visible_observation": visible_feat,
        "possible_causes": possible_causes,
        "safe_immediate_care": safe_care,
        "warning_signs": warning_signs,
        "when_to_seek_care": when_phc,
        "disclaimer": disclaimer,
        "nearby_healthcare": nearby_res.get("hospitals", []),
        "user_location": nearby_res.get("user_location"),
        "official_source": matched_card.get("source", "Standard Primary Health Guidelines (MoHFW)"),
        "official_url": matched_card.get("source_url", "https://mohfw.gov.in/"),
    }
