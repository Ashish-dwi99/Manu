import { humanDates } from "../model.js";
import { Labels, Loading, SectionHead } from "./common.jsx";
import { SignalList } from "./Signals.jsx";

/**
 * The practice-wide answer to "which cases need action to move forward?" Every row
 * is a fact the record supports, with its evidence attached. A signal is never a
 * verdict: a repeated date is not an adjournment, a gap is not proof, and nothing
 * here says whose fault anything is.
 */
export function AttentionView({ attention, today }) {
  const entries = attention.data?.entries || [];
  return (
    <section className="mn-sheet">
      <div className="mn-home narrow">
        <p className="mn-eyebrow">Case progression</p>
        <h1 className="mn-display">Needs attention</h1>
        <p className="mn-attention-lede">
          What the record itself says about cases that are not moving. Every signal shows its evidence; nothing here is a
          verdict on the court or anyone in it.
        </p>
        <Loading
          query={attention}
          empty={attention.data && !entries.length ? "No stall signals in any case you follow. The diary will say so here when the record shows one." : null}
        >
          {entries.map((entry) => (
            <div key={entry.id} className="mn-block">
              <SectionHead
                tools={
                  <a className="mn-text-btn" href={`#/c/${entry.id}`}>
                    Open case →
                  </a>
                }
              >
                {entry.title} <Labels labels={entry.labels} />
              </SectionHead>
              <p className="mn-attention-case-sub">
                {entry.next_date
                  ? `Next ${humanDates(entry.next_date)}${entry.next_purpose ? ` · ${entry.next_purpose}` : ""}`
                  : "No date listed"}
                {" · "}
                {entry.court}
              </p>
              <SignalList caseId={entry.id} signals={entry.signals} today={today} />
            </div>
          ))}
        </Loading>
      </div>
    </section>
  );
}
