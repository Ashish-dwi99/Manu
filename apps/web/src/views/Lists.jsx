import { countdown, eventLabel, eventTone, formatDate, formatLongDate, groupByDay, groupEventsByCase } from "../model.js";
import { Loading, RowLink, SectionHead } from "./common.jsx";

export function ChangesView({ changes }) {
  const groups = groupEventsByCase((changes.data?.events || []).filter((e) => e.kind !== "tracked"));
  return (
    <section className="mn-sheet">
      <div className="mn-home narrow">
        <p className="mn-eyebrow">From the courts, newest first</p>
        <h1 className="mn-display">What changed</h1>
        <Loading query={changes} empty={changes.data && !groups.length ? "Nothing has changed since you started following these cases." : null}>
          {groups.map((group) => (
            <div key={group.caseId} className="mn-block">
              <SectionHead tools={<a className="mn-text-btn" href={`#/c/${group.caseId}`}>Open case →</a>}>{group.title}</SectionHead>
              <ol className="mn-rows">
                {group.events.map((event) => (
                  <RowLink key={event.id} href={`#/c/${group.caseId}`} label={`${eventLabel(event.kind)}: ${event.summary}`}>
                    <span className={`mn-kind tone-${eventTone(event.kind)}`}>{eventLabel(event.kind)}</span>
                    <span className="mn-row-main">
                      <span className="mn-row-title plain">{event.summary}</span>
                    </span>
                    <span className="mn-row-aside">
                      <small>{formatDate(event.at)}</small>
                      {event.source?.connector ? <small className="mono">via {event.source.connector}</small> : null}
                    </span>
                  </RowLink>
                ))}
              </ol>
            </div>
          ))}
        </Loading>
      </div>
    </section>
  );
}

export function WeekView({ upcoming, today }) {
  const days = groupByDay(upcoming.data?.items);
  return (
    <section className="mn-sheet">
      <div className="mn-home narrow">
        <p className="mn-eyebrow">Hearings and directions, next seven days</p>
        <h1 className="mn-display">This week</h1>
        <Loading query={upcoming} empty={upcoming.data && !days.length ? "Nothing listed or due this week." : null}>
          {days.map(({ day, entries }) => (
            <div key={day} className="mn-block">
              <SectionHead tools={<span className={`mn-when ${day < today ? "red" : day === today ? "amber" : ""}`}>{countdown(day, today)}</span>}>
                {formatLongDate(day)}
              </SectionHead>
              <ol className="mn-rows">
                {entries.map((item) => (
                  <RowLink key={item.id} href={`#/c/${item.case_id}`} label={`Open ${item.case_title}`}>
                    <span className={`mn-kind ${item.kind === "hearing" ? "tone-blue" : item.overdue ? "tone-coral" : "tone-amber"}`}>
                      {item.kind === "hearing" ? "Hearing" : item.who}
                    </span>
                    <span className="mn-row-main">
                      <span className="mn-row-title plain">{item.kind === "hearing" ? item.what.replace(/^Hearing — /, "") : item.what}</span>
                      <span className="mn-row-sub">{item.case_title}</span>
                    </span>
                  </RowLink>
                ))}
              </ol>
            </div>
          ))}
        </Loading>
      </div>
    </section>
  );
}
