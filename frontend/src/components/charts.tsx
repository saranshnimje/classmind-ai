import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useTheme } from "../lib/theme";
import type { AnalysisWindow, Dashboard } from "../lib/types";

interface TooltipEntry {
  name?: string | number;
  value?: number | string | Array<number | string>;
  color?: string;
  dataKey?: string | number;
}

function ChartTooltip({
  active,
  payload,
  label,
  units = {},
  digits = 1,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
  units?: Record<string, string>;
  digits?: number;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg dark:border-slate-700 dark:bg-slate-900">
      {label !== undefined ? (
        <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      ) : null}
      <ul className="space-y-0.5">
        {payload.map((entry, index) => {
          const key = String(entry.dataKey ?? entry.name ?? index);
          const suffix = units[key] ?? "";
          const value =
            typeof entry.value === "number"
              ? `${entry.value.toFixed(digits)}${suffix}`
              : `${entry.value ?? "—"}${suffix}`;
          return (
            <li key={key} className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color ?? "#6366f1" }}
              />
              <span className="capitalize">{String(entry.name ?? key)}</span>
              <span className="ml-auto font-semibold text-slate-900 dark:text-white">{value}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function useChartTheme() {
  const { theme } = useTheme();
  const dark = theme === "dark";
  return {
    grid: dark ? "#1e293b" : "#e2e8f0",
    tick: dark ? "#94a3b8" : "#64748b",
    axis: dark ? "#334155" : "#cbd5e1",
    tooltipCursor: dark ? "rgba(148, 163, 184, 0.12)" : "rgba(100, 116, 139, 0.08)",
  };
}

const CHART_HEIGHT = 260;

export function EngagementTrendChart({ data }: { data: Dashboard["engagement_trend"] }) {
  const chart = useChartTheme();
  const rows = data.map((row) => ({
    ...row,
    label: row.date.slice(5),
    engagement: row.engagement === null ? null : Number((row.engagement * 100).toFixed(1)),
  }));

  return (
    <div style={{ height: CHART_HEIGHT }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke={chart.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={{ stroke: chart.axis }}
            tickLine={false}
          />
          <YAxis
            yAxisId="engagement"
            domain={[0, 100]}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <YAxis
            yAxisId="attendance"
            orientation="right"
            domain={[0, 100]}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip
            content={<ChartTooltip units={{ engagement: "%", attendance_rate: "%" }} />}
            cursor={{ stroke: chart.axis }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: chart.tick }} />
          <Line
            yAxisId="engagement"
            type="monotone"
            dataKey="engagement"
            name="Engagement proxy"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#6366f1" }}
            connectNulls
          />
          <Line
            yAxisId="attendance"
            type="monotone"
            dataKey="attendance_rate"
            name="Attendance rate"
            stroke="#10b981"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={{ r: 2.5, fill: "#10b981" }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SessionVolumeChart({ data }: { data: Dashboard["sessions_last_14_days"] }) {
  const chart = useChartTheme();
  const rows = data.map((row) => ({ ...row, label: row.date.slice(5) }));

  return (
    <div style={{ height: CHART_HEIGHT }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid stroke={chart.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={{ stroke: chart.axis }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            content={<ChartTooltip units={{ sessions: "" }} digits={0} />}
            cursor={{ fill: chart.tooltipCursor }}
          />
          <Bar dataKey="sessions" name="Sessions" fill="#818cf8" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WindowEngagementChart({ windows }: { windows: AnalysisWindow[] }) {
  const chart = useChartTheme();
  const rows = windows.map((window) => ({
    label: `${Math.round(window.start_sec)}s`,
    engagement:
      window.engagement_score === null
        ? null
        : Number((window.engagement_score * 100).toFixed(1)),
    audio:
      window.audio_active_ratio === null
        ? null
        : Number((window.audio_active_ratio * 100).toFixed(1)),
  }));

  return (
    <div style={{ height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="engagementFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={chart.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={{ stroke: chart.axis }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip
            content={<ChartTooltip units={{ engagement: "%", audio: "%" }} />}
            cursor={{ stroke: chart.axis }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: chart.tick }} />
          <ReferenceLine y={60} stroke="#10b981" strokeDasharray="3 3" strokeOpacity={0.5} />
          <ReferenceLine y={35} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
          <Area
            type="monotone"
            dataKey="engagement"
            name="Engagement proxy"
            stroke="#6366f1"
            strokeWidth={2.5}
            fill="url(#engagementFill)"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="audio"
            name="Speech activity"
            stroke="#0ea5e9"
            strokeWidth={1.75}
            strokeDasharray="4 3"
            dot={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WindowParticipationChart({ windows }: { windows: AnalysisWindow[] }) {
  const chart = useChartTheme();
  const rows = windows.map((window) => ({
    label: `${Math.round(window.start_sec)}s`,
    participants: window.participant_count,
    movement:
      window.movement_index === null ? null : Number((window.movement_index * 100).toFixed(1)),
  }));

  return (
    <div style={{ height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
          <CartesianGrid stroke={chart.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={{ stroke: chart.axis }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            yAxisId="movement"
            orientation="right"
            domain={[0, 100]}
            tick={{ fill: chart.tick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip
            content={<ChartTooltip units={{ participants: "", movement: "%" }} digits={0} />}
            cursor={{ fill: chart.tooltipCursor }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: chart.tick }} />
          <Bar
            dataKey="participants"
            name="Participants visible"
            fill="#a5b4fc"
            radius={[5, 5, 0, 0]}
          />
          <Line
            yAxisId="movement"
            type="monotone"
            dataKey="movement"
            name="Movement index"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
