import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, EyeOff } from "lucide-react";

import { api } from "../api.js";
import { humanDates, signalKindLabel, signalTone } from "../model.js";

/**
 * One stall signal: a fact about the record, the evidence it stands on, and — when
 * there is something to do — a next step the advocate confirms into their own to-do
 * list. Manu proposes; the advocate decides. Tucking a signal away lasts until the
 * record changes underneath it.
 */
export function SignalCard({ caseId, signal, today }) {
  const queryClient = useQueryClient();
  const onSuccess = () => queryClient.invalidateQueries();
  const dismiss = useMutation({ mutationFn: () => api.dismissSignal(caseId, signal.id, today), onSuccess });
  const accept = useMutation({ mutationFn: () => api.acceptSignal(caseId, signal.id, today), onSuccess });
  return (
    <li className={`mn-signal ${signal.tone}`}>
      <div className="mn-signal-head">
        <span className={`mn-kind tone-${signalTone(signal)}`}>{signalKindLabel(signal.kind)}</span>
        <span className="mn-signal-title">{humanDates(signal.title)}</span>
      </div>
      <p className="mn-signal-detail">{humanDates(signal.detail)}</p>
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
      {signal.action ? (
        <p className="mn-signal-action">
          <span>Next step, if you agree</span>
          {humanDates(signal.action)}
        </p>
      ) : null}
      <div className="mn-signal-foot">
        {signal.action ? (
          <button
            type="button"
            className="mn-btn small ink"
            disabled={accept.isPending}
            title="Make this your to-do. You still do it — Manu never acts for you."
            onClick={() => accept.mutate()}
          >
            <Check size={14} /> {accept.isPending ? "Adding…" : "Add to my to-do"}
          </button>
        ) : null}
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
