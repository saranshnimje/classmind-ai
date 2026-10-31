# Optional Streamlit Dashboard (EPIC 6.2)

## Setup
- Located in `streamlit_dashboard/`
- Uses existing backend APIs (same `VITE_API_BASE` / `API_URL` pattern)
- Separate `requirements.txt` so it does not interfere with main app

## Dependencies
- `streamlit>=1.34`
- `pandas>=2.0`
- `plotly>=5.20`
- `requests>=2.30`

## Run command
```bash
cd streamlit_dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Features shown
- Session overview
- Attendance summary description
- Engagement indicators (descriptive only, no performance claims)
- Time-series trends when data exists
- Rule-based suggestions labeled as descriptive
- Clear empty-state and demo-data labels
- Graceful backend error handling

## Limitations
- Does not replace the React/Vite primary frontend.
- Streamlit is optional; not required for Docker or deployment.
- Uses synthetic/demo data when no records exist.
- Does not display private recordings.
