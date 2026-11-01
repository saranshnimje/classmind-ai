import {
  Activity,
  AlertTriangle,
  AudioLines,
  BookOpenCheck,
  Camera,
  CheckCircle2,
  Cpu,
  Database,
  EyeOff,
  FileText,
  Gauge,
  Layers,
  Lock,
  ScanFace,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import {
  Badge,
  Card,
  CardHeader,
  InfoNote,
  PageHeader,
} from "../components/ui";
import { useDocumentTitle } from "../lib/hooks";
import { getDeploymentMode, privacyPrinciples, privacyMethodNote, privacySummary } from "../lib/privacy";

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof ShieldCheck;
  title: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            {title}
          </span>
        }
      />
      <div className="space-y-3 p-5 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        {children}
      </div>
    </Card>
  );
}

export function AboutPage() {
  useDocumentTitle("Privacy & method");

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Responsible use"
        title="Privacy & method"
        description="What ClassMind AI measures, how it works, and the limits you should keep in mind. This page is part of the deliverable: the system is designed to be inspected, not trusted blindly."
        actions={
          <Link to="/sessions/new" className="btn btn-primary btn-sm">
            <Camera className="h-3.5 w-3.5" /> New session
          </Link>
        }
      />

      <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            icon: Lock,
            title: "Local processing",
            text: "Media, database and results stay under the local data directory.",
          },
          {
            icon: EyeOff,
            title: "No biometrics",
            text: "No face recognition, no face embeddings, no identity inference.",
          },
          {
            icon: Users,
            title: "Anonymous tracks",
            text: "People are numbered observations until a teacher maps them manually.",
          },
          {
            icon: Gauge,
            title: "Transparent proxy",
            text: "Engagement is a documented blend of observable signals, not a grade.",
          },
        ].map((item) => (
          <Card key={item.title} className="p-4">
            <span className="inline-flex rounded-xl bg-brand-50 p-2 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <item.icon className="h-4 w-4" />
            </span>
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">{item.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              {item.text}
            </p>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Section icon={ShieldCheck} title="Privacy principles">
          <ul className="space-y-2">
            {privacyPrinciples(getDeploymentMode()).map((item) => (
              <li key={item} className="flex gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <InfoNote tone="info" title={privacySummary().title}>
            <p>
              {privacyMethodNote(getDeploymentMode())} {privacySummary().processing}
            </p>
          </InfoNote>
        </Section>

        <Section icon={BookOpenCheck} title="What this system is not">
          <ul className="space-y-2">
            {[
              "It is not a proctoring or surveillance product. It does not detect cheating, phones, or off-task behaviour.",
              "It does not measure learning, understanding, attention or motivation. Engagement is a coarse, descriptive proxy.",
              "It does not identify students. Any name on an attendance row came from a manual teacher mapping.",
              "It does not make automated decisions about students and must not be used for grading, discipline or eligibility.",
              "It does not replace observation, context or professional judgement.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <InfoNote tone="warning" title="Consent and policy">
            <p>
              Obtain the consent and approvals required by your school, district or institution.
              Inform participants that a recording is being analysed, explain the purpose, and
              follow local data-protection rules. If you cannot justify the use, do not record.
            </p>
          </InfoNote>
        </Section>

        <Section icon={Layers} title="How a session is processed">
          <ol className="space-y-3">
            {[
              {
                title: "Media validation",
                text: "FFmpeg probes duration, resolution and audio. Files are copied into the local data directory and validated against format and size limits.",
              },
              {
                title: "Frame sampling",
                text: "Frames are sampled at the configured interval (default 2s) and resized for speed. The number of analysed frames is capped.",
              },
              {
                title: "Person detection",
                text: "YOLO is preferred when installed; an OpenCV HOG fallback and a disabled detector are also available. Detections contain boxes and confidence only.",
              },
              {
                title: "Anonymous tracking",
                text: "Greedy IoU matching with a centre-distance fallback links detections across frames. Short fragments are stitched, but crowded scenes can still fragment.",
              },
              {
                title: "Attendance rules",
                text: "Observed presence is accumulated per track. Present requires the minimum presence time; late uses the first-seen offset; everything else stays unconfirmed.",
              },
              {
                title: "Audio and windows",
                text: "A local VAD estimates speech-active intervals. Vision and audio are aggregated into fixed windows with data-quality flags.",
              },
              {
                title: "Recommendations and reports",
                text: "Rules produce evidence-linked suggestions; optional Ollama can rephrase them. Reports are generated locally as JSON, CSV and printable HTML.",
              },
            ].map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {index + 1}
                </span>
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">{step.title}</p>
                  <p className="mt-0.5 text-slate-600 dark:text-slate-300">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </Section>

        <Section icon={Activity} title="Engagement proxy, in plain language">
          <p>
            Each window blends available signals into a 0–1 score: movement (frame-difference
            activity after compensating for camera motion), active presence (time visible and
            moving), and speech activity. The exact weights and rules are returned by the API and
            shown on the analytics page for every session.
          </p>
          <p>
            <strong>Missing data is never treated as low engagement.</strong> If a window has no
            usable visual data, it is reported as unavailable rather than zero. If audio is missing,
            the visual indicators stand alone and the score&apos;s confidence is reduced.
          </p>
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs dark:border-slate-700 dark:bg-slate-800/40">
            <p className="font-semibold text-slate-700 dark:text-slate-200">Reading the score</p>
            <p className="mt-1">
              0–35% low · 35–60% medium · 60–100% high, with confidence reported separately. These
              bands are descriptive conventions for this app, not validated thresholds. Always read
              the confidence, coverage and warnings alongside the number.
            </p>
          </div>
        </Section>

        <Section icon={Sparkles} title="Recommendations and the local model">
          <p>
            Recommendations are generated by deterministic rules from observed window data. Each
            item includes the category, observed value, interval, evidence and an interpretation.
            This separation is deliberate: you can audit the evidence without trusting the wording.
          </p>
          <p>
            If you enable Ollama, the local model may rephrase or add suggestions. The source is
            labelled on every card, and the rule-based fallback always remains available. No cloud
            language model is used, and no media is sent to the model — only aggregate summary text.
          </p>
          <Badge tone="brand">Rule source: deterministic</Badge>{" "}
          <Badge tone="neutral">Optional LLM source: local Ollama</Badge>
        </Section>

        <Section icon={AlertTriangle} title="Known limitations">
          <ul className="space-y-2">
            {[
              "CPU inference is slow. On a typical laptop, YOLO at 480px can take around two seconds per sampled frame; long recordings should use a larger sample interval.",
              "Crowded or fast-moving scenes cause track fragmentation. A fragmented track can split presence time and produce an unconfirmed result.",
              "Occlusion, low light, unusual camera angles and distant participants reduce detection quality. Check the quality notes before interpreting results.",
              "Head orientation is an approximate frontal-face position proxy, not gaze tracking. Side profiles are usually reported as unknown.",
              "Speech activity does not distinguish teacher from students, nor meaningful talk from noise. It can be high in a noisy room and low in a silent written task.",
              "The engagement proxy has not been validated against learning outcomes. Treat it as a conversation starter, not evidence of teaching quality.",
              "Live camera capture is optional and depends on hardware and permissions; it has not been verified on every platform.",
              "YOLO and Silero VAD are optional third-party dependencies with their own licences. The app runs without them using fallbacks.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section icon={ScanFace} title="Bias and fairness">
          <p>
            Person detectors and face detectors can perform differently across skin tones, lighting,
            clothing, body positions, disabilities and camera angles. Presence tracking may therefore
            under-count some participants. Anonymous tracks and the attendance-rate denominator
            reduce — but do not eliminate — this risk.
          </p>
          <p>
            Do not compare engagement scores between classes, teachers or demographic groups. Do not
            use them in decisions about individuals. If you notice systematic under-detection, treat
            it as a limitation of the recording and the tool, not as evidence about students.
          </p>
        </Section>

        <Section icon={Database} title="Data, retention and deletion">
          <p>
            Media and the SQLite database live under the configured data directory. Deleting a
            session removes its media files, tracks, attendance records, windows and recommendations.
            Retention can remove old sessions automatically at startup or on demand.
          </p>
          <p>
            Derived artefacts include CSV and printable HTML reports. If you export a report, it
            becomes a separate file outside the app; protect it according to your institution&apos;s
            policy.
          </p>
          <p className="flex flex-wrap gap-2">
            <Link to="/settings" className="btn btn-secondary btn-sm">
              <Trash2 className="h-3.5 w-3.5" /> Retention settings
            </Link>
            <Link to="/sessions" className="btn btn-secondary btn-sm">
              <FileText className="h-3.5 w-3.5" /> Manage sessions
            </Link>
          </p>
        </Section>

        <Section icon={Cpu} title="Stack and reproducibility">
          <p>
            Backend: Python, FastAPI, SQLAlchemy, SQLite, OpenCV, NumPy, optional Ultralytics YOLO
            and Silero VAD, FFmpeg via imageio-ffmpeg. Frontend: React, TypeScript, Vite, Tailwind
            CSS, Recharts. Tests: Pytest and Vitest/Testing Library.
          </p>
          <p>
            Demo sessions are explicitly labelled simulated data. They exercise the full interface
            without pretending to be inference results from a real classroom.
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge tone="neutral">No cloud AI</Badge>
            <Badge tone="neutral">No public media URLs</Badge>
            <Badge tone="neutral">No biometric templates</Badge>
            <Badge tone="neutral">Local SQLite</Badge>
          </div>
        </Section>

        <Section icon={AudioLines} title="If something looks wrong">
          <p>
            Start with the session quality notes: detector, sampled frames, brightness, camera motion
            and audio availability explain most surprising results. Check whether the recording angle
            makes participants hard to see, and whether the sample interval was too coarse.
          </p>
          <p>
            A failed job stores its error message on the session. You can replace the media, lower the
            detector resolution or switch to the HOG fallback, then re-run analysis. See the project
            README and troubleshooting guide for commands and environment details.
          </p>
          <p className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Cpu className="h-3.5 w-3.5" /> Performance depends on your CPU and the optional vision
            stack.
          </p>
        </Section>
      </div>

      <div className="mt-6">
        <InfoNote tone="info" title="A note on the name">
          <p>
            &quot;ClassMind AI&quot; is the project name. The system is a local analytics assistant,
            not a mind-reading model. It observes coarse signals in a recording and reports them with
            their uncertainty. Use it to support reflection, never to label a student.
          </p>
        </InfoNote>
      </div>
    </div>
  );
}
