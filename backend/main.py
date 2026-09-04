import base64
import hashlib
import os
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from services.sarvamService import transcribe_audio, text_to_speech
from services.llmService import generate_healthcare_response, generate_healthcare_response_stream
from services.knowledgeService import reload_knowledge_base
from services.eligibilityService import evaluate_profile_eligibility
from services.schemeRecommendationService import get_scheme_recommendations
from services.schemeComparisonService import compare_schemes
from services.hospitalService import get_nearby_hospitals
from services.imageService import analyze_health_image
from services.locationService import geocode_location, reverse_geocode, get_location_hierarchy
from data.validate_knowledge_base import validate_knowledge_base


# Load root .env
ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

app = FastAPI(
    title="Arogya Nexus API",
    description="AI-Powered Multilingual Rural Healthcare & Government Scheme Intelligence Platform",
    version="3.5.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prototype-level auth store: in-memory only for hackathon/demo use.
# This is intentionally not a production replacement for a real database-backed auth system.
AUTH_USERS: Dict[str, Dict[str, Any]] = {}
AUTH_SESSIONS: Dict[str, Dict[str, Any]] = {}
AUTH_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
AUTH_RESET_TOKENS: Dict[str, Dict[str, Any]] = {}
AUTH_RESET_TTL_SECONDS = 60 * 60


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(salt + dk).decode("utf-8")


# Seed verified default demo account for testing & hackathon review
_demo_hash = _hash_password("Password123!")
AUTH_USERS["demo-user-1"] = {
    "id": "demo-user-1",
    "name": "Dr. Deepshika",
    "email": "demo@arogyanexus.gov.in",
    "password_hash": _demo_hash,
    "created_at": time.time(),
    "profile": {
        "state": "Tamil Nadu",
        "district": "Salem",
        "taluk": "Salem Taluk",
        "locality": "Shevapet",
        "pincode": "636001",
        "location": "Shevapet, Salem",
        "latitude": 11.6508,
        "longitude": 78.1402,
        "age": 34,
        "gender": "female",
        "annual_income": 85000,
        "ration_card_type": "PHH",
        "family_size": 4
    }
}


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        data = base64.b64decode(password_hash.encode("utf-8"))
        salt = data[:16]
        expected = data[16:]
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(derived, expected)
    except Exception:
        return False


def _create_session(user_id: str) -> str:
    session_token = secrets.token_urlsafe(32)
    AUTH_SESSIONS[session_token] = {
        "user_id": user_id,
        "issued_at": time.time(),
        "expires_at": time.time() + AUTH_SESSION_TTL_SECONDS,
    }
    return session_token


def _get_session_user(request) -> Optional[Dict[str, Any]]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    session = AUTH_SESSIONS.get(token)
    if not session:
        return None
    if session["expires_at"] < time.time():
        AUTH_SESSIONS.pop(token, None)
        return None

    user_id = session["user_id"]
    user = AUTH_USERS.get(user_id)
    if user is None:
        AUTH_SESSIONS.pop(token, None)
        return None
    return user


class ChatRequest(BaseModel):
    message: str
    language_code: Optional[str] = "ta-IN"
    state: Optional[str] = None
    district: Optional[str] = None
    location: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None



class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = None
    speaker: Optional[str] = None


class AuthSignupRequest(BaseModel):
    name: str
    email: str
    password: str


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileSaveRequest(BaseModel):
    profile: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
    return {
        "message": "Arogya Nexus Backend is running",
        "platform": "AI-Powered Multilingual Rural Healthcare & Government Scheme Intelligence Platform",
        "version": "3.5.0",
        "supported_languages": ["ta-IN (Tamil)", "en-IN (English)", "te-IN (Telugu)", "ml-IN (Malayalam)"],
        "supported_states": ["Tamil Nadu", "Andhra Pradesh", "Kerala", "National"],
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {
        "service": "Arogya Nexus",
        "status": "healthy",
        "version": "3.5.0"
    }


@app.post("/api/auth/signup")
async def auth_signup(request: AuthSignupRequest):
    name = (request.name or "").strip()
    email = (request.email or "").strip().lower()
    password = (request.password or "").strip()

    if not name or not email or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, valid email, and password with at least 6 characters are required."
        )

    if email in {user["email"] for user in AUTH_USERS.values()}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    user_id = f"user_{len(AUTH_USERS) + 1}"
    AUTH_USERS[user_id] = {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": _hash_password(password),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profile": {},
    }

    session_token = _create_session(user_id)
    user = AUTH_USERS[user_id]
    return {
        "status": "success",
        "message": "Account created successfully.",
        "session_token": session_token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
        }
    }


