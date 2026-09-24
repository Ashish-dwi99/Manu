import assert from "node:assert/strict";
import test from "node:test";

import { countdown, dayDistance, formatDate, groupEventsByCase, shiftDay, verificationLabel } from "./model.js";

test("countdown speaks in days from the diary's today", () => {
  assert.equal(countdown("2026-09-24", "2026-09-24"), "Today");
  assert.equal(countdown("2026-09-25", "2026-09-24"), "Tomorrow");
  assert.equal(countdown("2026-10-01", "2026-09-24"), "In 7 days");
  assert.equal(countdown("2026-09-22", "2026-09-24"), "2 days overdue");
  assert.equal(countdown(null, "2026-09-24"), "Date not confirmed");
});

test("dates are Indian format", () => {
  assert.equal(formatDate("2026-10-01"), "01 Oct 2026");
  assert.equal(formatDate(""), "Date not set");
});

test("shiftDay crosses months", () => {
  assert.equal(shiftDay("2026-09-30", 1), "2026-10-01");
  assert.equal(dayDistance("2026-10-01", "2026-09-30"), 1);
});

test("verification labels never overstate", () => {
  assert.equal(verificationLabel("lead"), "Read by Manu — confirm");
  assert.equal(verificationLabel("anything"), "Unverified");
});

test("events group by case in first-seen order", () => {
  const groups = groupEventsByCase([
    { case_id: "a", case_title: "A", kind: "new_order" },
    { case_id: "b", case_title: "B", kind: "listed" },
    { case_id: "a", case_title: "A", kind: "hearing_date_changed" },
  ]);
  assert.deepEqual(groups.map((g) => [g.title, g.events.length]), [["A", 2], ["B", 1]]);
});
