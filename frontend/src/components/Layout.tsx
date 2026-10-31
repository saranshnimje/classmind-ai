import {
  Activity,
  BookOpenCheck,
  CalendarCheck2,
  LayoutDashboard,
  Lightbulb,
  Menu,
  Moon,
  PlusCircle,
  Settings as SettingsIcon,
  ShieldCheck,
  Sun,
  Video,
  X,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { api } from "../lib/api";
import { useTheme } from "../lib/theme";
import { LoadingBlock } from "./ui";

export const LAST_SESSION_KEY = "classmind-last-session";

export function rememberSession(id: string) {
  try {
    window.localStorage.setItem(LAST_SESSION_KEY, id);
  } catch {
    // storage may be unavailable (private mode); navigation still works
  }
}

function lastSessionId(): string | null {
  try {
    return window.localStorage.getItem(LAST_SESSION_KEY);
  } catch {
    return null;
  }
}

export function sessionIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/(?:sessions|attendance|analytics|recommendations)\/([^/]+)/);
  if (match && match[1] !== "new") return match[1];
  return lastSessionId();
}

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  end?: boolean;
  sessionScoped?: boolean;
}

const workspaceNav: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/sessions", label: "Sessions", icon: Video, end: true },
  { to: "/sessions/new", label: "New session", icon: PlusCircle },
];

const analysisNav: NavItem[] = [
  { to: "/attendance", label: "Attendance", icon: CalendarCheck2, sessionScoped: true },
  { to: "/analytics", label: "Engagement analytics", icon: Activity, sessionScoped: true },
  { to: "/recommendations", label: "Recommendations", icon: Lightbulb, sessionScoped: true },
];

const systemNav: NavItem[] = [
  { to: "/settings", label: "Settings", icon: SettingsIcon },
  { to: "/about", label: "Privacy & method", icon: ShieldCheck },
];

function useBackendStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        await api.health();
        if (!cancelled) setOnline(true);
      } catch {
        if (!cancelled) setOnline(false);
      }
    };
    void check();
    const timer = window.setInterval(check, 60000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return online;
}

