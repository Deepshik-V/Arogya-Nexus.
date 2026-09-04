/**
 * Arogya Nexus AI Service
 * Connects frontend with backend API endpoints on http://127.0.0.1:8000
 * - Speech-to-Text (Sarvam saaras:v3)
 * - Clinical Healthcare Chat (Sarvam 105b + Verified Knowledge Base)
 * - Text-to-Speech (Sarvam bulbul:v3)
 * - Multi-State Personalized Scheme Eligibility & Recommendations
 */

export const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== "undefined" && window.location?.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
};

export const API_BASE_URL = getApiBaseUrl();

/**
 * Transcribes audio blob using backend Sarvam STT.
 * @param {Blob} audioBlob - The recorded audio blob.
 * @param {string} [languageCode="unknown"] - Language code ('unknown', 'ta-IN', 'en-IN', 'te-IN', 'ml-IN')
 * @returns {Promise<{transcript: string, status: string}>}
 */
export async function transcribeAudio(audioBlob, languageCode = "unknown") {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error("No audio recording captured. Please speak into the microphone.");
  }

  const formData = new FormData();
  let extension = "webm";
  if (audioBlob.type.includes("wav")) {
    extension = "wav";
  } else if (audioBlob.type.includes("mp4") || audioBlob.type.includes("m4a")) {
    extension = "mp4";
  } else if (audioBlob.type.includes("ogg")) {
    extension = "ogg";
  }

  const filename = `patient_voice_${Date.now()}.${extension}`;
  formData.append("file", audioBlob, filename);
  if (languageCode) {
    formData.append("language_code", languageCode);
  }

  const response = await fetch(`${API_BASE_URL}/api/speech-to-text`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = "Speech-to-Text transcription failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  const data = await response.json();
  if (!data.transcript || !data.transcript.trim()) {
    throw new Error("No clear speech detected. Please speak clearly into your microphone.");
  }

  return data;
}

/**
 * Sends patient message to backend clinical LLM service with optional conversation history, language, and location.
 * @param {string} message - Spoken transcript or typed query.
 * @param {Array<{role: string, content: string}>} [history=[]] - Recent conversation history turns.
 * @param {string} [languageCode="ta-IN"] - Selected language code.
 * @param {string} [state=null] - Selected Indian state jurisdiction.
 * @param {string} [district=null] - User district.
 * @param {string} [location=null] - User city or location name.
 * @returns {Promise<any>}
 */
export async function sendChatMessage(
  message,
  history = [],
  languageCode = "ta-IN",
  state = null,
  district = null,
  location = null
) {
  if (!message || !message.trim()) {
    throw new Error("Message cannot be empty.");
  }

  const payload = {
    message: message.trim(),
    language_code: languageCode || "ta-IN",
    state: state || null,
    district: district || null,
    location: location || null,
    history: Array.isArray(history) ? history : [],
  };

  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = "Healthcare response generation failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  const data = await response.json();
  return {
    response: data.response || "",
    knowledge_used: Boolean(data.knowledge_used),
    matched_topics: data.matched_topics || [],
    matched_schemes: data.matched_schemes || [],
    sources: data.sources || [],
    is_emergency: Boolean(data.is_emergency),
    is_symptom: Boolean(data.is_symptom),
    suggest_nearby_hospitals: Boolean(data.suggest_nearby_hospitals),
    intent: data.intent || "HEALTH_SYMPTOM",
    nearby_hospitals: data.nearby_hospitals || [],
    user_location: data.user_location || null,
  };
}

/**
 * Instant token-by-token streaming chat client for Arogya Nexus AI Assistant using SSE.
 * Provides real-time response generation without waiting for complete completion.
 */
