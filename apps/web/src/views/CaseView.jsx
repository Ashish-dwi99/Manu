import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowUp, Check, CheckCheck, Download, FileText, Search, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { api } from "../api.js";
import { countdown, eventLabel, formatDate, s479Headline, verificationLabel } from "../model.js";
import { Labels, Loading } from "./common.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "papers", label: "Papers" },
  { id: "ask", label: "Ask this case" },
  { id: "dates", label: "List of dates" },
];

export function CaseView({ caseId, lens, today, onBack }) {
  const [tab, setTab] = useState("overview");
  const [page, setPage] = useState(null);
  const query = useQuery({ queryKey: ["case", caseId, today, lens], queryFn: () => api.case(caseId, today, lens) });
  const c = query.data;
  return (
    <div className="mn-measure wide">
      <button type="button" className="mn-btn accent small mn-back" onClick={onBack}>
        <ArrowLeft size={15} /> Diary
      </button>
      <Loading query={query}>
        {c ? (
          <>
            <header className="mn-case-head">
              <p className="mn-kicker">
                {c.case_number || c.cnr} · {c.court || "Court not yet read"}
              </p>
              <h1 className="mn-title">{c.title}</h1>
              <p className="mn-case-sub">
                <span>Stage: {c.stage.replace("_", " ")}</span>
                {c.status ? <span>Court status: {c.status}</span> : null}
                <span>CNR {c.cnr}</span>
              </p>
              <Labels labels={c.labels} />
            </header>

            <div className="mn-tabs" role="tablist">
              {TABS.map((t) => (
                <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
                  {t.label}
                </button>
              ))}
            </div>

            {tab === "overview" ? <Overview c={c} today={today} /> : null}
            {tab === "papers" ? <Papers caseId={caseId} onOpenPage={setPage} /> : null}
            {tab === "ask" ? <Ask caseId={caseId} c={c} onOpenPage={setPage} /> : null}
            {tab === "dates" ? <Dates caseId={caseId} /> : null}
          </>
        ) : null}
      </Loading>
      {page ? <PageDrawer target={page} onClose={() => setPage(null)} /> : null}
    </div>
  );
}

/* -- overview -------------------------------------------------------------------- */

