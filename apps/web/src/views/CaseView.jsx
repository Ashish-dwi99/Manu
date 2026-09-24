import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, CheckCheck, FileText, X } from "lucide-react";

import { api } from "../api.js";
import { countdown, eventLabel, formatDate, s479Headline, verificationLabel } from "../model.js";
import { Labels, State } from "./common.jsx";

export function CaseView({ caseId, lens, today, onBack }) {
  const query = useQuery({ queryKey: ["case", caseId, today, lens], queryFn: () => api.case(caseId, today, lens) });
  const c = query.data;
  return (
    <section className="manu-page">
      <button type="button" className="manu-back" onClick={onBack}>
        <ArrowLeft size={15} /> Back
      </button>
      <State query={query}>
        {c ? (
          <>
            <header className="manu-case-head">
              <p className="manu-eyebrow">
                {c.case_number || c.cnr} · {c.court}
              </p>
              <h1>{c.title}</h1>
              <p className="manu-case-sub">
                <span>Stage: {c.stage.replace("_", " ")}</span>
                {c.status ? <span>Court status: {c.status}</span> : null}
                <span>CNR {c.cnr}</span>
              </p>
              <Labels labels={c.labels} />
            </header>

            <div className="manu-case-grid">
              <div className="manu-case-col">
                <NextHearing c={c} today={today} />
                <LastOrder order={c.last_order} />
                <Obligations c={c} today={today} />
                {c.criminal ? <Liberty criminal={c.criminal} /> : null}
                {c.bail_facts?.applicable ? <BailFacts facts={c.bail_facts} /> : null}
              </div>
              <div className="manu-case-col narrow">
                <Timeline items={c.timeline} />
                <History events={c.events} />
              </div>
            </div>
          </>
        ) : null}
      </State>
    </section>
  );
}

