import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from services.locationService import geocode_location, reverse_geocode, get_location_hierarchy
from services.hospitalService import get_nearby_hospitals, haversine_distance, format_distance_label

client = TestClient(app)


def test_location_hierarchy_structure():
    hierarchy = get_location_hierarchy()
    assert "Tamil Nadu" in hierarchy
    assert "Salem" in hierarchy["Tamil Nadu"]
    assert "Salem Taluk" in hierarchy["Tamil Nadu"]["Salem"]
    assert "Shevapet" in hierarchy["Tamil Nadu"]["Salem"]["Salem Taluk"]
    assert "Chennai" in hierarchy["Tamil Nadu"]
    assert "Karnataka" in hierarchy
    assert "Bengaluru" in hierarchy["Karnataka"]


def test_geocoding_salem_shevapet():
    res = geocode_location(
        state="Tamil Nadu",
        district="Salem",
        taluk="Salem Taluk",
        locality="Shevapet",
        pincode="636001",
    )
    assert res["status"] == "success"
    assert abs(res["latitude"] - 11.6508) < 0.01
    assert abs(res["longitude"] - 78.1402) < 0.01
    assert "Shevapet" in res["label"]
    assert res["hierarchy"]["locality"] == "Shevapet"


def test_geocoding_chennai_park_town():
    res = geocode_location(
        state="Tamil Nadu",
        district="Chennai",
        taluk="Egmore",
        locality="Park Town",
        pincode="600003",
    )
    assert res["status"] == "success"
    assert abs(res["latitude"] - 13.0827) < 0.01
    assert abs(res["longitude"] - 80.2707) < 0.01


def test_geocoding_bengaluru():
    res = geocode_location(
        state="Karnataka",
        district="Bengaluru",
        taluk="Bengaluru South",
        locality="Jayanagar",
    )
    assert res["status"] == "success"
    assert abs(res["latitude"] - 12.9250) < 0.02
    assert abs(res["longitude"] - 77.5938) < 0.02


def test_reverse_geocoding():
    res = reverse_geocode(11.6508, 78.1402)
    assert res["status"] == "success"
    assert "latitude" in res
    assert "hierarchy" in res
    assert res["hierarchy"]["district"] in ("Salem", "Tamil Nadu")


def test_distance_formatting():
    assert format_distance_label(0.45) == "450 m away"
    assert format_distance_label(0.08) == "80 m away"
    assert format_distance_label(1.23) == "1.2 km away"
    assert format_distance_label(15.78) == "15.8 km away"


def test_nearby_hospitals_salem_shevapet_coordinates():
    # Coords of Shevapet, Salem
    shevapet_lat, shevapet_lon = 11.6508, 78.1402
    res = get_nearby_hospitals(latitude=shevapet_lat, longitude=shevapet_lon, radius_km=15.0)
    assert res["status"] == "success"
    assert len(res["hospitals"]) > 0

    first_hosp = res["hospitals"][0]
    # Mohan Kumaramangalam GH is on Fort Main Road, right next to Shevapet (<1.5 km)
    assert "Mohan Kumaramangalam" in first_hosp["name"]
    assert first_hosp["distance"] < 2.0
    assert "m away" in first_hosp["distance_label"] or "km away" in first_hosp["distance_label"]
    assert "https://www.google.com/maps/dir/?api=1" in first_hosp["maps_url"]
    assert "0427-2211444" in (first_hosp.get("phone") or "")


def test_radius_expansion_filtering():
    shevapet_lat, shevapet_lon = 11.6508, 78.1402
    # Tight radius: 2 km -> only Mohan Kumaramangalam
    res_tight = get_nearby_hospitals(latitude=shevapet_lat, longitude=shevapet_lon, radius_km=2.0)
    # Expanded radius: 30 km -> includes Omalur, Panamarathupatti, Attur
    res_expanded = get_nearby_hospitals(latitude=shevapet_lat, longitude=shevapet_lon, radius_km=30.0)

    assert len(res_expanded["hospitals"]) >= len(res_tight["hospitals"])


def test_api_endpoints_integration():
    # 1. Geocode endpoint
    geo_resp = client.post("/api/location/geocode", json={
        "state": "Tamil Nadu",
        "district": "Salem",
        "taluk": "Salem Taluk",
        "locality": "Shevapet",
    })
    assert geo_resp.status_code == 200
    geo_data = geo_resp.json()
    assert geo_data["status"] == "success"
    assert abs(geo_data["latitude"] - 11.6508) < 0.01

    # 2. Reverse geocode endpoint
    rev_resp = client.post("/api/location/reverse-geocode", json={
        "latitude": 11.6508,
        "longitude": 78.1402,
    })
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["status"] == "success"

    # 3. Hierarchy endpoint
    hier_resp = client.get("/api/location/hierarchy")
    assert hier_resp.status_code == 200
    assert "Tamil Nadu" in hier_resp.json()

    # 4. Nearby hospitals endpoint with coordinates and radius
    hosp_resp = client.get(f"/api/hospitals/nearby?latitude=11.6508&longitude=78.1402&radius_km=10")
    assert hosp_resp.status_code == 200
    hosp_data = hosp_resp.json()
    assert len(hosp_data["hospitals"]) > 0
