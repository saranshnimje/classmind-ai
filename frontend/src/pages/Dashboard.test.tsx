import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dashboard } from "../test/fixtures";
import { DashboardPage } from "./Dashboard";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    dashboard: vi.fn(),
    seedDemo: vi.fn(),
    clearDemo: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.dashboard.mockResolvedValue(dashboard);
    apiMock.seedDemo.mockResolvedValue({});
    apiMock.clearDemo.mockResolvedValue({ removed_sessions: 1 });
  });

  it("renders aggregate metrics and recent sessions", async () => {
    renderPage();

    expect(await screen.findByText("Grade 8 Science — Photosynthesis")).toBeInTheDocument();
    expect(screen.getByText("Average attendance")).toBeInTheDocument();
    expect(screen.getAllByText("66.7%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("62%").length).toBeGreaterThan(0);
    expect(screen.getByText("Analysis completed for Grade 8 Science.")).toBeInTheDocument();
  });

  it("seeds demo data and reloads the dashboard", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Grade 8 Science — Photosynthesis");

    await user.click(screen.getByRole("button", { name: /load demo data/i }));

    await waitFor(() => expect(apiMock.seedDemo).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(apiMock.dashboard).toHaveBeenCalledTimes(2));
  });

  it("shows an empty state when there are no sessions", async () => {
    apiMock.dashboard.mockResolvedValue({
      ...dashboard,
      total_sessions: 0,
      completed_sessions: 0,
      recent_sessions: [],
      engagement_trend: [],
      sessions_last_14_days: [],
      recent_events: [],
    });

    renderPage();

    expect(await screen.findByText("Start with a recording")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /create your first session/i })).toBeInTheDocument();
  });

  it("shows an error state with a retry action", async () => {
    apiMock.dashboard.mockRejectedValue(new Error("Backend unavailable"));
    renderPage();

    expect(await screen.findByText("Dashboard unavailable")).toBeInTheDocument();
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