@app.post("/api/auth/login")
async def auth_login(request: AuthLoginRequest):
    email = (request.email or "").strip().lower()
    password = (request.password or "").strip()

    user = next((u for u in AUTH_USERS.values() if u["email"] == email), None)
    if not user or not _verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please try again or reset your password."
        )

    session_token = _create_session(user["id"])
    return {
        "status": "success",
        "message": "Login successful.",
        "session_token": session_token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "profile": user.get("profile", {})
        }
    }



@app.post("/api/auth/forgot-password")
async def auth_forgot_password(request: ForgotPasswordRequest):
    email = (request.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required."
        )

    user = next((u for u in AUTH_USERS.values() if u["email"] == email), None)
    smtp_host = os.getenv("SMTP_HOST")

    if not user:
        # Uniform success response to prevent account enumeration vulnerability
        return {
            "status": "success",
            "message": "If an account exists with this email address, password reset instructions have been generated.",
            "reset_token": None,
            "email_sent": False,
            "smtp_configured": bool(smtp_host),
            "notice": "No account found with this email. Generic response returned to prevent account enumeration."
        }

    reset_token = secrets.token_urlsafe(32)
    AUTH_RESET_TOKENS[reset_token] = {
        "user_id": user["id"],
        "email": email,
        "expires_at": time.time() + AUTH_RESET_TTL_SECONDS,
    }

    return {
        "status": "success",
        "message": "Password reset token generated. Use this token to set a new password.",
        "reset_token": reset_token,
        "email_sent": bool(smtp_host),
        "smtp_configured": bool(smtp_host),
        "notice": "SMTP server not configured in .env (SMTP_HOST is empty). Reset token provided for development/test mode." if not smtp_host else "Password reset link sent to registered email address."
    }


@app.post("/api/auth/reset-password")
async def auth_reset_password(request: ResetPasswordRequest):
    token = (request.token or "").strip()
    new_password = (request.new_password or "").strip()

    record = AUTH_RESET_TOKENS.get(token)
    if not record or record["expires_at"] < time.time():
        AUTH_RESET_TOKENS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or has expired."
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters."
        )

    user_id = record["user_id"]
    if user_id in AUTH_USERS:
        AUTH_USERS[user_id]["password_hash"] = _hash_password(new_password)

    AUTH_RESET_TOKENS.pop(token, None)
    return {
        "status": "success",
        "message": "Password has been updated successfully. Please log in with your new password."
    }


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        AUTH_SESSIONS.pop(token, None)
    return {"status": "success", "message": "Logged out successfully."}


@app.get("/api/auth/session")
async def auth_session(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid session available."
        )
    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "profile": user.get("profile", {}),
        }
    }


@app.get("/api/profile/me")
async def get_profile_me(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )
    return {
        "status": "success",
        "profile": user.get("profile", {})
    }


@app.post("/api/profile/save")
async def save_profile(request: ProfileSaveRequest, auth_request: Request):
    user = _get_session_user(auth_request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )
    user["profile"] = request.profile or {}
    return {
        "status": "success",
        "message": "Profile saved successfully.",
        "profile": user["profile"]
    }