export async function streamChatMessage({
  message,
  history = [],
  languageCode = "ta-IN",
  state = null,
  district = null,
  location = null,
  onMetadata = null,
  onToken = null,
  onDone = null,
  onError = null,
}) {
  if (!message || !message.trim()) {
    if (onError) onError(new Error("Message cannot be empty."));
    return;
  }

  const payload = {
    message: message.trim(),
    language_code: languageCode || "ta-IN",
    state: state || null,
    district: district || null,
    location: location || null,
    history: Array.isArray(history) ? history : [],
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Streaming failed with HTTP status ${response.status}`);
    }

    if (!response.body) {
      throw new Error("ReadableStream not supported by response body.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep partial chunk

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;

        const dataStr = trimmed.replace(/^data:\s*/, "").trim();
        if (dataStr === "[DONE]") {
          if (onDone) onDone();
          return;
        }

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.metadata && onMetadata) {
            onMetadata(parsed.metadata);
          }
          if (parsed.token && onToken) {
            onToken(parsed.token);
          }
          if (parsed.error && onError) {
            onError(new Error(parsed.error));
          }
        } catch {
          // ignore unparseable chunk
        }
      }
    }

    if (onDone) onDone();
  } catch (err) {
    console.warn("Stream error, falling back to standard chat:", err);
    try {
      const fallback = await sendChatMessage(message, history, languageCode, state, district, location);
      if (onMetadata) onMetadata(fallback);
      if (onToken) onToken(fallback.response);
      if (onDone) onDone(fallback);
    } catch (fallbackErr) {
      if (onError) onError(fallbackErr);
    }
  }
}


/**
 * Sanitizes markdown text into natural, speakable plain language.
 * @param {string} text - Raw AI response text with markdown.
 * @returns {string} Clean plain text suitable for TTS speech synthesis.
 */
export function sanitizeTextForSpeech(text) {
  if (!text) return "";

  let clean = text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^#+\s+/gm, "")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(\*|_)(.*?)\1/g, "$2")
    .replace(/^[-*•]\s+/gm, "")
    .replace(/^>\s+/gm, "")
    .replace(/`{1,3}[^`]*`{1,3}/g, "")
    .replace(/[\n\r]+/g, ". ")
    .replace(/\s+/g, " ")
    .trim();

  if (clean.length > 1000) {
    const sentences = clean.split(/(?<=[.?!])\s+/);
    let summary = "";
    for (const s of sentences) {
      if ((summary + " " + s).length > 800) break;
      summary = summary ? `${summary} ${s}` : s;
    }
    clean = summary || clean.slice(0, 800) + "...";
  }

  return clean;
}

/**
 * Converts text into speech audio via backend Sarvam TTS.
 * @param {string} text - Healthcare advice text to speak.
 * @param {string} [languageCode] - 'ta-IN', 'en-IN', 'te-IN', 'ml-IN', or null for auto detection.
 * @returns {Promise<{audio: string, language_code: string}>}
 */
export async function generateSpeech(text, languageCode = null) {
  if (!text || !text.trim()) {
    throw new Error("Text cannot be empty for speech synthesis.");
  }

  const speechText = sanitizeTextForSpeech(text);

  const payload = {
    text: speechText.slice(0, 2400),
  };
  if (languageCode) {
    payload.language_code = languageCode;
  }

  const response = await fetch(`${API_BASE_URL}/api/text-to-speech`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = "Text-to-Speech synthesis failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Triggers safe knowledge base validation and memory reload (used for testing or n8n workflow triggers).
 */
export async function refreshKnowledgeBase() {
  const response = await fetch(`${API_BASE_URL}/api/knowledge/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = "Knowledge base refresh failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Evaluates user profile against verified government health schemes.
 * @param {Object} profile - Patient health & demographic profile.
 * @returns {Promise<{status: string, total_evaluated: number, schemes: Array<Object>, disclaimer: string}>}
 */
export async function checkProfileEligibility(profile = {}) {
  const response = await fetch(`${API_BASE_URL}/api/profile/eligibility`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ profile }),
  });

  if (!response.ok) {
    let errorDetail = "Profile eligibility evaluation failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Recommends top 3 verified government schemes based on user intent, state, and optional profile.
 * @param {Object} [profile={}] - Optional patient profile.
 * @param {string} [query=""] - User natural language query or symptom.
 * @param {string} [languageCode="ta-IN"] - Selected language code.
 * @param {string} [state=null] - Selected state.
 * @param {number} [topK=3] - Number of recommendations.
 * @returns {Promise<{status: string, recommendations: Array<Object>, total_evaluated: number}>}
 */
export async function getSchemeRecommendations(profile = {}, query = "", languageCode = "ta-IN", state = null, topK = 3) {
  const response = await fetch(`${API_BASE_URL}/api/schemes/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      profile,
      query,
      language_code: languageCode || "ta-IN",
      state: state || null,
      top_k: topK
    }),
  });

  if (!response.ok) {
    let errorDetail = "Scheme recommendation failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Side-by-side comparison of 2 or more government schemes.
 * @param {string[]} schemeIds - List of scheme IDs to compare.
 * @returns {Promise<{status: string, schemes: Array<Object>, comparison_insights: string}>}
 */
export async function compareSchemes(schemeIds = []) {
  const response = await fetch(`${API_BASE_URL}/api/schemes/compare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ scheme_ids: schemeIds }),
  });

  if (!response.ok) {
    let errorDetail = "Scheme comparison failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Requests a secure password reset token for the given registered email.
 * @param {string} email
 * @returns {Promise<{status: string, message: string, reset_token: string}>}
 */
export async function requestPasswordReset(email) {
  const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    let detail = "Password reset request failed.";
    try {
      const data = await response.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return await response.json();
}

/**
 * Confirms password reset using secure token and sets a new password.
 * @param {string} token
 * @param {string} newPassword
 * @returns {Promise<{status: string, message: string}>}
 */
export async function confirmPasswordReset(token, newPassword) {
  const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });

  if (!response.ok) {
    let detail = "Password reset failed.";
    try {
      const data = await response.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return await response.json();
}

/**
 * Retrieves verified nearby healthcare facilities and government hospitals.
 * Supports location priority: Current GPS → Saved Profile Location → Manual Location.
 * @param {Object} [params]
 * @param {number} [params.latitude]
 * @param {number} [params.longitude]
 * @param {string} [params.district]
 * @param {string} [params.location]
 * @param {string} [params.city]
 * @param {string} [params.state]
 * @param {string} [params.query]
 * @param {number} [params.limit=10]
 * @returns {Promise<{status: string, total: number, user_location: Object, hospitals: Array<Object>}>}
 */
export async function getNearbyHealthcare({
  latitude,
  longitude,
  district,
  location,
  city,
  state,
  taluk,
  locality,
  pincode,
  radius_km,
  query,
  limit = 10,
} = {}) {
  const params = new URLSearchParams();
  if (latitude !== undefined && latitude !== null) params.append("latitude", latitude);
  if (longitude !== undefined && longitude !== null) params.append("longitude", longitude);
  if (district) params.append("district", district);
  if (location) params.append("location", location);
  if (city) params.append("city", city);
  if (state) params.append("state", state);
  if (taluk) params.append("taluk", taluk);
  if (locality) params.append("locality", locality);
  if (pincode) params.append("pincode", pincode);
  if (radius_km !== undefined && radius_km !== null) params.append("radius_km", radius_km);
  if (query) params.append("query", query);
  if (limit) params.append("limit", limit);

  const response = await fetch(`${API_BASE_URL}/api/healthcare/nearby?${params.toString()}`);
  if (!response.ok) {
    let detail = "Failed to fetch nearby healthcare facilities.";
    try {
      const data = await response.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return await response.json();
}

// Alias for backward compatibility
export const getNearbyHospitals = getNearbyHealthcare;

export async function geocodeLocation({ state, district, taluk, locality, pincode } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/location/geocode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state, district, taluk, locality, pincode }),
  });
  if (!response.ok) throw new Error("Geocoding failed");
  return await response.json();
}

export async function reverseGeocodeLocation({ latitude, longitude }) {
  const response = await fetch(`${API_BASE_URL}/api/location/reverse-geocode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latitude, longitude }),
  });
  if (!response.ok) throw new Error("Reverse geocoding failed");
  return await response.json();
}

