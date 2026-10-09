import { describe, expect, it } from "vitest";
import { countdown, sortByDeadline } from "./deadline";

const NOW = new Date(2026, 9, 9, 11, 0);   // 9 Oct 2026, 11:00 local

describe("countdown", () => {
  it("counts calendar days left", () => {
    expect(countdown("2026-10-30T15:00:00", NOW)).toEqual({ label: "21 days left", urgent: false, passed: false });
    expect(countdown("2026-10-12T09:00:00", NOW)).toEqual({ label: "3 days left", urgent: true, passed: false });
    expect(countdown("2026-10-10T09:00:00", NOW)).toEqual({ label: "1 day left", urgent: true, passed: false });
  });

  it("says due today until the deadline time, then passed", () => {
    expect(countdown("2026-10-09T17:00:00", NOW)).toEqual({ label: "Due today", urgent: true, passed: false });
    expect(countdown("2026-10-09T10:00:00", NOW)).toEqual({ label: "Deadline passed", urgent: false, passed: true });
    expect(countdown("2026-09-30T17:00:00", NOW).passed).toBe(true);
  });

  it("is null without a usable date", () => {
    expect(countdown(null, NOW)).toBeNull();
    expect(countdown("not a date", NOW)).toBeNull();
  });
});

describe("sortByDeadline", () => {
  it("puts the soonest upcoming first, then undated, then passed", () => {
    const tenders = [
      { id: 1, deadline_at: "2026-09-01T17:00:00" },
      { id: 2, deadline_at: null },
      { id: 3, deadline_at: "2026-11-06T14:00:00" },
      { id: 4, deadline_at: "2026-10-12T09:00:00" },
    ];
    expect(sortByDeadline(tenders, NOW).map((t) => t.id)).toEqual([4, 3, 2, 1]);
  });
});
