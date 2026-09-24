import { ChevronRight } from "lucide-react";

export function Labels({ labels }) {
  if (!labels?.length) return null;
  return (
    <span className="manu-labels">
      {labels.map((label) => (
        <span key={`${label.code}:${label.reason}`} className={`manu-label tone-${label.tone}`} title={label.reason}>
          {label.code}
        </span>
      ))}
    </span>
  );
}

export function PageHead({ eyebrow, title, children }) {
  return (
    <header className="manu-page-head">
      <div>
        {eyebrow ? <p className="manu-eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
      </div>
      {children ? <div className="manu-page-actions">{children}</div> : null}
    </header>
  );
}

export function State({ query, empty, children }) {
  if (query.isPending) return <p className="manu-muted manu-pad">Loading…</p>;
  if (query.error) return <p className="manu-error manu-pad">Could not load: {String(query.error.message)}. Is the Manu API running?</p>;
  if (empty) return <p className="manu-muted manu-pad">{empty}</p>;
  return children;
}

export function RowLink({ onClick, children, label }) {
  return (
    <button type="button" className="manu-row" onClick={onClick} aria-label={label}>
      {children}
      <ChevronRight size={16} className="manu-row-chevron" aria-hidden="true" />
    </button>
  );
}
