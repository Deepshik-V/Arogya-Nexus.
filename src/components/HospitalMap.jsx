import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { t } from "../translations";

// SVG icon generator for user location (pulsing circle in healthcare blue)
function createUserLocationIcon(label = "You") {
  return L.divIcon({
    className: "custom-user-marker",
    html: `
      <div class="user-pulse-marker" title="${label}">
        <div class="pulse-ring"></div>
        <div class="user-center-dot">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="#ffffff">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
}

// SVG icon generator for hospital markers (Healthcare Teal/Blue)
function createHospitalMarkerIcon(isSelected = false) {
  const bg = isSelected ? "#0f766e" : "#0284c7";
  const border = isSelected ? "#14b8a6" : "#38bdf8";
  const scale = isSelected ? "scale(1.2)" : "scale(1)";

  return L.divIcon({
    className: "custom-hospital-marker",
    html: `
      <div class="hospital-pin ${isSelected ? "selected" : ""}" style="transform: ${scale};">
        <div class="pin-head" style="background: ${bg}; border-color: ${border};">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="#ffffff">
            <path d="M19 10.5h-4.5V6a1.5 1.5 0 0 0-3 0v4.5H7a1.5 1.5 0 0 0 0 3h4.5V18a1.5 1.5 0 0 0 3 0v-4.5H19a1.5 1.5 0 0 0 0-3z"/>
          </svg>
        </div>
        <div class="pin-point" style="border-top-color: ${bg};"></div>
      </div>
    `,
    iconSize: [36, 42],
    iconAnchor: [18, 42],
    popupAnchor: [0, -42],
  });
}

export default function HospitalMap({
  hospitals = [],
  userLocation = null,
  selectedHospital = null,
  onSelectHospital = null,
  height = "480px",
  languageCode = "en-IN",
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const markersMapRef = useRef({});

  // 1. Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const initLat = userLocation?.latitude
        ? Number(userLocation.latitude)
        : hospitals[0]?.latitude
        ? Number(hospitals[0].latitude)
        : 11.6643;
      const initLon = userLocation?.longitude
        ? Number(userLocation.longitude)
        : hospitals[0]?.longitude
        ? Number(hospitals[0].longitude)
        : 78.1460;

      const map = L.map(mapContainerRef.current, {
        center: [initLat, initLon],
        zoom: 13,
        zoomControl: false,
        attributionControl: false,
      });

      // Zoom Control at bottom-right
      L.control.zoom({ position: "bottomright" }).addTo(map);

      // OpenStreetMap Standard Tiles
      const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      });
      tileLayer.addTo(map);

      // Attribution at bottom-left
      L.control
        .attribution({ position: "bottomleft", prefix: false })
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

      const markersGroup = L.layerGroup().addTo(map);
      markersLayerRef.current = markersGroup;
      mapInstanceRef.current = map;

      // Invalidate size on initial mount
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 150);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markersLayerRef.current = null;
        markersMapRef.current = {};
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2. ResizeObserver to keep Leaflet container responsive and eliminate white/blank areas
  useEffect(() => {
    if (!mapContainerRef.current) return;
    const resizeObserver = new ResizeObserver(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    });
    resizeObserver.observe(mapContainerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // 3. Update User Location & Hospital Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersGroup = markersLayerRef.current;
    if (!map || !markersGroup) return;

    // Clear previous markers
    markersGroup.clearLayers();
    markersMapRef.current = {};

    const bounds = L.latLngBounds([]);

    // Plot User Marker
    if (userLocation?.latitude && userLocation?.longitude) {
      const uLat = Number(userLocation.latitude);
      const uLon = Number(userLocation.longitude);

      if (!isNaN(uLat) && !isNaN(uLon)) {
        const uLabel = userLocation.label || t("currentLocation", languageCode);
        const userIcon = createUserLocationIcon(uLabel);

        const uMarker = L.marker([uLat, uLon], { icon: userIcon });
        uMarker.bindPopup(`
          <div class="map-popup-inner user-popup">
            <strong style="color: #0284c7; font-size: 0.9rem;">📍 ${uLabel}</strong>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 3px;">
              ${userLocation.type === "gps" ? `🟢 ${t("gpsActive", languageCode)}` : `📍 ${t("profileLocation", languageCode)}`}
            </div>
          </div>
        `);
        uMarker.addTo(markersGroup);
        bounds.extend([uLat, uLon]);
      }
    }

    // Plot Hospital Markers
    hospitals.forEach((hospital) => {
      const hLat = Number(hospital.latitude);
      const hLon = Number(hospital.longitude);
      if (isNaN(hLat) || isNaN(hLon)) return;

      const isSelected = selectedHospital && selectedHospital.id === hospital.id;
      const icon = createHospitalMarkerIcon(isSelected);

      const marker = L.marker([hLat, hLon], { icon });

      // Build popup content
      const distLabel =
        hospital.distance_label ||
        (hospital.distance ? `${hospital.distance} km away` : "");
      const callBtnHtml = hospital.phone
        ? `<a href="tel:${hospital.phone}" class="map-popup-call-btn">📞 ${t("callHospital", languageCode)} (${hospital.phone})</a>`
        : "";
      const directionsUrl =
        hospital.directions_url ||
        hospital.maps_url ||
        `https://www.google.com/maps/dir/?api=1&destination=${hLat},${hLon}`;

      const popupHtml = `
        <div class="map-popup-inner">
          <div class="map-popup-header">
            <span class="map-popup-type">${hospital.type || "Government Hospital"}</span>
            ${distLabel ? `<span class="map-popup-dist">${distLabel}</span>` : ""}
          </div>
          <h4 class="map-popup-title">${hospital.name}</h4>
          <p class="map-popup-address">${hospital.address || ""}</p>
          <div class="map-popup-actions">
            <a href="${directionsUrl}" target="_blank" rel="noreferrer" class="map-popup-dir-btn">
              🗺️ ${t("getDirections", languageCode)}
            </a>
            ${callBtnHtml}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { maxWidth: 300 });

      marker.on("click", () => {
        if (onSelectHospital) {
          onSelectHospital(hospital);
        }
      });

      marker.addTo(markersGroup);
      markersMapRef.current[hospital.id] = marker;
      bounds.extend([hLat, hLon]);

      if (isSelected) {
        marker.openPopup();
      }
    });

    // 4. Focus on selected hospital or fit bounds
    if (selectedHospital?.latitude && selectedHospital?.longitude) {
      const sLat = Number(selectedHospital.latitude);
      const sLon = Number(selectedHospital.longitude);
      if (!isNaN(sLat) && !isNaN(sLon)) {
        map.flyTo([sLat, sLon], 15, { animate: true, duration: 0.6 });
        const existingMarker = markersMapRef.current[selectedHospital.id];
        if (existingMarker) {
          existingMarker.openPopup();
        }
      }
    } else if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [35, 35],
        maxZoom: 15,
        animate: true,
      });
    }

    map.invalidateSize();
  }, [hospitals, userLocation, selectedHospital, onSelectHospital, languageCode]);

  return (
    <div className="hospital-map-wrapper">
      <div
        ref={mapContainerRef}
        className="hospital-leaflet-container"
        style={{ height, width: "100%", borderRadius: "var(--radius-lg)" }}
        aria-label="Interactive Map of Nearby Healthcare Facilities"
      />
    </div>
  );
}
