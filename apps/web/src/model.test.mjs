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

import { asCnr, courtLabel, groupByCourt, groupByDay, locateQuote } from "./model.js";

test("a CNR is recognised with or without dashes and spaces", () => {
  assert.equal(asCnr("dlse01-000123-2024"), "DLSE010001232024");
  assert.equal(asCnr("DLSE 0100 0123 2024"), "DLSE010001232024");
  assert.equal(asCnr("State v. Aamir"), null);
  assert.equal(asCnr("DLSE01000123202"), null);
});

test("court names shorten to bench and place", () => {
  assert.equal(courtLabel("Court of ASJ-03, South District, Saket, New Delhi"), "ASJ-03 · Saket");
  assert.equal(courtLabel(""), "Court not yet read");
});

test("cases group by court, dated first", () => {
  const groups = groupByCourt([
    { id: "a", court: "Court of X, D, P, S", next_date: null },
    { id: "b", court: "Court of X, D, P, S", next_date: "2026-10-01" },
    { id: "c", court: "Court of A, D, Q, S", next_date: "2026-09-30" },
  ]);
  assert.deepEqual(groups.map((g) => [g.court, g.cases.map((c) => c.id)]), [["A · Q", ["c"]], ["X · P", ["b", "a"]]]);
});

test("items group by day in date order", () => {
  const groups = groupByDay([{ due: "2026-09-29" }, { due: "2026-09-25" }, { due: "2026-09-29" }]);
  assert.deepEqual(groups.map((g) => [g.day, g.entries.length]), [["2026-09-25", 1], ["2026-09-29", 2]]);
});

test("a quote is found across line breaks and spacing, never guessed", () => {
  const text = "Reply not filed.\nThe IO is directed  to file\nthe reply on or before 29.09.2026.";
  const range = locateQuote(text, "The IO is directed to file the reply on or before 29.09.2026.");
  assert.equal(text.slice(range[0], range[1]), "The IO is directed  to file\nthe reply on or before 29.09.2026");
  assert.deepEqual(locateQuote(text, "Reply not filed.", [0, 16]), [0, 16]);
  assert.equal(locateQuote(text, "bail is granted"), null);
});

import { humanDates } from "./model.js";

test("ISO dates in reasons read as Indian dates", () => {
  assert.equal(humanDates("crossed on 2026-09-28."), `crossed on ${formatDate("2026-09-28")}.`);
});
