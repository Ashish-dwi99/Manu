import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { api } from "../api.js";
import { countdown, formatDate, formatLongDate, shiftDay } from "../model.js";
import { Labels, PageHead, RowLink, State } from "./common.jsx";

export function DayView({ day, setDay, lens, today, onOpenCase }) {
  const query = useQuery({ queryKey: ["day", day, lens], queryFn: () => api.day(day, lens) });
  const entries = query.data?.entries || [];
  const judge = lens === "judge";
  return (
    <section className="manu-page">
      <PageHead eyebrow={judge ? "Cause list" : "Diary"} title={formatLongDate(day)}>
        <button type="button" className="manu-icon" aria-label="Previous day" onClick={() => setDay(shiftDay(day, -1))}>
          <ChevronLeft size={16} />
        </button>
        <button type="button" className="manu-quiet" onClick={() => setDay(today)} disabled={day === today}>
          Today
        </button>
        <button type="button" className="manu-icon" aria-label="Next day" onClick={() => setDay(shiftDay(day, 1))}>
          <ChevronRight size={16} />
        </button>
      </PageHead>

      <State query={query} empty={query.data && !entries.length ? "Nothing listed on this day." : null}>
        <ol className="manu-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <RowLink onClick={() => onOpenCase(entry.id)} label={`Open ${entry.title}`}>
                <span className="manu-serial">{entry.serial}</span>
                <span className="manu-row-body">
                  <span className="manu-row-title">
                    <strong>{entry.title}</strong>
                    <Labels labels={entry.labels} />
                  </span>
                  <span className="manu-row-meta">
                    {entry.case_number || entry.cnr} · {entry.court}
                  </span>
                  <span className="manu-row-purpose">Listed for {entry.next_purpose || "—"}</span>
                  {entry.last_order ? (
                    <span className="manu-row-last">
                      Last order {formatDate(entry.last_order.on)}
                      {entry.last_order.title ? ` — ${entry.last_order.title}` : ""}
                    </span>
                  ) : null}
                  {entry.due_by_today?.length ? (
                    <span className="manu-row-due">
                      {entry.due_by_today.length} direction{entry.due_by_today.length === 1 ? "" : "s"} due:{" "}
                      {entry.due_by_today.map((o) => `${o.who} (${countdown(o.due, day)})`).join(", ")}
                    </span>
                  ) : null}
                  {entry.changed_since?.length ? (
                    <span className="manu-row-changed">Changed: {entry.changed_since.map((e) => e.summary).join(" · ")}</span>
                  ) : null}
                </span>
                {judge ? (
                  <span className="manu-custody" title="Days in custody">
                    {entry.custody_days != null ? (
                      <>
                        <strong>{entry.custody_days}</strong>
                        <small>days in custody</small>
                      </>
                    ) : (
                      <small>not in custody</small>
                    )}
                  </span>
                ) : null}
              </RowLink>
            </li>
          ))}
        </ol>
      </State>
    </section>
  );
}
