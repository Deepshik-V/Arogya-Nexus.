import { useState, useEffect } from "react";
import { compareSchemes } from "../services/aiService";
import { t } from "../translations";

const SCHEME_OPTIONS = [
  // Tamil Nadu
  { id: "cmchis-tamil-nadu", name: "CMCHIS (Tamil Nadu Health Insurance)", state: "Tamil Nadu" },
  { id: "mrmbs-dr-muthulakshmi-reddy", name: "Dr. Muthulakshmi Reddy (MRMBS - TN)", state: "Tamil Nadu" },
  { id: "makkalai-thedi-maruthuvam", name: "Makkalai Thedi Maruthuvam (MTM - TN)", state: "Tamil Nadu" },
  { id: "nammai-kaakkum-48-innisaikarangal", name: "Innuyir Kaappom 48 (NK48 - TN)", state: "Tamil Nadu" },
  // Andhra Pradesh
  { id: "ysr-aarogyasri-andhra-pradesh", name: "Dr. YSR Aarogyasri (AP ₹25L Cover)", state: "Andhra Pradesh" },
  { id: "ysr-aarogya-asara-andhra-pradesh", name: "Dr. YSR Aarogya Asara (AP)", state: "Andhra Pradesh" },
  { id: "ysr-thalli-bidda-express-andhra-pradesh", name: "Dr. YSR Thalli Bidda Express (AP)", state: "Andhra Pradesh" },
  // Kerala
  { id: "kasp-karunya-arogya-suraksha-padhathi-kerala", name: "KASP & Karunya (Kerala ₹5L)", state: "Kerala" },
  { id: "medisep-kerala", name: "MEDISEP (Kerala Employees)", state: "Kerala" },
  { id: "thalolam-scheme-kerala", name: "Thalolam Child Health (Kerala)", state: "Kerala" },
  // National
  { id: "ayushman-bharat-pmjay", name: "Ayushman Bharat PM-JAY (National ₹5L)", state: "National" },
  { id: "janani-suraksha-yojana-jsy", name: "Janani Suraksha Yojana (JSY)", state: "National" },
  { id: "pmmvy-pradhan-mantri-matru-vandana", name: "PMMVY (Matru Vandana Yojana)", state: "National" },
  { id: "nphce-elderly-care", name: "NPHCE (National Elderly Care)", state: "National" },
];

const PRESETS = [
  { label: "CMCHIS vs PM-JAY", ids: ["cmchis-tamil-nadu", "ayushman-bharat-pmjay"] },
  { label: "YSR Aarogyasri vs PM-JAY", ids: ["ysr-aarogyasri-andhra-pradesh", "ayushman-bharat-pmjay"] },
  { label: "KASP vs MEDISEP", ids: ["kasp-karunya-arogya-suraksha-padhathi-kerala", "medisep-kerala"] },
  { label: "Maternity (MRMBS vs PMMVY)", ids: ["mrmbs-dr-muthulakshmi-reddy", "pmmvy-pradhan-mantri-matru-vandana"] },
];

function SchemeComparison({ languageCode = "en-IN" }) {
  const [selectedIds, setSelectedIds] = useState(["cmchis-tamil-nadu", "ayushman-bharat-pmjay"]);
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(false);
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
    async function loadData() {
      if (!selectedIds || selectedIds.length === 0) return;
      setLoading(true);
      setError("");
      try {
        const data = await compareSchemes(selectedIds);
        if (!isCancelled) {
          setComparisonData(data);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error("Comparison load error:", err);
          setError("Failed to load scheme comparison.");
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isCancelled = true;
    };
  }, [selectedIds]);

  const handleCheckboxToggle = (id) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        if (prev.length <= 1) return prev;
        return prev.filter((i) => i !== id);
      } else {
        if (prev.length >= 3) {
          return [...prev.slice(1), id];
        } else {
          return [...prev, id];
        }
      }
    });
  };

  const schemesList = comparisonData?.schemes || [];

  return (
    <div className="section-block" style={{ gap: "24px" }}>
      {/* Header */}
      <div className="section-header" style={{ flexWrap: "wrap" }}>
        <div>
          <h2 className="section-title">{t("comparisonTitle", languageCode)}</h2>
          <p className="hero-tagline" style={{ fontSize: "0.9rem" }}>
            {t("comparisonSubtitle", languageCode)}
          </p>
        </div>

        {/* Presets */}
        <div className="preset-bar">
          <span className="preset-title">{t("quickPresets", languageCode)}:</span>
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              className="preset-pill-btn"
              onClick={() => setSelectedIds(p.ids)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Selector Checkbox Chips */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <span style={{ fontSize: "0.84rem", color: "var(--text-secondary)", fontWeight: 600 }}>
          {t("selectSchemes", languageCode)} ({selectedIds.length}/3):
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {SCHEME_OPTIONS.map((opt) => {
            const isChecked = selectedIds.includes(opt.id);
            return (
              <button
                key={opt.id}
                type="button"
                className={`preset-pill-btn ${isChecked ? "active" : ""}`}
                onClick={() => handleCheckboxToggle(opt.id)}
                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <span>{isChecked ? "✓" : "+"}</span>
                <span>{opt.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading or Error */}
      {loading && (
        <div style={{ padding: "32px", textAlign: "center", color: "var(--text-secondary)" }}>
          <span>Loading verified scheme comparison...</span>
        </div>
      )}

      {error && (
        <div className="auth-error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Comparison Grid */}
      {!loading && schemesList.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${schemesList.length}, minmax(280px, 1fr))`,
            gap: "20px",
            overflowX: "auto",
            paddingBottom: "16px",
          }}
        >
          {schemesList.map((s) => {
            const name = s.scheme_name?.[langTag] || s.scheme_name?.en || s.scheme_id;
            const benefits = s.benefits?.[langTag] || s.benefits?.en || [];
            const eligibility = s.eligibility?.[langTag] || s.eligibility?.en || [];
            const documents = s.required_documents?.[langTag] || s.required_documents?.en || [];
            const whereApply = s.where_to_apply?.[langTag] || s.where_to_apply?.en || [];
            const desc = s.short_description?.[langTag] || s.short_description?.en || "";

            return (
              <div
                key={s.scheme_id}
                className="scheme-card"
                style={{ justifyContent: "flex-start", gap: "20px" }}
              >
                <div>
                  <div className="scheme-badges-row">
                    <span className="badge-state">{s.state || "National"}</span>
                  </div>
                  <h3 className="scheme-card-title">{name}</h3>
                  <p className="scheme-card-desc" style={{ WebkitLineClamp: "unset", marginTop: "8px" }}>
                    {desc}
                  </p>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "0.85rem", color: "var(--accent-primary)" }}>
                    {t("benefits", languageCode)}
                  </strong>
                  <ul style={{ paddingLeft: "18px", fontSize: "0.85rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {benefits.slice(0, 3).map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "0.85rem", color: "var(--accent-primary)" }}>
                    {t("eligibilityCriteria", languageCode)}
                  </strong>
                  <ul style={{ paddingLeft: "18px", fontSize: "0.85rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {eligibility.slice(0, 3).map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "0.85rem", color: "var(--accent-primary)" }}>
                    {t("requiredDocuments", languageCode)}
                  </strong>
                  <ul style={{ paddingLeft: "18px", fontSize: "0.85rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {documents.slice(0, 3).map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ marginTop: "auto", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    {whereApply[0] || "Primary Health Centre"}
                  </span>
                  {s.official_url && (
                    <a
                      href={s.official_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-view-details"
                    >
                      Official Link ↗
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SchemeComparison;
