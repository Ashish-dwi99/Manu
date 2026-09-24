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
