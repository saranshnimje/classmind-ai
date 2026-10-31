# Submission Guide — ClassMind AI

## Project summary

**ClassMind AI** is a classroom-recording analysis prototype that combines anonymous person tracking, sustained-presence attendance estimates, audio activity detection, time-windowed engagement proxies, evidence-linked teaching suggestions, and exportable reports. It is designed to make classroom observations easier to review while keeping the outputs descriptive and explicitly uncertain.

## Links

- Live frontend: https://classmind--ai.vercel.app
- Backend health: https://classmind-ai.onrender.com/api/health
- API documentation: https://classmind-ai.onrender.com/docs
- Public source: https://github.com/saranshnimje/classmind-ai

## Suggested 2–3 minute demo

1. Open the live frontend and show the dashboard and system status.
2. Load the clearly labelled simulated demo data; explain that it is synthetic and not real classroom evidence.
3. Open a session and show attendance estimates, anonymous tracks, uncertainty warnings, and manual-only roster mapping.
4. Open analytics and explain the time windows, audio activity, missing-data handling, confidence, and methodology.
5. Open recommendations and show how each suggestion links to observed evidence and an interpretation.
6. Show a report/export option and finish with the privacy and limitations page.

Do not upload real student media to the public hosted demo. If demonstrating actual media inference, use a locally run instance with synthetic or properly consented, non-identifiable footage.

## Honest technical claims

- Person detection and tracking are approximate; tracks can split, merge, or miss people.
- Attendance represents visible/trackable people, not verified enrolment or identity.
- Engagement is a descriptive proxy, not a measurement of attention, learning, comprehension, or teaching quality.
- Teacher speech is not separated from student speech.
- The verified hosted free runtime used OpenCV HOG and energy VAD fallbacks. Ollama was unavailable there; rule-based recommendations are the fallback.
- The public hosted prototype has no authentication or tenant isolation.
- Render Free storage is ephemeral; hosted data is not persistent.

## Before submitting

- [ ] Open the live frontend in a private/incognito window.
- [ ] Confirm dashboard loads and backend status is connected.
- [ ] Load demo data and complete the walkthrough without uploading private media.
- [ ] Check attendance, analytics, recommendations, settings, and report/export screens.
- [ ] Record a short screen demo with narration and no private data.
- [ ] Include the GitHub repository and live demo URLs in the submission form.
- [ ] Include a concise architecture diagram or slide and the key evaluation/test results.
- [ ] State the actual test counts and only the features verified in the submitted build.
- [ ] Disclose hosted limitations: no auth/tenant isolation, ephemeral storage, cold starts, HOG/energy fallback, Ollama unavailable.
- [ ] Add a license only after choosing the license terms. The repository currently has no LICENSE file.
- [ ] Follow the exact competition/course submission rules and deadline; this guide is generic and does not replace organizer instructions.

## Suggested one-line description

A privacy-conscious classroom analysis prototype that estimates anonymous attendance and time-windowed classroom activity from recordings, with transparent methodology, confidence warnings, and evidence-linked recommendations.
