import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BookMarked, Check, ExternalLink, RefreshCw, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { formatDate } from "../model.js";
import { Loading } from "./common.jsx";

const STANDING = {
  official: { label: "Official copy", tone: "ok" },
  licensed: { label: "Licensed source", tone: "ok" },
  lead: { label: "Lead — confirm from an official copy", tone: "lead" },
  demo: { label: "Demo library — fictional, not law", tone: "demo" },
};

export function Standing({ standing }) {
  const s = STANDING[standing] || { label: standing, tone: "lead" };
  return <span className={`mn-standing ${s.tone}`}>{s.label}</span>;
}

const CHECK = {
  verified: { label: "Verified", tone: "ok", icon: ShieldCheck },
  lead: { label: "Lead only — confirm", tone: "lead", icon: ShieldAlert },
  demo: { label: "Demo library", tone: "demo", icon: ShieldAlert },
  not_found: { label: "Not found in connected sources", tone: "bad", icon: ShieldAlert },
};

/** A judgment read by paragraph. Each paragraph can be relied on for this case, as read. */
export function JudgmentView({ caseId, source, docId, focus, relied }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["judgment", source, docId], queryFn: () => api.judgment(source, docId) });
  const rely = useMutation({
    mutationFn: (n) => api.addAuthority(caseId, source, docId, n),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case"] }),
  });
  const target = useRef(null);
  useEffect(() => {
    target.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [query.data, focus]);
  const j = query.data;
  const reliedOn = new Set((relied || []).filter((a) => a.source.doc_id === docId).map((a) => a.paragraph));
  return (
    <Loading query={query}>
      {j ? (
        <div className="mn-judgment">
          <div className="mn-source-head">
            <p className="mn-eyebrow">
              {j.court}
              {j.decided_on ? ` · ${formatDate(j.decided_on)}` : ""}
            </p>
            <h3>{j.title}</h3>
            <p className="mn-source-meta mono">{[...j.citations, j.uri].filter(Boolean).join(" · ")}</p>
            <Standing standing={j.standing} />
          </div>
          <ol className="mn-paras">
            {j.paragraphs.map((p) => {
              const on = reliedOn.has(p.n) || (rely.isSuccess && rely.variables === p.n);
              return (
                <li key={p.n} ref={p.n === focus ? target : undefined} className={p.n === focus ? "focus" : ""}>
                  <span className="mn-para-n mono">{p.n}</span>
                  <p>{p.text}</p>
                  <button type="button" className={`mn-btn small ${on ? "done" : ""}`} disabled={on || rely.isPending} onClick={() => rely.mutate(p.n)}>
                    {on ? <Check size={13} /> : <BookMarked size={13} />} {on ? "Relied on" : `Rely on ¶${p.n}`}
                  </button>
                </li>
              );
            })}
          </ol>
          {rely.error ? <p className="mn-error">{String(rely.error.message)}</p> : null}
        </div>
      ) : null}
    </Loading>
  );
}

/** The research tab: ask or search, open a judgment, rely on a paragraph; check citations. */
export function ResearchTab({ c }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);
  const run = useMutation({ mutationFn: (question) => api.research(c.id, question) });
  const [checkText, setCheckText] = useState("");
  const check = useMutation({ mutationFn: (text) => api.checkCitations(text) });

  if (open) {
    return (
      <div className="mn-papers">
        <button type="button" className="mn-text-btn" onClick={() => setOpen(null)}>
          <ArrowLeft size={14} /> Results
        </button>
        <JudgmentView caseId={c.id} source={open.source} docId={open.doc_id} focus={open.paragraph} relied={c.authorities} />
      </div>
    );
  }
  const data = run.data;
  return (
    <div className="mn-papers">
      <form
        className="mn-find"
        onSubmit={(e) => {
          e.preventDefault();
          if (q.trim().length >= 3) run.mutate(q.trim());
        }}
      >
        <Search size={15} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Judgments on… e.g. first-time offender 479" aria-label="Research" />
        {run.isPending ? <RefreshCw size={14} className="spin" /> : null}
      </form>
      {run.error ? <p className="mn-error">{String(run.error.message)}</p> : null}
      {data?.answer ? <div className="mn-answer mn-research-answer">{data.answer}</div> : null}
      {data && !data.answer ? <p className="mn-faint small">The research agent isn't connected here ({data.reason.replace(/\.$/, "")}). These are the judgments found; open one to read it and rely on a paragraph.</p> : null}
      {data ? (
        data.hits.length ? (
          <ul className="mn-hits">
            {data.hits.map((h) => (
              <li key={`${h.source}:${h.doc_id}`}>
                <button type="button" className="mn-match" onClick={() => setOpen(h)}>
                  <span className="mn-hit-title">{h.title}</span>
                  <span className="mn-match-head">
                    {[h.court, h.decided_on ? formatDate(h.decided_on) : "", ...h.citations].filter(Boolean).join(" · ")}
                  </span>
                  {h.snippet ? <span className="mn-match-quote">{h.snippet}</span> : null}
                  <Standing standing={h.standing} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mn-empty">Nothing found. Searched: {data.searched.map((s) => `${s.source} (${s.outcome})`).join(", ") || "no sources connected"}.</p>
        )
      ) : null}
      {data?.searched?.length ? (
        <p className="mn-faint small mono">Searched: {data.searched.map((s) => `${s.source} — ${s.outcome}`).join(" · ")}</p>
      ) : null}

      <details className="mn-check">
        <summary>Check citations in a draft</summary>
        <textarea value={checkText} onChange={(e) => setCheckText(e.target.value)} placeholder="Paste text with citations, e.g. (2020) 5 SCC 1" rows={4} />
        <button type="button" className="mn-btn small" disabled={!checkText.trim() || check.isPending} onClick={() => check.mutate(checkText)}>
          Check
        </button>
        {check.data ? (
          check.data.citations.length ? (
            <ul className="mn-checks">
              {check.data.citations.map((r) => {
                const k = CHECK[r.status];
                return (
                  <li key={`${r.citation}-${r.start}`} className={k.tone}>
                    <k.icon size={14} />
                    <span className="mono">{r.citation}</span>
                    <span>{k.label}</span>
                    {r.match ? (
                      <button type="button" className="mn-text-btn" onClick={() => setOpen(r.match)}>
                        {r.match.title} <ExternalLink size={12} />
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mn-faint small">No citation found in that text.</p>
          )
        ) : null}
      </details>
    </div>
  );
}
