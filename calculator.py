"""
Core carbon footprint calculation logic for conference travel.

Methodology follows ISO 14067 principles and uses emission factors from the
UK Department for Energy Security and Net Zero (DESNZ) GHG Conversion Factors 2026.

You can import these functions into your own scripts, or just run the Streamlit
app (app.py) for an interactive experience.
"""

from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

# ---------------------------------------------------------------------------
# Emission factors (kg CO2eq per passenger-km, return journey)
# Source: DESNZ GHG Conversion Factors 2026
# ---------------------------------------------------------------------------
EF_AIR   = 0.0842    # International air travel, average passenger, no radiative forcing
EF_CAR   = 0.17074   # Average car (gasoline)
EF_TRAIN = 0.0035    # Rail (approximate international average)

# A "virtual" participant travels zero km, so their travel emissions are zero.
# If you also want to include home-office energy for virtual attendees, see
# the GECCO 2026 full report (EF = 0.324 kg CO2eq/hour).

KNOWN_VENUES = {
    "San Antonio de Belen, Costa Rica (GECCO 2026)": (9.9946, -84.1665),
    "Malaga, Spain (GECCO 2025)":                    (36.7213, -4.4214),
    "Melbourne, Australia (GECCO 2024)":              (-37.8136, 144.9631),
    "Lisbon, Portugal (GECCO 2023)":                  (38.7169, -9.1399),
    "Krakow, Poland":                                 (50.0647, 19.9450),
    "Boston, USA":                                    (42.3601, -71.0589),
    "Amsterdam, Netherlands":                         (52.3676, 4.9041),
    "Tokyo, Japan":                                   (35.6762, 139.6503),
    "Singapore":                                      (1.3521, 103.8198),
}


def geocode_location(city: str, country: str, geocoder=None) -> tuple[float, float] | None:
    """
    Convert a city + country string into (latitude, longitude).

    We use the OpenStreetMap Nominatim geocoder, which is free but rate-limited
    to 1 request per second - hence the small sleep below. Results are good
    enough for great-circle distance calculations.

    Returns None if the location cannot be found.
    """
    if geocoder is None:
        geocoder = Nominatim(user_agent="conference_carbon_calculator")

    query = f"{city}, {country}" if city and str(city).strip() else str(country)
    try:
        time.sleep(1.1)   # be polite to the free geocoding service
        result = geocoder.geocode(query, timeout=10)
        if result:
            return (result.latitude, result.longitude)
    except Exception:
        pass
    return None


def calculate_distance_km(origin: tuple[float, float],
                          venue: tuple[float, float]) -> float:
    """
    Great-circle distance between two (lat, lon) points in km.
    This is the shortest path over the Earth's surface - a good proxy for
    actual flight distance on long-haul routes.
    """
    return geodesic(origin, venue).km


def emission_for_participant(distance_km: float,
                             attendance_mode: str,
                             transport_mode: str) -> float:
    """
    Carbon footprint (kg CO2eq) for one participant's travel to and from the venue.

    distance_km      : one-way great-circle distance from origin to venue
    attendance_mode  : 'in_person' or 'virtual'
    transport_mode   : 'air', 'car', or 'train'

    The return journey is included automatically (distance × 2).
    Virtual participants produce zero travel emissions.
    """
    if str(attendance_mode).strip().lower() in ("virtual", "online", "remote"):
        return 0.0

    mode = str(transport_mode).strip().lower() if transport_mode else "air"
    ef   = {"air": EF_AIR, "car": EF_CAR, "train": EF_TRAIN}.get(mode, EF_AIR)
    return distance_km * 2 * ef   # × 2 for the return journey


def summarise(results_df) -> dict:
    """
    Given a DataFrame that already has 'emissions_kg' and 'distance_km' columns,
    return a summary dictionary with the headline numbers.
    """
    total_kg      = results_df["emissions_kg"].sum()
    total_t       = total_kg / 1000
    n_all         = len(results_df)
    n_ip          = (results_df["attendance_mode"].str.lower()
                     .isin(["in_person", "inperson", "in-person"])).sum()
    n_vt          = n_all - n_ip

    per_all_kg    = total_kg / n_all   if n_all > 0 else 0
    ip_rows       = results_df[results_df["attendance_mode"].str.lower()
                               .isin(["in_person", "inperson", "in-person"])]
    per_ip_kg     = ip_rows["emissions_kg"].mean() if len(ip_rows) > 0 else 0

    return {
        "total_kg":    round(total_kg, 1),
        "total_t":     round(total_t, 2),
        "n_all":       n_all,
        "n_ip":        int(n_ip),
        "n_vt":        int(n_vt),
        "per_all_kg":  round(per_all_kg, 1),
        "per_ip_kg":   round(per_ip_kg, 1),
    }
