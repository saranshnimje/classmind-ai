# Multimodal Signal Fusion (EPIC 4.2)

## Architecture
- Vision pipeline (`backend/app/services/vision.py`) detects/tracks people.
- Audio pipeline (`backend/app/services/audio.py`) measures voice-activity ratios using energy VAD.
- Fusion module (`backend/app/services/fusion.py`) combines observations by session and timestamp.
- Analytics (`backend/app/services/analytics.py`) produces window-level engagement proxies.

## Data flow
1. Video + audio uploaded → pipeline extracts tracks + audio intervals.
2. Fusion describes which modalities were available and explains missing signals.
3. Analytics builds descriptive windows using vision tracks and audio ratios.
4. Results include quality warnings, modality flags, and methodology notes.

## Missing-modality behavior
- Vision-only: audio unavailable explained; vision-only proxies kept.
- Audio-only: vision unavailable explained; audio-only proxies kept.
- Both missing: no arbitrary score; empty descriptive result.
- Invalid timestamps / duplicates: validated by `validate_fusion_input`.

## Ethical / privacy boundaries
- No face recognition, biometric identification, emotion detection, or speaker identification.
- Engagement indicators are descriptive proxies only.
- No claim of measuring attention, learning ability, or academic performance.
- Synthetic/demo data clearly labeled.
