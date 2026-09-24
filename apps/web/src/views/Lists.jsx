import { countdown, eventLabel, eventTone, formatDate, groupEventsByCase } from "../model.js";
import { Loading, Row } from "./common.jsx";

export function ChangesView({ query, onOpenCase }) {
  const groups = groupEventsByCase((query.data?.events || []).filter((e) => e.kind !== "tracked"));
  return (
    <div className="mn-measure">
      <header className="mn-greeting">
        <h1>What changed</h1>
        <p>Everything the courts did in your cases, newest first, each with where it came from.</p>
      </header>
      <div style={{ height: 30 }} />
      <Loading query={query} empty={query.data && !groups.length ? "Nothing has changed since you started following these cases." : null}>
        <div className="mn-feed">
          {groups.map((group) => (
            <section key={group.caseId} className="mn-feed-case">
              <button type="button" onClick={() => onOpenCase(group.caseId)}>
                {group.title}
              </button>
              <ul>
                {group.events.map((event) => (
                  <li key={event.id} className={`tone-${eventTone(event.kind)}`}>
                    <span className="mn-feed-kind">
                      {eventLabel(event.kind)} · {formatDate(event.at)}
                      {event.source?.connector ? ` · via ${event.source.connector}` : ""}
                    </span>
                    <span>{event.summary}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Loading>
    </div>
  );
}

export function DueView({ query, today, onOpenCase }) {
  const items = query.data?.items || [];
  return (
    <div className="mn-measure">
      <header className="mn-greeting">
        <h1>Due this week</h1>
        <p>Directions from orders and hearings in the next seven days.</p>
      </header>
      <div style={{ height: 30 }} />
      <Loading query={query} empty={query.data && !items.length ? "Nothing due this week." : null}>
        <ol className="mn-rows">
          {items.map((item) => (
            <Row key={item.id} onClick={() => onOpenCase(item.case_id)} label={`Open ${item.case_title}`}>
              <span className={`mn-row-side ${item.overdue ? "overdue" : ""}`} style={{ justifyItems: "start", minWidth: 118 }}>
                <strong style={{ fontSize: 19 }}>{countdown(item.due, today)}</strong>
                <small>{formatDate(item.due)}</small>
              </span>
              <span className="mn-row-body">
                <span className="mn-row-title">
                  <strong>{item.kind === "hearing" ? item.what : item.who}</strong>
                </span>
                {item.kind !== "hearing" ? <span className="mn-row-note">{item.what}</span> : null}
                <span className="mn-row-meta">{item.case_title}</span>
              </span>
            </Row>
          ))}
        </ol>
      </Loading>
    </div>
  );
}
