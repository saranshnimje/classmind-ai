# Optional Streamlit Dashboard

Isolated from the main React/Vite app.

## Run locally

```bash
cd streamlit_dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Environment variables
- `VITE_API_BASE` or `API_URL`: backend base URL (default `http://127.0.0.1:8000/api`)

## Features shown
- Session overview using backend `/sessions`
- Attendance summary description
- Engagement indicators (descriptive proxies only)
- Trends over time (when data exists)
- Data-quality notes instead of fabricated performance scores
- Clear demo-data labeling when records are unavailable
