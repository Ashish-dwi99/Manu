import { ArrowRight } from "lucide-react";

import { humanDates } from "../model.js";

export function navigate(path) {
  window.location.hash = path;
}

/** Manu's mark: an M drawn as two bench steps, in the accent. */
export function Mark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="mn-mark">
      <rect width="64" height="64" rx="16" fill="currentColor" />
      <path d="M17 45V20l15 14 15-14v25" fill="none" stroke="var(--mark-ink)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Labels({ labels, only }) {
  const shown = (labels || []).filter((label) => !only || only(label));
  if (!shown.length) return null;
  return (
    <span className="mn-labels">
      {shown.map((label) => (
        <span key={`${label.code}:${label.reason}`} className={`mn-label tone-${label.tone}`} title={humanDates(label.reason)}>
          {label.code}
        </span>
      ))}
    </span>
  );
}

export function Loading({ query, empty, children }) {
  if (query.isPending) return <p className="mn-faint mn-pad">Loading…</p>;
  if (query.error) return <p className="mn-error">Could not load: {String(query.error.message)}. Is the Manu API running?</p>;
  if (empty) return <p className="mn-empty">{empty}</p>;
  return children;
}

export function SectionHead({ children, tools }) {
  return (
    <div className="mn-section-head">
      <h2>{children}</h2>
      {tools ? <div className="mn-section-tools">{tools}</div> : null}
    </div>
  );
}

/** A row that opens something: the whole row is the link, the arrow is decoration. */
export function RowLink({ href, onClick, label, children, className = "" }) {
  const inner = (
    <>
      {children}
      <ArrowRight size={15} className="mn-row-arrow" aria-hidden="true" />
    </>
  );
  return (
    <li>
      {href ? (
        <a className={`mn-row ${className}`} href={href} aria-label={label}>
          {inner}
        </a>
      ) : (
        <button type="button" className={`mn-row ${className}`} onClick={onClick} aria-label={label}>
          {inner}
        </button>
      )}
    </li>
  );
}

/**
 * The numbered citation. Every fact Manu shows points at the words it came from; the
 * pill opens those words in the source panel. Amber when only Manu has read it, red
 * when the words could not be found.
 */
export function CitePill({ n, verification, onClick, active, label }) {
  const tone = verification === "lead" ? "lead" : verification === "missing" ? "missing" : "ok";
  return (
    <button
      type="button"
      className={`mn-cite ${tone} ${active ? "on" : ""}`}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      aria-label={label || `Source ${n}`}
      title={label || `Source ${n}`}
    >
      {n}
    </button>
  );
}
