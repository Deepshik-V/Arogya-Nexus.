import { useState, useMemo, useEffect } from "react";
import { t } from "../translations";
import { geocodeLocation, getLocationHierarchy } from "../services/aiService";
import { STATIC_HIERARCHY } from "./LocationPermissionCard";

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
  annual_income: 100000,
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
  { id: "Karnataka", key: "stateKarnataka", fallback: "Karnataka" },
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
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [customLocationMode, setCustomLocationMode] = useState(false);
  const [hierarchy, setHierarchy] = useState(STATIC_HIERARCHY);

  useEffect(() => {
    getLocationHierarchy()
      .then((data) => {
        if (data && typeof data === "object" && Object.keys(data).length > 0) {
          setHierarchy((prev) => ({ ...prev, ...data }));
        }
      })
      .catch(() => {});
  }, []);

  const profileSteps = [
    { step: 1, key: "personalDetails", title: t("personalDetails", languageCode) || "Personal Details" },
    { step: 2, key: "locationDetails", title: t("locationDetails", languageCode) || "Location Hierarchy" },
    { step: 3, key: "familyIncome", title: t("familyIncome", languageCode) || "Financial & Family" },
    { step: 4, key: "healthInformation", title: t("healthInformation", languageCode) || "Clinical History" },
  ];

  const availableDistricts = useMemo(() => {
    const st = profile.state || "Tamil Nadu";
    return Object.keys(hierarchy[st] || {});
  }, [hierarchy, profile.state]);

  const availableTaluks = useMemo(() => {
    const st = profile.state || "Tamil Nadu";
    const dist = profile.district || "";
    return Object.keys((hierarchy[st] || {})[dist] || {});
  }, [hierarchy, profile.state, profile.district]);

  const availableLocalities = useMemo(() => {
    const st = profile.state || "Tamil Nadu";
    const dist = profile.district || "";
    const taluk = profile.taluk || "";
    return ((hierarchy[st] || {})[dist] || {})[taluk] || [];
  }, [hierarchy, profile.state, profile.district, profile.taluk]);

  const completionPercentage = useMemo(() => {
    let filled = 0;
    const totalFields = 6;
    if (profile.age) filled++;
    if (profile.gender) filled++;
    if (profile.state) filled++;
    if (profile.district) filled++;
    if (profile.income_range || profile.annual_income) filled++;
    if (profile.occupation || profile.health_conditions?.length > 0 || profile.is_pregnant || profile.has_child || profile.is_elderly) filled++;
    return Math.round((filled / totalFields) * 100);
  }, [profile]);

  const handleChange = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    setActivePreset(null);
  };

  const handleStateSelect = async (newState) => {
    const newDistricts = Object.keys(hierarchy[newState] || {});
    const defaultDist = newDistricts[0] || "";
    const newTaluks = Object.keys((hierarchy[newState] || {})[defaultDist] || {});
    const defaultTaluk = newTaluks[0] || "";
    const newLocs = ((hierarchy[newState] || {})[defaultDist] || {})[defaultTaluk] || [];
    const defaultLoc = newLocs[0] || "";

    const updated = {
      ...profile,
      state: newState,
      district: defaultDist,
      taluk: defaultTaluk,
      locality: defaultLoc,
    };
    setProfile(updated);
    setActivePreset(null);

    setIsGeocoding(true);
    try {
      const geo = await geocodeLocation({ state: newState, district: defaultDist, taluk: defaultTaluk, locality: defaultLoc });
      if (geo && geo.latitude) {
        setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
      }
    } catch {} finally {
      setIsGeocoding(false);
    }
  };

  const handleDistrictSelect = async (newDist) => {
    const st = profile.state || "Tamil Nadu";
    const newTaluks = Object.keys((hierarchy[st] || {})[newDist] || {});
    const defaultTaluk = newTaluks[0] || "";
    const newLocs = ((hierarchy[st] || {})[newDist] || {})[defaultTaluk] || [];
    const defaultLoc = newLocs[0] || "";

    const updated = {
      ...profile,
      district: newDist,
      taluk: defaultTaluk,
      locality: defaultLoc,
    };
    setProfile(updated);
    setActivePreset(null);

    setIsGeocoding(true);
    try {
      const geo = await geocodeLocation({ state: st, district: newDist, taluk: defaultTaluk, locality: defaultLoc });
      if (geo && geo.latitude) {
        setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
      }
    } catch {} finally {
      setIsGeocoding(false);
    }
  };

  const handleTalukSelect = async (newTaluk) => {
    const st = profile.state || "Tamil Nadu";
    const dist = profile.district || "";
    const newLocs = ((hierarchy[st] || {})[dist] || {})[newTaluk] || [];
    const defaultLoc = newLocs[0] || "";

    const updated = {
      ...profile,
      taluk: newTaluk,
      locality: defaultLoc,
    };
    setProfile(updated);
    setActivePreset(null);

    setIsGeocoding(true);
    try {
      const geo = await geocodeLocation({ state: st, district: dist, taluk: newTaluk, locality: defaultLoc });
      if (geo && geo.latitude) {
        setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
      }
    } catch {} finally {
      setIsGeocoding(false);
    }
  };

  const handleLocalitySelect = async (newLoc) => {
    const updated = { ...profile, locality: newLoc };
    setProfile(updated);
    setActivePreset(null);

    setIsGeocoding(true);
    try {
      const geo = await geocodeLocation({
        state: profile.state,
        district: profile.district,
        taluk: profile.taluk,
        locality: newLoc,
        pincode: profile.pincode,
      });
      if (geo && geo.latitude) {
        setProfile((p) => ({ ...p, latitude: geo.latitude, longitude: geo.longitude }));
      }
    } catch {} finally {
      setIsGeocoding(false);
    }
  };

  const handleAnnualIncomeChange = (rawVal) => {
    const num = rawVal === "" ? "" : Number(rawVal);
    let bracket = "< 1.2L";
    if (num > 500000) bracket = "> 5.0L";
    else if (num > 300000) bracket = "3.0L - 5.0L";
    else if (num > 120000) bracket = "1.2L - 3.0L";

    setProfile((prev) => ({
      ...prev,
      annual_income: num,
      income_range: bracket,
    }));
    setActivePreset(null);
  };

  const handleIncomeRangeSelect = (bracket) => {
    let impliedNum = 100000;
    if (bracket === "1.2L - 3.0L") impliedNum = 200000;
    else if (bracket === "3.0L - 5.0L") impliedNum = 400000;
    else if (bracket === "> 5.0L") impliedNum = 600000;

    setProfile((prev) => ({
      ...prev,
      income_range: bracket,
      annual_income: impliedNum,
    }));
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
      }, 900);
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
        annual_income: 96000,
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
        annual_income: 84000,
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
        annual_income: 72000,
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
        annual_income: 180000,
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
              <label className="field-label" htmlFor="hp-name">{t("nameLabel", languageCode) || "Full Name"}</label>
              <input
                id="hp-name"
                type="text"
                className="form-input"
                value={profile.name || ""}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="e.g. Citizen Name"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="hp-age">{t("ageLabel", languageCode) || "Age"}</label>
              <input
                id="hp-age"
                type="number"
                min="0"
                max="120"
                className="form-input"
                value={profile.age || ""}
                onChange={(e) => handleChange("age", e.target.value)}
                placeholder="e.g. 28"
              />
            </div>
            <div className="form-field">
              <label className="field-label" htmlFor="hp-gender">{t("genderLabel", languageCode) || "Gender"}</label>
              <select
                id="hp-gender"
                className="form-select"
                value={profile.gender || ""}
                onChange={(e) => handleChange("gender", e.target.value)}
              >
                <option value="">{t("notSpecified", languageCode) || "Not Specified"}</option>
                <option value="female">{t("genderFemale", languageCode) || "Female"}</option>
                <option value="male">{t("genderMale", languageCode) || "Male"}</option>
                <option value="other">{t("genderOther", languageCode) || "Other"}</option>
              </select>
            </div>
            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-occupation">{t("occupation", languageCode) || "Occupation"}</label>
              <input
                id="hp-occupation"
                type="text"
                className="form-input"
                value={profile.occupation || ""}
                onChange={(e) => handleChange("occupation", e.target.value)}
                placeholder="e.g. Homemaker, Teacher, Farmer, Self-employed"
              />
            </div>
          </div>
        )}

        {/* STEP 2: Administrative Location Hierarchy */}
        {currentStep === 2 && (
          <div className="form-grid-2">
            <div className="form-field col-span-2">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label className="field-label" htmlFor="hp-state" style={{ margin: 0 }}>
                  {t("stateLabel", languageCode) || "State / Jurisdiction"}
                </label>
                <button
                  type="button"
                  style={{ background: "none", border: "none", color: "var(--accent-primary)", fontSize: "0.8rem", cursor: "pointer", textDecoration: "underline" }}
                  onClick={() => setCustomLocationMode(!customLocationMode)}
                >
                  {customLocationMode ? "Use Dropdowns" : "Enter Custom Area"}
                </button>
              </div>
              <select
                id="hp-state"
                className="form-select"
                value={profile.state || "Tamil Nadu"}
                onChange={(e) => handleStateSelect(e.target.value)}
              >
                {STATE_OPTIONS.map((st) => (
                  <option key={st.id} value={st.id}>
                    {t(st.key, languageCode) || st.fallback || st.id}
                  </option>
                ))}
              </select>
            </div>

            {!customLocationMode ? (
              <>
                <div className="form-field">
                  <label className="field-label" htmlFor="hp-district-select">
                    {t("districtLabel", languageCode) || "District"}
                  </label>
                  <select
                    id="hp-district-select"
                    className="form-select"
                    value={profile.district || (availableDistricts[0] || "")}
                    onChange={(e) => handleDistrictSelect(e.target.value)}
                  >
                    {availableDistricts.length > 0 ? (
                      availableDistricts.map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))
                    ) : (
                      <option value={profile.district || ""}>{profile.district || "Select District"}</option>
                    )}
                  </select>
                </div>

                <div className="form-field">
                  <label className="field-label" htmlFor="hp-taluk-select">
                    {t("talukLabel", languageCode) || "Taluk / Tehsil / Mandal"}
                  </label>
                  <select
                    id="hp-taluk-select"
                    className="form-select"
                    value={profile.taluk || (availableTaluks[0] || "")}
                    onChange={(e) => handleTalukSelect(e.target.value)}
                  >
                    {availableTaluks.length > 0 ? (
                      availableTaluks.map((tk) => (
                        <option key={tk} value={tk}>{tk}</option>
                      ))
                    ) : (
                      <option value={profile.taluk || ""}>{profile.taluk || "General Taluk"}</option>
                    )}
                  </select>
                </div>

                <div className="form-field">
                  <label className="field-label" htmlFor="hp-locality-select">
                    {t("localityLabel", languageCode) || "Locality / Town / Village"}
                  </label>
                  <select
                    id="hp-locality-select"
                    className="form-select"
                    value={profile.locality || (availableLocalities[0] || "")}
                    onChange={(e) => handleLocalitySelect(e.target.value)}
                  >
                    {availableLocalities.length > 0 ? (
                      availableLocalities.map((loc) => (
                        <option key={loc} value={loc}>{loc}</option>
                      ))
                    ) : (
                      <option value={profile.locality || ""}>{profile.locality || "Central Town"}</option>
                    )}
                  </select>
                </div>
              </>
            ) : (
              <>
                <div className="form-field">
                  <label className="field-label" htmlFor="hp-district-input">
                    {t("districtLabel", languageCode) || "District"}
                  </label>
                  <input
                    id="hp-district-input"
                    type="text"
                    className="form-input"
                    value={profile.district || ""}
                    onChange={(e) => handleChange("district", e.target.value)}
                    placeholder="e.g. Salem, Chennai"
                  />
                </div>

                <div className="form-field">
                  <label className="field-label" htmlFor="hp-taluk-input">
                    {t("talukLabel", languageCode) || "Taluk / Mandal"}
                  </label>
                  <input
                    id="hp-taluk-input"
                    type="text"
                    className="form-input"
                    value={profile.taluk || ""}
                    onChange={(e) => handleChange("taluk", e.target.value)}
                    placeholder="e.g. Salem Taluk"
                  />
                </div>

                <div className="form-field">
                  <label className="field-label" htmlFor="hp-locality-input">
                    {t("localityLabel", languageCode) || "Locality"}
                  </label>
                  <input
                    id="hp-locality-input"
                    type="text"
                    className="form-input"
                    value={profile.locality || ""}
                    onChange={(e) => handleChange("locality", e.target.value)}
                    placeholder="e.g. Shevapet"
                  />
                </div>
              </>
            )}

            <div className="form-field">
              <label className="field-label" htmlFor="hp-pincode">{t("pincodeLabel", languageCode) || "Pincode"}</label>
              <input
                id="hp-pincode"
                type="text"
                className="form-input"
                value={profile.pincode || ""}
                onChange={(e) => handleChange("pincode", e.target.value)}
                placeholder="e.g. 636001"
                maxLength={6}
              />
            </div>

            <div className="form-field col-span-2">
              <div style={{
                padding: "12px 14px",
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between"
              }}>
                <div>
                  📍 <strong>Administrative Coordinates:</strong>{" "}
                  {profile.latitude && profile.longitude ? (
                    <span style={{ color: "var(--accent-primary)", fontWeight: 600 }}>
                      {Number(profile.latitude).toFixed(4)}° N, {Number(profile.longitude).toFixed(4)}° E
                    </span>
                  ) : (
                    "Determined from selected district / taluk"
                  )}
                </div>
                {isGeocoding && <span style={{ fontSize: "0.8rem", color: "var(--accent-primary)" }}>Resolving...</span>}
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Financial & Demographic Eligibility */}
        {currentStep === 3 && (
          <div className="form-grid-2">
            <div className="form-field">
              <label className="field-label" htmlFor="hp-annual-income">
                Annual Family Income (₹)
              </label>
              <input
                id="hp-annual-income"
                type="number"
                min="0"
                step="5000"
                className="form-input"
                value={profile.annual_income !== undefined && profile.annual_income !== null ? profile.annual_income : ""}
                onChange={(e) => handleAnnualIncomeChange(e.target.value)}
                placeholder="e.g. 100000"
              />
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                Auto-syncs with income bracket for health scheme qualification.
              </span>
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="hp-income">
                {t("incomeLabel", languageCode) || "Income Bracket"}
              </label>
              <select
                id="hp-income"
                className="form-select"
                value={profile.income_range || "< 1.2L"}
                onChange={(e) => handleIncomeRangeSelect(e.target.value)}
              >
                <option value="< 1.2L">Below ₹1.2 Lakh (High Priority BPL)</option>
                <option value="1.2L - 3.0L">₹1.2 Lakh - ₹3.0 Lakh</option>
                <option value="3.0L - 5.0L">₹3.0 Lakh - ₹5.0 Lakh (Aarogyasri Tier)</option>
                <option value="> 5.0L">Above ₹5.0 Lakh</option>
              </select>
            </div>

            <div className="form-field col-span-2">
              <label className="field-label" htmlFor="hp-family-size">
                {t("familySizeLabel", languageCode) || "Family Size"}
              </label>
              <select
                id="hp-family-size"
                className="form-select"
                value={profile.family_size || "4"}
                onChange={(e) => handleChange("family_size", e.target.value)}
              >
                <option value="1">1 Person</option>
                <option value="2">2 Persons</option>
                <option value="3">3 Persons</option>
                <option value="4">4 Persons</option>
                <option value="5">5 Persons</option>
                <option value="6+">6+ Persons</option>
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
                  <span>{t("pregnancy", languageCode) || "Pregnant Woman"}</span>
                </label>
                <label className="checkbox-pill-label">
                  <input
                    type="checkbox"
                    checked={Boolean(profile.has_child)}
                    onChange={(e) => handleChange("has_child", e.target.checked)}
                  />
                  <span>{t("childInFamily", languageCode) || "Infant / Child in Family"}</span>
                </label>
                <label className="checkbox-pill-label col-span-2">
                  <input
                    type="checkbox"
                    checked={Boolean(profile.is_elderly)}
                    onChange={(e) => handleChange("is_elderly", e.target.checked)}
                  />
                  <span>{t("seniorInFamily", languageCode) || "Senior Citizen (60+)"}</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Health Information */}
        {currentStep === 4 && (
          <div className="form-field">
            <span className="field-label" style={{ marginBottom: "12px", display: "block" }}>
              {t("conditionsLabel", languageCode) || "Pre-existing Health Conditions"}
            </span>
            <div className="checkbox-group">
              {[
                { id: "hypertension", labelKey: "hypertension", fallback: "Hypertension" },
                { id: "diabetes", labelKey: "diabetes", fallback: "Diabetes" },
                { id: "cardiac", labelKey: "cardiacCondition", fallback: "Cardiac Condition" },
                { id: "kidney", labelKey: "kidneyCondition", fallback: "Kidney Disease" },
              ].map((cond) => (
                <label key={cond.id} className="checkbox-pill-label">
                  <input
                    type="checkbox"
                    checked={(profile.health_conditions || []).includes(cond.id)}
                    onChange={() => handleConditionToggle(cond.id)}
                  />
                  <span>{t(cond.labelKey, languageCode) || cond.fallback}</span>
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
              ← {t("back", languageCode) || "Back"}
            </button>
            <button
              type="button"
              className="header-action-btn"
              onClick={handleClear}
              style={{ color: "var(--text-muted)" }}
            >
              {t("clearProfile", languageCode) || "Reset"}
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {savedMessage && (
              <span style={{ color: "var(--success-color)", fontSize: "0.85rem", fontWeight: 600 }}>
                ✓ {t("profileSaved", languageCode) || "Profile Saved"}
              </span>
            )}
            {currentStep < profileSteps.length ? (
              <button
                type="button"
                className="btn-primary-auth"
                style={{ width: "auto", padding: "10px 20px" }}
                onClick={() => setCurrentStep((prev) => Math.min(profileSteps.length, prev + 1))}
              >
                {t("next", languageCode) || "Next"} →
              </button>
            ) : (
              <button
                type="submit"
                className="btn-primary-auth"
                style={{ width: "auto", padding: "10px 24px" }}
              >
                {t("saveProfile", languageCode) || "Save Profile"}
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
            <h3 className="modal-title">{t("healthProfile", languageCode) || "Health Profile"}</h3>
            <button type="button" className="modal-close-btn" onClick={onClose} aria-label={t("close", languageCode) || "Close"}>
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
        <h2 className="section-title">{t("healthProfile", languageCode) || "Health Profile"}</h2>
        {onClose && (
          <button type="button" className="header-action-btn" onClick={onClose}>
            ✕ {t("close", languageCode) || "Close"}
          </button>
        )}
      </div>
      {content}
    </div>
  );
}

export default HealthProfile;