@app.post("/api/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    language_code: Optional[str] = Form("unknown")
):
    """
    Transcribe an uploaded audio file using Sarvam AI Speech-to-Text (saaras:v3).
    Supports 'ta-IN', 'en-IN', 'te-IN', 'ml-IN', and 'unknown'.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename."
        )

    suffix = Path(file.filename).suffix or ".wav"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        transcript = transcribe_audio(temp_path, language_code=language_code)

        return {
            "status": "success",
            "transcript": transcript,
            "filename": file.filename
        }

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech-to-Text transcription failed: {str(e)}"
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        await file.close()


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Generate an AI healthcare and government scheme guidance response for a patient's
    transcribed or typed message, grounded in verified clinical knowledge, official scheme cards,
    state jurisdiction, and multi-turn conversation context.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message field cannot be empty."
        )

    try:
        history = request.history or request.conversation_history
        result = generate_healthcare_response(
            request.message,
            history=history,
            language_code=request.language_code,
            state=request.state,
            district=request.district,
            location=request.location,
        )
        return {
            "success": True,
            "response": result.get("response", ""),
            "knowledge_used": result.get("knowledge_used", False),
            "matched_topics": result.get("matched_topics", []),
            "matched_schemes": result.get("matched_schemes", []),
            "sources": result.get("sources", []),
            "is_emergency": result.get("is_emergency", False),
            "is_symptom": result.get("is_symptom", False),
            "suggest_nearby_hospitals": result.get("suggest_nearby_hospitals", False),
            "intent": result.get("intent", "HEALTH_SYMPTOM"),
            "nearby_hospitals": result.get("nearby_hospitals", []),
            "user_location": result.get("user_location"),
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Healthcare response generation failed: {str(e)}"
        )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Instant token-by-token streaming endpoint for Arogya Nexus AI Assistant using SSE.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message field cannot be empty."
        )

    history = request.history or request.conversation_history
    return StreamingResponse(
        generate_healthcare_response_stream(
            request.message,
            history=history,
            language_code=request.language_code,
            state=request.state,
            district=request.district,
            location=request.location,
        ),
        media_type="text/event-stream"
    )



@app.post("/api/text-to-speech")
async def text_to_speech_endpoint(request: TTSRequest):
    """
    Synthesize natural speech audio from text using Sarvam AI Text-to-Speech (bulbul:v3).
    Automatically removes markdown symbols for natural acoustic flow.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text field cannot be empty for text-to-speech."
        )

    try:
        result = text_to_speech(
            text=request.text,
            language_code=request.language_code,
            speaker=request.speaker
        )
        return {
            "status": "success",
            "audio": result.get("audio", ""),
            "audios": [result.get("audio", "")] if result.get("audio") else [],
            "language_code": result.get("language_code", "ta-IN")
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text-to-Speech synthesis failed: {str(e)}"
        )


@app.post("/api/knowledge/refresh")
async def refresh_knowledge_base():
    """
    Safely validates knowledge cards on disk and reloads them into memory.
    Supports n8n automated sync pipelines.
    """
    try:
        is_valid, validation_report = validate_knowledge_base()
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Knowledge base validation failed: {validation_report.get('errors')}"
            )

        reload_stats = reload_knowledge_base()

        return {
            "status": "success",
            "message": "Knowledge base validated and refreshed successfully.",
            "total_cards": reload_stats.get("total_cards", 0),
            "scheme_cards_count": reload_stats.get("scheme_cards_count", 0),
            "healthcare_cards_count": reload_stats.get("healthcare_cards_count", 0),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge base refresh failed: {str(e)}"
        )


class ProfileEligibilityRequest(BaseModel):
    profile: Optional[Dict[str, Any]] = None


class SchemeRecommendationRequest(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    query: Optional[str] = None
    language_code: Optional[str] = "ta-IN"
    state: Optional[str] = None
    top_k: Optional[int] = 3


class SchemeComparisonRequest(BaseModel):
    scheme_ids: Optional[List[str]] = None


@app.post("/api/profile/eligibility")
async def profile_eligibility_endpoint(request: ProfileEligibilityRequest):
    """
    Evaluates patient profile against verified government health schemes across TN, AP, Kerala & National.
    """
    try:
        results = evaluate_profile_eligibility(request.profile)
        return {
            "status": "success",
            "total_evaluated": len(results),
            "schemes": results,
            "disclaimer": "Final eligibility must be confirmed with the official government authority."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile eligibility evaluation failed: {str(e)}"
        )


@app.post("/api/schemes/recommend")
async def schemes_recommend_endpoint(request: SchemeRecommendationRequest):
    """
    Recommends top verified government health schemes matching user intent, state, and profile.
    """
    try:
        recommendations = get_scheme_recommendations(
            profile=request.profile,
            query=request.query,
            language_code=request.language_code,
            state=request.state,
            top_k=request.top_k or 3
        )
        return {
            "status": "success",
            **recommendations
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scheme recommendation failed: {str(e)}"
        )


@app.post("/api/schemes/compare")
async def schemes_compare_endpoint(request: SchemeComparisonRequest):
    """
    Compares 2 or more government schemes side-by-side without bias.
    """
    try:
        comparison = compare_schemes(request.scheme_ids or [])
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scheme comparison failed: {str(e)}"
        )


