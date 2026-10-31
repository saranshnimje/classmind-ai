import {
  AlertTriangle,
  ArrowRight,
  Clock,
  Lightbulb,
  ListFilter,
  Sparkles,
  Target,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SessionPicker } from "../components/SessionPicker";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  InfoNote,
  LoadingBlock,
  PageHeader,
  PriorityBadge,
  SourceBadge,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtClock, relativeTime } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { RecommendationResponse } from "../lib/types";

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export function RecommendationsPage() {
  const { id } = useParams<{ id: string }>();
  useDocumentTitle("Recommendations");

  const { data, loading, error, reload } = useAsync<RecommendationResponse | null>(
    () => (id ? api.recommendations(id) : Promise.resolve(null)),
    [id],
  );
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");

  const categories = useMemo(
    () => Array.from(new Set((data?.recommendations ?? []).map((item) => item.category))).sort(),
    [data],
  );

  const visible = useMemo(() => {
    const items = data?.recommendations ?? [];
    return [...items]
      .filter((item) => (priority ? item.priority === priority : true))
      .filter((item) => (category ? item.category === category : true))
      .sort((a, b) => {
        const rank = (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9);
        if (rank !== 0) return rank;
        return (a.start_sec ?? 0) - (b.start_sec ?? 0);
      });
  }, [data, priority, category]);

  if (!id) {
    return (
      <div className="animate-fade-in">
        <PageHeader
          eyebrow="Evidence-linked suggestions"
          title="Recommendations"
          description="Rule-based suggestions tied to observed windows. Optional local LLM wording never replaces the evidence shown."
        />
        <SessionPicker sessionId={null} basePath="/recommendations" label="Choose a session" />
        <EmptyState
          icon={Lightbulb}
          title="Select a session"
          description="Choose a completed session above to review suggestions derived from its windows."
          action={
            <Link to="/sessions" className="btn btn-secondary">
              Browse sessions
            </Link>
          }
        />
      </div>
    );
  }

  if (loading && !data) return <LoadingBlock label="Loading recommendations" />;
  if (error)
    return (
      <ErrorState
        error={error}
        onRetry={reload}
        title="Recommendations unavailable"
      />
    );
  if (!data) return null;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Evidence-linked suggestions"
        title="Recommendations"
        description="Each suggestion shows the observed evidence, the time interval, and the interpretation it supports. These are prompts for teacher reflection, not automated decisions."
        actions={
          <>
            <Link to={`/sessions/${id}`} className="btn btn-secondary btn-sm">
              Session
            </Link>
            <Link to={`/analytics/${id}`} className="btn btn-secondary btn-sm">
              Analytics
            </Link>
          </>
        }
      />

      <SessionPicker sessionId={id} basePath="/recommendations" />

      <InfoNote tone="info" title="How to read these suggestions">
        <p>{data.disclaimer}</p>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <Badge tone={data.generated_by.includes("llm") ? "brand" : "neutral"}>
            {data.generated_by === "none"
              ? "No suggestions"
              : data.generated_by.includes("llm")
                ? "Local model + rules"
                : "Deterministic rules"}
          </Badge>
          <span>{data.llm_status}</span>
        </p>
      </InfoNote>

      {data.recommendations.length === 0 ? (
        <div className="mt-5">
          <EmptyState
            icon={Lightbulb}
            title="No suggestions for this session"
            description={
              data.llm_status ||
              "No rule conditions matched this session's data. Recommendations are only generated from observed evidence."
            }
            action={
              <Link to={`/sessions/${id}`} className="btn btn-secondary">
                Review the session
              </Link>
            }
          />
        </div>
      ) : (
        <>
          <Card className="mt-5 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="sm:w-48">
                <label htmlFor="priority-filter" className="label">
                  <span className="flex items-center gap-1.5">
                    <ListFilter className="h-3.5 w-3.5" /> Priority
                  </span>
                </label>
                <select
                  id="priority-filter"
                  className="input"
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                >
                  <option value="">All priorities</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="sm:w-56">
                <label htmlFor="category-filter" className="label">
                  Category
                </label>
                <select
                  id="category-filter"
                  className="input"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                >
                  <option value="">All categories</option>
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
              <p className="pb-2.5 text-xs text-slate-500 dark:text-slate-400">
                Showing {visible.length} of {data.recommendations.length} suggestions
              </p>
            </div>
          </Card>

          {visible.length === 0 ? (
            <div className="mt-5">
              <EmptyState
                icon={ListFilter}
                title="No suggestions match these filters"
                description="Clear the filters to see all suggestions for this session."
                action={
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setPriority("");
                      setCategory("");
                    }}
                  >
                    Clear filters
                  </button>
                }
              />
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {visible.map((item) => (
                <Card key={item.id} className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <PriorityBadge priority={item.priority} />
                        <SourceBadge source={item.source} />
                        <Badge tone="neutral">{item.category}</Badge>
                        <span className="text-xs text-slate-400 dark:text-slate-500">
                          {item.confidence} confidence
                        </span>
                      </div>
                      <h3 className="mt-2 text-base font-semibold text-slate-900 dark:text-white">
                        {item.title}
                      </h3>
                    </div>
                    {item.start_sec !== null ? (
                      <span className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        <Clock className="h-3.5 w-3.5" />
                        {fmtClock(item.start_sec)}
                        {item.end_sec !== null ? ` – ${fmtClock(item.end_sec)}` : ""}
                      </span>
                    ) : null}
                  </div>

                  <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    {item.detail}
                  </p>

                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <Target className="h-3.5 w-3.5" /> Observed
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                        {item.observed}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <Sparkles className="h-3.5 w-3.5" /> Interpretation
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                        {item.interpretation}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <AlertTriangle className="h-3.5 w-3.5" /> Evidence
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                        {item.evidence}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 dark:text-slate-500">
                    <span>Generated {relativeTime(item.created_at)}</span>
                    <Link
                      to={`/analytics/${id}`}
                      className="link inline-flex items-center gap-1"
                    >
                      Inspect the windows <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          )}

          <div className="mt-5">
            <InfoNote tone="warning" title="Use with judgement">
              <p>
                Suggestions describe patterns in the recording; they do not know why a class was
                quiet or active. Consider lesson design, camera placement, time of day and the
                limitations of the sensors before acting. Do not use these values for grading,
                discipline or student profiling.
              </p>
              <p className="mt-2">
                Re-run analysis from the session page to regenerate suggestions after changing
                media or thresholds.
              </p>
            </InfoNote>
          </div>
        </>
      )}
    </div>
  );
}
