import { useState, useMemo } from "react";
import { t } from "../translations";
import { geocodeLocation } from "../services/aiService";

const STORAGE_KEY = "arogya_patient_profile";

const INITIAL_PROFILE = {
  name: "",
  age: "",
  gender: "",
  state: "Tamil Nadu",
  district: "Salem",
  taluk: "Salem Taluk",
  locality: "Shevapet",
  pincode: "636001",
  latitude: 11.6508,
  longitude: 78.1402,
  income_range: "< 1.2L",
  family_size: "4",
  is_pregnant: false,
  has_child: false,
  is_elderly: false,
  health_conditions: [],
  occupation: "",
};

const STATE_OPTIONS = [
  { id: "Tamil Nadu", key: "stateTamilNadu" },
  { id: "Andhra Pradesh", key: "stateAndhraPradesh" },
  { id: "Kerala", key: "stateKerala" },
  { id: "National", key: "stateAllIndia" },
];

function HealthProfile({ onProfileChange, languageCode = "en-IN", userState = "Tamil Nadu", isModal = false, onClose = null }) {
  const [profile, setProfile] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? { ...INITIAL_PROFILE, state: userState, ...JSON.parse(stored) } : { ...INITIAL_PROFILE, state: userState };
    } catch {
      return { ...INITIAL_PROFILE, state: userState };
    }
  });

  const [currentStep, setCurrentStep] = useState(1);
  const [activePreset, setActivePreset] = useState(null);
  const [savedMessage, setSavedMessage] = useState(false);

  const profileSteps = [
    { step: 1, key: "personalDetails", title: t("personalDetails", languageCode) },
    { step: 2, key: "locationDetails", title: t("locationDetails", languageCode) },
    { step: 3, key: "familyIncome", title: t("familyIncome", languageCode) },
    { step: 4, key: "healthInformation", title: t("healthInformation", languageCode) },
  ];

  const completionPercentage = useMemo(() => {
    let filled = 0;
    const totalFields = 6;
    if (profile.age) filled++;
    if (profile.gender) filled++;
    if (profile.state) filled++;
    if (profile.district) filled++;
    if (profile.income_range) filled++;
    if (profile.occupation || profile.health_conditions?.length > 0 || profile.is_pregnant || profile.has_child || profile.is_elderly) filled++;
    return Math.round((filled / totalFields) * 100);
  }, [profile]);

  const handleChange = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    setActivePreset(null);
  };

  const handleConditionToggle = (conditionId) => {
    setProfile((prev) => {
      const current = prev.health_conditions || [];
      const updated = current.includes(conditionId)
        ? current.filter((item) => item !== conditionId)
        : [...current, conditionId];
      return { ...prev, health_conditions: updated };
    });
    setActivePreset(null);
  };

  const handleSave = (event) => {
    if (event) event.preventDefault();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
      setSavedMessage(true);
      if (onProfileChange) onProfileChange(profile);
      setTimeout(() => {
        setSavedMessage(false);
        if (onClose) onClose();
      }, 1000);
    } catch (error) {
      console.warn("Could not save profile:", error);
    }
  };

  const handleClear = () => {
    localStorage.removeItem(STORAGE_KEY);
    const reset = { ...INITIAL_PROFILE, state: userState };
    setProfile(reset);
    setActivePreset(null);
    setCurrentStep(1);
    if (onProfileChange) onProfileChange(reset);
  };

  const applyPreset = (presetKey) => {
    setActivePreset(presetKey);
    let nextProfile = { ...INITIAL_PROFILE, state: userState };

    if (presetKey === "pregnancy") {
      nextProfile = {
        ...nextProfile,
        age: "24",
        gender: "female",
        state: "Tamil Nadu",
        district: "Madurai",
        taluk: "Madurai South",
        locality: "Periyar",
        pincode: "625001",
        latitude: 9.9195,
        longitude: 78.1194,
        income_range: "< 1.2L",
        family_size: "3",
        is_pregnant: true,
        occupation: "Homemaker",
      };
    } else if (presetKey === "low_income") {
      nextProfile = {
        ...nextProfile,
        age: "42",
        gender: "male",
        state: "Andhra Pradesh",
        district: "Tirupati",
        taluk: "Tirupati Urban",
        locality: "Alipiri",
        pincode: "517501",
        latitude: 13.6288,
        longitude: 79.4192,
        income_range: "< 1.2L",
        family_size: "4",
        has_child: true,
        health_conditions: ["hypertension"],
        occupation: "Agricultural Worker",
      };
    } else if (presetKey === "senior") {
      nextProfile = {
        ...nextProfile,
        age: "68",
        gender: "male",
        state: "Tamil Nadu",
        district: "Coimbatore",
        taluk: "Coimbatore North",
        locality: "RS Puram",
        pincode: "641002",
        latitude: 11.0088,
        longitude: 76.9530,
        income_range: "< 1.2L",
        family_size: "2",
        is_elderly: true,
        health_conditions: ["hypertension", "diabetes"],
        occupation: "Retired",
      };
    } else if (presetKey === "pensioner") {
      nextProfile = {
        ...nextProfile,
        age: "64",
        gender: "female",
        state: "Kerala",
        district: "Thiruvananthapuram",
        taluk: "Thiruvananthapuram Taluk",
        locality: "Palayam",
        pincode: "695034",
        latitude: 8.5061,
        longitude: 76.9555,
        income_range: "1.2L - 3.0L",
        family_size: "2",
        is_elderly: true,
        occupation: "Pensioner",
      };
    }

    setProfile(nextProfile);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextProfile));
    if (onProfileChange) onProfileChange(nextProfile);
  };

  const content = (
    <div className="health-profile-editor">
      {/* Quick Presets Bar */}
      <div className="preset-bar" style={{ marginBottom: "20px" }}>
        <span className="preset-title">{t("profileQuickPresets", languageCode)}:</span>
        <button
          type="button"
          className={`preset-pill-btn ${activePreset === "pregnancy" ? "active" : ""}`}
          onClick={() => applyPreset("pregnancy")}
        >
          {t("presetPregnancy", languageCode)}
        </button>
        <button
          type="button"
          className={`preset-pill-btn ${activePreset === "low_income" ? "active" : ""}`}
          onClick={() => applyPreset("low_income")}
        >
          {t("presetLowIncome", languageCode)}
        </button>
        <button
          type="button"
          className={`preset-pill-btn ${activePreset === "senior" ? "active" : ""}`}
          onClick={() => applyPreset("senior")}
        >
          {t("presetSeniorCitizen", languageCode)}
        </button>
        <button
          type="button"
          className={`preset-pill-btn ${activePreset === "pensioner" ? "active" : ""}`}
          onClick={() => applyPreset("pensioner")}
        >
          {t("presetPensioner", languageCode)}
        </button>
      </div>

      {/* Stepper Progress Bar */}
      <div className="stepper-progress-bar" style={{ marginBottom: "24px" }}>
        <div className="stepper-header-row">
          <span>
            {t("step", languageCode) || "Step"} {currentStep} {t("of", languageCode) || "of"} {profileSteps.length}:{" "}
            <strong>{profileSteps[currentStep - 1].title}</strong>
          </span>
          <span className="profile-completion-badge">{completionPercentage}% {t("profileCompletion", languageCode)}</span>
        </div>
        <div className="stepper-track" aria-hidden="true">
          {profileSteps.map((s) => (
            <div
              key={s.step}
              className={`stepper-segment ${s.step <= currentStep ? "active" : ""}`}
            />
          ))}
        </div>
      </div>

      {/* Form Steps */}
      <form onSubmit={handleSave}>
        {/* STEP 1: Basic Information */}
        {currentStep === 1 && (
          <div className="form-grid-2">
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-name">{t("nameLabel", languageCode)}</label>
              <input
                id="hp-name"
                type="text"
                className="form-input"
                value={profile.name || ""}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="e.g. Deepshika"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="hp-age">{t("ageLabel", languageCode)}</label>
              <input
                id="hp-age"
                type="number"
                min="0"
                max="120"
                className="form-input"
                value={profile.age || ""}
                onChange={(e) => handleChange("age", e.target.value)}
                placeholder="e.g. 24"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="hp-gender">{t("genderLabel", languageCode)}</label>
              <select
                id="hp-gender"
                className="form-select"
                value={profile.gender || ""}
                onChange={(e) => handleChange("gender", e.target.value)}
              >
                <option value="">{t("notSpecified", languageCode)}</option>
                <option value="female">{t("genderFemale", languageCode)}</option>
                <option value="male">{t("genderMale", languageCode)}</option>
                <option value="other">{t("genderOther", languageCode)}</option>
              </select>
            </div>
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-occupation">{t("occupation", languageCode)}</label>
              <input
                id="hp-occupation"
                type="text"
                className="form-input"
                value={profile.occupation || ""}
                onChange={(e) => handleChange("occupation", e.target.value)}
                placeholder="e.g. Homemaker, Teacher, Farmer"
              />
            </div>
          </div>
        )}

        {/* STEP 2: Location */}
        {currentStep === 2 && (
          <div className="form-grid-2">
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-state">{t("stateLabel", languageCode)}</label>
              <select
                id="hp-state"
                className="form-select"
                value={profile.state || "Tamil Nadu"}
                onChange={async (e) => {
                  const newState = e.target.value;
                  handleChange("state", newState);
                  try {
                    const geo = await geocodeLocation({ state: newState, district: profile.district, taluk: profile.taluk, locality: profile.locality, pincode: profile.pincode });
                    if (geo && geo.latitude) {
                      setProfile((p) => ({ ...p, state: newState, latitude: geo.latitude, longitude: geo.longitude }));
                    }
                  } catch {}
                }}
              >
                {STATE_OPTIONS.map((st) => (
                  <option key={st.id} value={st.id}>
                    {t(st.key, languageCode)}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="hp-district">{t("districtLabel", languageCode)}</label>
              <input
                id="hp-district"
                type="text"
                className="form-input"
                value={profile.district || ""}
                onChange={(e) => handleChange("district", e.target.value)}
                onBlur={async () => {
                  try {
                    const geo = await geocodeLocation({ state: profile.state, district: profile.district, taluk: profile.taluk, locality: profile.locality, pincode: profile.pincode });
                    if (geo && geo.latitude) {
                      setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
                    }
                  } catch {}
                }}
                placeholder="e.g. Salem, Chennai, Madurai"
              />
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="hp-taluk">{t("talukLabel", languageCode)}</label>
              <input
                id="hp-taluk"
                type="text"
                className="form-input"
                value={profile.taluk || ""}
                onChange={(e) => handleChange("taluk", e.target.value)}
                onBlur={async () => {
                  try {
                    const geo = await geocodeLocation({ state: profile.state, district: profile.district, taluk: profile.taluk, locality: profile.locality, pincode: profile.pincode });
                    if (geo && geo.latitude) {
                      setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
                    }
                  } catch {}
                }}
                placeholder="e.g. Salem Taluk, Omalur"
              />
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="hp-locality">{t("localityLabel", languageCode)}</label>
              <input
                id="hp-locality"
                type="text"
                className="form-input"
                value={profile.locality || ""}
                onChange={(e) => handleChange("locality", e.target.value)}
                onBlur={async () => {
                  try {
                    const geo = await geocodeLocation({ state: profile.state, district: profile.district, taluk: profile.taluk, locality: profile.locality, pincode: profile.pincode });
                    if (geo && geo.latitude) {
                      setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
                    }
                  } catch {}
                }}
                placeholder="e.g. Shevapet, Fairlands"
              />
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="hp-pincode">{t("pincodeLabel", languageCode)}</label>
              <input
                id="hp-pincode"
                type="text"
                className="form-input"
                value={profile.pincode || ""}
                onChange={(e) => handleChange("pincode", e.target.value)}
                onBlur={async () => {
                  try {
                    const geo = await geocodeLocation({ state: profile.state, district: profile.district, taluk: profile.taluk, locality: profile.locality, pincode: profile.pincode });
                    if (geo && geo.latitude) {
                      setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
                    }
                  } catch {}
                }}
                placeholder="e.g. 636001"
                maxLength={6}
              />
            </div>

            <div className="form-field col-span-2">
              <div style={{ padding: "10px 14px", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                📍 <strong>Verified Coordinates:</strong>{" "}
                {profile.latitude && profile.longitude
                  ? <span style={{ color: "var(--accent-primary)", fontWeight: 600 }}>{Number(profile.latitude).toFixed(4)}° N, {Number(profile.longitude).toFixed(4)}° E</span>
                  : "Auto-detected from administrative area"}
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Financial & Family */}
        {currentStep === 3 && (
          <div className="form-grid-2">
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-income">{t("incomeLabel", languageCode)}</label>
              <select
                id="hp-income"
                className="form-select"
                value={profile.income_range || "< 1.2L"}
                onChange={(e) => handleChange("income_range", e.target.value)}
              >
                <option value="< 1.2L">Below ₹1.2 Lakh</option>
                <option value="1.2L - 3.0L">₹1.2 Lakh - ₹3.0 Lakh</option>
                <option value="3.0L - 5.0L">₹3.0 Lakh - ₹5.0 Lakh</option>
                <option value="> 5.0L">Above ₹5.0 Lakh</option>
              </select>
            </div>
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-family-size">{t("familySizeLabel", languageCode)}</label>
              <select
                id="hp-family-size"
                className="form-select"
                value={profile.family_size || "4"}
                onChange={(e) => handleChange("family_size", e.target.value)}
              >
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6+">6+</option>
              </select>
            </div>
            <div className="form-field col-span-2" style={{ marginTop: "8px" }}>
              <span className="field-label" style={{ marginBottom: "8px", display: "block" }}>
                Special Demographic Criteria
              </span>
              <div className="checkbox-group">
                <label className="checkbox-pill-label">
                  <input
                    type="checkbox"
                    checked={Boolean(profile.is_pregnant)}
                    onChange={(e) => handleChange("is_pregnant", e.target.checked)}
                  />
                  <span>{t("pregnancy", languageCode)}</span>
                </label>
                <label className="checkbox-pill-label">
                  <input
                    type="checkbox"
                    checked={Boolean(profile.has_child)}
                    onChange={(e) => handleChange("has_child", e.target.checked)}
                  />
                  <span>{t("childInFamily", languageCode)}</span>
                </label>
                <label className="checkbox-pill-label col-span-2">
                  <input
                    type="checkbox"
                    checked={Boolean(profile.is_elderly)}
                    onChange={(e) => handleChange("is_elderly", e.target.checked)}
                  />
                  <span>{t("seniorInFamily", languageCode)}</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Health Information */}
        {currentStep === 4 && (
          <div className="form-field">
            <span className="field-label" style={{ marginBottom: "12px", display: "block" }}>
              {t("conditionsLabel", languageCode)}
            </span>
            <div className="checkbox-group">
              {[
                { id: "hypertension", labelKey: "hypertension" },
                { id: "diabetes", labelKey: "diabetes" },
                { id: "cardiac", labelKey: "cardiacCondition" },
                { id: "kidney", labelKey: "kidneyCondition" },
              ].map((cond) => (
                <label key={cond.id} className="checkbox-pill-label">
                  <input
                    type="checkbox"
                    checked={(profile.health_conditions || []).includes(cond.id)}
                    onChange={() => handleConditionToggle(cond.id)}
                  />
                  <span>{t(cond.labelKey, languageCode)}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons Row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: "28px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border-subtle)",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="header-action-btn"
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
              disabled={currentStep === 1}
              style={{ opacity: currentStep === 1 ? 0.4 : 1 }}
            >
              ← {t("back", languageCode)}
            </button>
            <button
              type="button"
              className="header-action-btn"
              onClick={handleClear}
              style={{ color: "var(--text-muted)" }}
            >
              {t("clearProfile", languageCode)}
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {savedMessage && (
              <span style={{ color: "var(--success-color)", fontSize: "0.85rem", fontWeight: 600 }}>
                ✓ {t("profileSaved", languageCode)}
              </span>
            )}
            {currentStep < profileSteps.length ? (
              <button
                type="button"
                className="btn-primary-auth"
                style={{ width: "auto", padding: "10px 20px" }}
                onClick={() => setCurrentStep((prev) => Math.min(profileSteps.length, prev + 1))}
              >
                {t("next", languageCode)} →
              </button>
            ) : (
              <button
                type="submit"
                className="btn-primary-auth"
                style={{ width: "auto", padding: "10px 24px" }}
              >
                {t("saveProfile", languageCode)}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );

  if (isModal) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3 className="modal-title">{t("healthProfile", languageCode)}</h3>
            <button type="button" className="modal-close-btn" onClick={onClose} aria-label={t("close", languageCode)}>
              ✕
            </button>
          </div>
          <div className="modal-body">{content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-summary-card" style={{ maxWidth: "800px", margin: "0 auto" }}>
      <div className="profile-card-top">
        <h2 className="section-title">{t("healthProfile", languageCode)}</h2>
        {onClose && (
          <button type="button" className="header-action-btn" onClick={onClose}>
            ✕ {t("close", languageCode)}
          </button>
        )}
      </div>
      {content}
    </div>
  );
}

export default HealthProfile;
