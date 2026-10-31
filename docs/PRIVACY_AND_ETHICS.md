# Privacy and Ethics

ClassMind AI processes classroom recordings. That is sensitive data, even when the
software does not identify anyone. This document states what the app does, what it does
not do, and the conditions for responsible use.

## Privacy commitments

1. **Local processing only.** Video, audio, extracted frames, the database, and reports
   stay in the configured local data directory. The app does not call a cloud AI service
   and does not send telemetry.
2. **No biometric identification.** There is no face recognition, face embedding,
   biometric template, speaker identification, voiceprint, emotion detection, or
   demographic inference.
3. **Anonymous tracks.** Detected people are numbered participants. Identity is attached
   only when a teacher manually maps a track to a roster entry, and the mapping is marked
   as manual and uncertain.
4. **Data minimisation.** Only the media needed for analysis is stored. Retention can
   delete old sessions automatically, and media can be deleted after processing.
5. **No public URLs.** Media is not served from a public bucket or CDN. Exports are
   generated locally.
6. **Transparent outputs.** Reports state the method, limitations, and data-quality
   warnings. Demo data is always labelled as simulated.

## What the system observes

- Number and position of **people** (not faces or identities).
- Approximate movement between sampled frames.
- Presence duration and first/last observation time.
- Coarse frontal-face position as a head-orientation proxy.
- Speech activity from local voice activity detection.

## What the system does not do

- It does not know who a person is.
- It does not measure attention, comprehension, emotion, intelligence, or learning.
- It does not distinguish teacher speech from student speech.
- It does not grade, rank, discipline, or profile students.
- It does not infer protected characteristics.
- It does not replace a teacher's observation or professional judgement.

## Ethical use

Use ClassMind AI only when you have a legitimate educational purpose and the appropriate
consent, notice, and institutional approval. In particular:

- Inform participants that a recording is being analysed and explain what is measured.
- Follow local law and institutional policy for recording, retention, and access.
- Restrict access to the machine and data directory.
- Do not use engagement values in grades, discipline, promotion, or employment decisions.
- Do not use attendance estimates as the sole record of attendance; verify against a
  reliable source.
- Treat `unconfirmed` tracks as unknown, not as absence.
- Review data-quality warnings before drawing conclusions.
- Delete recordings when they are no longer needed.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Re-identification by combining data | No biometrics; anonymous tracks; access control; retention limits. |
| Over-interpreting engagement | Explicit proxy definition, confidence labels, warnings, and limitations in UI and reports. |
| Missing data treated as low engagement | Missing signals are excluded and scored as `null`, never zero. |
| Attendance errors from track fragmentation | Warnings, uncertainty flags, manual review, and no automatic identity mapping. |
| Sensitive media leaking | Local storage, generated filenames, no public URLs, retention controls. |
| Model bias or poor performance | Documented limitations; quality warnings; human review required. |

## Data location and deletion

By default, data lives under `./data`:

```
data/
├── classmind.db
├── sessions/<session_id>/
├── exports/
└── models/
```

Delete a session from the UI to remove its database rows and media directory. Use the
retention setting to remove sessions older than a chosen number of days. Removing the
whole `data/` directory resets the app, but also deletes all recordings and results.

## Demo data

Demo sessions are generated locally from a script. They contain no real inference and are
labelled `Demo data — simulated`. Do not present demo values as evidence about a real
class.

## Contact and review

Before deploying in a real institution, have the privacy notice, consent process, data
retention policy, and access controls reviewed by the appropriate data protection or
legal contact.
