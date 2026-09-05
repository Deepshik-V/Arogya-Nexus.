import { useState, useRef, useEffect, useCallback } from "react";
import {
  transcribeAudio,
  streamChatMessage,
  generateSpeech,
} from "../services/aiService";


import HospitalMap from "./HospitalMap";
import { t } from "../translations";

const QUICK_PROMPT_PILLS = {
  "ta-IN": [
    { label: "காய்ச்சல் & உடல்வலி", query: "எனக்கு 2 நாட்களாக கடுமையான காய்ச்சல் மற்றும் உடல்வலி உள்ளது. என்ன முதலுதவி செய்ய வேண்டும்?" },
    { label: "இருமல் & சளி", query: "எனக்கு வறட்டு இருமல் மற்றும் தொண்டை வலி உள்ளது. பாதுகாப்பான வீட்டு வைத்தியம் என்ன?" },
    { label: "வயிற்று வலி", query: "எனக்கு கடுமையான வயிற்று வலி மற்றும் வாந்தி வருகிறது. என்ன செய்ய வேண்டும்?" },
    { label: "தலைச்சுற்றல் & மயக்கம்", query: "எனக்கு திடீரென தலைச்சுற்றல் மற்றும் சோர்வு ஏற்படுகிறது." },
    { label: "அருகிலுள்ள மருத்துவமனைகள்", query: "என் அருகில் உள்ள அவசர சிகிச்சை அரசு மருத்துவமனைகள் எவை?" },
  ],
  "te-IN": [
    { label: "జ్వరం & ఒళ్ళు నొప్పులు", query: "నాకు 2 రోజులుగా తీవ్రమైన జ్వరం మరియు ఒళ్ళు నొప్పులు ఉన్నాయి. ఏమి చేయాలి?" },
    { label: "దగ్గు & గొంతు నొప్పి", query: "నాకు పొడి దగ్గు మరియు గొంతు నొప్పి ఉంది. సురక్షిత గృహ చిట్కాలు ఏమిటి?" },
    { label: "కడుపు నొప్పి", query: "నాకు విపరీతమైన కడుపు నొప్పి మరియు వాంతులు అవుతున్నాయి. ఏమి చేయాలి?" },
    { label: "తలతిరుగుడు & అలసట", query: "నాకు తీవ్రమైన తలతిరుగుడు మరియు అలసటగా ఉంది." },
    { label: "సమీప ఆసుపత్రులు", query: "సమీపంలోని 24/7 ప్రభుత్వ ఆసుపత్రుల వివరాలు చెప్పండి." },
  ],
  "ml-IN": [
    { label: "പനിയും ശരീരവേദനയും", query: "എനിക്ക് 2 ദിവസമായി കടുത്ത പനിയും ശരീരവേദനയും ഉണ്ട്. എന്ത് ചെയ്യണം?" },
    { label: "ചുമയും തൊണ്ടവേദനയും", query: "എനിക്ക് വിട്ടുമാറാത്ത ചുമയും തൊണ്ടവേദനയും ഉണ്ട്. വീട്ടിൽ ചെയ്യാവുന്ന പരിചരണങ്ങൾ എന്തൊക്കെയാണ്?" },
    { label: "വയറുവേദന & ഛർദ്ദി", query: "എനിക്ക് കഠിനമായ വയറുവേദനയും ഛർദ്ദിയും ഉണ്ട്. എന്ത് ചെയ്യണം?" },
    { label: "തലകറക്കം & ക്ഷീണം", query: "എനിക്ക് കഠിനമായ തലകറക്കവും ക്ഷീണവും അനുഭവപ്പെടുന്നു." },
    { label: "അടുത്തുള്ള ആശുപത്രികൾ", query: "അടുത്തുള്ള 24 മണിക്കൂർ സർക്കാർ ആശുപത്രികളുടെ വിവരങ്ങൾ നൽകുക." },
  ],
  "en-IN": [
    { label: "Fever & Body Pain", query: "I have had a high fever and body pain for 2 days. What supportive home care should I follow?" },
    { label: "Cough & Sore Throat", query: "I have a persistent cough and sore throat. What safe home remedies can I follow?" },
    { label: "Stomach Pain & Nausea", query: "I have acute stomach pain and nausea. What immediate steps should I take?" },
    { label: "Dizziness & Fatigue", query: "I feel dizzy and exhausted. What could be the cause and what should I do?" },
    { label: "Find Nearby Hospitals", query: "Where are the nearest 24/7 government hospitals and emergency centres?" },
  ],
};

