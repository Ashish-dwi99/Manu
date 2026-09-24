import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, FileText, Search, ShieldAlert, ShieldCheck, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { eventLabel, formatDate, humanDates, locateQuote, splitAround } from "../model.js";
import { CitePill, Loading } from "./common.jsx";
import { JudgmentView, ResearchTab } from "./Research.jsx";

export const PANEL_TABS = [
  { id: "source", label: "Source" },
  { id: "papers", label: "Papers" },
  { id: "research", label: "Research" },
  { id: "dates", label: "Dates" },
  { id: "timeline", label: "Timeline" },
];

/**
 * The right-hand panel: where every citation lands. A citation opens the order or the
 * page it came from, scrolled to its words and highlighted, with a verdict on whether
 * the words are really there. The other tabs are the case's papers, its list of dates
 * and its timeline.
 */
export function SourcePanel({ c, panel, setPanel, onClose, openCite }) {
  return (
    <aside className="mn-panel" aria-label="Case sources">
      <header className="mn-panel-tabs" role="tablist">
        {PANEL_TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={panel.tab === t.id} onClick={() => setPanel({ ...panel, tab: t.id })}>
            {t.label}
          </button>
        ))}
        <button type="button" className="mn-icon ghost tiny" aria-label="Close panel" onClick={onClose}>
          <X size={16} />
        </button>
      </header>
      <div className="mn-panel-body">
        {panel.tab === "source" ? <SourceTab c={c} panel={panel} setPanel={setPanel} /> : null}
        {panel.tab === "papers" ? <PapersTab caseId={c.id} openCite={openCite} /> : null}
        {panel.tab === "research" ? <ResearchTab c={c} /> : null}
        {panel.tab === "dates" ? <DatesTab caseId={c.id} /> : null}
        {panel.tab === "timeline" ? <TimelineTab c={c} /> : null}
      </div>
    </aside>
  );
}

/* -- source ------------------------------------------------------------------------ */

function SourceTab({ c, panel, setPanel }) {
  const cite = panel.list?.[panel.index];
  if (!cite) {
    return (
      <div className="mn-panel-empty">
        <FileText size={22} />
        <p>Click a numbered source anywhere on the case to read the words it came from.</p>
      </div>
    );
  }
  const step = (delta) => setPanel({ ...panel, index: (panel.index + delta + panel.list.length) % panel.list.length });
  return (
    <div className="mn-source">
      {panel.list.length > 1 ? (
        <div className="mn-source-nav">
          <button type="button" className="mn-icon ghost tiny" aria-label="Previous source" onClick={() => step(-1)}>
            <ChevronLeft size={15} />
          </button>
          <span>
            Source {panel.index + 1} of {panel.list.length}
          </span>
          <button type="button" className="mn-icon ghost tiny" aria-label="Next source" onClick={() => step(1)}>
            <ChevronRight size={15} />
          </button>
        </div>
      ) : null}
      {cite.kind === "order" ? <OrderSource key={`${cite.on}:${cite.quote}`} caseId={c.id} cite={cite} /> : null}
      {cite.kind === "doc" ? <PageSource key={`${cite.docId}:${cite.page}:${cite.quote}`} cite={cite} /> : null}
      {cite.kind === "working" ? <WorkingSource cite={cite} /> : null}
      {cite.kind === "judgment" ? (
        <JudgmentView key={`${cite.docId}:${cite.paragraph}`} caseId={c.id} source={cite.source} docId={cite.docId} focus={cite.paragraph} relied={c.authorities} />
      ) : null}
    </div>
  );
}

/** A deadline Manu worked out: its source is the working itself and the dates a person entered. */
function WorkingSource({ cite }) {
  const lines = String(cite.quote || "")
    .split("\n")
    .filter(Boolean);
  return (
    <>
      <div className="mn-source-head">
        <p className="mn-eyebrow">Worked out by fixed rules</p>
        <h3>{cite.title}</h3>
        <p className="mn-source-meta">From dates in the record and dates you entered. Not from an order.</p>
      </div>
      <ol className="mn-working boxed">
        {lines.map((line) => (
          <li key={line}>{humanDates(line)}</li>
        ))}
      </ol>
    </>
  );
}

function trimEllipsis(quote) {
  return String(quote || "").replace(/^[\s…]+|[\s…]+$/g, "");
}

