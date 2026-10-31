import { describe, expect, it } from "vitest";

import {
  engagementTone,
  fmtClock,
  fmtDuration,
  fmtRate,
  fmtRatio,
  fmtScore,
  validateMediaFile,
} from "../lib/format";

const limits = {
  max_upload_mb: 1,
  video_extensions: [".mp4", ".mov"],
  audio_extensions: [".wav", ".mp3"],
};

function makeFile(name: string, size: number): File {
  return new File([new Uint8Array(size)], name, { type: "application/octet-stream" });
}

describe("format helpers", () => {
  it("formats durations and clocks", () => {
    expect(fmtDuration(75)).toBe("1:15");
    expect(fmtDuration(3675)).toBe("1h 01m");
    expect(fmtClock(65)).toBe("01:05");
    expect(fmtClock(3661)).toBe("01:01:01");
    expect(fmtDuration(null)).toBe("—");
  });

  it("formats ratios and rates differently", () => {
    expect(fmtRatio(0.6234)).toBe("62%");
    expect(fmtRatio(0.6234, 1)).toBe("62.3%");
    expect(fmtRate(66.67)).toBe("66.7%");
    expect(fmtScore(0.618)).toBe("0.62");
  });

  it("returns an em dash for missing values", () => {
    expect(fmtRatio(null)).toBe("—");
    expect(fmtRate(undefined)).toBe("—");
    expect(fmtScore(Number.NaN)).toBe("—");
  });

  it("maps engagement scores to descriptive bands", () => {
    expect(engagementTone(0.7)).toBe("high");
    expect(engagementTone(0.45)).toBe("medium");
    expect(engagementTone(0.2)).toBe("low");
    expect(engagementTone(null)).toBe("unknown");
  });
});

describe("validateMediaFile", () => {
  it("accepts a supported, non-empty file within the limit", () => {
    expect(validateMediaFile(makeFile("lesson.mp4", 1024), "video", limits)).toBeNull();
    expect(validateMediaFile(makeFile("room.wav", 1024), "audio", limits)).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    const problem = validateMediaFile(makeFile("lesson.txt", 1024), "video", limits);
    expect(problem).toContain("Unsupported video format");
    expect(problem).toContain(".txt");
  });

  it("rejects files over the configured limit", () => {
    const problem = validateMediaFile(makeFile("lesson.mp4", 2 * 1024 * 1024), "video", limits);
    expect(problem).toContain("limit is 1 MB");
  });

  it("rejects empty files", () => {
    expect(validateMediaFile(makeFile("lesson.mp4", 0), "video", limits)).toBe(
      "The selected file is empty.",
    );
  });
});