function Block({ title, children, tone }) {
  return (
    <section className={`manu-block ${tone ? `tone-${tone}` : ""}`}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function NextHearing({ c, today }) {
  return (
    <Block title="Next hearing">
      <p className="manu-big">
        {c.next_date ? formatDate(c.next_date) : "Not listed"}
        {c.next_date ? <small> · {countdown(c.next_date, today)}</small> : null}
      </p>
      <p>{c.next_purpose || "Purpose not recorded"}</p>
    </Block>
  );
}

function LastOrder({ order }) {
  if (!order) return <Block title="Last order"><p className="manu-muted">No order on record yet.</p></Block>;
  return (
    <Block title={`Last order · ${formatDate(order.on)}`}>
      {order.title ? <p className="manu-strong">{order.title}</p> : null}
      <blockquote className="manu-quote">{order.excerpt}</blockquote>
      <p className="manu-source">
        <FileText size={13} /> {order.source.uri || "court record"}
        {order.source.connector ? ` · via ${order.source.connector}` : ""}
      </p>
    </Block>
  );
}

function Obligations({ c, today }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, status }) => api.setObligation(c.id, id, status),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const open = c.obligations.filter((o) => o.status === "open");
  const closed = c.obligations.filter((o) => o.status !== "open");
  return (
    <Block title={`Directions · ${open.length} open`}>
      {!open.length ? <p className="manu-muted">No open directions.</p> : null}
      <ul className="manu-obligations">
        {open.map((o) => (
          <li key={o.id}>
            <div className="manu-obligation-head">
              <strong>{o.who}</strong>
              <span className={o.due && o.due < today ? "manu-overdue" : "manu-muted"}>
                {o.due ? `${formatDate(o.due)} · ${countdown(o.due, today)}` : "No date given"}
              </span>
            </div>
            <p>{o.what}</p>
            <p className={`manu-verification v-${o.source.verification}`}>{verificationLabel(o.source.verification)}</p>
            <div className="manu-actions">
              {o.source.verification === "lead" ? (
                <button type="button" className="manu-quiet" onClick={() => update.mutate({ id: o.id, status: "confirmed" })}>
                  <Check size={14} /> Confirm
                </button>
              ) : null}
              <button type="button" className="manu-quiet" onClick={() => update.mutate({ id: o.id, status: "done" })}>
                <CheckCheck size={14} /> Done
              </button>
              <button type="button" className="manu-quiet" onClick={() => update.mutate({ id: o.id, status: "dismissed" })}>
                <X size={14} /> Not a direction
              </button>
            </div>
          </li>
        ))}
      </ul>
      {closed.length ? (
        <details className="manu-closed">
          <summary>{closed.length} closed</summary>
          <ul>
            {closed.map((o) => (
              <li key={o.id}>
                <span className="manu-muted">{o.status}</span> {o.who}: {o.what}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </Block>
  );
}

function Liberty({ criminal }) {
  return (
    <Block title="Charges and liberty">
      <ul className="manu-charges">
        {criminal.charges.map((charge) => (
          <li key={charge.raw}>
            <strong>{charge.raw}</strong> {charge.title ? `— ${charge.title}` : ""}
            {!charge.offence ? <span className="manu-overdue"> not matched{charge.suggested ? ` (likely ${charge.suggested})` : ""}</span> : null}
            {charge.warnings
              .filter((w) => !w.includes("not been reviewed"))
              .map((w) => (
                <small key={w} className="manu-warning">
                  {w}
                </small>
              ))}
          </li>
        ))}
      </ul>
      {criminal.accused.map((a) => (
        <div key={a.name} className="manu-accused">
          <h3>
            {a.name} {a.in_custody ? <small>in custody</small> : <small>not in custody</small>}
          </h3>
          <div className={`manu-s479 status-${a.s479.status}`}>
            <p className="manu-strong">Section 479 BNSS — {s479Headline(a.s479)}</p>
            {a.s479.percent != null ? (
              <div className="manu-meter" role="meter" aria-valuenow={a.s479.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Share of threshold served">
                <span style={{ width: `${Math.min(100, a.s479.percent)}%` }} />
              </div>
            ) : null}
            <ol className="manu-working">
              {a.s479.working.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ol>
            {[...a.s479.gaps, ...a.s479.flags]
              .filter((w) => !w.includes("not yet reviewed"))
              .map((w) => (
                <small key={w} className="manu-warning">
                  {w}
                </small>
              ))}
          </div>
          {a.default_bail.status !== "not_applicable" ? (
            <div className="manu-s479">
              <p className="manu-strong">
                Default bail — {a.default_bail.status.replace("_", " ")}
                {a.default_bail.accrual_date ? ` · accrues ${formatDate(a.default_bail.accrual_date)}` : ""}
              </p>
              <ol className="manu-working">
                {a.default_bail.working.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ol>
              {[...a.default_bail.gaps, ...a.default_bail.flags].map((w) => (
                <small key={w} className="manu-warning">
                  {w}
                </small>
              ))}
            </div>
          ) : null}
        </div>
      ))}
      <p className="manu-footnote">Computed from the record by fixed rules, with the working shown. The court decides.</p>
    </Block>
  );
}

function BailFacts({ facts }) {
  return (
    <Block title="Bail facts">
      <p className="manu-muted">{facts.note}</p>
      <div className="manu-facts">
        {facts.factors.map((factor) => (
          <div key={factor.title} className="manu-fact">
            <h3>{factor.title}</h3>
            <small className="manu-muted">Source: {factor.source}</small>
            <dl>
              {factor.items.map((item) => (
                <div key={item.label}>
                  <dt>{item.label}</dt>
                  <dd className={item.value === "Data unavailable" ? "manu-gap" : ""}>{item.value}</dd>
                </div>
              ))}
            </dl>
            {factor.gaps.map((gap) => (
              <small key={gap} className="manu-gap">
                {gap}
              </small>
            ))}
          </div>
        ))}
      </div>
    </Block>
  );
}

function Timeline({ items }) {
  return (
    <Block title="Timeline">
      <ol className="manu-timeline">
        {items.map((item, index) => (
          <li key={`${item.on}-${index}`} className={`kind-${item.kind}`}>
            <time>{formatDate(item.on)}</time>
            <span>{item.label}</span>
            {item.detail ? <small className="manu-muted">{item.detail}</small> : null}
          </li>
        ))}
      </ol>
    </Block>
  );
}

function History({ events }) {
  return (
    <Block title="History">
      <ul className="manu-history">
        {events.map((event) => (
          <li key={event.id}>
            <span className="manu-event-kind">{eventLabel(event.kind)}</span>
            <span>{event.summary}</span>
            <small className="manu-muted">{formatDate(event.at)}</small>
          </li>
        ))}
      </ul>
    </Block>
  );
}
