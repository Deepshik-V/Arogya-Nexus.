import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.locationService import geocode_location, COORDINATE_INDEX

HOSPITALS_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "hospitals" / "tamil_nadu_hospitals.json"
_CACHED_HOSPITALS: Optional[List[Dict[str, Any]]] = None

# Verified regional district centers
VERIFIED_DISTRICT_CENTERS: Dict[str, Tuple[float, float]] = {
    # Tamil Nadu
    "salem": (11.6643, 78.1460),
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "tiruchirappalli": (10.7905, 78.7047),
    "trichy": (10.7905, 78.7047),
    "tirunelveli": (8.7139, 77.7567),
    "vellore": (12.9165, 79.1325),
    "thanjavur": (10.7870, 79.1378),
    "erode": (11.3410, 77.7172),
    "dindigul": (10.3673, 77.9803),
    "kanchipuram": (12.8342, 79.7036),
    "tiruppur": (11.1085, 77.3411),
    "dharmapuri": (12.1211, 78.1582),
    "krishnagiri": (12.5186, 78.2137),
    "namakkal": (11.2189, 78.1674),
    "cuddalore": (11.7480, 79.7714),
    "viluppuram": (11.9401, 79.4861),
    "tiruvannamalai": (12.2253, 79.0747),
    "thoothukudi": (8.7642, 78.1348),
    "virudhunagar": (9.5680, 77.9624),
    "theni": (10.0104, 77.4768),
    "kanyakumari": (8.0883, 77.5385),
    "nagercoil": (8.1833, 77.4119),
    # Karnataka
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mysuru": (12.2958, 76.6394),
    # Andhra Pradesh
    "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185),
    "guntur": (16.3067, 80.4365),
    "tirupati": (13.6288, 79.4192),
    "kurnool": (15.8281, 78.0373),
    # Kerala
    "thiruvananthapuram": (8.5241, 76.9366),
    "kochi": (9.9312, 76.2673),
    "ernakulam": (9.9816, 76.2999),
    "kozhikode": (11.2588, 75.7804),
    "thrissur": (10.5276, 76.2144),
    "kollam": (8.8932, 76.6141),
}


def load_all_hospitals(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _CACHED_HOSPITALS
    if _CACHED_HOSPITALS is not None and not force_reload:
        return _CACHED_HOSPITALS

    if not HOSPITALS_DATA_FILE.exists():
        return []

    try:
        with open(HOSPITALS_DATA_FILE, "r", encoding="utf-8") as f:
            _CACHED_HOSPITALS = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load hospitals data: {e}")
        _CACHED_HOSPITALS = []

    return _CACHED_HOSPITALS or []


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def format_distance_label(dist_km: float) -> str:
    """Formats distance nicely as meters (<1 km) or kilometers (>=1 km)."""
    if dist_km < 1.0:
        meters = max(50, int(round(dist_km * 1000 / 10.0) * 10))
        return f"{meters} m away"
    return f"{dist_km:.1f} km away"


def resolve_location_coordinates(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    locality: Optional[str] = None,
    location: Optional[str] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Resolves user coordinates following the priority:
    1. GPS (latitude, longitude provided) -> type: 'gps'
    2. Hierarchical Locality/Taluk/District Geocoding -> type: 'profile' / 'manual'
    3. Verified District Centroid -> type: 'manual'
    4. Default regional fallback -> type: 'default'
    """
    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude), "Current GPS Location", "gps"

    # Try precise hierarchical geocoding
    active_state = state or "Tamil Nadu"
    active_district = district or location or city or "Salem"
    geo_res = geocode_location(
        state=active_state,
        district=active_district,
        taluk=taluk,
        locality=locality,
        pincode=pincode,
    )
    if geo_res.get("status") == "success":
        label_parts = [p for p in [locality, taluk, active_district] if p and p.strip()]
        display_label = ", ".join(label_parts) if label_parts else str(active_district)
        return geo_res["latitude"], geo_res["longitude"], display_label, "profile" if district else "manual"

    # Fallback to District Centroid
    search_term = (location or district or city or "").strip().lower()
    if search_term:
        for key, (lat, lon) in VERIFIED_DISTRICT_CENTERS.items():
            if key in search_term:
                return lat, lon, key.capitalize(), "profile" if district else "manual"

    # Default fallback to Chennai reference
    def_lat, def_lon = VERIFIED_DISTRICT_CENTERS["chennai"]
    return def_lat, def_lon, "Chennai (Regional Reference)", "default"


def search_osm_overpass_hospitals(
    latitude: float,
    longitude: float,
    radius_km: float = 15.0,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Queries live OpenStreetMap Overpass API for real hospitals and health clinics
    within the specified radius. Fails gracefully in <2.5s with zero impact.
    """
    radius_meters = int(radius_km * 1000)
    overpass_query = f"""
    [out:json][timeout:2];
    (
      node["amenity"="hospital"](around:{radius_meters},{latitude},{longitude});
      way["amenity"="hospital"](around:{radius_meters},{latitude},{longitude});
      node["amenity"="clinic"](around:{radius_meters},{latitude},{longitude});
    );
    out center {limit};
    """
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "ArogyaNexus/3.5.0"})

    results: List[Dict[str, Any]] = []
    try:
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            elements = raw.get("elements", [])
            for elem in elements:
                tags = elem.get("tags", {})
                name = tags.get("name") or tags.get("name:en")
                if not name:
                    continue

                lat = elem.get("lat") or elem.get("center", {}).get("lat")
                lon = elem.get("lon") or elem.get("center", {}).get("lon")
                if not lat or not lon:
                    continue

                h_type = tags.get("healthcare") or tags.get("amenity") or "Hospital"
                if "clinic" in h_type.lower():
                    h_type = "Healthcare Clinic"
                else:
                    h_type = "Public Healthcare / Hospital"

                phone = tags.get("phone") or tags.get("contact:phone") or None
                emergency = tags.get("emergency") == "yes"

                addr_parts = [
                    tags.get("addr:street"),
                    tags.get("addr:suburb") or tags.get("addr:district"),
                    tags.get("addr:city"),
                    tags.get("addr:postcode")
                ]
                clean_addr = ", ".join([p for p in addr_parts if p]) or f"Near coordinates {lat:.4f}, {lon:.4f}"

                dist = haversine_distance(latitude, longitude, float(lat), float(lon))
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"

                results.append({
                    "id": f"osm-{elem.get('id', len(results))}",
                    "name": name,
                    "type": h_type,
                    "district": tags.get("addr:district") or tags.get("addr:city") or "Nearby",
                    "state": tags.get("addr:state") or "",
                    "address": clean_addr,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "phone": phone,
                    "open_status": "Emergency Services Available" if emergency else "Open Healthcare Facility",
                    "services": ["Outpatient Care", "General Medicine"] + (["Emergency Services"] if emergency else []),
                    "schemes_accepted": ["PM-JAY", "State Health Mission"],
                    "distance": dist,
                    "distance_km": dist,
                    "distance_label": format_distance_label(dist),
                    "maps_url": maps_url,
                    "directions_url": maps_url,
                    "source": "osm_live",
                })
    except Exception as e:
        # Graceful fallback: never crash or delay user experience
        pass

    return results