export async function getLocationHierarchy() {
  const response = await fetch(`${API_BASE_URL}/api/location/hierarchy`);
  if (!response.ok) throw new Error("Failed to load location hierarchy");
  return await response.json();
}



/**
 * AI Health Image Assistant API
 * Analyzes visible skin or superficial physical concerns with medical safety guardrails.
 * @param {Object} params
 * @param {File} [params.file] - Image File object (from file input or camera capture)
 * @param {string} [params.imageBase64] - Base64 encoded image string
 * @param {string} [params.filename="captured_photo.jpg"]
 * @param {string} [params.userNotes=""] - Optional user notes or description
 * @param {string} [params.patternHint] - Optional pattern hint ('redness', 'wound', 'swelling')
 * @param {string} [params.languageCode="en-IN"]
 * @param {number} [params.latitude]
 * @param {number} [params.longitude]
 * @param {string} [params.district]
 * @param {string} [params.location]
 * @returns {Promise<Object>}
 */
export async function analyzeHealthImage({
  file,
  imageBase64,
  filename = "captured_photo.jpg",
  userNotes = "",
  patternHint,
  languageCode = "en-IN",
  latitude,
  longitude,
  district,
  location,
} = {}) {
  let response;

  if (file) {
    const formData = new FormData();
    formData.append("file", file, filename || file.name || "health_photo.jpg");
    if (userNotes) formData.append("user_notes", userNotes);
    if (patternHint) formData.append("pattern_hint", patternHint);
    if (languageCode) formData.append("language_code", languageCode);
    if (latitude !== undefined && latitude !== null) formData.append("latitude", latitude);
    if (longitude !== undefined && longitude !== null) formData.append("longitude", longitude);
    if (district) formData.append("district", district);
    if (location) formData.append("location", location);

    response = await fetch(`${API_BASE_URL}/api/image-analysis/upload`, {
      method: "POST",
      body: formData,
    });
  } else if (imageBase64) {
    const payload = {
      image_base64: imageBase64,
      filename,
      user_notes: userNotes,
      pattern_hint: patternHint,
      language_code: languageCode,
      latitude,
      longitude,
      district,
      location,
    };

    response = await fetch(`${API_BASE_URL}/api/image-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    throw new Error("Please select or capture a photo to analyze.");
  }

  if (!response.ok) {
    let errorDetail = "Visual health observation analysis failed.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}


