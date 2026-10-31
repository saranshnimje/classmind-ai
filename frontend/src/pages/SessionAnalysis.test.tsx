import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { analytics, attendance, sessionDetail, settings } from "../test/fixtures";
import { SessionAnalysisPage } from "./SessionAnalysis";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getSession: vi.fn(),
    getStatus: vi.fn(),
    settings: vi.fn(),
    processSession: vi.fn(),
    uploadMedia: vi.fn(),
    attendance: vi.fn(),
    analytics: vi.fn(),
    startLive: vi.fn(),
    stopLive: vi.fn(),
    liveStatus: vi.fn(),
    deleteSession: vi.fn(),
    reportUrl: vi.fn((id: string, kind: "html" | "csv" = "html") => `/api/sessions/${id}/report.${kind}`),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/sessions/sess-1"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionAnalysisPage />} />
        <Route path="/sessions" element={<div>Sessions list</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionAnalysisPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.settings.mockResolvedValue(settings);
    apiMock.attendance.mockResolvedValue(attendance);
    apiMock.analytics.mockResolvedValue(analytics);
  });

  it("rejects an unsupported upload before contacting the backend", async () => {
    apiMock.getSession.mockResolvedValue({ ...sessionDetail, status: "uploaded" });
    const user = userEvent.setup({ applyAccept: false });
    renderPage();

    const input = await screen.findByLabelText(/video file/i);
    const badFile = new File(["not a video"], "lesson.txt", { type: "text/plain" });
    await user.upload(input, badFile);

    expect(await screen.findByText(/unsupported video format/i)).toBeInTheDocument();
    expect(apiMock.uploadMedia).not.toHaveBeenCalled();
  });

  it("renders job progress while processing", async () => {
    apiMock.getSession.mockResolvedValue({
      ...sessionDetail,
      status: "processing",
      latest_job: {
        ...sessionDetail.latest_job!,
        status: "processing",
        stage: "detecting",
        progress: 40,
        message: "Detecting people in sampled frames",
      },
    });
    apiMock.getStatus.mockResolvedValue({
      session_id: "sess-1",
      status: "processing",
      error: null,
      job: null,
      media_ready: true,
      progress: 40,
      stage: "detecting",
      message: "Detecting people in sampled frames",
    });

    renderPage();

    expect(
      await screen.findByText(/detecting people in sampled frames/i),
    ).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
  });

  it("shows the failure message when processing failed", async () => {
    apiMock.getSession.mockResolvedValue({
      ...sessionDetail,
      status: "failed",
      error_message: "No frames could be decoded from the uploaded video.",
    });

    renderPage();

    expect(await screen.findByText("Analysis failed")).toBeInTheDocument();
    expect(
      screen.getByText("No frames could be decoded from the uploaded video."),
    ).toBeInTheDocument();
  });

  it("shows completed results and review links", async () => {
    apiMock.getSession.mockResolvedValue(sessionDetail);

    renderPage();

    expect(await screen.findByText("Analysis complete")).toBeInTheDocument();
    expect(screen.getByText("Review the analysis")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /attendance/i })[0]).toHaveAttribute(
      "href",
      "/attendance/sess-1",
    );
    expect(screen.getAllByRole("link", { name: /analytics/i })[0]).toHaveAttribute(
      "href",
      "/analytics/sess-1",
    );
  });

  it("starts processing and reloads the session", async () => {
    apiMock.getSession.mockResolvedValue({ ...sessionDetail, status: "uploaded" });
    apiMock.processSession.mockResolvedValue({
      session_id: "sess-1",
      status: "queued",
      job_id: "job-2",
      message: "queued",
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /run analysis/i }));

    expect(apiMock.processSession).toHaveBeenCalledWith("sess-1");
    expect(apiMock.getSession).toHaveBeenCalledTimes(2);
  });
});
