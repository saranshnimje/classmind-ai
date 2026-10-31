import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  RefreshCw,
  ShieldAlert,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, type ReactNode } from "react";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "demo";

const badgeTones: Record<Tone, string> = {
  neutral:
    "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  brand: "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300",
  success:
    "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  warning: "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
  danger: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  demo: "bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-500/15 dark:text-fuchsia-300",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <span className={`chip ${badgeTones[tone]} ${className}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, Tone> = {
    completed: "success",
    failed: "danger",
    processing: "brand",
    queued: "warning",
    uploaded: "brand",
    created: "neutral",
  };
  return <Badge tone={map[status] ?? "neutral"}>{statusLabel(status)}</Badge>;
}

export function StateBadge({ state }: { state: string }) {
  const map: Record<string, Tone> = {
    present: "success",
    late: "warning",
    unconfirmed: "neutral",
  };
  return (
    <Badge tone={map[state] ?? "neutral"}>
      {state.charAt(0).toUpperCase() + state.slice(1)}
    </Badge>
  );
}

export function PriorityBadge({ priority }: { priority: string }) {
  const map: Record<string, Tone> = { high: "danger", medium: "warning", low: "neutral" };
  return <Badge tone={map[priority] ?? "neutral"}>{priority}</Badge>;
}

export function SourceBadge({ source }: { source: string }) {
  return source === "local_llm" ? (
    <Badge tone="brand">Local model</Badge>
  ) : (
    <Badge tone="neutral">Rule-based</Badge>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    created: "Created",
    uploaded: "Media ready",
    queued: "Queued",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  };
  return labels[status] ?? status;
}

export function Card({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return <Tag className={`card ${className}`}>{children}</Tag>;
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
      <div>
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">{title}</h2>
        {description ? (
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "brand",
  loading = false,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon: LucideIcon;
  tone?: Tone;
  loading?: boolean;
}) {
  const iconTone: Record<Tone, string> = {
    neutral: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    brand: "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300",
    success: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300",
    warning: "bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300",
    danger: "bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300",
    demo: "bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-500/15 dark:text-fuchsia-300",
  };
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {label}
          </p>
          {loading ? (
            <div className="mt-2 h-8 w-24 skeleton" />
          ) : (
            <p className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              {value}
            </p>
          )}
          {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
        </div>
        <span className={`rounded-xl p-2.5 ${iconTone[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>
    </Card>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        {eyebrow ? (
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-600 dark:text-brand-400">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} aria-hidden="true" />;
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500 dark:text-slate-400">
      <Spinner className="h-5 w-5" />
      <span>{label}…</span>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 px-6 py-14 text-center dark:border-slate-700">
      <span className="mb-4 rounded-2xl bg-slate-100 p-3 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <h3 className="text-base font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-slate-500 dark:text-slate-400">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  title = "Something went wrong",
}: {
  error: Error;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-rose-200 bg-rose-50 p-6 dark:border-rose-900/60 dark:bg-rose-950/30"
    >
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" />
        <div className="min-w-0">
          <h3 className="font-semibold text-rose-900 dark:text-rose-200">{title}</h3>
          <p className="mt-1 break-words text-sm text-rose-700 dark:text-rose-300">{error.message}</p>
          {onRetry ? (
            <button type="button" onClick={onRetry} className="btn btn-secondary btn-sm mt-4">
              <RefreshCw className="h-3.5 w-3.5" /> Try again
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function ProgressBar({
  value,
  label,
  tone = "brand",
}: {
  value: number;
  label?: string;
  tone?: "brand" | "success" | "danger";
}) {
  const width = Math.max(0, Math.min(100, value));
  const colors = {
    brand: "bg-brand-600",
    success: "bg-emerald-500",
    danger: "bg-rose-500",
  };
  return (
    <div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-valuenow={Math.round(width)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${colors[tone]}`}
          style={{ width: `${width}%` }}
        />
      </div>
      {label ? (
        <div className="mt-1.5 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>{label}</span>
          <span>{Math.round(width)}%</span>
        </div>
      ) : null}
    </div>
  );
}

const noteTones = {
  info: {
    wrap: "border-brand-200 bg-brand-50/70 dark:border-brand-900 dark:bg-brand-950/30",
    text: "text-brand-900 dark:text-brand-200",
    icon: Info,
  },
  warning: {
    wrap: "border-amber-200 bg-amber-50/80 dark:border-amber-900 dark:bg-amber-950/30",
    text: "text-amber-900 dark:text-amber-200",
    icon: AlertTriangle,
  },
  danger: {
    wrap: "border-rose-200 bg-rose-50/80 dark:border-rose-900 dark:bg-rose-950/30",
    text: "text-rose-900 dark:text-rose-200",
    icon: ShieldAlert,
  },
  success: {
    wrap: "border-emerald-200 bg-emerald-50/80 dark:border-emerald-900 dark:bg-emerald-950/30",
    text: "text-emerald-900 dark:text-emerald-200",
    icon: CheckCircle2,
  },
};

export function InfoNote({
  tone = "info",
  title,
  children,
  className = "",
}: {
  tone?: keyof typeof noteTones;
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  const config = noteTones[tone];
  const Icon = config.icon;
  return (
    <div className={`rounded-2xl border p-4 ${config.wrap} ${className}`}>
      <div className={`flex items-start gap-3 ${config.text}`}>
        <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div className="min-w-0 text-sm leading-relaxed">
          {title ? <p className="mb-1 font-semibold">{title}</p> : null}
          <div className="[&_p]:mt-1">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function ChartCard({
  title,
  description,
  empty,
  emptyMessage = "No data available yet.",
  children,
  footnote,
  action,
}: {
  title: string;
  description?: string;
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
  footnote?: string;
  action?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} action={action} />
      <div className="p-4 sm:p-5">
        {empty ? (
          <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 px-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {emptyMessage}
          </div>
        ) : (
          children
        )}
        {footnote ? (
          <p className="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            {footnote}
          </p>
        ) : null}
      </div>
    </Card>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
        onClick={() => !busy && onCancel()}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
        <h2 id="confirm-title" className="pr-8 text-lg font-semibold text-slate-900 dark:text-white">
          {title}
        </h2>
        <div className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {description}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={busy}>
            {busy ? <Spinner /> : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 text-sm">
      <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-900 dark:text-slate-100">{value}</dd>
    </div>
  );
}
