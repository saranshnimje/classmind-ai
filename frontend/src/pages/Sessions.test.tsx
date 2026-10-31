import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { session } from "../test/fixtures";
import { SessionsPage } from "./Sessions";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    listSessions: vi.fn(),
    deleteSession: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
}

describe("SessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listSessions.mockResolvedValue([session]);
    apiMock.deleteSession.mockResolvedValue(undefined);
  });

  it("lists sessions with status and metrics", async () => {
    renderPage();

    expect(await screen.findByText("Grade 8 Science — Photosynthesis")).toBeInTheDocument();
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getByText("62%")).toBeInTheDocument();
    expect(screen.getByText(/1\.0 MB/)).toBeInTheDocument();
  });

  it("shows an empty state when no sessions exist", async () => {
    apiMock.listSessions.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("No sessions yet")).toBeInTheDocument();
  });

  it("deletes a session after confirmation", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Grade 8 Science — Photosynthesis");
    await user.click(
      screen.getByRole("button", { name: "Delete Grade 8 Science — Photosynthesis" }),
    );

    expect(await screen.findByText("Delete this session?")).toBeInTheDocument();
    expect(apiMock.deleteSession).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /delete session/i }));

    await waitFor(() => expect(apiMock.deleteSession).toHaveBeenCalledWith("sess-1"));
  });

  it("shows an error state when loading fails", async () => {
    apiMock.listSessions.mockRejectedValue(new Error("Could not read the local database"));
    renderPage();

    expect(await screen.findByText("Sessions unavailable")).toBeInTheDocument();
    expect(screen.getByText("Could not read the local database")).toBeInTheDocument();
  });
});
