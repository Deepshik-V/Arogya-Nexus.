import { useState, useEffect, useCallback } from "react";
import { t } from "../translations";
import { geocodeLocation, reverseGeocodeLocation, getLocationHierarchy } from "../services/aiService";

// Pre-seeded fallback hierarchy to ensure immediate offline/instant rendering
const STATIC_HIERARCHY = {
  "Tamil Nadu": {
    "Salem": {
      "Salem Taluk": ["Shevapet", "Suramangalam", "Hasthampatti", "Ammapet", "Gugai", "Fairlands", "Alagapuram", "Kitchipalayam"],
      "Omalur": ["Omalur Town", "Tharamangalam", "Kamalapuram", "Karuppur"],
      "Attur": ["Attur Town", "Narasingapuram", "Thalaivasal", "Mallur"],
      "Mettur": ["Mettur Dam", "Mecheri", "Kolathur", "P.N. Patti"],
      "Sankari": ["Sankari Town", "Thevoor", "Arasiramani", "Magudanchavadi"],
      "Edappadi": ["Edappadi Town", "Poolampatti", "Avaniperur"],
      "Yercaud": ["Yercaud Town", "Kiliyur", "Nagallur"],
      "Panamarathupatti": ["Panamarathupatti Town", "Mallur"]
    },
    "Chennai": {
      "Egmore": ["Park Town", "Egmore Central", "Pudupet", "Chintadripet"],
      "Mylapore": ["Mylapore", "Royapettah", "Alwarpet", "Mandaveli", "Santhome"],
      "Tondiarpet": ["Royapuram", "George Town", "Tondiarpet", "Washermanpet"],
      "Guindy": ["Guindy", "Saidapet", "Ekkatuthangal", "Kotturpuram"],
      "Velachery": ["Velachery", "Madipakkam", "Adambakkam", "Tharamani"],
      "Ambattur": ["Ambattur", "Anna Nagar West", "Mogappair", "Padi"],
      "Aminjikarai": ["Kilpauk", "Shenoy Nagar", "Aminjikarai", "Chetpet"]
    },
    "Coimbatore": {
      "Coimbatore North": ["Gandhipuram", "RS Puram", "Saibaba Colony", "Ganapathy"],
      "Coimbatore South": ["Ukkadam", "Singanallur", "Ramanathapuram", "Peelamedu"],
      "Pollachi": ["Pollachi Town", "Anamalai", "Kinathukadavu"],
      "Mettupalayam": ["Mettupalayam Town", "Karamadai"]
    },
    "Madurai": {
      "Madurai North": ["Goripalayam", "Sellur", "Tallakulam", "Koodal Nagar"],
      "Madurai South": ["Simmakkal", "South Gate", "Periyar", "Villapuram"],
      "Melur": ["Melur Town", "Kottampatti"],
      "Thirumangalam": ["Thirumangalam Town", "Kalligudi"]
    },
    "Tiruchirappalli": {
      "Tiruchirappalli West": ["Thillai Nagar", "Woraiyur", "Cantonment"],
      "Tiruchirappalli East": ["Palakarai", "Ponmalai", "Golden Rock"],
      "Srirangam": ["Srirangam Town", "Thiruvanaikoil"]
    },
    "Tirunelveli": {
      "Tirunelveli Taluk": ["Tirunelveli Town", "Junction", "Palayamkottai"],
      "Ambasamudram": ["Ambasamudram Town", "Kallidaikurichi"]
    },
    "Vellore": {
      "Vellore Taluk": ["Vellore Fort Area", "Sathuvachari", "Katpadi"],
      "Gudiyatham": ["Gudiyatham Town", "Pernambut"]
    },
    "Erode": {
      "Erode Taluk": ["Erode Town", "Perundurai", "Bhavani", "Gobichettipalayam"]
    }
  },
  "Karnataka": {
    "Bengaluru": {
      "Bengaluru South": ["Jayanagar", "JP Nagar", "BTM Layout", "Banashankari", "Koramangala"],
      "Bengaluru North": ["Malleshwaram", "Hebbal", "Yelahanka", "Yeshwanthpur"],
      "Bengaluru East": ["Indiranagar", "Whitefield", "Marathahalli"],
      "Bengaluru Central": ["Shivaji Nagar", "MG Road", "Majestic"]
    },
    "Mysuru": {
      "Mysuru Taluk": ["Chamundipuram", "Gokulam", "Jayalakshmipuram"]
    }
  },
  "Kerala": {
    "Thiruvananthapuram": {
      "Thiruvananthapuram Taluk": ["Palayam", "Medical College", "Pattom", "Kowdiar"],
      "Neyyattinkara": ["Neyyattinkara Town", "Balaramapuram"]
    },
    "Ernakulam": {
      "Kanayannur": ["MG Road", "Kaloor", "Edappally", "Fort Kochi"],
      "Aluva": ["Aluva Town", "Angamaly"]
    },
    "Kozhikode": {
      "Kozhikode Taluk": ["Mananchira", "Medical College", "Palayam"]
    }
  },
  "Andhra Pradesh": {
    "Visakhapatnam": {
      "Visakhapatnam Urban": ["Gajuwaka", "MVP Colony", "Siripuram"],
      "Anakapalle": ["Anakapalle Town", "Kasimkota"]
    },
    "Vijayawada": {
      "Vijayawada Urban": ["Benz Circle", "Governorpet", "Gunadala"]
    },
    "Tirupati": {
      "Tirupati Urban": ["Alipiri", "Bhavani Nagar", "Korlagunta"]
    }
  }
};

