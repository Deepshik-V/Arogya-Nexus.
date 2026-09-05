import { useState, useRef } from "react";
import { analyzeHealthImage } from "../services/aiService";
import { t } from "../translations";

// Inline SVG Icons
const CameraIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
    <circle cx="12" cy="13" r="4" />
  </svg>
);

const GalleryIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

const AlertTriangleIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

const ShieldCheckIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);

const EyeIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const InfoIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="16" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12.01" y2="8" />
  </svg>
);

const HeartHandshakeIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
  </svg>
);

const MapPinIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

export default function ImageAssistant({
  currentLang = "ta-IN",
  userProfile = null,
  onNavigateToHospitals = null,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [userNotes, setUserNotes] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      processFile(file);
    }
  };

  const processFile = (file) => {
    if (!file) return;
    if (!file.type || !file.type.startsWith("image/")) {
      setAnalysisError("Invalid file type. Please upload or capture an image (JPEG, PNG, WebP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setAnalysisError("Image file size exceeds 10MB. Please select a smaller photo or compress it.");
      return;
    }

    setSelectedFile(file);
    setAnalysisResult(null);
    setAnalysisError(null);

    const reader = new FileReader();
    reader.onload = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUserNotes("");
    setAnalysisResult(null);
    setAnalysisError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setAnalysisError(t("uploadOrCapture", currentLang));
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const res = await analyzeHealthImage({
        file: selectedFile,
        userNotes: userNotes.trim(),
        languageCode: currentLang,
        latitude: userProfile?.latitude,
        longitude: userProfile?.longitude,
        district: userProfile?.district,
        location: userProfile?.location || userProfile?.district,
      });

      if (res.status === "error") {
        setAnalysisError(res.message || "Could not analyze image. Please try again with a clearer photo in good lighting.");
        setAnalysisResult(null);
      } else {
        setAnalysisResult(res);
      }
    } catch (err) {
      setAnalysisError(err.message || "Failed to analyze image. Please check your network and try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="image-assistant-container">
      {/* 1. Header Banner */}
      <div className="image-header-banner">
        <div className="image-header-content">
          <div className="image-badge-tag">
            <EyeIcon />
            <span>{t("imageNav", currentLang)}</span>
          </div>
          <h1 className="image-title">{t("imageAssistantTitle", currentLang)}</h1>
          <p className="image-subtitle">{t("imageAssistantSubtitle", currentLang)}</p>
        </div>

        <div className="image-disclaimer-pill">
          <ShieldCheckIcon />
          <span>{t("imageDisclaimer", currentLang)}</span>
        </div>
      </div>

      {/* 2. Upload / Capture Box */}
      <div className="image-workspace-card">
        {/* Hidden inputs — triggered only by bespoke buttons */}
        <input
          type="file"
          ref={fileInputRef}
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <input
          type="file"
          ref={cameraInputRef}
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />

        {!previewUrl ? (
          <div className="image-upload-dropzone">
            <div className="image-upload-icon-circle">
              <CameraIcon />
            </div>

            <div className="image-upload-copy">
              <h3>{t("uploadOrCapture", currentLang)}</h3>
              <p>{t("uploadOrCaptureDesc", currentLang)}</p>
            </div>

            <div className="image-buttons-row">
              <button
                type="button"
                className="btn-take-photo"
                onClick={() => cameraInputRef.current && cameraInputRef.current.click()}
              >
                <CameraIcon />
                <span>{t("takePhoto", currentLang)}</span>
              </button>

              <button
                type="button"
                className="btn-browse-gallery"
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
              >
                <GalleryIcon />
                <span>{t("uploadGallery", currentLang)}</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="image-preview-wrapper">
            <div className="image-preview-card">
              <img src={previewUrl} alt="Health concern preview" className="image-preview-img" />
              <div className="image-preview-overlay">
                <span className="image-file-meta">
                  📸 {selectedFile?.name || "photo.jpg"} ({Math.round((selectedFile?.size || 0) / 1024)} KB)
                </span>
                <button
                  type="button"
                  className="btn-remove-photo"
                  onClick={handleReset}
                  title="Remove photo"
                >
                  ✕ {t("changePhoto", currentLang)}
                </button>
              </div>
            </div>

            {/* Optional Notes Input */}
            <div className="image-notes-field">
              <label className="field-label" htmlFor="image-notes-input">
                {t("describeConcern", currentLang)} ({t("optional", currentLang)})
              </label>
              <input
                id="image-notes-input"
                type="text"
                value={userNotes}
                onChange={(e) => setUserNotes(e.target.value)}
                placeholder="e.g. Mild redness on forearm, itching for 2 days"
                className="field-input image-notes-input"
              />
            </div>

            {/* Action Buttons */}
            <div className="image-action-buttons">
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                className="btn-analyze-health"
              >
                {isAnalyzing ? (
                  <>
                    <span className="spinner-dot" />
                    <span>{t("analyzingImageState", currentLang)}</span>
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    <span>{t("analyzeImageBtn", currentLang)}</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleReset}
                disabled={isAnalyzing}
                className="btn-reset-photo"
              >
                {t("reset", currentLang)}
              </button>
            </div>
          </div>
        )}

        {/* Error Notice */}
        {analysisError && (
          <div className="image-error-notice">
            <AlertTriangleIcon />
            <div>
              <strong>{t("observationNotice", currentLang)}:</strong>
              <div>{analysisError}</div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Structured Observation Results */}
      {analysisResult && (
        <div className="image-result-section">
          <div className="image-result-card">
            <div className="image-result-top">
              <div>
                <span className="image-result-category-badge">
                  Pattern: {analysisResult.pattern_category?.replace("_", " ")}
                </span>
                <h2 className="image-result-title">{analysisResult.title}</h2>
              </div>
              <div className="image-safety-stamp">
                <ShieldCheckIcon />
                <span>{t("verifiedGuidelines", currentLang)}</span>
              </div>
            </div>

            {/* Medical Safety Disclaimer Banner */}
            <div className="image-safety-disclaimer-banner">
              <AlertTriangleIcon />
              <span>{analysisResult.disclaimer}</span>
            </div>

            <div className="image-details-grid">
              {/* Visible Observation */}
              <div className="image-detail-block">
                <div className="image-detail-header">
                  <EyeIcon />
                  <span>{t("visibleObservation", currentLang)}</span>
                </div>
                <p className="image-detail-body">{analysisResult.visible_observation}</p>
              </div>

              {/* Possible Causes (Not a diagnosis) */}
              <div className="image-detail-block">
                <div className="image-detail-header">
                  <InfoIcon />
                  <span>{t("possibleExplanations", currentLang)}</span>
                </div>
                <p className="image-detail-body">{analysisResult.possible_causes}</p>
              </div>
            </div>

            {/* Safe Immediate Care */}
            {analysisResult.safe_immediate_care && analysisResult.safe_immediate_care.length > 0 && (
              <div className="image-care-section safe">
                <div className="image-care-header green">
                  <CheckCircleIcon />
                  <span>{t("safeCare", currentLang)}</span>
                </div>
                <ul className="image-care-list">
                  {analysisResult.safe_immediate_care.map((item, idx) => (
                    <li key={idx}>
                      <span className="bullet-dot green" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warning Signs */}
            {analysisResult.warning_signs && analysisResult.warning_signs.length > 0 && (
              <div className="image-care-section warning">
                <div className="image-care-header amber">
                  <AlertTriangleIcon />
                  <span>{t("warningSigns", currentLang)}</span>
                </div>
                <ul className="image-care-list">
                  {analysisResult.warning_signs.map((sign, idx) => (
                    <li key={idx}>
                      <span className="bullet-dot amber" />
                      <span>{sign}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* When to visit PHC */}
            {analysisResult.when_to_seek_care && analysisResult.when_to_seek_care.length > 0 && (
              <div className="image-care-section phc">
                <div className="image-care-header violet">
                  <HeartHandshakeIcon />
                  <span>{t("whenToVisitPHC", currentLang)}</span>
                </div>
                <div className="image-phc-content">
                  {analysisResult.when_to_seek_care.map((when, idx) => (
                    <p key={idx}>{when}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Official Source */}
            <div className="image-result-footer">
              <span>Verified Source: {analysisResult.official_source}</span>
              {analysisResult.official_url && (
                <a
                  href={analysisResult.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="image-source-link"
                >
                  Official Health Guidelines ↗
                </a>
              )}
            </div>
          </div>

          {/* Nearby Healthcare Facilities */}
          {analysisResult.nearby_healthcare && analysisResult.nearby_healthcare.length > 0 && (
            <div className="image-hospitals-section">
              <div className="image-hospitals-header">
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <MapPinIcon />
                  <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    Nearby Healthcare Facilities ({analysisResult.user_location?.label || "Your Area"})
                  </h3>
                </div>
                {onNavigateToHospitals && (
                  <button
                    type="button"
                    className="btn-view-details"
                    onClick={onNavigateToHospitals}
                  >
                    View All on Map →
                  </button>
                )}
              </div>

              <div className="image-hospitals-grid">
                {analysisResult.nearby_healthcare.slice(0, 3).map((hosp) => (
                  <div key={hosp.id} className="image-hospital-card">
                    <div className="hospital-header">
                      <span className="badge-state">{hosp.type || "Government PHC"}</span>
                      {hosp.distance_label && (
                        <span className="badge-distance">{hosp.distance_label}</span>
                      )}
                    </div>
                    <h4 className="hospital-name" style={{ fontSize: "0.95rem" }}>{hosp.name}</h4>
                    <p className="hospital-address" style={{ fontSize: "0.82rem" }}>{hosp.address}</p>
                    <div className="hospital-card-actions">
                      <a
                        href={hosp.maps_url || hosp.directions_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-hospital-directions"
                      >
                        🗺️ Directions
                      </a>
                      {hosp.phone && (
                        <a href={`tel:${hosp.phone}`} className="btn-hospital-call">
                          📞 Call
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
