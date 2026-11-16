# GECCO 2026 Sustainability report

The detailed sustainability report for the Genetic and Evolutionary Computation Conference (GECCO)  2026.

---

# Conference Carbon Footprint Calculator 🌱

A simple, interactive tool for conference organisers to estimate the **travel-related carbon emissions** of their event - in just a few clicks.

Built as part of the sustainability monitoring work for the [GECCO](https://gecco-2026.sigevo.org/) conference series.

---

## What it does

Upload a CSV with your participant list, choose the conference venue, and the tool will:

- Calculate the **great-circle distance** from each participant's origin to the venue
- Apply the appropriate emission factor (air, car, or train)
- Return the **total emissions** and **per-participant average**
- Show breakdowns by country, attendance mode, and distance

---

## Quick start

```bash
# 1. Clone the repository
git clone https://github.com/AbdallahHisham/conference-carbon-calculator.git
cd conference-carbon-calculator

# 2. Install dependencies (Python 3.10+ recommended)
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Input CSV format

Your file needs at minimum a **`country`** and **`attendance_mode`** column.
Adding a **`city`** column gives more accurate distances.

| Column | Required | Values | Notes |
|---|---|---|---|
| `city` | Optional | Any city name | Improves accuracy over country centroid |
| `country` | **Required** | Any country name | Used for geocoding |
| `attendance_mode` | **Required** | `in_person` / `virtual` | Virtual participants get zero travel emissions |
| `transport_mode` | Optional | `air` / `car` / `train` | Defaults to `air` if not provided |

A ready-to-use example is included in [`sample_participants.csv`](sample_participants.csv).

---

## Methodology

Distances are calculated as **great-circle (geodesic) distances**, doubled for the return journey.

| Mode | Emission factor | Source |
|---|---|---|
| Air | 0.0842 kg CO₂eq / passenger-km | DESNZ GHG Conversion Factors 2026 |
| Car | 0.17074 kg CO₂eq / km | DESNZ GHG Conversion Factors 2026 |
| Train | 0.0035 kg CO₂eq / passenger-km | Approximate international average |

- Radiative forcing from aviation is **not** included.
- Coordinates are resolved via the free [OpenStreetMap Nominatim](https://nominatim.org/) geocoder. The tool falls back to the country centroid if a city cannot be found.
- Virtual participants are assigned **zero** travel emissions (home-office energy is not included in this tool; see the full GECCO report for that).

This tool covers **travel only**. For a complete conference carbon footprint (hotel, catering, venue energy, materials, virtual-attendance home-office energy), refer to the GECCO 2026 Sustainability Report.

---

## Project structure

```
conference-carbon-calculator/
├── app.py                   # Streamlit web app
├── calculator.py            # Core calculation functions (import-friendly)
├── sample_participants.csv  # Example input file
├── requirements.txt         # Python dependencies
└── README.md
```

The calculation logic in `calculator.py` is kept separate so you can import it into your own scripts without needing Streamlit.

---

## Citation

If you use this tool in published work, please cite the GECCO sustainability reports:

> Reigada, L., Vasconcelos, J., Rodrigues, M., Pereira, J., Silva, S., & Silva, C. (2024).
> Sustainability of GECCO 2023. *SIGEVOlution*, 17(1).
> https://doi.org/10.1145/3687242.3687243

> Ekárt, A., Abdelhameed, A., Silva, C., & Trujillo, L. (2026).
> Sustainability of GECCO Conferences (2023-2026).

---

## License

MIT - free to use, adapt, and share.
