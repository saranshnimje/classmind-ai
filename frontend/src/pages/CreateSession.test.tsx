import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { session, settings } from "../test/fixtures";
import { CreateSessionPage } from "./CreateSession";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    settings: vi.fn(),
    createSession: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/sessions/new"]}>
      <Routes>
        <Route path="/sessions/new" element={<CreateSessionPage />} />
        <Route path="/sessions/:id" element={<div>Session detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CreateSessionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.settings.mockResolvedValue(settings);
    apiMock.createSession.mockResolvedValue({ ...session, id: "new-session" });
  });

  it("validates required fields before submitting", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /create session/i }));

    expect(await screen.findByText("A session title is required.")).toBeInTheDocument();
    expect(apiMock.createSession).not.toHaveBeenCalled();
  });

  it("creates a session and navigates to its detail page", async () => {
    const user = userEvent.setup();
    renderPage();

    const title = screen.getByLabelText(/session title/i);
    await user.clear(title);
    await user.type(title, "Grade 9 History — Industrial Revolution");
    await user.click(screen.getByRole("button", { name: /create session/i }));

    await waitFor(() => expect(apiMock.createSession).toHaveBeenCalledTimes(1));
    expect(apiMock.createSession).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Grade 9 History — Industrial Revolution",
        subject: "General",
      }),
    );
    expect(await screen.findByText("Session detail page")).toBeInTheDocument();
  });

  it("sends optional analysis overrides when provided", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/session title/i), "Short lesson");
    await user.click(screen.getByText("Analysis thresholds"));
    await user.type(screen.getByLabelText(/minimum presence/i), "45");
    await user.type(screen.getByLabelText(/frame sample interval/i), "4");
    await user.click(screen.getByRole("button", { name: /create session/i }));

    await waitFor(() =>
      expect(apiMock.createSession).toHaveBeenCalledWith(
        expect.objectContaining({ min_presence_sec: 45, sample_interval_sec: 4 }),
      ),
    );
  });

  it("shows the backend error when creation fails", async () => {
    apiMock.createSession.mockRejectedValue(new Error("A session with this title exists"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/session title/i), "Duplicate");
    await user.click(screen.getByRole("button", { name: /create session/i }));

    expect(await screen.findByText("Could not create session")).toBeInTheDocument();
    expect(screen.getByText("A session with this title exists")).toBeInTheDocument();
  });
});
