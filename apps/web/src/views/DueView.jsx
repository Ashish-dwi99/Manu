import { useQuery } from "@tanstack/react-query";

import { api } from "../api.js";
import { countdown, formatDate } from "../model.js";
import { PageHead, RowLink, State } from "./common.jsx";

export function DueView({ today, onOpenCase }) {
  const query = useQuery({ queryKey: ["upcoming", today], queryFn: () => api.upcoming(today) });
  const items = query.data?.items || [];
  return (
    <section className="manu-page">
      <PageHead eyebrow="Next 14 days" title="Due" />
      <State query={query} empty={query.data && !items.length ? "Nothing due in the next two weeks." : null}>
        <ol className="manu-list">
          {items.map((item) => (
            <li key={item.id}>
              <RowLink onClick={() => onOpenCase(item.case_id)} label={`Open ${item.case_title}`}>
                <span className={`manu-when ${item.overdue ? "overdue" : ""}`}>
                  <strong>{countdown(item.due, today)}</strong>
                  <small>{formatDate(item.due)}</small>
                </span>
                <span className="manu-row-body">
                  <span className="manu-row-title">
                    <strong>{item.kind === "hearing" ? item.what : item.who}</strong>
                  </span>
                  {item.kind !== "hearing" ? <span className="manu-row-purpose">{item.what}</span> : null}
                  <span className="manu-row-meta">{item.case_title}</span>
                </span>
              </RowLink>
            </li>
          ))}
        </ol>
      </State>
    </section>
  );
}
