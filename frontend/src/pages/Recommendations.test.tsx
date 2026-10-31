import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { recommendations, session } from "../test/fixtures";
import { RecommendationsPage } from "./Recommendations";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    recommendations: vi.fn(),
    listSessions: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/recommendations/sess-1"]}>
      <Routes>
        <Route path="/recommendations/:id" element={<RecommendationsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RecommendationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.recommendations.mockResolvedValue(recommendations);
    apiMock.listSessions.mockResolvedValue([session]);
  });

  it("renders evidence-linked suggestions with their source", async () => {
    renderPage();

    expect(await screen.findByText("Consider a short peer discussion")).toBeInTheDocument();
    expect(screen.getByText("Rule-based")).toBeInTheDocument();
    expect(
      screen.getByText("Window 1 engagement 52% vs window 2 engagement 72%."),
    ).toBeInTheDocument();
    expect(screen.getByText("Engagement proxy rose from 52% to 72% across the session.")).toBeInTheDocument();
    expect(
      screen.getAllByText(/Suggestions describe patterns in the recording/i).length,
    ).toBeGreaterThan(0);
  });

  it("filters suggestions by priority", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Consider a short peer discussion");
    await user.selectOptions(screen.getByLabelText(/priority/i), "high");

    expect(await screen.findByText("No suggestions match these filters")).toBeInTheDocument();
  });

  it("shows an empty state when no rule matched", async () => {
    apiMock.recommendations.mockResolvedValue({
      ...recommendations,
      generated_by: "none",
      recommendations: [],
      llm_status: "No rule conditions matched this session's data.",
    });

    renderPage();

    expect(await screen.findByText("No suggestions for this session")).toBeInTheDocument();
  });
});
