export type SessionStatus =
  | "created"
  | "uploaded"
  | "queued"
  | "processing"
  | "completed"
  | "failed";

export type AttendanceState = "present" | "late" | "unconfirmed";

export interface Session {
  id: string;
  title: string;
  subject: string;
  class_label: string | null;
  session_date: string;
  notes: string | null;
  status: SessionStatus;
  error_message: string | null;
  is_demo: boolean;
  duration_sec: number | null;
  has_audio: boolean;
  video_filename: string | null;
  audio_filename: string | null;
  video_size_bytes: number | null;
  audio_size_bytes: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  sample_interval_sec: number;
  min_presence_sec: number;
  late_after_sec: number;
  window_sec: number;
  detector_used: string | null;
  audio_method: string | null;
  quality_json: Record<string, unknown>;
  methodology_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  attendance_count: number;
  track_count: number;
  average_engagement: number | null;
}

export interface Job {
  id: string;
  status: string;
  stage: string;
  progress: number;
  message: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface SessionDetail extends Session {
  latest_job: Job | null;
}

export interface ProcessingStatus {
  session_id: string;
  status: SessionStatus;
  error: string | null;
  job: Job | null;
  media_ready: boolean;
  progress: number;
  stage: string | null;
  message: string | null;
}

export interface UploadResult {
  session_id: string;
  status: string;
  video_filename: string | null;
  audio_filename: string | null;
  duration_sec: number | null;
  has_audio: boolean;
  size_bytes: number | null;
  message: string;
}

export interface AttendanceRecord {
  id: string;
  track_id: string;
  roster_id: string | null;
  display_name: string;
  state: AttendanceState;
  presence_sec: number;
  first_seen_sec: number;
  last_seen_sec: number;
  confidence: number;
  uncertain: boolean;
  note: string | null;
}

export interface Track {
  id: string;
  track_index: number;
  display_label: string;
  roster_id: string | null;
  identity_status: "anonymous" | "mapped";
  first_seen_sec: number;
  last_seen_sec: number;
  duration_sec: number;
  samples_seen: number;
  confidence_avg: number;
  movement_index: number;
  inactive_sec: number;
  head_center_ratio: number;
  head_left_ratio: number;
  head_right_ratio: number;
  head_unknown_ratio: number;
  attendance_state: AttendanceState;
  uncertain: boolean;
  note: string | null;
}

export interface AttendanceSummary {
  session_id: string;
  session_duration_sec: number | null;
  min_presence_sec: number;
  late_after_sec: number;
  total_detected: number;
  present: number;
  late: number;
  unconfirmed: number;
  mapped: number;
  anonymous: number;
  uncertain: number;
  attendance_rate: number | null;
  records: AttendanceRecord[];
  tracks: Track[];
  warnings: string[];
}

export interface AnalysisWindow {
  window_index: number;
  start_sec: number;
  end_sec: number;
  participant_count: number;
  attendance_changes: number;
  movement_index: number | null;
  active_ratio: number | null;
  inactivity_ratio: number | null;
  looking_away_ratio: number | null;
  audio_active_ratio: number | null;
  engagement_score: number | null;
  engagement_confidence: "high" | "medium" | "low" | null;
  data_quality: "good" | "partial" | "poor";
  warnings_json: string[];
  metrics_json: Record<string, unknown>;
}

export interface AudioInterval {
  start_sec: number;
  end_sec: number;
  kind: "speech" | "silence";
  mean_energy: number;
}

export interface AudioSummary {
  available: boolean;
  method: string | null;
  speech_active_sec: number;
  speech_ratio: number | null;
  interval_count: number;
  intervals: AudioInterval[];
  warnings: string[];
}

export interface MovementSummary {
  tracked_participants?: number;
  mean_movement_index?: number | null;
  total_inactive_sec?: number;
  longest_inactive_sec?: number;
  inactive_participants?: number;
  face_visible_ratio?: number | null;
}

export interface EngagementMethodology {
  engagement_proxy?: {
    definition?: string;
    formula?: string;
    movement_index?: string;
    active_ratio?: string;
    missing_data_policy?: string;
    confidence_rules?: Record<string, string>;
    window_sec?: number;
    sample_interval_sec?: number;
  };
  attendance?: { rule?: string; late_rule?: string; identity?: string };
  head_orientation?: { method?: string; limitations?: string };
  audio?: { method?: string; limitations?: string };
}

export interface Analytics {
  session_id: string;
  title: string;
  duration_sec: number | null;
  window_sec: number;
  average_engagement: number | null;
  engagement_confidence: string | null;
  peak_window: number | null;
  lowest_window: number | null;
  windows: AnalysisWindow[];
  audio: AudioSummary;
  movement_summary: MovementSummary;
  attendance_summary: Record<string, number | null>;
  quality: {
    score?: "good" | "partial" | "poor";
    detector?: string;
    sampled_frames?: number;
    brightness_mean?: number;
    camera_motion?: number;
    face_visible_ratio?: number | null;
    audio_available?: boolean;
    warnings?: string[];
    [key: string]: unknown;
  };
  methodology: EngagementMethodology;
  warnings: string[];
}

export interface Recommendation {
  id: string;
  source: "rule" | "local_llm";
  category: string;
  title: string;
  detail: string;
  evidence: string;
  observed: string;
  interpretation: string;
  start_sec: number | null;
  end_sec: number | null;
  priority: "high" | "medium" | "low";
  confidence: "high" | "medium" | "low";
  created_at: string;
}

export interface RecommendationResponse {
  session_id: string;
  generated_by: string;
  llm_available: boolean;
  llm_status: string;
  disclaimer: string;
  recommendations: Recommendation[];
}

export interface Report {
  session: Session;
  generated_at: string;
  attendance: AttendanceSummary;
  analytics: Analytics;
  recommendations: Recommendation[];
  quality: Record<string, unknown>;
  methodology: EngagementMethodology;
  limitations: string[];
}

export interface RosterEntry {
  id: string;
  name: string;
  external_id: string | null;
  class_label: string | null;
  created_at: string;
}

export interface EventItem {
  id: string;
  level: "info" | "success" | "warning" | "error" | string;
  event: string;
  message: string;
  session_id: string | null;
  created_at: string;
}

export interface DashboardSession {
  id: string;
  title: string;
  subject: string;
  class_label: string | null;
  session_date: string;
  status: SessionStatus;
  duration_sec: number | null;
  is_demo: boolean;
  created_at: string;
  attendance_rate: number | null;
  average_engagement: number | null;
  error_message: string | null;
}

export interface DetectorStatus {
  requested: string;
  yolo_installed: boolean;
  yolo_weights_present: boolean;
  yolo_weights_path: string;
  active: string;
  note: string;
}

export interface VadStatus {
  backend_requested: string;
  active: string;
  silero_available: boolean;
  note: string;
}

export interface LlmStatus {
  enabled: boolean;
  reachable: boolean;
  model: string;
  model_available: boolean;
  installed_models: string[];
  detail: string;
}

export interface ModelsStatus {
  detector: DetectorStatus;
  audio_vad: VadStatus;
  llm: LlmStatus;
}

export interface Dashboard {
  total_sessions: number;
  completed_sessions: number;
  total_attendance_records: number;
  average_attendance_rate: number | null;
  average_engagement: number | null;
  sessions_last_14_days: { date: string; sessions: number }[];
  engagement_trend: {
    session_id: string;
    title: string;
    date: string;
    engagement: number | null;
    attendance_rate: number | null;
    is_demo: boolean;
  }[];
  recent_sessions: DashboardSession[];
  recent_events: EventItem[];
  processing: {
    active: boolean;
    queue: { active: string[]; pending: string[] };
    active_jobs: number;
  };
  models: ModelsStatus;
  definitions: Record<string, string>;
}

export interface Settings {
  min_presence_sec: number;
  sample_interval_sec: number;
  window_sec: number;
  late_after_sec: number;
  detector_backend: string;
  ollama_enabled: boolean;
  ollama_url: string;
  ollama_model: string;
  retention_days: number;
  delete_media_after_processing: boolean;
  data_dir: string;
  database_path: string;
  models: ModelsStatus;
  limits: {
    max_upload_mb: number;
    max_media_duration_sec: number;
    video_extensions: string[];
    audio_extensions: string[];
    max_analysis_frames: number;
    analysis_max_width: number;
  };
}

export interface Health {
  status: string;
  app: string;
  version: string;
  database: string;
  data_dir_writable: boolean;
  processing_active: boolean;
  detector: DetectorStatus;
  audio_vad: VadStatus;
  llm: LlmStatus;
  ffmpeg: { available: boolean; version: string | null };
  timestamp: string;
}

export interface LiveStatus {
  session_id: string;
  active: boolean;
  frames: number;
  seconds: number;
  max_seconds?: number;
  error: string | null;
  video_filename?: string;
  message: string;
}
