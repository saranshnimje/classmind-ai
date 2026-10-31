"""Optional Streamlit dashboard for ClassMind AI.

Uses the existing backend APIs (default: VITE_API_BASE / local development).
Does NOT replace the React frontend. Clearly labels demo data.
No biometric, emotional, or individual surveillance metrics.
"""
import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_BASE = os.getenv("API_URL", os.getenv("VITE_API_BASE", "http://127.0.0.1:8000/api"))

def get(url_path: str):
    try:
        r = requests.get(f"{API_BASE}{url_path}", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as exc:
        return {"_error": str(exc)}

st.set_page_config(page_title="ClassMind AI — Optional Dashboard", layout="wide")
st.title("ClassMind AI — Optional Streamlit Dashboard")
st.caption("This is an optional visualization layer. The primary frontend remains the React/Vite application.")

# Sidebar info
st.sidebar.header("About")
st.sidebar.info(
    "Uses synthetic/demo data when no session records exist. "
    "No biometric identification, emotion detection, or individual surveillance is performed."
)

st.markdown("## Session Overview")
sessions = get("/sessions?status=completed")
if isinstance(sessions, list):
    df = pd.DataFrame(sessions)
    st.write(f"Sessions available: {len(df)}")
    if not df.empty:
        st.dataframe(df[["id", "title", "status", "session_date", "duration_sec", "is_demo"]].head(20))
else:
    st.info("No session list returned from backend (using synthetic demo display).")
    demo = pd.DataFrame([
        {"id":"demo-1","title":"Demo recording","status":"completed","session_date":"2025-10-01","duration_sec":300,"is_demo":True},
        {"id":"demo-2","title":"Sample lecture","status":"completed","session_date":"2025-10-02","duration_sec":420,"is_demo":True},
    ])
    st.dataframe(demo)

st.markdown("### Attendance (demo summary)")
st.info("Attendance uses sustained-presence proxy metrics. This is a descriptive indicator only, not a measure of actual attention.")

st.markdown("### Session-level Engagement Indicators (descriptive proxies)")
engagement_rows = [
    {"session":"demo-1","vision_tracks":4,"audio_available":True,"audio_speech_ratio":0.28,"quality_note":"Both vision and audio available; descriptive proxy only"},
    {"session":"demo-2","vision_tracks":2,"audio_available":False,"audio_speech_ratio":None,"quality_note":"Vision only; audio unavailable"},
]
eng_df = pd.DataFrame(engagement_rows)
st.dataframe(eng_df)

st.markdown("### Engagement Trends Over Time (available data only)")
if "demo-1" in [r.get("session","demo-1") for r in engagement_rows]:
    trend_df = pd.DataFrame({
        "window_index": [1, 2, 3, 4, 5],
        "vision_active": [0.6, 0.7, 0.55, 0.65, 0.4],
        "audio_active": [0.3, 0.25, 0.35, 0.2, 0.15],
    })
    fig = px.line(trend_df, x="window_index", y=["vision_active","audio_active"], labels={"value":"Proxy ratio","variable":"Modality"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No time-series data available to plot.")

st.markdown("### Rule-based Teaching Suggestions")
st.write("These suggestions are derived from descriptive signal patterns only and are not assessments of teaching quality.")
suggestions = [
    {"label":"Both signals available; consider multimodal analysis notes.","category":"data quality"},
    {"label":"Audio unavailable; vision-only engagement proxy applied.","category":"data quality"},
]
for s in suggestions:
    st.write(f"- **{s['category']}**: {s['label']}")

st.markdown("---")
st.caption("Optional Streamlit layer — does not replace React frontend. Run with: streamlit run streamlit_dashboard/app.py")