function Verdict({ found, cite }) {
  if (!cite.quote) return null;
  if (!found) {
    return (
      <p className="mn-verdict bad">
        <ShieldAlert size={14} /> These words were not found in the text. Do not rely on them.
      </p>
    );
  }
  if (cite.verification === "lead") {
    return (
      <p className="mn-verdict lead">
        <ShieldCheck size={14} /> Words found in the order. Read by Manu — confirm the direction.
      </p>
    );
  }
  return (
    <p className="mn-verdict ok">
      <ShieldCheck size={14} /> Words found in the source{cite.verification === "human_confirmed" ? " · confirmed by you" : ""}.
    </p>
  );
}

function Highlighted({ text, range, terms }) {
  const mark = useRef(null);
  useEffect(() => {
    mark.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [range, text]);
  if (range) {
    const [before, match, after] = splitAround(text, range);
    return (
      <div className="mn-doc-text">
        {before}
        <mark ref={mark}>{match}</mark>
        {after}
      </div>
    );
  }
  const words = (terms || []).filter(Boolean);
  if (!words.length) return <div className="mn-doc-text">{text}</div>;
  const pattern = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  let first = true;
  return (
    <div className="mn-doc-text">
      {text.split(pattern).map((part, i) => {
        if (i % 2 === 0) return part;
        const ref = first ? mark : undefined;
        first = false;
        return (
          <mark key={i} ref={ref} className="soft">
            {part}
          </mark>
        );
      })}
    </div>
  );
}

function OrderSource({ caseId, cite }) {
  const query = useQuery({ queryKey: ["order", caseId, cite.on], queryFn: () => api.order(caseId, cite.on), enabled: !!cite.on });
  const order = query.data;
  const quote = trimEllipsis(cite.quote);
  const range = order ? locateQuote(order.text, quote, cite.span) : null;
  if (!cite.on) return <p className="mn-error">The order this came from is not on record.</p>;
  return (
    <Loading query={query}>
      {order ? (
        <>
          <div className="mn-source-head">
            <p className="mn-eyebrow">Order · {formatDate(order.on)}</p>
            <h3>{order.title || "Order"}</h3>
            <p className="mn-source-meta mono">
              {order.source.uri}
              {order.source.connector ? ` · via ${order.source.connector}` : ""}
              {order.source.sha256 ? ` · ${order.source.sha256.slice(0, 10)}` : ""}
            </p>
          </div>
          {quote ? <blockquote className="mn-quote">“{quote}”</blockquote> : null}
          <Verdict found={!!range} cite={cite} />
          <Highlighted text={order.text} range={range} terms={range ? null : cite.terms} />
        </>
      ) : null}
    </Loading>
  );
}

function PageSource({ cite }) {
  const query = useQuery({ queryKey: ["page", cite.docId, cite.page], queryFn: () => api.page(cite.docId, cite.page) });
  const data = query.data;
  const quote = trimEllipsis(cite.quote);
  const range = data?.text ? locateQuote(data.text, quote) : null;
  return (
    <Loading query={query}>
      {data ? (
        <>
          <div className="mn-source-head">
            <p className="mn-eyebrow">
              Page {data.page} of {data.document.pages}
            </p>
            <h3>{data.document.name}</h3>
            <p className="mn-source-meta mono">
              {data.document.kind.replace("_", " ")} · {data.document.sha256.slice(0, 10)}
            </p>
          </div>
          {quote ? <blockquote className="mn-quote">“{quote}”</blockquote> : null}
          {quote ? <Verdict found={!!range} cite={cite} /> : null}
          {data.text ? (
            <Highlighted text={data.text} range={range} terms={range ? null : cite.terms} />
          ) : (
            <p className="mn-faint">This page has no text layer. It needs OCR.</p>
          )}
        </>
      ) : null}
    </Loading>
  );
}

/* -- papers ------------------------------------------------------------------------ */

/** Turn a search match into a citation the source tab can open. */
export function matchToCite(m) {
  return m.kind === "document"
    ? { kind: "doc", docId: m.ref, page: m.page, quote: m.quote, terms: m.terms, verification: "verified", label: `${m.name}, p. ${m.page}` }
    : { kind: "order", on: m.ref, quote: m.quote, terms: m.terms, verification: "verified", label: m.name };
}

export function MatchList({ matches, openCite, empty, start = 1 }) {
  if (!matches.length) return <p className="mn-empty">{empty}</p>;
  const cites = matches.map(matchToCite);
  return (
    <ul className="mn-matches">
      {matches.map((m, i) => (
        <li key={`${m.ref}-${m.page}-${i}`}>
          <button type="button" className="mn-match" onClick={() => openCite(cites, i)}>
            <span className="mn-match-head">
              <CitePill n={start + i} verification="verified" onClick={() => openCite(cites, i)} label={cites[i].label} />
              <span>{m.kind === "document" ? `${m.name} · p. ${m.page}` : m.name}</span>
            </span>
            <span className="mn-match-quote">{m.quote}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function PapersTab({ caseId, openCite }) {
  const queryClient = useQueryClient();
  const input = useRef(null);
  const [q, setQ] = useState("");
  const docs = useQuery({ queryKey: ["documents", caseId], queryFn: () => api.documents(caseId) });
  const upload = useMutation({
    mutationFn: (file) => api.upload(caseId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", caseId] }),
  });
  const search = useMutation({ mutationFn: (text) => api.search(caseId, text) });
  const list = docs.data?.documents || [];
  return (
    <div className="mn-papers">
      <form
        className="mn-find"
        onSubmit={(event) => {
          event.preventDefault();
          if (q.trim()) search.mutate(q.trim());
        }}
      >
        <Search size={15} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find in papers and orders" aria-label="Find in papers and orders" />
      </form>
      {search.data ? (
        <MatchList matches={search.data.matches} openCite={openCite} empty={`Nothing in the papers says “${search.data.query}”.`} />
      ) : null}
      {search.error ? <p className="mn-error">{String(search.error.message)}</p> : null}

      <p className="mn-eyebrow">Papers · {list.length}</p>
      <ul className="mn-docs">
        {list.map((d) => (
          <li key={d.id}>
            <button
              type="button"
              className="mn-doc"
              onClick={() => openCite([{ kind: "doc", docId: d.id, page: 1, verification: "verified", label: d.name }], 0)}
            >
              <FileText size={16} />
              <span>
                {d.name}
                <small>
                  {d.kind.replace("_", " ")} · {d.pages} {d.pages === 1 ? "page" : "pages"}
                  {d.pages_without_text ? ` · ${d.pages_without_text} need OCR` : ""}
                </small>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="mn-drop" onClick={() => input.current?.click()} disabled={upload.isPending}>
        <Upload size={15} /> {upload.isPending ? "Reading…" : "Add PDF, Word or text"}
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
      <p className="mn-faint small">Orders Manu reads from the court are searched too.</p>
    </div>
  );
}

/* -- dates and timeline ------------------------------------------------------------- */

function DatesTab({ caseId }) {
  const query = useQuery({ queryKey: ["dates", caseId], queryFn: () => api.dates(caseId) });
  return (
    <div className="mn-papers">
      <div className="mn-panel-row">
        <p className="mn-eyebrow">List of dates · each row sourced</p>
        <a className="mn-btn small" href={api.datesDocxUrl(caseId)}>
          <Download size={14} /> .docx
        </a>
      </div>
      <Loading query={query} empty={query.data && !query.data.rows.length ? "Nothing on record yet." : null}>
        <ol className="mn-dates">
          {(query.data?.rows || []).map((row, i) => (
            <li key={`${row.date}-${i}`}>
              <time className="mono">{row.display}</time>
              <span>
                {row.event}
                <small>{row.source}</small>
              </span>
            </li>
          ))}
        </ol>
      </Loading>
      <p className="mn-faint small">Advocate review required before filing.</p>
    </div>
  );
}

function TimelineTab({ c }) {
  return (
    <div className="mn-papers">
      <p className="mn-eyebrow">Timeline</p>
      <ol className="mn-timeline">
        {c.timeline.map((item, i) => (
          <li key={`${item.on}-${i}`} className={`kind-${item.kind}`}>
            <time className="mono">{formatDate(item.on)}</time>
            <span>{item.label}</span>
            {item.detail ? <small>{item.detail}</small> : null}
          </li>
        ))}
      </ol>
      <p className="mn-eyebrow">What Manu saw</p>
      <ol className="mn-timeline log">
        {c.events.map((event) => (
          <li key={event.id}>
            <time className="mono">
              {eventLabel(event.kind)} · {formatDate(event.at)}
            </time>
            <span>{event.summary}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
