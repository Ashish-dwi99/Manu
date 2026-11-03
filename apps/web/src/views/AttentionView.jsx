import { humanDates } from "../model.js";
import { Labels, Loading, SectionHead } from "./common.jsx";
import { NextStepRow, SignalList } from "./Signals.jsx";

/**
 * The practice-wide answer to "which cases need action to move forward?" Every signal
 * is a fact the record supports, with its evidence attached — never a verdict on the
 * court or anyone in it. Next steps you already accepted stay listed here until they
 * are done: accepting work never makes it disappear.
 */
export function AttentionView({ attention, today }) {
  const entries = attention.data?.entries || [];
  const inProgress = attention.data?.in_progress || [];
  const nothing = attention.data && !entries.length && !inProgress.length;
  return (
    <section className="mn-sheet">
      <div className="mn-home narrow">
        <p className="mn-eyebrow">Case progression</p>
        <h1 className="mn-display">Needs attention</h1>
        <Loading
          query={attention}
          empty={nothing ? "No stall signals in any case you follow. The diary will say so here when the record shows one." : null}
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

          {inProgress.length ? (
            <div className="mn-block">
              <SectionHead>In progress · next steps you accepted</SectionHead>
              <ul className="mn-steps">
                {inProgress.map((entry) =>
                  entry.next_steps.map((step) => <NextStepRow key={step.id} step={step} today={today} />),
                )}
              </ul>
            </div>
          ) : null}
        </Loading>
      </div>
    </section>
  );
}