function createWelcomeMessage(lang) {
  let text = "Welcome to Arogya Nexus! I am your AI healthcare assistant. You can speak naturally or type your symptoms or scheme questions.";
  if (lang === "ta-IN") {
    text = "வணக்கம்! நான் ஆரோக்கிய நெக்ஸஸ் AI மருத்துவ உதவியாளர். உங்கள் உடல்நலப் பிரச்சனைகள் அல்லது அரசு மருத்துவ திட்டங்கள் குறித்து குரல் வழியாகவோ அல்லது டைப் செய்தோ கேட்கலாம்.";
  } else if (lang === "te-IN") {
    text = "నమస్కారం! నేను ఆరోగ్య నెక్సస్ AI ఆరోగ్య సహాయకుడిని. మీ ఆరోగ్య సమస్యలు లేదా ప్రభుత్వ ఆరోగ్య పథకాల గురించి మాట్లాడవచ్చు లేదా టైప్ చేయవచ్చు.";
  } else if (lang === "ml-IN") {
    text = "നമസ്കാരം! ഞാൻ ആരോഗ്യ നെക്സസ് AI ആരോഗ്യ സഹായിയാണ്. നിങ്ങളുടെ ആരോഗ്യ പ്രശ്നങ്ങളെക്കുറിച്ചോ സർക്കാർ പദ്ധതികളെക്കുറിച്ചോ സംസാരിക്കുകയോ ടൈപ്പ് ചെയ്യുകയോ ചെയ്യാം.";
  }

  return {
    id: "welcome",
    sender: "ai",
    text,
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    isEmergency: false,
    matchedTopics: ["Verified Healthcare Knowledge", "Public Health Schemes"],
    sources: [],
    audioBase64: null,
  };
}

