import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, CheckCheck, ChevronDown, EyeOff } from "lucide-react";

import { api } from "../api.js";
import { countdown, formatDate, humanDates, signalKindLabel, signalTone } from "../model.js";

/**
 * One stall signal: the fact, the action, the evidence. The fact and what to do come
 * first; what the signal is *not* (no blame, no proof from gaps) sits one tap away.
 * Manu proposes; the advocate decides. Tucking a signal away lasts until the record
 * changes underneath it; an accepted next step stays on the practice view until done.
 */
export function SignalCard({ caseId, signal, today }) {
  const queryClient = useQueryClient();
  const onSuccess = () => queryClient.invalidateQueries();
  const dismiss = useMutation({ mutationFn: () => api.dismissSignal(caseId, signal.id, today), onSuccess });
  const accept = useMutation({ mutationFn: () => api.acceptSignal(caseId, signal.id, today), onSuccess });
  const accepted = signal.accepted;
  return (
    <li className={`mn-signal ${signal.tone}`}>
      <div className="mn-signal-head">
        <span className={`mn-kind tone-${signalTone(signal)}`}>{signalKindLabel(signal.kind)}</span>
        <span className="mn-signal-title">{humanDates(signal.title)}</span>
      </div>

      {accepted ? (
        <p className="mn-signal-accepted" title="Accepted next steps live in the case's To do and in Needs attention until done.">
          <CheckCheck size={14} />
          On your to-do: {humanDates(accepted.what)}
          {accepted.due ? <span className="mn-when"> · {countdown(accepted.due, today)}</span> : null}
        </p>
      ) : signal.action ? (
        <div className="mn-signal-act">
          <span className="mn-signal-action-text">{humanDates(signal.action)}</span>
          <span className="mn-signal-foot">
            <button
              type="button"
              className="mn-btn small ink"
              disabled={accept.isPending}
              title="Make this your to-do. You still do it — Manu never acts for you."
              onClick={() => accept.mutate()}
            >
              <Check size={14} /> {accept.isPending ? "Adding…" : "Add to my to-do"}
            </button>
            <button
              type="button"
              className="mn-btn small"
              disabled={dismiss.isPending}
              title="Tuck this away. It comes back on its own if the record changes."
              onClick={() => dismiss.mutate()}
            >
              <EyeOff size={14} /> Tuck away
            </button>
          </span>
        </div>
      ) : (
        <div className="mn-signal-foot">
          <button
            type="button"
            className="mn-btn small"
            disabled={dismiss.isPending}
            title="Tuck this away. It comes back on its own if the record changes."
            onClick={() => dismiss.mutate()}
          >
            <EyeOff size={14} /> Tuck away
          </button>
        </div>
      )}

      {signal.evidence?.length ? (
        <ul className="mn-signal-ev">
          {signal.evidence.map((e, i) => (
            <li key={`${e.label}:${i}`}>
              <span>{humanDates(e.label)}</span>
              {e.quote ? <q>{e.quote}</q> : null}
            </li>
          ))}
        </ul>
      ) : null}

      <details className="mn-signal-more">
        <summary>
          <ChevronDown size={13} /> What this is, and is not
        </summary>
        <p>{humanDates(signal.detail)}</p>
      </details>

      {accept.error ? <p className="mn-error">{String(accept.error.message)}</p> : null}
      {dismiss.error ? <p className="mn-error">{String(dismiss.error.message)}</p> : null}
    </li>
  );
}

export function SignalList({ caseId, signals, today }) {
  if (!signals?.length) return null;
  return (
    <ul className="mn-signals">
      {signals.map((signal) => (
        <SignalCard key={signal.id} caseId={caseId} signal={signal} today={today} />
      ))}
    </ul>
  );
}

/** One accepted next step in the practice view, with its done/dismiss controls. */
export function NextStepRow({ step, today }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: (status) => api.setObligation(step.case_id, step.id, status),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  return (
    <li className={`mn-step ${step.overdue ? "late" : ""}`}>
      <span className="mn-step-what">
        <a href={`#/c/${step.case_id}`}>{step.case_title}</a>
        {humanDates(step.what)}
      </span>
      <span className={`mn-todo-due ${step.overdue ? "red" : step.due === today ? "amber" : ""}`}>
        <span title={step.due ? formatDate(step.due) : undefined}>{step.due ? countdown(step.due, today) : "—"}</span>
        {step.created_at ? <small>added {formatDate(step.created_at)}</small> : null}
      </span>
      <span className="mn-todo-actions">
        <button type="button" className="mn-icon small" aria-label="Done" title="Done" onClick={() => update.mutate("done")}>
          <CheckCheck size={15} />
        </button>
        <button type="button" className="mn-icon small" aria-label="Dismiss" title="Dismiss" onClick={() => update.mutate("dismissed")}>
          <EyeOff size={15} />
        </button>
      </span>
    </li>
  );
}
