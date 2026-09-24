import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { api } from "../api.js";
import { countdown, formatDate, formatLongDate, greeting, plural, shiftDay } from "../model.js";
import { Labels, Loading, Row } from "./common.jsx";

export function HomeView({ day, setDay, lens, today, onOpenCase, go, changeCount, dueCount }) {
  const query = useQuery({ queryKey: ["day", day, lens], queryFn: () => api.day(day, lens) });
  const entries = query.data?.entries || [];
  const judge = lens === "judge";
  const isToday = day === today;

  return (
    <div className="mn-measure">
      <header className="mn-greeting">
        <h1>{greeting()}.</h1>
        <p>
          {formatLongDate(today)} ·{" "}
          {judge ? "Your cause list, with what the record says about liberty." : "Your diary, read from the court this morning."}
        </p>
      </header>

      <div className="mn-glance">
        <button type="button" onClick={() => setDay(today)}>
          <strong>{isToday ? entries.length : "—"}</strong>
          <span>{judge ? "matters listed today" : "cases listed today"}</span>
        </button>
        <button type="button" onClick={() => go("changes")}>
          <strong>{changeCount}</strong>
          <span>changes since yesterday</span>
        </button>
        <button type="button" onClick={() => go("due")}>
          <strong>{dueCount}</strong>
          <span>directions due this week</span>
        </button>
      </div>

      <div className="mn-head">
        <div>
          <p className="mn-kicker">{judge ? "Cause list" : "Listed"}</p>
          <h2>{isToday ? "Today" : formatLongDate(day)}</h2>
        </div>
        <div className="mn-actions">
          <button type="button" className="mn-icon" aria-label="Previous day" onClick={() => setDay(shiftDay(day, -1))}>
            <ChevronLeft size={17} />
          </button>
          <button type="button" className="mn-btn small" onClick={() => setDay(today)} disabled={isToday}>
            Today
          </button>
          <button type="button" className="mn-icon" aria-label="Next day" onClick={() => setDay(shiftDay(day, 1))}>
            <ChevronRight size={17} />
          </button>
        </div>
      </div>

      <Loading query={query} empty={query.data && !entries.length ? "Nothing listed on this day." : null}>
        <ol className="mn-rows">
          {entries.map((entry) => (
            <Row key={entry.id} onClick={() => onOpenCase(entry.id)} label={`Open ${entry.title}`}>
              <span className="mn-serial">{entry.serial}</span>
              <span className="mn-row-body">
                <span className="mn-row-title">
                  <strong>{entry.title}</strong>
                  <Labels labels={entry.labels} />
                </span>
                <span className="mn-row-meta">
                  {entry.case_number || entry.cnr} · {entry.court}
                </span>
                <span className="mn-row-note">
                  For <b>{entry.next_purpose || "—"}</b>
                  {entry.last_order ? ` · last order ${formatDate(entry.last_order.on)}${entry.last_order.title ? `, ${entry.last_order.title.toLowerCase()}` : ""}` : ""}
                </span>
                {entry.due_by_today?.length ? (
                  <span className="mn-row-due">
                    {plural(entry.due_by_today.length, "direction")} due: {entry.due_by_today.map((o) => `${o.who} (${countdown(o.due, day)})`).join(", ")}
                  </span>
                ) : null}
                {entry.changed_since?.length ? (
                  <span className="mn-row-changed">{entry.changed_since.map((e) => e.summary).join(" · ")}</span>
                ) : null}
              </span>
              {judge ? (
                <span className="mn-row-side" title="Days in custody">
                  {entry.custody_days != null ? (
                    <>
                      <strong>{entry.custody_days}</strong>
                      <small>days in custody</small>
                    </>
                  ) : (
                    <small>on bail</small>
                  )}
                </span>
              ) : null}
            </Row>
          ))}
        </ol>
      </Loading>
    </div>
  );
}
