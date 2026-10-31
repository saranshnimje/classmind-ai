import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { health, settings } from "../test/fixtures";
import { SettingsPage } from "./Settings";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    settings: vi.fn(),
    health: vi.fn(),
    updateSettings: vi.fn(),
    applyRetention: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.settings.mockResolvedValue(settings);
    apiMock.health.mockResolvedValue(health);
    apiMock.updateSettings.mockResolvedValue({ ...settings, min_presence_sec: 45 });
    apiMock.applyRetention.mockResolvedValue({ removed_sessions: 0 });
  });

  it("loads current settings and active component status", async () => {
    renderPage();

    const minPresence = await screen.findByLabelText(/minimum presence/i);
    expect(minPresence).toHaveValue(30);
    expect(screen.getByLabelText(/late after/i)).toHaveValue(300);
    expect(screen.getAllByText("yolo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("energy").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Local LLM disabled/i).length).toBeGreaterThan(0);
  });

  it("saves updated analysis defaults", async () => {
    const user = userEvent.setup();
    renderPage();

    const minPresence = await screen.findByLabelText(/minimum presence/i);
    await user.clear(minPresence);
    await user.type(minPresence, "45");
    await user.click(screen.getByRole("button", { name: /save settings/i }));

    await waitFor(() =>
      expect(apiMock.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          min_presence_sec: 45,
          sample_interval_sec: 2,
          window_sec: 300,
          detector_backend: "auto",
        }),
      ),
    );
    expect(await screen.findByText("Settings saved")).toBeInTheDocument();
  });

  it("rejects invalid numeric values before saving", async () => {
    const user = userEvent.setup();
    renderPage();

    const minPresence = await screen.findByLabelText(/minimum presence/i);
    await user.clear(minPresence);
    await user.type(minPresence, "0");
    await user.click(screen.getByRole("button", { name: /save settings/i }));

    expect(await screen.findByText(/must be between 1 and 3600/i)).toBeInTheDocument();
    expect(apiMock.updateSettings).not.toHaveBeenCalled();
  });

  it("applies retention after confirmation", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(/minimum presence/i);
    await user.click(screen.getByRole("button", { name: /apply retention now/i }));
    expect(await screen.findByText("Apply retention now?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^apply retention$/i }));

    await waitFor(() => expect(apiMock.applyRetention).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("No sessions were old enough to remove.")).toBeInTheDocument();
  });
});