function Overview({ c, today }) {
  return (
    <div className="mn-grid">
      <div className="mn-col">
        <section className="mn-card sunken">
          <h3>Next hearing</h3>
          <p className="mn-big">
            {c.next_date ? formatDate(c.next_date) : "Not listed"}
            {c.next_date ? <small> · {countdown(c.next_date, today)}</small> : null}
          </p>
          <p>{c.next_purpose || "Purpose not recorded"}</p>
        </section>
        <LastOrder order={c.last_order} />
        <Directions c={c} today={today} />
        {c.criminal ? <Liberty criminal={c.criminal} /> : null}
        {c.bail_facts?.applicable ? <BailFacts facts={c.bail_facts} /> : null}
      </div>
      <div className="mn-col">
        <section className="mn-card">
          <h3>Timeline</h3>
          {c.timeline.length ? (
            <ol className="mn-timeline">
              {c.timeline.map((item, i) => (
                <li key={`${item.on}-${i}`} className={`kind-${item.kind}`}>
                  <time>{formatDate(item.on)}</time>
                  <span>{item.label}</span>
                  {item.detail ? <small className="mn-faint">{item.detail}</small> : null}
                </li>
              ))}
            </ol>
          ) : (
            <p className="mn-faint">Nothing on record yet.</p>
          )}
        </section>
        <section className="mn-card">
          <h3>History</h3>
          <ol className="mn-timeline">
            {c.events.map((event) => (
              <li key={event.id}>
                <time>
                  {eventLabel(event.kind)} · {formatDate(event.at)}
                </time>
                <span>{event.summary}</span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}

function LastOrder({ order }) {
  if (!order) {
    return (
      <section className="mn-card">
        <h3>Last order</h3>
        <p className="mn-faint">No order on record yet.</p>
      </section>
    );
  }
  return (
    <section className="mn-card">
      <h3>Last order · {formatDate(order.on)}</h3>
      {order.title ? <p style={{ fontWeight: 600 }}>{order.title}</p> : null}
      <p className="mn-order">{order.excerpt}</p>
      <p className="mn-source">
        <FileText size={13} /> {order.source.uri || "court record"}
        {order.source.connector ? ` · via ${order.source.connector}` : ""}
      </p>
    </section>
  );
}

function Directions({ c, today }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, status }) => api.setObligation(c.id, id, status),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const open = c.obligations.filter((o) => o.status === "open");
  const closed = c.obligations.filter((o) => o.status !== "open");
  return (
    <section className="mn-card">
      <h3>Directions · {open.length} open</h3>
      {!open.length ? <p className="mn-faint">No open directions.</p> : null}
      <ul className="mn-obligations">
        {open.map((o) => (
          <li key={o.id}>
            <div className="mn-ob-head">
              <strong>{o.who}</strong>
              <span className={o.due && o.due < today ? "mn-overdue" : "mn-faint"}>
                {o.due ? `${formatDate(o.due)} · ${countdown(o.due, today)}` : "No date given"}
              </span>
            </div>
            <p>{o.what}</p>
            <p className={`mn-verify v-${o.source.verification}`}>{verificationLabel(o.source.verification)}</p>
            <div className="mn-actions">
              {o.source.verification === "lead" ? (
                <button type="button" className="mn-btn small" onClick={() => update.mutate({ id: o.id, status: "confirmed" })}>
                  <Check size={14} /> Confirm
                </button>
              ) : null}
              <button type="button" className="mn-btn small" onClick={() => update.mutate({ id: o.id, status: "done" })}>
                <CheckCheck size={14} /> Done
              </button>
              <button type="button" className="mn-btn small" onClick={() => update.mutate({ id: o.id, status: "dismissed" })}>
                <X size={14} /> Not a direction
              </button>
            </div>
          </li>
        ))}
      </ul>
      {closed.length ? (
        <details className="mn-closed">
          <summary>{closed.length} closed</summary>
          <ul>
            {closed.map((o) => (
              <li key={o.id}>
                {o.status}: {o.who} — {o.what}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function Liberty({ criminal }) {
  return (
    <section className="mn-card">
      <h3>Charges and liberty</h3>
      <ul className="mn-charges">
        {criminal.charges.map((charge) => (
          <li key={charge.raw}>
            <span>
              <strong>{charge.raw}</strong>
              {charge.title ? ` — ${charge.title}` : ""}
            </span>
            {!charge.offence ? <span className="mn-overdue">Not matched{charge.suggested ? ` (likely ${charge.suggested})` : ""}</span> : null}
            {charge.warnings
              .filter((w) => !w.includes("not been reviewed"))
              .map((w) => (
                <small key={w} className="mn-warning">
                  {w}
                </small>
              ))}
          </li>
        ))}
      </ul>
      {criminal.accused.map((a) => {
        const alert = ["approaching", "crossed", "maximum_exceeded"].includes(a.s479.status);
        return (
          <div key={a.name} style={{ display: "grid", gap: 10 }}>
            <p>
              <strong>{a.name}</strong> <span className="mn-faint">{a.in_custody ? "in custody" : "not in custody"}</span>
            </p>
            <div className={`mn-liberty ${alert ? "alert" : ""}`}>
              <strong>Section 479 BNSS — {s479Headline(a.s479)}</strong>
              {a.s479.percent != null ? (
                <div className="mn-meter" role="meter" aria-valuenow={a.s479.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Share of threshold served">
                  <span style={{ width: `${Math.min(100, a.s479.percent)}%` }} />
                </div>
              ) : null}
              <ol className="mn-working">
                {a.s479.working.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ol>
              {[...a.s479.gaps, ...a.s479.flags]
                .filter((w) => !w.includes("not yet reviewed"))
                .map((w) => (
                  <small key={w} className="mn-warning">
                    {w}
                  </small>
                ))}
            </div>
            {a.default_bail.status !== "not_applicable" ? (
              <div className={`mn-liberty ${["approaching", "accrued"].includes(a.default_bail.status) ? "alert" : ""}`}>
                <strong>
                  Default bail — {a.default_bail.status.replace("_", " ")}
                  {a.default_bail.accrual_date ? ` · accrues ${formatDate(a.default_bail.accrual_date)}` : ""}
                </strong>
                <ol className="mn-working">
                  {a.default_bail.working.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ol>
                {[...a.default_bail.gaps, ...a.default_bail.flags].map((w) => (
                  <small key={w} className="mn-warning">
                    {w}
                  </small>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
      <p className="mn-footnote">Computed from the record by fixed rules, with the working shown. The court decides.</p>
    </section>
  );
}

function BailFacts({ facts }) {
  return (
    <section className="mn-card">
      <h3>Bail facts</h3>
      <p className="mn-soft">{facts.note}</p>
      <div className="mn-facts">
        {facts.factors.map((factor) => (
          <div key={factor.title} className="mn-fact">
            <h4>{factor.title}</h4>
            <small className="mn-faint">Source: {factor.source}</small>
            <dl>
              {factor.items.map((item) => (
                <div key={item.label}>
                  <dt>{item.label}</dt>
                  <dd className={item.value === "Data unavailable" ? "mn-gap" : ""}>{item.value}</dd>
                </div>
              ))}
            </dl>
            {factor.gaps.map((gap) => (
              <small key={gap} className="mn-gap">
                {gap}
              </small>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

/* -- papers ------------------------------------------------------------------------ */

function Papers({ caseId, onOpenPage }) {
  const queryClient = useQueryClient();
  const input = useRef(null);
  const [q, setQ] = useState("");
  const docs = useQuery({ queryKey: ["documents", caseId], queryFn: () => api.documents(caseId) });
  const upload = useMutation({
    mutationFn: (file) => api.upload(caseId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", caseId] }),
  });
  const search = useMutation({ mutationFn: (text) => api.search(caseId, text) });
  return (
    <div className="mn-grid">
      <div className="mn-col">
        <form
          className="mn-search"
          onSubmit={(event) => {
            event.preventDefault();
            if (q.trim()) search.mutate(q.trim());
          }}
        >
          <Search size={17} className="mn-faint" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find in the papers and orders — e.g. recovered, first-time offender" />
          <button type="submit" className="mn-btn ink small" disabled={!q.trim()}>
            Find
          </button>
        </form>
        {search.data ? <Matches matches={search.data.matches} onOpenPage={onOpenPage} empty={`Nothing in the papers says “${search.data.query}”.`} /> : null}
        {search.error ? <p className="mn-error">{String(search.error.message)}</p> : null}
      </div>
      <div className="mn-col">
        <section className="mn-card">
          <h3>Papers · {docs.data?.documents.length ?? 0}</h3>
          <ul className="mn-docs">
            {(docs.data?.documents || []).map((d) => (
              <li key={d.id} className="mn-doc">
                <FileText size={18} className="mn-faint" />
                <div>
                  <span>{d.name}</span>
                  <small>
                    {d.kind.replace("_", " ")} · {d.pages} {d.pages === 1 ? "page" : "pages"}
                    {d.pages_without_text ? ` · ${d.pages_without_text} need OCR` : ""}
                  </small>
                </div>
                <button type="button" className="mn-chip" onClick={() => onOpenPage({ docId: d.id, page: 1 })}>
                  p. 1
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="mn-drop" onClick={() => input.current?.click()} disabled={upload.isPending}>
            <Upload size={17} /> {upload.isPending ? "Reading…" : "Add PDF, Word or text"}
          </button>
          <input
            ref={input}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload.mutate(file);
              event.target.value = "";
            }}
          />
          {upload.error ? <p className="mn-error">{String(upload.error.message)}</p> : null}
          <p className="mn-faint" style={{ fontSize: 12.5 }}>
            Orders Manu reads from the court are searched too.
          </p>
        </section>
      </div>
    </div>
  );
}

function Matches({ matches, onOpenPage, empty }) {
  if (!matches.length) return <p className="mn-empty">{empty}</p>;
  return (
    <ul className="mn-matches">
      {matches.map((m, i) => (
        <li key={`${m.ref}-${m.page}-${i}`}>
          <p className="mn-source">
            <FileText size={13} /> {m.name}
            {m.kind === "document" ? (
              <button type="button" className="mn-chip" onClick={() => onOpenPage({ docId: m.ref, page: m.page, terms: m.terms })}>
                p. {m.page}
              </button>
            ) : (
              <span className="mn-chip">order</span>
            )}
          </p>
          <blockquote>{m.quote}</blockquote>
        </li>
      ))}
    </ul>
  );
}

function highlight(text, terms) {
  const words = (terms || []).filter(Boolean);
  if (!words.length) return text;
  const pattern = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return text.split(pattern).map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part));
}

function PageDrawer({ target, onClose }) {
  const query = useQuery({ queryKey: ["page", target.docId, target.page], queryFn: () => api.page(target.docId, target.page) });
  const text = query.data?.text || "";
  return (
    <div className="mn-scrim right" role="presentation" onMouseDown={onClose}>
      <aside className="mn-drawer" role="dialog" aria-label="Document page" onMouseDown={(e) => e.stopPropagation()}>
        <header>
          <div>
            <p className="mn-kicker">{query.data ? `Page ${query.data.page} of ${query.data.document.pages}` : "Loading…"}</p>
            <h2>{query.data?.document.name || ""}</h2>
          </div>
          <button type="button" className="mn-icon" aria-label="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </header>
        {query.data ? (
          <div className="mn-page-text">{text ? highlight(text, target.terms) : <span className="mn-faint">This page has no text layer. It needs OCR.</span>}</div>
        ) : null}
      </aside>
    </div>
  );
}

/* -- ask ------------------------------------------------------------------------------ */

function Ask({ caseId, c, onOpenPage }) {
  const [question, setQuestion] = useState("");
  const ask = useMutation({ mutationFn: (q) => api.ask(caseId, q) });
  const suggestions = c.criminal
    ? ["What did the last order direct?", "Is the accused a first-time offender?", "What was recovered?"]
    : ["What did the last order direct?", "What relief is claimed?", "When is the written statement due?"];
  const submit = (q) => {
    setQuestion(q);
    if (q.trim()) ask.mutate(q.trim());
  };
  return (
    <div style={{ display: "grid", gap: 18, maxWidth: 780 }}>
      <form
        className="mn-composer"
        onSubmit={(event) => {
          event.preventDefault();
          submit(question);
        }}
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`Ask about ${c.title}…`}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(question);
            }
          }}
        />
        <footer>
          <span className="mn-faint" style={{ fontSize: 12.5 }}>
            Answers only from this case's record and papers, with the page.
          </span>
          <button type="submit" className="mn-btn ink small" disabled={!question.trim() || ask.isPending} aria-label="Ask">
            {ask.isPending ? "Reading…" : <ArrowUp size={16} />}
          </button>
        </footer>
      </form>
      {!ask.data && !ask.isPending ? (
        <div className="mn-suggestions">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => submit(s)}>
              {s}
            </button>
          ))}
        </div>
      ) : null}
      {ask.error ? <p className="mn-error">{String(ask.error.message)}</p> : null}
      {ask.data ? (
        <>
          {ask.data.answer ? (
            <section className="mn-card">
              <h3>Manu</h3>
              <p className="mn-answer">{ask.data.answer}</p>
              {ask.data.quotes?.length ? (
                <ul className="mn-quotes">
                  {ask.data.quotes.map((q) => (
                    <li key={q.quote} className={q.verified ? "ok" : "bad"}>
                      {q.verified ? "Quote found in " + q.source + (q.page ? `, p. ${q.page}` : "") : "Quote not found in this case's papers — do not rely on it"}
                      <span>“{q.quote}”</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          ) : (
            <div className="mn-notice">
              <strong>Manu's reader isn't connected on this installation.</strong>
              <span className="mn-soft">
                {ask.data.reason} Meanwhile, here is where the papers mention it.
              </span>
            </div>
          )}
          <p className="mn-kicker">Where the papers say it</p>
          <Matches matches={ask.data.matches} onOpenPage={onOpenPage} empty="No page mentions every word of the question. Try fewer words." />
        </>
      ) : null}
    </div>
  );
}

/* -- list of dates ------------------------------------------------------------------ */

function Dates({ caseId }) {
  const query = useQuery({ queryKey: ["dates", caseId], queryFn: () => api.dates(caseId) });
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="mn-head">
        <div>
          <p className="mn-kicker">Built from the record · every row has its source</p>
          <h2>List of dates and events</h2>
        </div>
        <a className="mn-btn ink" href={api.datesDocxUrl(caseId)}>
          <Download size={15} /> Download .docx
        </a>
      </div>
      <Loading query={query} empty={query.data && !query.data.rows.length ? "Nothing on record yet." : null}>
        <table className="mn-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Event</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {(query.data?.rows || []).map((row, i) => (
              <tr key={`${row.date}-${i}`}>
                <td>{row.display}</td>
                <td>{row.event}</td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Loading>
      <p className="mn-footnote">Advocate review required before filing.</p>
    </div>
  );
}
