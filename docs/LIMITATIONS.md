# Limitations

ClassMind AI produces **estimates from sampled, noisy sensor data**. The following
limitations are inherent to the approach and are surfaced in the UI and reports.

## Detection and tracking

- Person detection is not identity detection. A track is an anonymous cluster of
  detections, not a verified student.
- Tracks can fragment when people are occluded, leave the frame, or move quickly. Fragment
  stitching reduces but does not eliminate this.
- Tracks can merge when people overlap, especially in crowded rooms.
- Small people, low light, motion blur, and wide camera angles reduce recall.
- The number of tracks is not the number of students in the room.

## Attendance

- Attendance reflects who was **visible and trackable** during sampled frames.
- A student who is present but occluded, still, or out of frame may be missed.
- A student who walks through the frame may be counted as a short track.
- `unconfirmed` means insufficient observed time, not absence.
- Late classification depends on the first sampled observation, which can be delayed by
  sampling or detection misses.
- Manual roster mapping is a teacher assertion, not a biometric match.

## Engagement proxy

- The score is a descriptive blend of movement, active presence, and speech activity.
- It is **not** attention, engagement in the psychological sense, comprehension,
  learning, or teaching quality.
- A still classroom can score low even when students are listening intently.
- A noisy, moving classroom can score high without learning.
- Speech activity does not distinguish teacher from students, or on-task from off-task
  talk.
- Missing audio or video lowers confidence; it is never treated as low engagement.
- Window boundaries are arbitrary and can hide short events.

## Head orientation

- The head-orientation signal is a frontal-face-position proxy from a Haar cascade.
- It is not gaze tracking and cannot tell what a person is looking at.
- Side profiles, turned heads, masks, and small faces are usually `unknown`.
- Face visibility is often low in classroom-wide shots.

## Audio

- Energy VAD is sensitive to background noise and may mark noise as speech.
- Silero VAD is speech-oriented but still affected by music, noise, and overlapping talk.
- The system does not transcribe speech, identify speakers, or analyse content.
- Separate audio and video tracks are aligned from time zero; drift is warned about.

## Recommendations

- Rule-based suggestions are deterministic and limited to the conditions implemented.
- They describe patterns, not causes.
- Optional Ollama suggestions depend on the local model and can be wrong or generic.
- Suggestions are decision support only and require human judgement.

## Performance

- YOLO CPU inference is slow; a long recording at a short sample interval can take a long
  time.
- The frame cap and analysis width trade accuracy for speed.
- HOG is faster but less accurate than YOLO on many classroom scenes.
- Live capture depends on camera drivers and permissions and is not verified on every
  platform.

## Operational

- The app has no authentication and is intended for a trusted local machine. Do not
  expose it to the public internet.
- SQLite is suitable for a single local user, not concurrent multi-user deployment.
- Docker packaging is provided but not verified in every environment.
- Retention and deletion depend on correct configuration and filesystem permissions.

## Interpretation guidance

Use the numbers to ask better questions, not to make high-stakes decisions. Cross-check
with direct observation, student work, and context. Treat low confidence and quality
warnings as reasons to look more carefully, not as evidence about students.