def get_nearby_hospitals(
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
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Finds and ranks verified healthcare facilities and government hospitals.
    Location Priority:
    1. Exact GPS Coordinates
    2. Hierarchical Saved Profile Location (State -> District -> Taluk -> Locality)
    3. Manual District / City Search
    Computes real Haversine distances and filters by radius_km.
    """
    hospitals = load_all_hospitals()
    filtered: List[Dict[str, Any]] = []

    target_lat, target_lon, loc_label, loc_type = resolve_location_coordinates(
        latitude=latitude,
        longitude=longitude,
        state=state,
        district=district,
        taluk=taluk,
        locality=locality,
        location=location,
        city=city,
        pincode=pincode,
    )

    norm_district = (district or location or city or "").strip().lower()
    norm_query = (query or "").strip().lower()

    # Determine practical search radius (default 50km for district search, or explicit radius_km)
    effective_radius = float(radius_km) if radius_km is not None else 65.0

    for h in hospitals:
        match = True
        h_district = h.get("district", "").lower()
        h_name = h.get("name", "").lower()
        h_type = h.get("type", "").lower()

        # If a specific district filter is explicitly set (and not 'all')
        if norm_district and norm_district not in ("all", "all tamil nadu", "all india"):
            if norm_district not in h_district and h_district not in norm_district:
                # If GPS/explicit coordinates are provided, evaluate purely by geographic distance
                if latitude is None or longitude is None:
                    match = False

        if norm_query and not (norm_query in h_name or norm_query in h_type or norm_query in h_district):
            match = False

        if match:
            item = dict(h)
            dist: Optional[float] = None
            if target_lat is not None and target_lon is not None:
                dist = haversine_distance(target_lat, target_lon, h["latitude"], h["longitude"])
                item["distance"] = dist
                item["distance_km"] = dist
                item["distance_label"] = format_distance_label(dist)

                # Filter by search radius if an explicit radius was provided or if coordinates were used
                if radius_km is not None and dist > radius_km:
                    continue
            else:
                item["distance"] = None
                item["distance_km"] = None
                item["distance_label"] = h.get("district", "Tamil Nadu")

            # Verified maps URL and direct Google Maps navigation link
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={h['latitude']},{h['longitude']}"
            item["maps_url"] = maps_url
            item["directions_url"] = maps_url

            phone_val = str(h.get("phone") or "").strip()
            item["phone"] = phone_val if phone_val else None
            item["source"] = "verified_registry"

            filtered.append(item)

    # If 0 results within radius and coordinates are valid, try live OSM query
    if len(filtered) == 0 and target_lat is not None and target_lon is not None:
        osm_results = search_osm_overpass_hospitals(
            latitude=target_lat,
            longitude=target_lon,
            radius_km=effective_radius,
            limit=limit,
        )
        if osm_results:
            filtered.extend(osm_results)

    # Clinical condition prioritization (Emergency/Trauma or Maternal)
    is_maternity_concern = any(w in norm_query for w in ["pregnant", "pregnancy", "delivery", "maternity", "baby", "infant", "கர்ப்பம்", "பிரசவம்"])
    is_emergency_concern = any(w in norm_query for w in ["chest pain", "heart", "cardiac", "stroke", "accident", "trauma", "severe", "emergency", "நெஞ்சு"])

    def _hospital_sort_key(item: Dict[str, Any]):
        dist = item["distance"] if item["distance"] is not None else 99999.0
        priority = 1
        services_str = " ".join(item.get("services", [])).lower() + " " + item.get("type", "").lower()
        if is_maternity_concern and any(k in services_str for k in ["maternity", "delivery", "pediatric", "obstetric", "nicu"]):
            if dist <= 25.0:
                priority = 0
        elif is_emergency_concern and any(k in services_str for k in ["trauma", "emergency", "cardiology", "level-1"]):
            if dist <= 25.0:
                priority = 0
        return (priority, dist)

    filtered.sort(key=_hospital_sort_key)

    return {
        "status": "success",
        "source": "verified_registry",
        "user_location": {
            "latitude": target_lat,
            "longitude": target_lon,
            "label": loc_label,
            "type": loc_type,
        },
        "radius_km": effective_radius,
        "total": len(filtered),
        "district": district or location or "All",
        "hospitals": filtered[:limit],
    }
