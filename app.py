"""
Conference Carbon Footprint Calculator
=======================================
A simple tool for conference organisers to estimate the travel-related
carbon emissions of their event.

How to run:
    pip install -r requirements.txt
    streamlit run app.py

What you need:
    A CSV file with one row per participant containing at least:
      - city          : departure city (improves accuracy; country centroid used if missing)
      - country       : departure country
      - attendance_mode : 'in_person' or 'virtual'
      - transport_mode  : 'air', 'car', or 'train'  (optional; defaults to 'air')

See sample_participants.csv for a ready-to-use example.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import time

from calculator import (
    KNOWN_VENUES,
    geocode_location,
    calculate_distance_km,
    emission_for_participant,
    summarise,
    EF_AIR,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Conference Carbon Calculator",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Conference Carbon Footprint Calculator")
st.markdown(
    "Estimate the **travel-related carbon emissions** of your conference. "
    "Upload a CSV of participants, pick your venue, and get results in seconds."
)

# ---------------------------------------------------------------------------
# Sidebar: venue selection
# ---------------------------------------------------------------------------
st.sidebar.header("📍 Conference Venue")
venue_choice = st.sidebar.selectbox(
    "Choose a known venue, or select 'Enter manually' below",
    options=["Enter manually"] + list(KNOWN_VENUES.keys()),
)

if venue_choice == "Enter manually":
    venue_city    = st.sidebar.text_input("Venue city", placeholder="e.g. Vienna")
    venue_country = st.sidebar.text_input("Venue country", placeholder="e.g. Austria")
    venue_coords  = None   # will be geocoded later
else:
    venue_coords  = KNOWN_VENUES[venue_choice]
    venue_city    = venue_choice
    venue_country = ""

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Options")
use_city = st.sidebar.checkbox(
    "Use city-level precision for origins",
    value=True,
    help="When ticked, the tool geocodes the 'city' column for more accurate distances. "
         "Untick to use country centroids only (faster, no internet needed for participants).",
)

# ---------------------------------------------------------------------------
# Main: file upload
# ---------------------------------------------------------------------------
st.subheader("📂 Upload your participant list")
st.markdown(
    "Your CSV needs at least a **`country`** and **`attendance_mode`** column. "
    "Adding a **`city`** column improves accuracy. "
    "Download the sample below to see the expected format."
)

col_dl, col_up = st.columns([1, 2])
with col_dl:
    with open("sample_participants.csv", "rb") as f:
        st.download_button(
            "⬇️ Download sample CSV",
            data=f,
            file_name="sample_participants.csv",
            mime="text/csv",
        )

with col_up:
    uploaded = st.file_uploader("Upload your CSV", type="csv")

if uploaded is None:
    st.info("👆 Upload a CSV to get started, or use the sample file above.")
    st.stop()

# ---------------------------------------------------------------------------
# Load and validate the CSV
# ---------------------------------------------------------------------------
df = pd.read_csv(uploaded)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

required = {"country", "attendance_mode"}
missing  = required - set(df.columns)
if missing:
    st.error(f"Your CSV is missing required column(s): **{', '.join(missing)}**. "
             f"Please check the sample file for the expected format.")
    st.stop()

if "city" not in df.columns:
    df["city"] = ""
if "transport_mode" not in df.columns:
    df["transport_mode"] = "air"

df["city"]          = df["city"].fillna("").astype(str).str.strip()
df["country"]       = df["country"].fillna("").astype(str).str.strip()
df["attendance_mode"]= df["attendance_mode"].fillna("in_person").astype(str).str.strip()
df["transport_mode"] = df["transport_mode"].fillna("air").astype(str).str.strip()

st.success(f"Loaded **{len(df)} participants** from {df['country'].nunique()} countries.")
with st.expander("Preview uploaded data"):
    st.dataframe(df.head(10), use_container_width=True)

# ---------------------------------------------------------------------------
# Resolve venue coordinates
# ---------------------------------------------------------------------------
if venue_coords is None:
    if not venue_city or not venue_country:
        st.warning("Please enter both a venue city and country in the sidebar.")
        st.stop()
    with st.spinner(f"Looking up coordinates for {venue_city}, {venue_country}…"):
        gc = Nominatim(user_agent="conference_carbon_calculator")
        venue_coords = geocode_location(venue_city, venue_country, geocoder=gc)
    if venue_coords is None:
        st.error(f"Could not find coordinates for '{venue_city}, {venue_country}'. "
                 "Try a larger nearby city or check the spelling.")
        st.stop()
    st.sidebar.success(f"Venue found: {venue_coords[0]:.3f}°, {venue_coords[1]:.3f}°")

# ---------------------------------------------------------------------------
# Geocode participant origins and calculate emissions
# ---------------------------------------------------------------------------
run_btn = st.button("🔢 Calculate emissions", type="primary")
if not run_btn:
    st.info("👆 Press **Calculate emissions** when you're ready.")
    st.stop()

gc = Nominatim(user_agent="conference_carbon_calculator")

rows = []
failed = []

progress = st.progress(0, text="Geocoding participant origins…")
n = len(df)

for i, row in df.iterrows():
    progress.progress((i + 1) / n, text=f"Processing {i+1} / {n}…")

    # --- find origin coordinates ---
    coords = None
    if use_city and row["city"]:
        coords = geocode_location(row["city"], row["country"], geocoder=gc)
    if coords is None:
        # fall back to country centroid
        coords = geocode_location("", row["country"], geocoder=gc)

    if coords is None:
        failed.append(row["country"])
        rows.append({**row.to_dict(), "origin_lat": None, "origin_lon": None,
                     "distance_km": None, "emissions_kg": 0.0})
        continue

    dist_km   = calculate_distance_km(coords, venue_coords)
    emissions = emission_for_participant(dist_km, row["attendance_mode"], row["transport_mode"])

    rows.append({**row.to_dict(),
                 "origin_lat":   coords[0],
                 "origin_lon":   coords[1],
                 "distance_km":  round(dist_km, 1),
                 "emissions_kg": round(emissions, 2)})

progress.empty()
results = pd.DataFrame(rows)

if failed:
    st.warning(f"Could not geocode {len(failed)} participant(s) from: "
               f"{', '.join(set(failed))}. Their travel emissions are set to 0.")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
summary = summarise(results)

st.markdown("---")
st.subheader("📊 Results")

# Headline metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total travel emissions",    f"{summary['total_t']:.1f} t CO₂eq")
c2.metric("Per participant (all)",      f"{summary['per_all_kg']:.0f} kg CO₂eq")
c3.metric("Per in-person participant",  f"{summary['per_ip_kg']:.0f} kg CO₂eq")
c4.metric("Participants",
          f"{summary['n_ip']} in-person / {summary['n_vt']} virtual")

st.markdown("---")

# Top emitting countries
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Top 10 countries by total travel emissions**")
    top_countries = (
        results.groupby("country")["emissions_kg"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_countries["emissions_t"] = (top_countries["emissions_kg"] / 1000).round(2)
    fig_bar = px.bar(
        top_countries,
        x="emissions_t",
        y="country",
        orientation="h",
        labels={"emissions_t": "Total emissions (t CO₂eq)", "country": "Country"},
        color="emissions_t",
        color_continuous_scale="Reds",
    )
    fig_bar.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=0, r=0, t=10, b=0),
        height=350,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_b:
    st.markdown("**Emissions by attendance mode**")
    mode_summary = (
        results.groupby("attendance_mode")["emissions_kg"]
        .sum()
        .reset_index()
    )
    mode_summary["emissions_t"] = (mode_summary["emissions_kg"] / 1000).round(2)
    fig_pie = px.pie(
        mode_summary,
        values="emissions_t",
        names="attendance_mode",
        color_discrete_sequence=["#27AE60", "#2980B9"],
        hole=0.4,
    )
    fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

# Distance vs emissions scatter
st.markdown("**Distance vs. emissions per participant**")
fig_scatter = px.scatter(
    results[results["distance_km"].notna() & (results["emissions_kg"] > 0)],
    x="distance_km",
    y="emissions_kg",
    color="attendance_mode",
    hover_data=["city", "country", "transport_mode"],
    labels={
        "distance_km":   "One-way distance (km)",
        "emissions_kg":  "Emissions (kg CO₂eq)",
        "attendance_mode": "Mode",
    },
    color_discrete_map={"in_person": "#C0392B", "virtual": "#2980B9"},
)
fig_scatter.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
st.plotly_chart(fig_scatter, use_container_width=True)

# Detailed results table
st.markdown("---")
st.subheader("📋 Full results table")
display_cols = [c for c in
    ["city", "country", "attendance_mode", "transport_mode",
     "distance_km", "emissions_kg"]
    if c in results.columns]
st.dataframe(
    results[display_cols].sort_values("emissions_kg", ascending=False),
    use_container_width=True,
)

# Download results
csv_out = results[display_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download full results as CSV",
    data=csv_out,
    file_name="carbon_footprint_results.csv",
    mime="text/csv",
)

# ---------------------------------------------------------------------------
# Methodology note
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📖 Methodology")
st.markdown(f"""
Distances are calculated as great-circle (geodesic) distances from the departure
city (or country centroid) to the conference venue, **doubled** to account for the
return journey.

| Transport mode | Emission factor | Source |
|---|---|---|
| Air (international, avg. passenger) | {EF_AIR} kg CO₂eq / passenger-km | DESNZ GHG Conversion Factors 2026 |
| Car | 0.17074 kg CO₂eq / km | DESNZ GHG Conversion Factors 2026 |
| Train | 0.0035 kg CO₂eq / passenger-km | Approximate international average |

Radiative forcing from aviation is **not** included in the air factor.
Virtual participants are assigned **zero** travel emissions.

Coordinates are resolved using the OpenStreetMap Nominatim geocoder.
If a city cannot be found, the tool falls back to the country centroid.

For a full conference carbon footprint (including hotel, food, venue energy,
and virtual-attendance home-office energy), see the
[GECCO 2026 Sustainability Report](https://github.com/).
""")
