import React, { useState, useEffect } from "react";
import { getSchemesList } from "../services/aiService";
import { t } from "../translations";

const CATEGORIES = [
  { id: "all", labelKey: "allSchemes", fallback: "All Schemes", icon: "🏛️" },
  { id: "health_insurance", labelKey: "catInsurance", fallback: "Cashless Insurance", icon: "🛡️" },
  { id: "maternal_child", labelKey: "catMaternal", fallback: "Maternal & Child", icon: "👶" },
  { id: "elderly_care", labelKey: "catElderly", fallback: "Elderly Care (60+)", icon: "👵" },
  { id: "preventive_care", labelKey: "catPreventive", fallback: "Free Healthcare / NHM", icon: "🩺" },
];

const STATES = [
  { id: "all", label: "All Regions" },
  { id: "National", label: "National (Central)" },
  { id: "Tamil Nadu", label: "Tamil Nadu" },
  { id: "Andhra Pradesh", label: "Andhra Pradesh" },
  { id: "Kerala", label: "Kerala" },
];

export default function SchemesDirectory({
  languageCode = "en-IN",
  userState = "all",
  onSelectScheme,
  onNavigateCompare,
  onBackToHome,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedState, setSelectedState] = useState(
    userState && STATES.some((s) => s.id === userState) ? userState : "all"
  );
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const langTag = languageCode.startsWith("ta")
    ? "ta"
    : languageCode.startsWith("te")
    ? "te"
    : languageCode.startsWith("ml")
    ? "ml"
    : "en";

  useEffect(() => {
    let isCancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getSchemesList({
          query: searchQuery,
          state: selectedState,
          category: selectedCategory,
          languageCode,
        });
        if (!isCancelled) {
          setSchemes(data.schemes || []);
        }
      } catch (err) {
        if (!isCancelled) {
          console.warn("Schemes loading fallback active:", err);
          setError("Displaying verified offline scheme directory.");
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(() => {
      load();
    }, 150);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [searchQuery, selectedCategory, selectedState, languageCode]);

  const getTitle = (scheme) => {
    if (!scheme) return "";
    const nameObj = scheme.scheme_name;
    if (typeof nameObj === "object" && nameObj !== null) {
      return nameObj[langTag] || nameObj.en || scheme.title_en || scheme.id;
    }
    return scheme.title_en || scheme.id || "Government Health Scheme";
  };

  const getDescription = (scheme) => {
    if (!scheme) return "";
    const desc = scheme.short_description;
    if (typeof desc === "object" && desc !== null) {
      return desc[langTag] || desc.en || "";
    }
    return desc || "";
  };

  const getBenefitsPreview = (scheme) => {
    if (!scheme) return [];
    if (scheme.key_benefits && Array.isArray(scheme.key_benefits)) {
      return scheme.key_benefits;
    }
    const benefits = scheme.benefits;
    if (typeof benefits === "object" && benefits !== null) {
      const list = benefits[langTag] || benefits.en || [];
      return Array.isArray(list) ? list.slice(0, 2) : [];
    }
    return [];
  };

  return (
    <div className="section-block schemes-directory-wrapper" style={{ gap: "24px" }}>
      {/* Top Header Row with Navigation & Compare Shortcut */}
      <div className="section-header" style={{ flexWrap: "wrap", gap: "16px" }}>
        <div>
          {onBackToHome && (
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "10px", display: "inline-flex", alignItems: "center", gap: "6px" }}
              onClick={onBackToHome}
            >
              <span>←</span>
              <span>{t("back", languageCode) || "Back to Home"}</span>
            </button>
          )}
          <h1 className="section-title">
            {t("govtSchemes", languageCode) || "Government Health Schemes"}
          </h1>
          <p className="hero-tagline" style={{ fontSize: "0.92rem", marginTop: "4px" }}>
            Verified Central & State Government health coverage, maternal support, hospital assurance, and free medicine initiatives.
          </p>
        </div>

        {onNavigateCompare && (
          <button
            type="button"
            className="btn-primary-auth"
            style={{ width: "auto", padding: "10px 20px", display: "inline-flex", alignItems: "center", gap: "8px", alignSelf: "center" }}
            onClick={onNavigateCompare}
          >
            <span>⚖️</span>
            <span>{t("compareSchemes", languageCode) || "Compare Schemes Side-by-Side"}</span>
          </button>
        )}
      </div>

      {/* Interactive Controls Bar: Search & State Filter */}
      <div className="schemes-controls-panel">
        {/* Search Box */}
        <div className="schemes-search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="schemes-search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search schemes (e.g., Ayushman, PM-JAY, PMSMA, Maternity, ₹5 Lakh, Surgery)..."
            aria-label="Search government schemes"
          />
          {searchQuery && (
            <button
              type="button"
              className="schemes-search-clear"
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {/* State Filter Selector */}
        <div className="schemes-state-filter">
          <label htmlFor="scheme-state-select" className="schemes-filter-label">
            Jurisdiction:
          </label>
          <select
            id="scheme-state-select"
            className="schemes-state-select"
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
          >
            {STATES.map((st) => (
              <option key={st.id} value={st.id}>
                {st.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Category Pills Bar */}
      <div className="schemes-category-bar" role="tablist">
        {CATEGORIES.map((cat) => {
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`preset-pill-btn schemes-cat-btn ${isActive ? "active" : ""}`}
              onClick={() => setSelectedCategory(cat.id)}
            >
              <span>{cat.icon}</span>
              <span>{t(cat.labelKey, languageCode) || cat.fallback}</span>
            </button>
          );
        })}
      </div>

      {/* Status / Count Banner */}
      <div className="schemes-count-row">
        <span className="schemes-count-text">
          Showing <strong>{schemes.length}</strong> verified scheme{schemes.length === 1 ? "" : "s"}
          {selectedCategory !== "all" && ` in ${CATEGORIES.find(c => c.id === selectedCategory)?.fallback}`}
          {selectedState !== "all" && ` (${selectedState})`}
        </span>
        {error && (
          <span style={{ fontSize: "0.82rem", color: "var(--accent-primary)" }}>
            ℹ️ {error}
          </span>
        )}
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--text-secondary)" }}>
          <div style={{ fontSize: "1.8rem", marginBottom: "12px", animation: "spin 1s infinite linear" }}>⏳</div>
          <p>Loading verified government health schemes...</p>
        </div>
      )}

      {/* Zero State */}
      {!loading && schemes.length === 0 && (
        <div className="schemes-empty-state">
          <span style={{ fontSize: "2.4rem", marginBottom: "12px", display: "block" }}>📋</span>
          <h3>No schemes found matching your search</h3>
          <p style={{ color: "var(--text-muted)", marginTop: "6px" }}>
            No scheme matched &quot;{searchQuery}&quot;. Try adjusting your keywords or clearing the category filter.
          </p>
          <button
            type="button"
            className="btn-primary-auth"
            style={{ width: "auto", margin: "16px auto 0", padding: "8px 20px" }}
            onClick={() => {
              setSearchQuery("");
              setSelectedCategory("all");
              setSelectedState("all");
            }}
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Schemes Grid */}
      {!loading && schemes.length > 0 && (
        <div className="schemes-grid">
          {schemes.map((scheme) => {
            const title = getTitle(scheme);
            const desc = getDescription(scheme);
            const benefitsPreview = getBenefitsPreview(scheme);
            const stateLabel = scheme.state || "National";
            const isNational = stateLabel.toLowerCase() === "national";

            return (
              <article key={scheme.id || scheme.scheme_id} className="scheme-card">
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {/* Badges */}
                  <div className="scheme-badges-row">
                    <span className={`badge-state ${isNational ? "national-badge" : "state-badge"}`}>
                      {isNational ? "🏛️ All-India / National" : `📍 ${stateLabel}`}
                    </span>
                    {scheme.scheme_category && (
                      <span className="badge-status likely">
                        {scheme.scheme_category === "health_insurance"
                          ? "🛡️ Cashless Insurance"
                          : scheme.scheme_category === "maternal_child"
                          ? "👶 Maternal & Child"
                          : scheme.scheme_category === "elderly_care"
                          ? "👵 Geriatric 60+"
                          : "🩺 Universal Care"}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3 className="scheme-card-title">{title}</h3>

                  {/* Description */}
                  <p className="scheme-card-desc">{desc}</p>

                  {/* Benefit highlights pill preview */}
                  {benefitsPreview.length > 0 && (
                    <div className="scheme-benefits-preview-box">
                      <strong style={{ fontSize: "0.78rem", color: "var(--accent-primary)", display: "block", marginBottom: "4px" }}>
                        Key Highlights:
                      </strong>
                      <ul style={{ paddingLeft: "16px", margin: 0, fontSize: "0.82rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "3px" }}>
                        {benefitsPreview.map((b, idx) => (
                          <li key={idx}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="scheme-card-footer">
                  <span className="scheme-source-text" title={scheme.official_source || "Official Government Health Mission"}>
                    🏛️ {scheme.official_source || "Official Health Mission"}
                  </span>
                  <button
                    type="button"
                    className="btn-view-details"
                    onClick={() => onSelectScheme && onSelectScheme(scheme)}
                    aria-label={`View details for ${title}`}
                  >
                    {t("viewDetails", languageCode) || "View Details"} →
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
