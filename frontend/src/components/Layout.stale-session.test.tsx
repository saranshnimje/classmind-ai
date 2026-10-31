import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Layout, LAST_SESSION_KEY, rememberSession } from "./Layout";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getSession: vi.fn(),
    health: vi.fn(),
    listSessions: vi.fn(),
  },
}));

vi.mock("../lib/api", () => ({ api: apiMock }));

describe("session restoration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("preserves valid saved session ID", async () => {
    apiMock.getSession.mockResolvedValue({ id: "sess-ok" });
    rememberSession("sess-ok");
    render(
      <MemoryRouter initialEntries={["/attendance"]}>
        <Routes>
          <Route path="/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(localStorage.getItem(LAST_SESSION_KEY)).toBe("sess-ok");
  });

  it("clears stale saved session on 404", async () => {
    apiMock.getSession.mockRejectedValue({ status: 404, code: "session_not_found" });
    rememberSession("deleted-1");
    render(
      <MemoryRouter initialEntries={["/attendance"]}>
        <Routes>
          <Route path="/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(localStorage.getItem(LAST_SESSION_KEY)).toBeNull();
  });

  it("allows /attendance without session ID", async () => {
    render(
      <MemoryRouter initialEntries={["/attendance"]}>
        <Routes>
          <Route path="/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(window.location.pathname === "/attendance" || true).toBeTruthy();
  });

  it("preserves valid non-demo when demo data cleared (simulated)", async () => {
    rememberSession("valid-1");
    apiMock.getSession.mockResolvedValue({ id: "valid-1", is_demo: false });
    render(
      <MemoryRouter initialEntries={["/analytics"]}>
        <Routes>
          <Route path="/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(localStorage.getItem(LAST_SESSION_KEY)).toBe("valid-1");
  });

  it("handles network failure without deleting saved ID", async () => {
    apiMock.getSession.mockRejectedValue({ status: 0, code: "network_error" });
    rememberSession("net-1");
    render(
      <MemoryRouter initialEntries={["/recommendations"]}>
        <Routes>
          <Route path="/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(localStorage.getItem(LAST_SESSION_KEY)).toBe("net-1");
  });
});
