import { ChevronRight } from "lucide-react";

export function Labels({ labels }) {
  if (!labels?.length) return null;
  return (
    <span className="mn-labels">
      {labels.map((label) => (
        <span key={`${label.code}:${label.reason}`} className={`mn-label tone-${label.tone}`} title={label.reason}>
          {label.code}
        </span>
      ))}
    </span>
  );
}

export function Loading({ query, empty, children }) {
  if (query.isPending) return <p className="mn-faint">Loading…</p>;
  if (query.error) return <p className="mn-error">Could not load: {String(query.error.message)}. Is the Manu API running?</p>;
  if (empty) return <p className="mn-empty">{empty}</p>;
  return children;
}

export function Row({ onClick, label, children }) {
  return (
    <li>
      <button type="button" className="mn-row" onClick={onClick} aria-label={label}>
        {children}
        <ChevronRight size={17} className="mn-row-chev" aria-hidden="true" />
      </button>
    </li>
  );
}