const RADIUS_OPTIONS = [5, 10, 25, 50];

export default function LocationPermissionCard({
  currentLocationType = "profile", // "gps" | "profile" | "manual"
  activeLocationLabel = "Salem, Tamil Nadu",
  coordinates = null, // { latitude, longitude }
  selectedState = "Tamil Nadu",
  selectedDistrict = "Salem",
  selectedTaluk = "Salem Taluk",
  selectedLocality = "Shevapet",
  selectedPincode = "636001",
  searchRadiusKm = 10,
  onLocationChange = () => {},
  onRadiusChange = () => {},
  onRequestGPS = () => {},
  onSearchAgain = () => {},
  isBusy = false,
  languageCode = "en-IN",
  permissionNotice = "",
}) {
  const [hierarchy, setHierarchy] = useState(STATIC_HIERARCHY);
  const [showManualInputs, setShowManualInputs] = useState(false);
  const [isGeocoding, setIsGeocoding] = useState(false);

  // Controlled form state for hierarchy
  const [localState, setLocalState] = useState(selectedState || "Tamil Nadu");
  const [localDistrict, setLocalDistrict] = useState(selectedDistrict || "Salem");
  const [localTaluk, setLocalTaluk] = useState(selectedTaluk || "");
  const [localLocality, setLocalLocality] = useState(selectedLocality || "");
  const [localPincode, setLocalPincode] = useState(selectedPincode || "");

  // Sync internal state when parent props change
  useEffect(() => {
    if (selectedState) setLocalState(selectedState);
    if (selectedDistrict) setLocalDistrict(selectedDistrict);
    if (selectedTaluk !== undefined) setLocalTaluk(selectedTaluk || "");
    if (selectedLocality !== undefined) setLocalLocality(selectedLocality || "");
    if (selectedPincode !== undefined) setLocalPincode(selectedPincode || "");
  }, [selectedState, selectedDistrict, selectedTaluk, selectedLocality, selectedPincode]);

  // Load latest live hierarchy from backend on mount
  useEffect(() => {
    let active = true;
    getLocationHierarchy()
      .then((data) => {
        if (active && data && typeof data === "object" && Object.keys(data).length > 0) {
          setHierarchy(data);
        }
      })
      .catch(() => {
        // Fall back gracefully to static hierarchy
      });
    return () => {
      active = false;
    };
  }, []);

  // Compute available districts, taluks, localities from hierarchy
  const availableStates = Object.keys(hierarchy);
  const stateData = hierarchy[localState] || {};
  const availableDistricts = Object.keys(stateData);
  const districtData = stateData[localDistrict] || {};
  const availableTaluks = Object.keys(districtData);
  const availableLocalities = localTaluk && districtData[localTaluk] ? districtData[localTaluk] : [];

  // Handle Geocoding and propagate hierarchy change to parent
  const applyHierarchyLocation = useCallback(
    async (newState, newDistrict, newTaluk = "", newLocality = "", newPincode = "") => {
      setIsGeocoding(true);
      try {
        const geoRes = await geocodeLocation({
          state: newState,
          district: newDistrict,
          taluk: newTaluk || undefined,
          locality: newLocality || undefined,
          pincode: newPincode || undefined,
        });

        const resolvedLat = geoRes.latitude;
        const resolvedLon = geoRes.longitude;

        onLocationChange({
          state: newState,
          district: newDistrict,
          taluk: newTaluk,
          locality: newLocality,
          pincode: newPincode,
          latitude: resolvedLat,
          longitude: resolvedLon,
          type: "manual",
          label: geoRes.display_name || `${newLocality || newTaluk || newDistrict}, ${newState}`,
        });
      } catch (err) {
        console.warn("Geocoding failed, falling back to district center:", err);
        onLocationChange({
          state: newState,
          district: newDistrict,
          taluk: newTaluk,
          locality: newLocality,
          pincode: newPincode,
          type: "manual",
          label: `${newLocality || newTaluk || newDistrict}, ${newState}`,
        });
      } finally {
        setIsGeocoding(false);
      }
    },
    [onLocationChange]
  );

  const handleStateChange = (e) => {
    const val = e.target.value;
    setLocalState(val);
    const firstDistrict = Object.keys(hierarchy[val] || {})[0] || "";
    setLocalDistrict(firstDistrict);
    setLocalTaluk("");
    setLocalLocality("");
    applyHierarchyLocation(val, firstDistrict, "", "", localPincode);
  };

  const handleDistrictChange = (e) => {
    const val = e.target.value;
    setLocalDistrict(val);
    const talukList = Object.keys(stateData[val] || {});
    const firstTaluk = talukList.length > 0 ? talukList[0] : "";
    setLocalTaluk(firstTaluk);
    const locList = firstTaluk && stateData[val] && stateData[val][firstTaluk] ? stateData[val][firstTaluk] : [];
    const firstLoc = locList.length > 0 ? locList[0] : "";
    setLocalLocality(firstLoc);
    applyHierarchyLocation(localState, val, firstTaluk, firstLoc, localPincode);
  };

  const handleTalukChange = (e) => {
    const val = e.target.value;
    setLocalTaluk(val);
    const locList = val && districtData[val] ? districtData[val] : [];
    const firstLoc = locList.length > 0 ? locList[0] : "";
    setLocalLocality(firstLoc);
    applyHierarchyLocation(localState, localDistrict, val, firstLoc, localPincode);
  };

  const handleLocalityChange = (e) => {
    const val = e.target.value;
    setLocalLocality(val);
    applyHierarchyLocation(localState, localDistrict, localTaluk, val, localPincode);
  };

  const handlePincodeBlur = () => {
    applyHierarchyLocation(localState, localDistrict, localTaluk, localLocality, localPincode);
  };

  return (
    <div className="location-permission-card">
      <div className="location-permission-top">
        <div className="location-info-block">
          <div className="location-title-row">
            <span className="location-icon-pin">📍</span>
            <h3 className="location-card-title">
              {t("findHealthcareNearYou", languageCode) || "Find healthcare near you"}
            </h3>
            <span className={`location-status-tag ${currentLocationType}`}>
              {currentLocationType === "gps"
                ? `🟢 ${t("gpsActive", languageCode)}`
                : currentLocationType === "profile"
                ? `📍 ${t("profileLocation", languageCode)}`
                : `✏️ ${t("manualLocation", languageCode)}`}
            </span>
          </div>

          <p className="location-card-desc">
            {t("allowLocationPrompt", languageCode) || "Accurate GPS or hierarchical administrative location determines real travel distance to hospitals."}
          </p>

          <div className="active-location-indicator">
            {t("usingLocation", languageCode)}{" "}
            <strong>{activeLocationLabel}</strong>
            {coordinates && coordinates.latitude && coordinates.longitude && (
              <span className="location-coord-badge">
                ({Number(coordinates.latitude).toFixed(4)}°, {Number(coordinates.longitude).toFixed(4)}°)
              </span>
            )}
          </div>
        </div>

        <div className="location-actions-group">
          <button
            type="button"
            className={`btn-location-gps ${currentLocationType === "gps" ? "active" : ""}`}
            onClick={onRequestGPS}
            disabled={isBusy || isGeocoding}
            aria-label={t("useCurrentLocation", languageCode)}
          >
            {isBusy ? t("detecting", languageCode) : `📍 ${t("useCurrentLocation", languageCode)}`}
          </button>

          <button
            type="button"
            className="btn-location-manual"
            onClick={() => setShowManualInputs((prev) => !prev)}
            aria-label={t("changeLocation", languageCode)}
          >
            ✏️ {t("changeLocation", languageCode)} {showManualInputs ? "▲" : "▼"}
          </button>

          <button
            type="button"
            className="btn-location-refresh"
            onClick={onSearchAgain}
            disabled={isBusy}
            title={t("searchAgain", languageCode)}
          >
            🔄 {t("searchAgain", languageCode)}
          </button>
        </div>
      </div>

      {/* SEARCH RADIUS SELECTOR PILLS */}
      <div className="location-radius-bar">
        <span className="radius-bar-label">
          🎯 {t("searchRadius", languageCode)}:
        </span>
        <div className="radius-pills-row">
          {RADIUS_OPTIONS.map((rad) => (
            <button
              key={rad}
              type="button"
              className={`radius-pill-btn ${searchRadiusKm === rad ? "active" : ""}`}
              onClick={() => onRadiusChange(rad)}
              disabled={isBusy}
            >
              {rad} km {rad === 10 ? `(${t("default", languageCode) || "Default"})` : ""}
            </button>
          ))}
        </div>
      </div>

      {permissionNotice && (
        <div className="location-notice-banner">
          <span>ℹ️</span>
          <span>{permissionNotice}</span>
        </div>
      )}

      {/* HIERARCHICAL LOCATION SELECTORS */}
      {showManualInputs && (
        <div className="location-hierarchy-box">
          <div className="hierarchy-box-header">
            <strong>🏛️ Administrative Location Hierarchy</strong>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              State ↓ District ↓ Taluk/Town ↓ Locality/Area ↓ Pincode
            </span>
          </div>

          <div className="location-hierarchy-grid">
            {/* 1. State */}
            <div className="manual-field-group">
              <label className="manual-field-label">{t("stateLabel", languageCode)}</label>
              <select
                className="manual-select"
                value={localState}
                onChange={handleStateChange}
                disabled={isBusy || isGeocoding}
              >
                {availableStates.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            {/* 2. District / City */}
            <div className="manual-field-group">
              <label className="manual-field-label">{t("districtLabel", languageCode)}</label>
              <select
                className="manual-select"
                value={localDistrict}
                onChange={handleDistrictChange}
                disabled={isBusy || isGeocoding}
              >
                {availableDistricts.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* 3. Taluk / Municipality */}
            <div className="manual-field-group">
              <label className="manual-field-label">{t("talukLabel", languageCode)}</label>
              {availableTaluks.length > 0 ? (
                <select
                  className="manual-select"
                  value={localTaluk}
                  onChange={handleTalukChange}
                  disabled={isBusy || isGeocoding}
                >
                  <option value="">-- Select Taluk / Town --</option>
                  {availableTaluks.map((tk) => (
                    <option key={tk} value={tk}>
                      {tk}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="manual-input"
                  value={localTaluk}
                  onChange={(e) => setLocalTaluk(e.target.value)}
                  onBlur={() => applyHierarchyLocation(localState, localDistrict, localTaluk, localLocality, localPincode)}
                  placeholder="e.g. Salem Taluk, Omalur"
                  disabled={isBusy || isGeocoding}
                />
              )}
            </div>

            {/* 4. Locality / Village */}
            <div className="manual-field-group">
              <label className="manual-field-label">{t("localityLabel", languageCode)}</label>
              {availableLocalities.length > 0 ? (
                <select
                  className="manual-select"
                  value={localLocality}
                  onChange={handleLocalityChange}
                  disabled={isBusy || isGeocoding}
                >
                  <option value="">-- Select Area / Locality --</option>
                  {availableLocalities.map((loc) => (
                    <option key={loc} value={loc}>
                      {loc}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="manual-input"
                  value={localLocality}
                  onChange={(e) => setLocalLocality(e.target.value)}
                  onBlur={() => applyHierarchyLocation(localState, localDistrict, localTaluk, localLocality, localPincode)}
                  placeholder="e.g. Shevapet, Fairlands"
                  disabled={isBusy || isGeocoding}
                />
              )}
            </div>

            {/* 5. Pincode */}
            <div className="manual-field-group">
              <label className="manual-field-label">{t("pincodeLabel", languageCode)}</label>
              <input
                type="text"
                className="manual-input"
                value={localPincode}
                onChange={(e) => setLocalPincode(e.target.value)}
                onBlur={handlePincodeBlur}
                placeholder="e.g. 636001"
                maxLength={6}
                disabled={isBusy || isGeocoding}
              />
            </div>
          </div>

          {isGeocoding && (
            <div style={{ marginTop: "8px", fontSize: "0.82rem", color: "var(--accent-primary)" }}>
              ⏳ Resolving verified coordinates for selected area...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
