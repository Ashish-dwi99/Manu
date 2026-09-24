// Pure helpers for the diary UI. Dates are read and shown in India time, as in Tura's
// Manu workspace model (features/advocate/manuWorkspaceModel.js), which these port.

export const MANU_TIME_ZONE = "Asia/Kolkata";

const DATE = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric", timeZone: MANU_TIME_ZONE });
const LONG = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", weekday: "long", year: "numeric", timeZone: MANU_TIME_ZONE });
const KEY = new Intl.DateTimeFormat("en-CA", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: MANU_TIME_ZONE });

export function indiaDateKey(now = new Date()) {
  return KEY.format(now);
}

function parse(value) {
  const parsed = new Date(`${String(value).slice(0, 10)}T12:00:00+05:30`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDate(value, fallback = "Date not set") {
  const parsed = value ? parse(value) : null;
  return parsed ? DATE.format(parsed) : fallback;
}

export function formatLongDate(value) {
  const parsed = value ? parse(value) : new Date();
  return parsed ? LONG.format(parsed) : "";
}

export function dayDistance(value, todayKey) {
  if (!value) return null;
  const target = parse(value);
  const today = parse(todayKey);
  if (!target || !today) return null;
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export function countdown(value, todayKey) {
  const days = dayDistance(value, todayKey);
  if (days === null) return "Date not confirmed";
  if (days < 0) return `${-days} day${days === -1 ? "" : "s"} overdue`;
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  return `In ${days} days`;
}

export function shiftDay(key, delta) {
  const parsed = parse(key);
  parsed.setUTCDate(parsed.getUTCDate() + delta);
  return indiaDateKey(parsed);
}

const EVENT_LABELS = {
  tracked: "Now following",
  new_order: "New order",
  hearing_date_changed: "Date moved",
  listed: "Listed",
  status_changed: "Status changed",
  stage_changed: "Stage moved",
  disposed: "Disposed",
  obligation_found: "Direction found",
  fetch_failed: "Could not read court",
  brief_prepared: "Brief prepared",
};

export function eventLabel(kind) {
  return EVENT_LABELS[kind] || kind;
}

export function eventTone(kind) {
  if (kind === "fetch_failed") return "coral";
  if (kind === "hearing_date_changed" || kind === "disposed") return "amber";
  if (kind === "new_order" || kind === "obligation_found") return "accent";
  return "muted";
}

export function verificationLabel(verification) {
  return {
    verified: "From the court",
    human_confirmed: "Confirmed by you",
    lead: "Read by Manu — confirm",
    unverified: "Unverified",
  }[verification] || "Unverified";
}

export function s479Headline(s479) {
  if (!s479) return "";
  const map = {
    not_applicable: "Section 479 does not apply",
    insufficient_data: "Cannot compute — data missing",
    not_yet: "Below threshold",
    approaching: "Threshold approaching",
    crossed: "Threshold crossed",
    maximum_exceeded: "Maximum period reached",
  };
  return map[s479.status] || s479.status;
}

export function groupEventsByCase(events) {
  const groups = new Map();
  for (const event of events || []) {
    const key = event.case_id;
    if (!groups.has(key)) groups.set(key, { caseId: key, title: event.case_title || key, events: [] });
    groups.get(key).events.push(event);
  }
  return [...groups.values()];
}

export function greeting(now = new Date()) {
  const hour = Number(new Intl.DateTimeFormat("en-IN", { hour: "numeric", hour12: false, timeZone: MANU_TIME_ZONE }).format(now));
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function plural(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

// -- one case OS: helpers for the shell, the board and the source panel -----------------

/** A CNR is 16 characters: state (2) + district (2) + establishment (2) + number (6) + year (4). */
export function asCnr(value) {
  const cleaned = String(value || "").toUpperCase().replace(/[\s-]/g, "");
  return /^[A-Z]{4}\d{2}\d{6}(19|20)\d{2}$/.test(cleaned) ? cleaned : null;
}

/** "Court of ASJ-03, South District, Saket, New Delhi" → { name: "ASJ-03", place: "Saket" }. */
export function shortCourt(court) {
  const parts = String(court || "").split(",").map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return { name: "Court not yet read", place: "" };
  const name = parts[0].replace(/^(the\s+)?court of\s+(the\s+)?/i, "");
  const place = parts.length > 2 ? parts[parts.length - 2] : parts[1] || "";
  return { name, place };
}

export function courtLabel(court) {
  const { name, place } = shortCourt(court);
  return place ? `${name} · ${place}` : name;
}

/** Cases grouped by court, courts in name order, cases by next date (undated last). */
export function groupByCourt(cases) {
  const groups = new Map();
  for (const c of cases || []) {
    const key = courtLabel(c.court);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([court, items]) => ({
      court,
      cases: items.sort((a, b) => (a.next_date || "9999").localeCompare(b.next_date || "9999")),
    }));
}

/** Items with a `due` date grouped by day, in date order. */
export function groupByDay(items) {
  const groups = new Map();
  for (const item of items || []) {
    const key = String(item.due || "").slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([day, entries]) => ({ day, entries }));
}

function normalise(text) {
  // Lower-case letters and digits only, with a map back to the original offsets, so a
  // quote still matches across line breaks, double spaces and curly punctuation.
  const chars = [];
  const index = [];
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (/[\p{L}\p{N}]/u.test(ch)) {
      chars.push(ch.toLowerCase());
      index.push(i);
    }
  }
  return { flat: chars.join(""), index };
}

/**
 * Where a quote sits in a text, as [start, end) offsets, or null. Tries the exact
 * words first, then letters-and-digits only. A span the reader already recorded wins
 * when it still holds the quote.
 */
export function locateQuote(text, quote, span) {
  if (!text || !quote) return null;
  if (span && span[0] != null && span[1] != null && text.slice(span[0], span[1]) === quote) return [span[0], span[1]];
  const exact = text.indexOf(quote);
  if (exact >= 0) return [exact, exact + quote.length];
  const hay = normalise(text);
  const needle = normalise(quote).flat;
  if (!needle) return null;
  const at = hay.flat.indexOf(needle);
  if (at < 0) return null;
  return [hay.index[at], hay.index[at + needle.length - 1] + 1];
}

/** Split text into [before, match, after] around a located quote. */
export function splitAround(text, range) {
  if (!range) return [text, "", ""];
  return [text.slice(0, range[0]), text.slice(range[0], range[1]), text.slice(range[1])];
}

const RED_LABELS = new Set(["red"]);

export function urgentLabels(labels) {
  return (labels || []).filter((label) => RED_LABELS.has(label.tone));
}

export function firstName(title) {
  return String(title || "").replace(/^State v\.\s*/i, "");
}

/** Reasons from the law engine carry ISO dates; people read "28 Sept 2026". */
export function humanDates(text) {
  return String(text || "").replace(/\b(\d{4}-\d{2}-\d{2})\b/g, (iso) => formatDate(iso));
}
