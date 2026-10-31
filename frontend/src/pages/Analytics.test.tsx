import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { analytics, session } from "../test/fixtures";
import { AnalyticsPage } from "./Analytics";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    analytics: vi.fn(),
    listSessions: vi.fn(),
    reportUrl: vi.fn((id: string, kind: "html" | "csv" = "html") => `/api/sessions/${id}/report.${kind}`),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/analytics/sess-1"]}>
      <Routes>
        <Route path="/analytics/:id" element={<AnalyticsPage />} />
        <Route path="/analytics" element={<div>Analytics picker</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.analytics.mockResolvedValue(analytics);
    apiMock.listSessions.mockResolvedValue([session]);
  });

  it("renders engagement summary, windows and methodology", async () => {
    renderPage();

    expect(await screen.findByText("Engagement over time")).toBeInTheDocument();
    expect(screen.getAllByText("62%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("#1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("#2").length).toBeGreaterThan(0);
    expect(screen.getByText("A descriptive blend of observable classroom signals.")).toBeInTheDocument();
    expect(
      screen.getByText("Missing indicators are excluded and confidence is reduced."),
    ).toBeInTheDocument();
    expect(screen.getByText("Energy-based voice activity detection.")).toBeInTheDocument();
    expect(screen.getByText("yolo")).toBeInTheDocument();
    expect(screen.getByText("112.40")).toBeInTheDocument();
  });

  it("shows the audio interval timeline and speech ratio", async () => {
    renderPage();

    expect(await screen.findByText("Audio activity")).toBeInTheDocument();
    expect(screen.getAllByText("40%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Speech").length).toBeGreaterThan(0);
  });

  it("shows an empty state when no windows exist", async () => {
    apiMock.analytics.mockResolvedValue({
      ...analytics,
      windows: [],
      average_engagement: null,
      peak_window: null,
      lowest_window: null,
    });

    renderPage();

    expect(await screen.findByText("No analysis windows")).toBeInTheDocument();
  });

  it("shows an error state when the session has no results", async () => {
    apiMock.analytics.mockRejectedValue(
      new Error("This session has no analysis results yet. Upload media and run processing first."),
    );

    renderPage();

    expect(await screen.findByText("Analytics unavailable")).toBeInTheDocument();
    expect(
      screen.getByText(/This session has no analysis results yet/i),
    ).toBeInTheDocument();
  });
});
