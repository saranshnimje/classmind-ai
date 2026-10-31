import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { attendance, roster, session } from "../test/fixtures";
import { AttendancePage } from "./Attendance";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    attendance: vi.fn(),
    roster: vi.fn(),
    listSessions: vi.fn(),
    mapTrack: vi.fn(),
    createRoster: vi.fn(),
    deleteRoster: vi.fn(),
    attendanceCsvUrl: vi.fn((id: string) => `/api/sessions/${id}/attendance.csv`),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/attendance/sess-1"]}>
      <Routes>
        <Route path="/attendance/:id" element={<AttendancePage />} />
        <Route path="/attendance" element={<div>Attendance picker</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AttendancePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.attendance.mockResolvedValue(attendance);
    apiMock.roster.mockResolvedValue(roster);
    apiMock.listSessions.mockResolvedValue([session]);
    apiMock.mapTrack.mockResolvedValue(attendance.records[1]);
    apiMock.createRoster.mockResolvedValue(roster[0]);
    apiMock.deleteRoster.mockResolvedValue(undefined);
  });

  it("renders attendance counts, warnings and anonymous tracks", async () => {
    renderPage();

    expect(await screen.findByText("Attendance rate")).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(
      screen.getByText("One track was visible for less than the minimum presence time."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Participant 2").length).toBeGreaterThan(0);
    expect(screen.getByText("Uncertain")).toBeInTheDocument();
  });

  it("requires confirmation before mapping a track to a roster entry", async () => {
    const user = userEvent.setup();
    renderPage();

    const row = (await screen.findAllByText("Participant 2"))[0].closest("tr");
    expect(row).not.toBeNull();
    const scoped = within(row as HTMLElement);

    await user.selectOptions(
      scoped.getByLabelText("Map Participant 2 to a roster entry"),
      "roster-1",
    );
    await user.click(scoped.getByRole("button", { name: /^map$/i }));

    expect(await screen.findByText("Map this track?")).toBeInTheDocument();
    expect(apiMock.mapTrack).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /confirm mapping/i }));

    await waitFor(() =>
      expect(apiMock.mapTrack).toHaveBeenCalledWith("sess-1", "track-2", "roster-1", true),
    );
  });

  it("adds a roster entry", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Attendance rate");
    await user.type(screen.getByLabelText("Name"), "New Student");
    await user.click(screen.getByRole("button", { name: /add roster entry/i }));

    await waitFor(() =>
      expect(apiMock.createRoster).toHaveBeenCalledWith({
        name: "New Student",
        external_id: null,
        class_label: null,
      }),
    );
  });

  it("shows an empty state when there are no detected tracks", async () => {
    apiMock.attendance.mockResolvedValue({
      ...attendance,
      total_detected: 0,
      present: 0,
      late: 0,
      unconfirmed: 0,
      mapped: 0,
      anonymous: 0,
      attendance_rate: null,
      records: [],
      tracks: [],
      warnings: [],
    });

    renderPage();

    expect(await screen.findByText("No attendance records yet")).toBeInTheDocument();
  });
});