function NavSection({
  title,
  items,
  onNavigate,
  sessionId,
}: {
  title: string;
  items: NavItem[];
  onNavigate: () => void;
  sessionId: string | null;
}) {
  return (
    <div className="px-3">
      <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
        {title}
      </p>
      <ul className="space-y-1">
        {items.map((item) => {
          const target =
            item.sessionScoped && sessionId ? `${item.to}/${sessionId}` : item.to;
          return (
            <li key={item.to}>
              <NavLink
                to={target}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-200"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white",
                  ].join(" ")
                }
              >
                <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SidebarContent({
  onNavigate,
  sessionId,
}: {
  onNavigate: () => void;
  sessionId: string | null;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 px-6 py-5">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-600 text-white shadow-sm">
          <BookOpenCheck className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold tracking-tight text-slate-900 dark:text-white">
            ClassMind AI
          </p>
          <p className="truncate text-[11px] text-slate-500 dark:text-slate-400">
            Local classroom intelligence
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto pb-6" aria-label="Primary">
        <NavSection
          title="Workspace"
          items={workspaceNav}
          onNavigate={onNavigate}
          sessionId={sessionId}
        />
        <NavSection
          title="Analysis"
          items={analysisNav}
          onNavigate={onNavigate}
          sessionId={sessionId}
        />
        <NavSection
          title="System"
          items={systemNav}
          onNavigate={onNavigate}
          sessionId={sessionId}
        />
      </nav>

      <div className="border-t border-slate-200 p-4 dark:border-slate-800">
        <div className="rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          <p className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            Privacy-first
          </p>
          <p className="mt-1">
            {(() => {
              const raw = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
              const mode = typeof raw === "string" ? raw.trim().toLowerCase() : "";
              const isHosted = mode === "hosted";
              const isLocal = mode === "local";
              if (isHosted) {
                return (
                  <>
                    Frontend is hosted on Vercel. Recordings are sent over HTTPS to the Render backend for processing.
                    Processing and temporary/persistent storage depend on Render's filesystem and database configuration.
                  </>
                );
              }
              if (isLocal) {
                return (
                  <>
                    Media stays on this machine. No face recognition, no cloud uploads, no student surveillance profiles.
                  </>
                );
              }
              return (
                <>
                  Deployment mode unknown. Processing location is not confirmed. Use synthetic/demo recordings unless authorization and consent are in place.
                </>
              );
            })()}
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
            {(() => {
              const raw = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
              const mode = typeof raw === "string" ? raw.trim().toLowerCase() : "";
              const isHosted = mode === "hosted";
              const isLocal = mode === "local";
              if (isHosted) return "Data location: Render (instance filesystem). Use synthetic/demo recordings unless authorization and consent are in place.";
              if (isLocal) return "Data is stored according to the local Docker configuration.";
              return "Data location: unconfirmed. Use synthetic/demo recordings unless authorization and consent are in place.";
            })()}
          </p>
        </div>
      </div>
    </div>
  );
}

export function useValidatedSessionId(pathname: string) {
  const [validated, setValidated] = useState<string | null>(null);

  useEffect(() => {
    const fromPath = sessionIdFromPath(pathname);
    if (fromPath && pathname.match(/^\/(?:sessions|attendance|analytics|recommendations)\/[^/]+$/)) {
      setValidated(fromPath);
      
      return;
    }
    const saved = lastSessionId();
    if (!saved) {
      setValidated(null);
      
      return;
    }
    let cancelled = false;
    api.getSession(saved)
      .then(() => {
        if (!cancelled) { setValidated(saved);  }
      })
      .catch((err: Error) => {
        if (cancelled) return;
        const e = err as { status?: number; code?: string };
        if (e.status === 404 || e.code === "session_not_found") {
          try { window.localStorage.removeItem(LAST_SESSION_KEY); } catch {}
          setValidated(null);
        } else {
          setValidated(saved);
        }
        
      });
    return () => { cancelled = true; };
  }, [pathname]);

  return validated;
}

export function Layout() {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const sessionId = useValidatedSessionId(location.pathname);
  const online = useBackendStatus();

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (sessionId) rememberSession(sessionId);
  }, [sessionId]);

  useEffect(() => {
    if (!drawerOpen) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [drawerOpen]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900">
        <SidebarContent onNavigate={() => undefined} sessionId={sessionId} />
      </aside>

      {drawerOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
          >
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent onNavigate={() => setDrawerOpen(false)} sessionId={sessionId} />
          </div>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 dark:border-slate-800 dark:bg-slate-900/90">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden dark:text-slate-400 dark:hover:bg-slate-800"
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="hidden items-center gap-2 text-xs font-medium text-slate-500 sm:flex dark:text-slate-400">
              <span
                className={`h-2 w-2 rounded-full ${
                  online === false
                    ? "bg-rose-500"
                    : online
                      ? "bg-emerald-500"
                      : "bg-slate-300 dark:bg-slate-600"
                }`}
              />
              {online === false
                ? "Backend offline"
                : online
                  ? "Backend connected · processed locally"
                  : "Checking backend…"}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/sessions/new"
              className="btn btn-primary btn-sm hidden sm:inline-flex"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              New session
            </Link>
            <button
              type="button"
              onClick={toggle}
              className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={theme === "dark" ? "Light theme" : "Dark theme"}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Suspense fallback={<LoadingBlock label="Loading page" />}>
            <Outlet />
          </Suspense>
        </main>

        <footer className="mx-auto w-full max-w-7xl px-4 pb-8 text-xs leading-relaxed text-slate-400 sm:px-6 lg:px-8 dark:text-slate-500">
          {(() => {
            const raw = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
            const mode = typeof raw === "string" ? raw.trim().toLowerCase() : "";
            if (mode === "hosted") {
              return (
                <>
                  Frontend is hosted on Vercel. Recordings are sent over HTTPS to the Render backend for processing. Processing and storage depend on Render's filesystem and database configuration. Detected people remain anonymous until you explicitly map a track to a roster entry. Engagement scores are descriptive proxies, not assessments.{" "}
                  <Link to="/about" className="link">Read the privacy &amp; method notes</Link>.
                </>
              );
            }
            if (mode === "local") {
              return (
                <>
                  ClassMind AI runs locally on this machine. Media stays here; no face recognition, no cloud uploads, no student surveillance profiles. Detected people remain anonymous until you explicitly map a track to a roster entry. Engagement scores are descriptive proxies, not assessments.{" "}
                  <Link to="/about" className="link">Read the privacy &amp; method notes</Link>.
                </>
              );
            }
            return (
              <>
                Deployment mode unknown. Processing location is not confirmed. Use synthetic/demo recordings unless authorization and consent are in place. Detected people remain anonymous until you explicitly map a track to a roster entry. Engagement scores are descriptive proxies, not assessments.{" "}
                <Link to="/about" className="link">Read the privacy &amp; method notes</Link>.
              </>
            );
          })()}
        </footer>
      </div>
    </div>
  );
}