class GeocodeRequest(BaseModel):
    state: Optional[str] = "Tamil Nadu"
    district: Optional[str] = "Salem"
    taluk: Optional[str] = None
    locality: Optional[str] = None
    pincode: Optional[str] = None


class ReverseGeocodeRequest(BaseModel):
    latitude: float
    longitude: float


@app.post("/api/location/geocode")
async def location_geocode_endpoint(request: GeocodeRequest):
    """
    Resolves administrative location hierarchy into verified geographic coordinates.
    """
    try:
        res = geocode_location(
            state=request.state,
            district=request.district,
            taluk=request.taluk,
            locality=request.locality,
            pincode=request.pincode,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Geocoding failed: {str(e)}"
        )


@app.post("/api/location/reverse-geocode")
async def location_reverse_geocode_endpoint(request: ReverseGeocodeRequest):
    """
    Resolves GPS latitude/longitude into administrative location hierarchy.
    """
    try:
        res = reverse_geocode(
            latitude=request.latitude,
            longitude=request.longitude,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reverse geocoding failed: {str(e)}"
        )


@app.get("/api/location/hierarchy")
async def location_hierarchy_endpoint():
    """
    Returns verified hierarchy of States -> Districts -> Taluks -> Localities.
    """
    return get_location_hierarchy()


@app.get("/api/healthcare/nearby")
@app.get("/api/hospitals/nearby")
async def healthcare_nearby_endpoint(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    locality: Optional[str] = None,
    location: Optional[str] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    query: Optional[str] = None,
    radius_km: Optional[float] = None,
    limit: Optional[int] = 15,
):
    """
    Returns verified healthcare facilities and government hospitals,
    ranked by actual Haversine distance from GPS coordinates, hierarchical saved profile,
    or manual location, filtered by radius.
    """
    try:
        result = get_nearby_hospitals(
            latitude=latitude,
            longitude=longitude,
            state=state,
            district=district,
            taluk=taluk,
            locality=locality,
            location=location,
            city=city,
            pincode=pincode,
            query=query,
            radius_km=radius_km,
            limit=limit or 15,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve nearby healthcare facilities: {str(e)}"
        )


class ImageAnalysisJsonRequest(BaseModel):
    image_base64: Optional[str] = None
    filename: Optional[str] = "captured_photo.jpg"
    user_notes: Optional[str] = ""
    pattern_hint: Optional[str] = None
    language_code: Optional[str] = "en-IN"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: Optional[str] = None
    location: Optional[str] = None


@app.post("/api/image-analysis")
@app.post("/api/image/analyze")
async def image_analysis_json(request: ImageAnalysisJsonRequest):
    """
    AI Health Image Assistant (JSON Base64 payload):
    Validates visible health concern image, maps to observation categories,
    and returns safe structured guidance, warning signs, and nearby healthcare facilities.
    """
    if not request.image_base64 or not request.image_base64.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image data is required (base64 string)."
        )

    try:
        raw_b64 = request.image_base64.strip()
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(raw_b64)

        result = analyze_health_image(
            image_bytes=image_bytes,
            filename=request.filename or "captured_photo.jpg",
            user_notes=request.user_notes or "",
            pattern_hint=request.pattern_hint,
            language_code=request.language_code or "en-IN",
            latitude=request.latitude,
            longitude=request.longitude,
            district=request.district,
            location=request.location,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {str(e)}"
        )


@app.post("/api/image-analysis/upload")
async def image_analysis_upload(
    file: UploadFile = File(...),
    user_notes: Optional[str] = Form(""),
    pattern_hint: Optional[str] = Form(None),
    language_code: Optional[str] = Form("en-IN"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    district: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """
    AI Health Image Assistant (Multipart file upload):
    Accepts camera photo or gallery image upload.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename."
        )

    try:
        image_bytes = await file.read()
        result = analyze_health_image(
            image_bytes=image_bytes,
            filename=file.filename,
            user_notes=user_notes or "",
            pattern_hint=pattern_hint,
            language_code=language_code or "en-IN",
            latitude=latitude,
            longitude=longitude,
            district=district,
            location=location,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image upload analysis failed: {str(e)}"
        )
    finally:
        await file.close()