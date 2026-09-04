import os
import re
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv
from sarvamai import SarvamAI

# Root directory path (two levels up from backend/services/)
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

# Load environment variables from root .env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


def get_sarvam_client() -> SarvamAI:
    """
    Initializes and returns a SarvamAI client using SARVAM_API_KEY from .env.
    Raises ValueError if SARVAM_API_KEY is not configured.
    """
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "SARVAM_API_KEY is missing or empty. Please set your SARVAM_API_KEY in the root .env file."
        )

    return SarvamAI(api_subscription_key=api_key.strip())


def sanitize_text_for_speech(text: str) -> str:
    """
    Sanitizes markdown formatted text into natural, speakable plain text.
    Removes Markdown headers, asterisks, bullet points, URLs, and noisy symbols.
    """
    if not text:
        return ""

    clean = text
    # Remove markdown link text brackets [title](url) -> title first
    clean = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", clean)
    # Remove standalone URLs
    clean = re.sub(r"https?://\S+|www\.\S+", "", clean)
    # Remove bold, italics, headers, code blocks, blockquotes, and brackets
    clean = re.sub(r"[*#_`~>\[\]\(\)]", " ", clean)
    # Remove markdown bullets and emojis
    clean = re.sub(r"^[\s*•\-–—]+\s*", "", clean, flags=re.MULTILINE)
    # Collapse multiple whitespaces and newlines
    clean = re.sub(r"\n+", ". ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def transcribe_audio(
    file_path: Union[str, Path],
    language_code: Optional[str] = "unknown"
) -> str:
    """
    Transcribes an audio file using Sarvam AI Speech-to-Text with model 'saaras:v3'.
    Supports 'ta-IN', 'en-IN', 'te-IN', 'ml-IN', and 'unknown' (auto-detection).
    """
    client = get_sarvam_client()
    target_path = Path(file_path)

    if not target_path.exists():
        raise FileNotFoundError(f"Audio file not found at: {target_path}")

    # Standardize language codes
    valid_langs = {"ta-IN": "ta-IN", "en-IN": "en-IN", "te-IN": "te-IN", "ml-IN": "ml-IN", "hi-IN": "hi-IN"}
    lang_to_send = valid_langs.get(language_code, "unknown")

    with open(target_path, "rb") as audio_file:
        response = client.speech_to_text.transcribe(
            file=(target_path.name, audio_file),
            model="saaras:v3",
            mode="transcribe",
            language_code=lang_to_send
        )

    # Extract transcript text
    if hasattr(response, "transcript"):
        return response.transcript
    elif isinstance(response, dict) and "transcript" in response:
        return response["transcript"]

    return str(response)


def text_to_speech(
    text: str,
    language_code: Optional[str] = None,
    speaker: Optional[str] = None
) -> dict:
    """
    Converts text to natural speech using Sarvam AI Text-to-Speech (bulbul:v3).
    Supports Tamil, English, Telugu, and Malayalam with automatic language identification.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for Text-to-Speech conversion.")

    client = get_sarvam_client()

    # Clean markdown and special symbols for natural speech synthesis
    clean_text = sanitize_text_for_speech(text)
    if len(clean_text) > 2400:
        clean_text = clean_text[:2400] + "..."

    # Determine language code if not specified or unknown
    if not language_code or language_code in ("unknown", "auto"):
        has_tamil = any("\u0B80" <= char <= "\u0BFF" for char in clean_text)
        has_telugu = any("\u0C00" <= char <= "\u0C7F" for char in clean_text)
        has_malayalam = any("\u0D00" <= char <= "\u0D7F" for char in clean_text)

        if has_tamil:
            target_lang = "ta-IN"
        elif has_telugu:
            target_lang = "te-IN"
        elif has_malayalam:
            target_lang = "ml-IN"
        else:
            target_lang = "en-IN"
    else:
        target_lang = language_code

    # Convert to speech with natural Indic voice
    kwargs = {
        "text": clean_text,
        "language_code": target_lang,
        "model": "bulbul:v3"
    }
    if speaker:
        kwargs["speaker"] = speaker

    response = client.text_to_speech.convert(**kwargs)

    audio_base64 = ""
    if hasattr(response, "audios") and response.audios:
        audio_base64 = response.audios[0]
    elif isinstance(response, dict) and "audios" in response and response["audios"]:
        audio_base64 = response["audios"][0]
    elif hasattr(response, "audio"):
        audio_base64 = response.audio

    return {
        "audio": audio_base64,
        "language_code": target_lang
    }