function VoiceAssistant({
  selectedLang = "en-IN",
  userState = "Tamil Nadu",
  userProfile = null,
  userGPSCoords = null,
  onNavigateToHospitals = null,
}) {
  const [currentState, setCurrentState] = useState("Ready");
  const [errorMessage, setErrorMessage] = useState("");
  const [isEmergency, setIsEmergency] = useState(false);
  const [chatHistory, setChatHistory] = useState(() => [createWelcomeMessage(selectedLang)]);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [textInput, setTextInput] = useState("");
  const [activePlayingId, setActivePlayingId] = useState(null);

  const msgIdCounterRef = useRef(10);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const currentAudioRef = useRef(null);
  const chatScrollRef = useRef(null);

  // Audio Visualizer
  const canvasRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);

  const stopVisualizer = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        if (audioContextRef.current.state !== "closed") {
          audioContextRef.current.close();
        }
      } catch {
        // ignore
      }
      audioContextRef.current = null;
    }
    analyserRef.current = null;

    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, []);

  const stopRecordingCleanup = useCallback(() => {
    stopVisualizer();
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
  }, [stopVisualizer]);

  const stopCurrentAudio = useCallback(() => {
    if (currentAudioRef.current) {
      try {
        currentAudioRef.current.pause();
        currentAudioRef.current.currentTime = 0;
      } catch {
        // ignore
      }
      currentAudioRef.current = null;
    }
    setActivePlayingId(null);
  }, []);

  // Update chat welcome message if language changes
  const prevLangRef = useRef(selectedLang);
  useEffect(() => {
    if (prevLangRef.current !== selectedLang) {
      prevLangRef.current = selectedLang;
      setChatHistory([createWelcomeMessage(selectedLang)]);
      setCurrentState("Ready");
      setIsEmergency(false);
      setErrorMessage("");
    }
  }, [selectedLang]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCurrentAudio();
      stopRecordingCleanup();
    };
  }, [stopCurrentAudio, stopRecordingCleanup]);

  // Live Visualizer with Violet Theme
  const startLiveVisualizer = useCallback((stream) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const drawVisualizer = () => {
        if (!analyserRef.current || !canvasRef.current) return;
        animFrameRef.current = requestAnimationFrame(drawVisualizer);
        analyserRef.current.getByteFrequencyData(dataArray);

        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;
        ctx.clearRect(0, 0, width, height);

        const barWidth = (width / bufferLength) * 1.6;
        let x = 2;

        for (let i = 0; i < bufferLength; i++) {
          const barHeight = Math.max(3, (dataArray[i] / 255) * height * 0.95);
          const gradient = ctx.createLinearGradient(0, height - barHeight, 0, height);
          gradient.addColorStop(0, "#0284c7");
          gradient.addColorStop(1, "#0f766e");

          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.roundRect(x, height - barHeight, Math.max(1, barWidth - 2), barHeight, [3, 3, 0, 0]);
          ctx.fill();

          x += barWidth + 2;
        }
      };

      drawVisualizer();
    } catch (err) {
      console.warn("Live visualizer error:", err);
    }
  }, []);

  const playAudio = useCallback((base64Data, messageId = null) => {
    return new Promise((resolve) => {
      stopCurrentAudio();
      const audioSrc = base64Data.startsWith("data:")
        ? base64Data
        : `data:audio/wav;base64,${base64Data}`;

      const audio = new Audio(audioSrc);
      currentAudioRef.current = audio;
      setActivePlayingId(messageId);
      setCurrentState(t("stateSpeaking", selectedLang));

      audio.onended = () => {
        stopCurrentAudio();
        setCurrentState("Ready");
        resolve();
      };

      audio.onerror = () => {
        stopCurrentAudio();
        setCurrentState("Ready");
        resolve();
      };

      audio.play().catch(() => {
        stopCurrentAudio();
        setCurrentState("Ready");
        resolve();
      });
    });
  }, [stopCurrentAudio, selectedLang]);

  const isSubmittingRef = useRef(false);

  const executeChatStreaming = useCallback(
    async (messageText, isVoiceMode = false) => {
      if (isSubmittingRef.current) return;
      isSubmittingRef.current = true;

      setCurrentState(t("stateProcessing", selectedLang) || "Arogya Nexus is responding...");
      setErrorMessage("");

      const userMsgId = `user-msg-${Date.now()}-${msgIdCounterRef.current++}`;
      const userMsg = {
        id: userMsgId,
        sender: "user",
        text: messageText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      const aiMsgId = `ai-msg-${Date.now()}-${msgIdCounterRef.current++}`;
      const initialAiMsg = {
        id: aiMsgId,
        sender: "ai",
        text: "",
        isStreaming: true,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isEmergency: false,
        isSymptom: false,
        suggestNearbyHospitals: false,
        nearbyHospitals: [],
        nearbyUserLocation: null,
        matchedTopics: [],
        matchedSchemes: [],
        sources: [],
        knowledgeUsed: false,
        audioBase64: null,
      };

      // Atomic append: exactly one user message bubble and one streaming AI placeholder
      setChatHistory((prev) => {
        const cleaned = prev.filter((m) => !m.isStreaming || (m.text && m.text.trim()));
        return [...cleaned, userMsg, initialAiMsg];
      });

      const recentTurns = chatHistory
        .filter((m) => m.id !== "welcome" && !m.isStreaming)
        .slice(-4)
        .map((m) => ({
          role: m.sender === "user" ? "user" : "assistant",
          content: m.text,
        }));

      let accumulatedText = "";

      try {
        await streamChatMessage({
          message: messageText,
          history: recentTurns,
          languageCode: selectedLang,
          state: userState,
          district: userProfile?.district,
          location: userProfile?.location || userProfile?.district,
          lat: userGPSCoords?.latitude,
          lon: userGPSCoords?.longitude,
          onMetadata: (meta) => {

            if (meta.is_emergency) {
              setIsEmergency(true);
            }
            setChatHistory((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? {
                      ...m,
                      intent: meta.intent,
                      isEmergency: Boolean(meta.is_emergency),
                      isSymptom: Boolean(meta.is_symptom),
                      suggestNearbyHospitals: Boolean(meta.suggest_nearby_hospitals),
                      matchedTopics: meta.matched_topics || [],
                      matchedSchemes: meta.matched_schemes || [],
                      nearbyHospitals: meta.nearby_hospitals || [],
                      nearbyUserLocation: meta.user_location,
                      knowledgeUsed: Boolean(meta.knowledge_used),
                    }
                  : m
              )
            );
          },
          onToken: (token) => {
            accumulatedText += token;
            setChatHistory((prev) =>
              prev.map((m) => (m.id === aiMsgId ? { ...m, text: accumulatedText } : m))
            );
          },
          onDone: async () => {
            setChatHistory((prev) =>
              prev.map((m) => (m.id === aiMsgId ? { ...m, isStreaming: false } : m))
            );

            // Synthesize voice audio ONLY if user spoke via microphone
            if (isVoiceMode && accumulatedText.trim()) {
              try {
                setCurrentState(t("stateSpeaking", selectedLang));
                const ttsResult = await generateSpeech(accumulatedText, selectedLang);
                if (ttsResult?.audio) {
                  setChatHistory((prev) =>
                    prev.map((m) => (m.id === aiMsgId ? { ...m, audioBase64: ttsResult.audio } : m))
                  );
                  await playAudio(ttsResult.audio, aiMsgId);
                } else {
                  setCurrentState("Ready");
                }
              } catch {
                setCurrentState("Ready");
              }
            } else {
              setCurrentState("Ready");
            }
            isSubmittingRef.current = false;
          },
          onError: (err) => {
            console.error("Chat streaming error:", err);
            setChatHistory((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? {
                      ...m,
                      isStreaming: false,
                      text: m.text || "Sorry, I couldn't complete that request. Please try again.",
                    }
                  : m
              )
            );
            setCurrentState("Ready");
            isSubmittingRef.current = false;
          },
        });
      } catch (err) {
        console.error("Execute chat error:", err);
        setErrorMessage(err.message || "Failed to generate healthcare guidance.");
        setCurrentState("Ready");
        isSubmittingRef.current = false;
      }
    },
    [chatHistory, playAudio, selectedLang, userState, userProfile, userGPSCoords]
  );


  const processVoiceInput = useCallback(
    async (audioBlob) => {
      try {
        setCurrentState(t("stateProcessing", selectedLang));
        setErrorMessage("");

        const sttResult = await transcribeAudio(audioBlob, selectedLang || "unknown");
        const userText = sttResult.transcript;

        if (!userText || !userText.trim()) {
          throw new Error("No clear speech detected. Please speak into the microphone.");
        }

        await executeChatStreaming(userText, true);
      } catch (err) {
        console.error("Voice input error:", err);
        setErrorMessage(err.message || "Could not transcribe audio.");
        setCurrentState("Ready");
      }
    },
    [executeChatStreaming, selectedLang]
  );

  const handleStartListening = async () => {
    stopCurrentAudio();
    setErrorMessage("");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone is not supported in this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });

      startLiveVisualizer(stream);
      audioChunksRef.current = [];

      let mimeType = "";
      const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/wav"];
      for (const candidate of candidates) {
        if (MediaRecorder.isTypeSupported(candidate)) {
          mimeType = candidate;
          break;
        }
      }

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stopVisualizer();
        stream.getTracks().forEach((track) => track.stop());

        if (recordingTimerRef.current) {
          clearInterval(recordingTimerRef.current);
          recordingTimerRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || "audio/webm" });
        if (audioBlob.size > 0) {
          await processVoiceInput(audioBlob);
        } else {
          setCurrentState("Ready");
          setErrorMessage(t("noSpeechDetected", selectedLang) || "No speech detected. Please speak into the microphone.");
        }
      };

      recorder.start(250);
      setCurrentState(t("stateListening", selectedLang));
      setRecordingDuration(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => {
          if (prev >= 45) {
            handleStopListening();
            return 45;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      console.error("Microphone error:", err);
      setErrorMessage(err.message || "Microphone access denied.");
      setCurrentState("Ready");
    }
  };

  const handleStopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    stopRecordingCleanup();
  };

  const handleSendText = (e) => {
    if (e) e.preventDefault();
    if (!textInput || !textInput.trim() || isSubmittingRef.current) return;

    stopCurrentAudio();
    const query = textInput.trim();
    setTextInput("");
    executeChatStreaming(query, false);
  };

  const handlePromptClick = (query) => {
    if (isSubmittingRef.current) return;
    stopCurrentAudio();
    executeChatStreaming(query, false);
  };


  const handleReplayAudio = async (msg) => {
    if (activePlayingId === msg.id) {
      stopCurrentAudio();
      setCurrentState("Ready");
      return;
    }
    if (msg.audioBase64) {
      await playAudio(msg.audioBase64, msg.id);
    } else {
      try {
        setCurrentState(t("stateSpeaking", selectedLang));
        const res = await generateSpeech(msg.text, selectedLang);
        if (res.audio) {
          setChatHistory((prev) =>
            prev.map((m) => (m.id === msg.id ? { ...m, audioBase64: res.audio } : m))
          );
          await playAudio(res.audio, msg.id);
        }
      } catch {
        setCurrentState("Ready");
      }
    }
  };

  const isListening = currentState.toLowerCase().includes("listen");
  const isBusy = currentState !== "Ready" && !isListening;
  const quickPills = QUICK_PROMPT_PILLS[selectedLang] || QUICK_PROMPT_PILLS["en-IN"];

  return (
    <div className="voice-assistant-card">
      {/* Emergency Red-Flag Alert */}
      {isEmergency && (
        <div className="auth-error-banner" style={{ borderColor: "var(--emergency-color)", color: "#fca5a5" }}>
          <span>🚨</span>
          <div>
            <strong>{t("emergencyAlertTitle", selectedLang)}</strong> — {t("emergencyAlertDesc", selectedLang)}
          </div>
        </div>
      )}

      {/* Voice Assistant Header */}
      <div className="voice-card-header">
        <div className="voice-title-box">
          <h2 className="voice-title">
            <span>🎙️</span>
            {t("voiceFirstTitle", selectedLang)}
          </h2>
          <span className="hero-tagline" style={{ fontSize: "0.85rem" }}>
            {t("voiceFirstDesc", selectedLang)}
          </span>
        </div>

        <div className={`voice-status-pill ${isListening ? "listening" : ""}`}>
          <span className="status-indicator-dot" />
          <span>{currentState}</span>
          {isListening && <span>({recordingDuration}s)</span>}
        </div>
      </div>

      {/* Controls & Waveform */}
      <div className="voice-controls-row">
        <button
          type="button"
          className={`mic-action-btn ${isListening ? "active" : ""}`}
          onClick={isListening ? handleStopListening : handleStartListening}
          disabled={isBusy}
          aria-label={isListening ? t("stopRecording", selectedLang) : t("startRecording", selectedLang)}
        >
          {isListening ? (
            <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          )}
        </button>

        <canvas
          ref={canvasRef}
          width={140}
          height={42}
          className="visualizer-canvas"
          aria-label="Audio waveform visualizer"
        />

        <div className="voice-helper-copy">
          <strong>{t("howCanIHelp", selectedLang)}</strong>
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            {isListening ? t("stateListening", selectedLang) : t("startRecording", selectedLang)}
          </div>
        </div>
      </div>

      {/* Quick Prompts Bar */}
      <div className="quick-prompt-chips">
        {quickPills.map((pill, idx) => (
          <button
            key={idx}
            type="button"
            className="prompt-chip-btn"
            onClick={() => handlePromptClick(pill.query)}
            disabled={isBusy || isListening}
          >
            {pill.label}
          </button>
        ))}
      </div>

      {/* Error Notice */}
      {errorMessage && (
        <div className="auth-error-banner">
          <span>⚠️</span>
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Chat Messages */}
      <div className="voice-chat-history" ref={chatScrollRef}>
        {chatHistory.map((msg) => (
          <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
            <div className="bubble-meta">
              <span>{msg.sender === "ai" ? "🤖 Arogya Nexus" : `👤 ${t("you", selectedLang)}`}</span>
              <span>{msg.timestamp}</span>
            </div>
            {msg.isStreaming && !msg.text ? (
              <div className="streaming-state-row" style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0", color: "#c4b5fd" }}>
                <span className="spinner-dot" />
                <span style={{ fontSize: "0.88rem", fontWeight: 500 }}>
                  {t("stateProcessing", selectedLang) || "Arogya Nexus is responding..."}
                </span>
              </div>
            ) : (
              <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
            )}


            {msg.sender === "ai" && (
              <>
                {/* Hospital map and cards: ONLY when intent is NEARBY_HOSPITAL, NEARBY_HEALTHCARE or EMERGENCY */}
                {(msg.intent === "NEARBY_HOSPITAL" || msg.intent === "NEARBY_HEALTHCARE" || msg.isEmergency) && (
                  <>
                    {msg.nearbyHospitals && msg.nearbyHospitals.length > 0 && (
                      <div className="chat-nearby-hospitals-section">
                        <div className="chat-hospitals-header">
                          <span className="chat-hospitals-title">
                            📍 {t("nearbyHospitalsTitle", selectedLang)} ({msg.nearbyUserLocation?.label || "Your Area"})
                          </span>
                          {onNavigateToHospitals && (
                            <button
                              type="button"
                              className="chat-hospitals-expand-btn"
                              onClick={() => onNavigateToHospitals(userProfile?.district || "Salem")}
                            >
                              {t("fullDirectory", selectedLang)} →
                            </button>
                          )}
                        </div>

                        <HospitalMap
                          hospitals={msg.nearbyHospitals}
                          userLocation={msg.nearbyUserLocation}
                          height="220px"
                          languageCode={selectedLang}
                        />

                        <div className="chat-hospitals-cards-list">
                          {msg.nearbyHospitals.map((hosp) => (
                            <div key={hosp.id} className="chat-hospital-compact-card">
                              <div className="chat-hosp-top">
                                <span className="chat-hosp-name">{hosp.name}</span>
                                {hosp.distance_label && (
                                  <span className="badge-distance">{hosp.distance_label}</span>
                                )}
                              </div>
                              <p className="chat-hosp-address">{hosp.address}</p>
                              <div className="chat-hosp-actions">
                                <a
                                  href={hosp.maps_url || hosp.directions_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn-hospital-directions"
                                >
                                  🗺️ {t("getDirections", selectedLang) || "Directions"}
                                </a>
                                {hosp.phone && (
                                  <a href={`tel:${hosp.phone}`} className="btn-hospital-call">
                                    📞 {t("callHospital", selectedLang) || "Call"}
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Symptom Follow-Up: Direct button to navigate to Nearby Hospitals */}
                {msg.isSymptom && !(msg.intent === "NEARBY_HOSPITAL" || msg.intent === "NEARBY_HEALTHCARE" || msg.isEmergency) && (
                  <div style={{ marginTop: "12px", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                    {onNavigateToHospitals && (
                      <button
                        type="button"
                        className="btn-hospital-symptom-action"
                        onClick={() => onNavigateToHospitals(userProfile?.district || "Salem")}
                      >
                        🏥 {t("nearbyHospitalsTitle", selectedLang)} ({userProfile?.district || "Salem"}) →
                      </button>
                    )}
                  </div>
                )}

                {/* Emergency Banner when severe condition or red flag is indicated */}
                {msg.isEmergency && (
                  <div className="chat-emergency-banner" style={{ marginTop: "10px", padding: "10px 14px", background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                    <span style={{ fontSize: "0.86rem", color: "#dc2626", fontWeight: 600 }}>
                      🚨 {t("emergencyAlertTitle", selectedLang) || "Medical Emergency"}: Immediate emergency care recommended.
                    </span>
                    <a href="tel:108" className="btn-call-108" style={{ background: "#dc2626", color: "#fff", padding: "6px 14px", borderRadius: "999px", fontSize: "0.82rem", fontWeight: 700, textDecoration: "none" }}>
                      📞 {t("emergencyCall108", selectedLang) || "Call 108"}
                    </a>
                  </div>
                )}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "6px" }}>
                  {msg.matchedTopics && msg.matchedTopics.length > 0 ? (
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      ✓ {msg.matchedTopics[0]}
                    </span>
                  ) : <span />}

                  <button
                    type="button"
                    className="audio-play-btn"
                    onClick={() => handleReplayAudio(msg)}
                  >
                    {activePlayingId === msg.id ? `⏹ ${t("stopAudio", selectedLang)}` : `🔊 ${t("listenAudio", selectedLang)}`}
                  </button>
                </div>
              </>
            )}
          </div>
        ))}


      </div>

      {/* Text Input Row */}
      <form className="voice-input-row" onSubmit={handleSendText}>
        <input
          type="text"
          className="voice-text-input"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder={t("inputPlaceholder", selectedLang)}
          disabled={isBusy || isListening}
        />
        <button
          type="submit"
          className="voice-send-btn"
          disabled={!textInput.trim() || isBusy || isListening}
        >
          {t("send", selectedLang)}
        </button>
      </form>
    </div>
  );
}

export default VoiceAssistant;