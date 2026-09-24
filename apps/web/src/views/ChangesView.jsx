import { useQuery } from "@tanstack/react-query";

import { api } from "../api.js";
import { eventLabel, eventTone, formatDate, groupEventsByCase } from "../model.js";
import { PageHead, State } from "./common.jsx";

export function ChangesView({ onOpenCase }) {
  const query = useQuery({ queryKey: ["changes"], queryFn: api.changes });
  const groups = groupEventsByCase((query.data?.events || []).filter((e) => e.kind !== "tracked"));
  return (
    <section className="manu-page">
      <PageHead eyebrow="Across your cases" title="What changed" />
      <State query={query} empty={query.data && !groups.length ? "Nothing has changed since you started following these cases." : null}>
        <div className="manu-groups">
          {groups.map((group) => (
            <article key={group.caseId} className="manu-group">
              <button type="button" className="manu-group-title" onClick={() => onOpenCase(group.caseId)}>
                {group.title}
              </button>
              <ul>
                {group.events.map((event) => (
                  <li key={event.id} className={`tone-${eventTone(event.kind)}`}>
                    <span className="manu-event-kind">{eventLabel(event.kind)}</span>
                    <span className="manu-event-summary">{event.summary}</span>
                    <small className="manu-muted">
                      {formatDate(event.at)}
                      {event.source?.connector ? ` · via ${event.source.connector}` : ""}
                    </small>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </State>
    </section>
  );
}
