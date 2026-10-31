# Activity 6.3 Evidence Index

| Scenario | Evidence | Status |
|---|---|---|
| Fluctuating lighting / detection loss | docs/evidence/activity-6.3/edge-cases.txt (test_detect_failure...) | VERIFIED |
| Background noise / VAD | docs/evidence/activity-6.3/edge-cases.txt (test_vad_background_noise...) | VERIFIED |
| Partial occlusion / duplicate tracks | docs/evidence/activity-6.3/edge-cases.txt (test_duplicate_track...) | VERIFIED |
| Short appearances / sustained presence | docs/evidence/activity-6.3/edge-cases.txt (test_single_frame...) | VERIFIED |
| Intermittent / missing audio | docs/evidence/activity-6.3/edge-cases.txt (test_missing_audio..., test_delayed_audio...) | VERIFIED |
| Multimodal fusion — all combos | docs/evidence/activity-6.3/edge-cases.txt + backend/app/services/fusion.py | VERIFIED |
| Streamlit import | docs/evidence/activity-6.3/streamlit-import.txt (created by manual check) | PARTIALLY VERIFIED |
| Streamlit server start | Manual step required (streamlit run streamlit_dashboard/app.py) | NOT VERIFIED — manual |
| Docker / API health | docs/evidence/activity-6.3/docker-status.txt | VERIFIED |

Notes:
- No biometric/face/emotion identification added.
- Engagement proxies remain descriptive.
- Synthetic/demo data clearly labelled.
- No private recordings exposed.
