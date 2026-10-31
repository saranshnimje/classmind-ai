import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AboutPage } from "./About";

function renderPage() {
  return render(
    <MemoryRouter>
      <AboutPage />
    </MemoryRouter>,
  );
}

describe("AboutPage", () => {
  it("explains local processing and the absence of biometric identification", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Privacy & method" })).toBeInTheDocument();
    expect(screen.getAllByText("Local processing").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/No face recognition, no face embeddings, no identity inference/i)
        .length,
    ).toBeGreaterThan(0);
  });

  it("links to creating a session", () => {
    renderPage();

    expect(screen.getByRole("link", { name: /new session/i })).toHaveAttribute(
      "href",
      "/sessions/new",
    );
  });
});
