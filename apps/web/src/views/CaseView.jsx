import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Check, CheckCheck, ChevronDown, FilePen, FileText, MessageCircle, PanelRight, Radio, RefreshCw, Search, ShieldAlert, Timer, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api.js";
import { countdown, courtLabel, formatDate, humanDates, s479Headline, timeAgo } from "../model.js";
import { CitePill, Labels, Loading } from "./common.jsx";
import { DraftEditor } from "./DraftEditor.jsx";
import { DraftSheet } from "./DraftSheet.jsx";
import { Standing } from "./Research.jsx";
import { MatchList, SourcePanel } from "./SourcePanel.jsx";


/**
 * One case, read in a minute: when it is next listed and for what, what the court said
 * last, what somebody has to do, and — in a criminal case — the liberty arithmetic. Every
 * line carries a numbered source that opens the order at those words.
 */
export function CaseView({ caseId, today }) {
  const query = useQuery({ queryKey: ["case", caseId, today], queryFn: () => api.case(caseId, today) });
  // The panel waits to be asked for: a citation opens it, and it closes again.
  const [panelOpen, setPanelOpen] = useState(false);
  const [panel, setPanel] = useState({ tab: "source", list: [], index: 0 });
  const c = query.data;

  const openCite = (list, index) => {
    setPanel({ tab: "source", list, index });
    setPanelOpen(true);
  };
  const cites = useMemo(() => (c ? caseCites(c) : []), [c]);
  const numberOf = (key) => cites.findIndex((x) => x.key === key) + 1;
  const citeProps = (key) => {
    const n = numberOf(key);
    const cite = cites[n - 1];
    return {
      n,
      verification: cite?.verification,
      label: cite?.label,
      active: panelOpen && panel.tab === "source" && panel.list?.[panel.index]?.key === key,
      onClick: () => openCite(cites, n - 1),
    };
  };

  // The first time a case opens, the source panel shows the last order.
  const seeded = useRef(false);
  useEffect(() => {
    if (c && !seeded.current) {
      seeded.current = true;
      if (cites.length) setPanel({ tab: "source", list: cites, index: 0 });
    }
  }, [c, cites]);

  return (
    <div className={`mn-case ${panelOpen ? "with-panel" : ""}`}>
      <section className="mn-sheet mn-case-sheet">
        <Loading query={query}>
          {c ? (
            <>
              <header className="mn-case-head">
                <div className="mn-case-title">
                  <h1>
                    {c.title} <Labels labels={c.labels} />
                  </h1>
                  <p className="mono">
                    {[c.case_number, courtLabel(c.court)].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <div className="mn-case-tools">
                  <button
                    type="button"
                    className={`mn-icon ${panelOpen ? "on" : ""}`}
                    aria-label={panelOpen ? "Hide sources" : "Show sources"}
                    aria-pressed={panelOpen}
                    onClick={() => setPanelOpen(!panelOpen)}
                  >
                    <PanelRight size={17} />
                  </button>
                </div>
              </header>

              <div className="mn-case-scroll">
                <div className="mn-case-body">
                  <NextHearing c={c} today={today} />
                  <LastOrder c={c} cite={citeProps("order")} onRead={() => openCite(cites, numberOf("order") - 1)} />
                  <Directions c={c} today={today} citeProps={citeProps} />
                  {c.criminal ? <Liberty criminal={c.criminal} today={today} /> : null}
                  <Workbench
                    c={c}
                    today={today}
                    citeProps={citeProps}
                    openResearch={() => {
                      setPanel({ ...panel, tab: "research" });
                      setPanelOpen(true);
                    }}
                  />
                  <Conversation c={c} openCite={openCite} openTab={(tab) => {
                    setPanel({ ...panel, tab });
                    setPanelOpen(true);
                  }} />
                </div>
              </div>
            </>
          ) : null}
        </Loading>
      </section>
      {c && panelOpen ? <SourcePanel c={c} panel={panel} setPanel={setPanel} openCite={openCite} onClose={() => setPanelOpen(false)} /> : null}
      {c && panelOpen ? <div className="mn-panel-scrim" onClick={() => setPanelOpen(false)} aria-hidden="true" /> : null}
    </div>
  );
}

/** Open directions and deadlines, soonest first; undated last. */
function openByDue(obligations) {
  return obligations.filter((o) => o.status === "open").sort((a, b) => (a.due || "9999").localeCompare(b.due || "9999"));
}

/** Every source on the case page, numbered in reading order: last order, then open directions. */
function caseCites(c) {
  const out = [];
  const orderOn = (uri) => c.orders.find((o) => o.uri === uri)?.on;
  if (c.last_order) {
    out.push({
      key: "order",
      kind: "order",
      on: c.last_order.on,
      quote: "",
      verification: "verified",
      label: `Order dated ${formatDate(c.last_order.on)}`,
    });
  }
  for (const o of openByDue(c.obligations)) {
    if (o.source.kind === "human") {
      out.push({ key: o.id, kind: "working", title: o.what, quote: o.source.quote, verification: "human_confirmed", label: "Worked out from dates you entered" });
      continue;
    }
    const on = orderOn(o.source.uri);
    out.push({
      key: o.id,
      kind: "order",
      on,
      quote: o.source.quote,
      span: o.source.span,
      verification: o.source.verification,
      label: on ? `Order dated ${formatDate(on)}` : "Order not on record",
    });
  }
  for (const a of c.authorities || []) {
    out.push({
      key: a.id,
      kind: "judgment",
      source: a.source.name,
      docId: a.source.doc_id,
      paragraph: a.paragraph,
      verification: a.standing === "official" || a.standing === "licensed" ? "verified" : "lead",
      label: `${a.citation || a.title}, para ${a.paragraph}`,
    });
  }
  return out;
}

/* -- the brief -------------------------------------------------------------------------- */

function NextHearing({ c, today }) {
  const listedToday = c.next_date === today;
  const boards = useQuery({ queryKey: ["boards", today], queryFn: () => api.boards(today), refetchInterval: 60_000, enabled: listedToday });
  const board = boards.data?.boards.find((b) => b.court === c.court);
  const mine = board?.yours.find((y) => y.case_id === c.id);
  const [drafting, setDrafting] = useState(false);
  const where = [
    c.listing?.item ? `Item ${c.listing.item}` : "",
    c.listing?.court_hall ? c.listing.court_hall.split(",")[0] : "",
    board?.state === "in_session" && board.current_item
      ? `court at ${board.current_item}${mine?.ahead > 0 ? `, ${mine.ahead} ahead` : mine?.ahead === 0 ? ", you're on" : ""}`
      : "",
  ].filter(Boolean);
  return (
    <section className="mn-next">
      {c.next_date ? (
        <button type="button" className="mn-icon ghost mn-next-action" aria-label="Draft a client update" title="Draft a client update" onClick={() => setDrafting(true)}>
          <MessageCircle size={16} />
        </button>
      ) : null}
      {drafting ? <DraftSheet kind="client" caseId={c.id} today={today} onClose={() => setDrafting(false)} /> : null}
      <p className="mn-next-date">
        {c.next_date ? formatDate(c.next_date) : c.stage === "disposed" ? "Disposed" : "Not listed yet"}
        {c.next_date ? <span>{countdown(c.next_date, today)}</span> : null}
      </p>
      {c.next_purpose ? <p className="mn-next-purpose">{c.next_purpose}</p> : null}
      {where.length ? (
        <p className="mn-next-where" title={board?.connector ? `Board via ${board.connector}, ${timeAgo(board.as_of)}` : undefined}>
          {board?.state === "in_session" ? <Radio size={13} className="mn-live" /> : null}
          {where.join(" · ")}
        </p>
      ) : null}
    </section>
  );
}

/** An order's first lines record who appeared; the preview starts at what the court said. */
function withoutAppearances(text) {
  const lines = String(text || "").split("\n");
  const rest = lines.filter((line) => !/^\s*(present|coram)\s*:/i.test(line));
  return (rest.length ? rest : lines).join("\n");
}

function LastOrder({ c, cite, onRead }) {
  const order = c.last_order;
  if (!order) return null;
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        Last order <span>{formatDate(order.on)}</span>
      </h2>
      <button type="button" className="mn-order-card" onClick={onRead} title="Read the order">
        <span className="mn-order-title">
          {order.title || "Order"} <CitePill {...cite} />
        </span>
        <span className="mn-order-text">{withoutAppearances(order.excerpt)}</span>
      </button>
    </section>
  );
}

function Directions({ c, today, citeProps }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, status }) => api.setObligation(c.id, id, status),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const open = openByDue(c.obligations);
  const closed = c.obligations.filter((o) => o.status !== "open");
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        To do <span>{open.length || "nothing open"}</span>
      </h2>
      {open.length ? (
        <ul className="mn-todo">
          {open.map((o) => {
            const late = o.due && o.due < today;
            return (
              <li key={o.id} className={late ? "late" : ""}>
                <span className="mn-todo-who">{o.who}</span>
                <span className="mn-todo-what">
                  {o.what} <CitePill {...citeProps(o.id)} />
                </span>
                <span className={`mn-todo-due ${late ? "red" : o.due === today ? "amber" : ""}`}>
                  <span title={o.due ? formatDate(o.due) : undefined}>{o.due ? countdown(o.due, today) : "—"}</span>
                </span>
                <span className="mn-todo-actions">
                  {o.source.verification === "lead" ? (
                    <button type="button" className="mn-btn small" onClick={() => update.mutate({ id: o.id, status: "confirmed" })} title="Manu read this from the order. Confirm it says so.">
                      <Check size={14} /> Confirm
                    </button>
                  ) : null}
                  <button type="button" className="mn-icon small" aria-label="Mark done" title="Done" onClick={() => update.mutate({ id: o.id, status: "done" })}>
                    <CheckCheck size={15} />
                  </button>
                  <button
                    type="button"
                    className="mn-icon small"
                    aria-label="Not a direction"
                    title="Not a direction"
                    onClick={() => update.mutate({ id: o.id, status: "dismissed" })}
                  >
                    <X size={15} />
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
      {closed.length ? (
        <details className="mn-more">
          <summary>
            <ChevronDown size={14} /> {closed.length} closed
          </summary>
          <ul className="mn-closed">
            {closed.map((o) => (
              <li key={o.id}>
                <b>{o.status}</b> {o.who} — {o.what}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

/* -- workbench: everything that is not the next hearing, one click away --------------- */

function Workbench({ c, today, citeProps, openResearch }) {
  const [tab, setTab] = useState(null);
  const tabs = [
    ["notes", "Notes", c.notes.length],
    ["authorities", "Authorities", (c.authorities || []).length],
    ["deadline", "Deadline"],
    ["draft", "Draft"],
    ...(c.bail_facts?.applicable ? [["bail", "Bail facts"]] : []),
  ];
  return (
    <section className="mn-bench">
      <div className="mn-bench-tabs" role="tablist" aria-label="Case tools">
        {tabs.map(([id, label, count]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(tab === id ? null : id)}>
            {label}
            {count ? <small>{count}</small> : null}
          </button>
        ))}
      </div>
      {tab ? (
        <div className="mn-bench-body">
          {tab === "notes" ? <Notes c={c} today={today} /> : null}
          {tab === "authorities" ? <Authorities c={c} citeProps={citeProps} openResearch={openResearch} /> : null}
          {tab === "deadline" ? <Limitation c={c} today={today} startOpen /> : null}
          {tab === "draft" ? <Drafts c={c} today={today} /> : null}
          {tab === "bail" ? <BailFacts facts={c.bail_facts} /> : null}
        </div>
      ) : null}
    </section>
  );
}

/* -- drafts ------------------------------------------------------------------------------- */

function Drafts({ c, today }) {
  const templates = useQuery({ queryKey: ["draft-templates", c.id], queryFn: () => api.draftTemplates(c.id) });
  const [open, setOpen] = useState(null);
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        Draft
      </h2>
      <div className="mn-draft-buttons">
        {(templates.data?.templates || []).map((t) => (
          <button key={t.key} type="button" className="mn-limitation-open" onClick={() => setOpen(t.key)}>
            <FilePen size={16} />
            <span>
              {t.title}
            </span>
          </button>
        ))}
      </div>
      {open ? <DraftEditor c={c} template={open} today={today} onClose={() => setOpen(null)} /> : null}
    </section>
  );
}

/* -- authorities ------------------------------------------------------------------------ */

function Authorities({ c, citeProps, openResearch }) {
  const queryClient = useQueryClient();
  const remove = useMutation({ mutationFn: (id) => api.deleteAuthority(c.id, id), onSuccess: () => queryClient.invalidateQueries() });
  const list = c.authorities || [];
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        Authorities
      </h2>
      <button type="button" className="mn-text-btn mn-bench-action" onClick={openResearch}>
        <Search size={14} /> Find judgments
      </button>
      {list.length ? (
        <ul className="mn-authorities">
          {list.map((a) => (
            <li key={a.id}>
              <p className="mn-auth-head">
                <b>{a.title}</b>
                {a.citation ? <span className="mono">{a.citation}</span> : null}
                <span className="mono">¶{a.paragraph}</span>
                <CitePill {...citeProps(a.id)} />
              </p>
              <p className="mn-auth-quote">“{a.quote}”</p>
              <p className="mn-auth-foot">
                <Standing standing={a.standing} />
                <button type="button" className="mn-text-btn" onClick={() => remove.mutate(a.id)}>
                  <Trash2 size={13} /> Remove
                </button>
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mn-faint small">None yet.</p>
      )}
    </section>
  );
}

/* -- notes ------------------------------------------------------------------------------- */

function Notes({ c, today }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [on, setOn] = useState(today);
  const [all, setAll] = useState(false);
  const add = useMutation({
    mutationFn: () => api.addNote(c.id, text.trim(), on),
    onSuccess: () => {
      setText("");
      queryClient.invalidateQueries();
    },
  });
  const remove = useMutation({ mutationFn: (id) => api.deleteNote(c.id, id), onSuccess: () => queryClient.invalidateQueries() });
  const shown = all ? c.notes : c.notes.slice(0, 3);
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        Notes
      </h2>
      <form
        className="mn-note-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (text.trim()) add.mutate();
        }}
      >
        <textarea
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={c.next_date === today ? "What happened today? e.g. APP sought time, IO absent, arguments part-heard" : "Add a note for the diary"}
          aria-label="New note"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && text.trim()) add.mutate();
          }}
        />
        <div className="mn-note-form-foot">
          <label className="mn-chip-flat">
            For
            <input type="date" value={on} max={today} onChange={(e) => setOn(e.target.value || today)} aria-label="Court day this note is about" />
          </label>
          <button type="submit" className="mn-btn small" disabled={!text.trim() || add.isPending}>
            {add.isPending ? "Saving…" : "Save note"}
          </button>
        </div>
      </form>
      {add.error ? <p className="mn-error">{String(add.error.message)}</p> : null}
      {c.notes.length ? (
        <ul className="mn-notes">
          {shown.map((n) => (
            <li key={n.id}>
              <time className="mono">{formatDate(n.on)}</time>
              <p>{n.text}</p>
              <button type="button" className="mn-icon tiny ghost" aria-label="Delete note" title="Delete note" onClick={() => remove.mutate(n.id)}>
                <Trash2 size={13} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {c.notes.length > 3 ? (
        <button type="button" className="mn-text-btn" onClick={() => setAll(!all)}>
          {all ? "Show fewer" : `Show all ${c.notes.length} notes`}
        </button>
      ) : null}
    </section>
  );
}

/* -- limitation ------------------------------------------------------------------------ */

const GROUPS = { civil: "Civil", criminal: "Criminal", supreme_court: "Supreme Court", pleadings: "Pleadings" };

const LIMITATION_STATUS = {
  running: "",
  due_soon: "amber",
  last_day: "red",
  extension_only: "red",
  expired: "red",
};

function Limitation({ c, today, startOpen = false }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(startOpen);
  const rules = useQuery({ queryKey: ["limitation-rules"], queryFn: api.limitationRules, enabled: open, staleTime: Infinity });
  const lastOrder = c.orders[0]?.on || today;
  const [form, setForm] = useState({ rule: "", start: lastOrder, copy_applied: "", copy_ready: "" });
  const rule = rules.data?.rules.find((r) => r.key === form.rule);
  const body = { rule: form.rule, start: form.start, copy_applied: form.copy_applied || null, copy_ready: form.copy_ready || null, on: today };
  const result = useQuery({
    queryKey: ["limitation", body],
    queryFn: () => api.limitation(body),
    enabled: open && !!form.rule && !!form.start,
  });
  const save = useMutation({
    mutationFn: () => api.addDeadline(c.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setOpen(false);
      setForm({ rule: "", start: lastOrder, copy_applied: "", copy_ready: "" });
    },
  });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const r = result.data;
  const fromOrder = c.orders.find((o) => o.on === form.start);

  if (!open) {
    return (
      <section className="mn-part">
        <button type="button" className="mn-limitation-open" onClick={() => setOpen(true)}>
          <Timer size={16} />
          <span>Work out a deadline</span>
        </button>
      </section>
    );
  }
  return (
    <section className="mn-part mn-limitation">
      <h2 className="mn-part-title">
        Deadline
        <button type="button" className="mn-icon tiny ghost" aria-label="Close" onClick={() => setOpen(false)}>
          <X size={14} />
        </button>
      </h2>
      <div className="mn-lim-form">
        <label>
          What are you filing?
          <select value={form.rule} onChange={set("rule")}>
            <option value="">Choose…</option>
            {Object.entries(GROUPS).map(([group, label]) => (
              <optgroup key={group} label={label}>
                {(rules.data?.rules || [])
                  .filter((x) => x.group === group)
                  .map((x) => (
                    <option key={x.key} value={x.key}>
                      {x.title} — {x.days} days
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </label>
        <label>
          {rule ? `From ${rule.reckoned_from}` : "From"}
          <select value={fromOrder ? form.start : "other"} onChange={(e) => setForm({ ...form, start: e.target.value === "other" ? "" : e.target.value })}>
            {c.orders.map((o) => (
              <option key={o.on} value={o.on}>
                Order {formatDate(o.on)}
                {o.title ? ` — ${o.title}` : ""}
              </option>
            ))}
            <option value="other">Another date…</option>
          </select>
          {!fromOrder ? <input type="date" value={form.start} onChange={set("start")} aria-label="Start date" /> : null}
          <small>{fromOrder ? "Date from the court record" : "Date you entered"}</small>
        </label>
        {rule?.copy_exclusion ? (
          <div className="mn-lim-copy">
            <label>
              Certified copy applied
              <input type="date" value={form.copy_applied} onChange={set("copy_applied")} />
            </label>
            <label>
              Copy ready
              <input type="date" value={form.copy_ready} onChange={set("copy_ready")} />
            </label>
          </div>
        ) : null}
      </div>

      {r ? (
        <div className={`mn-lim-result ${LIMITATION_STATUS[r.status]}`}>
          <p className="mn-eyebrow">{r.rule.provision}</p>
          <p className="mn-lim-date">
            {r.status === "extension_only" ? "Only with the court's leave, by" : "File by"} {formatDate(r.status === "extension_only" ? r.outer_day : r.file_by)}
            <span>
              {r.status === "expired"
                ? `period ran ${-r.days_left} ${r.days_left === -1 ? "day" : "days"} ago`
                : r.days_left === 0
                  ? "today"
                  : `in ${r.days_left} ${r.days_left === 1 ? "day" : "days"}`}
            </span>
          </p>
          <details>
            <summary>Working</summary>
            <ol className="mn-working">
              {r.working.map((line) => (
                <li key={line}>{humanDates(line)}</li>
              ))}
            </ol>
          </details>
          {[...r.gaps, ...r.flags].map((w) => (
            <p key={w} className="mn-warning">
              {humanDates(w)}
            </p>
          ))}
          <div className="mn-lim-actions">
            <button type="button" className="mn-btn small ink" onClick={() => save.mutate()} disabled={save.isPending || r.status === "expired"}>
              {save.isPending ? "Adding…" : "Add to to-do"}
            </button>
            <span className="mn-faint small">Check against the Bare Act before relying on it.</span>
          </div>
          {save.error ? <p className="mn-error">{String(save.error.message)}</p> : null}
        </div>
      ) : result.error ? (
        <p className="mn-error">{String(result.error.message)}</p>
      ) : null}
    </section>
  );
}

const DEFAULT_BAIL = {
  insufficient_data: "Cannot compute — data missing",
  needs_review: "Needs review",
  chargesheet_filed: "Chargesheet filed before the right accrued",
  accrued: "Right has accrued",
  approaching: "Right accrues soon",
  not_yet: "Not yet",
};

const ALERT = new Set(["approaching", "crossed", "maximum_exceeded", "accrued"]);

function Liberty({ criminal, today }) {
  const gaps = criminal.charges.filter((ch) => !ch.offence);
  return (
    <section className="mn-part">
      <h2 className="mn-part-title">
        Liberty{" "}
        <span title={criminal.charges.map((ch) => `${ch.raw}${ch.title ? ` — ${ch.title}` : ""}`).join("\n")}>
          {criminal.charges.map((ch) => ch.raw).join(", ")}
        </span>
      </h2>
      {gaps.map((ch) => (
        <p key={ch.raw} className="mn-warning">
          <ShieldAlert size={14} /> {ch.raw} is not in the offence table
          {ch.suggested ? ` — possibly ${ch.suggested}; check the record` : ""}. Nothing is computed from it.
        </p>
      ))}
      {criminal.accused.map((a) => (
        <div key={a.name} className="mn-accused">
          <p className="mn-accused-name">
            {a.name}
            <small>{a.in_custody ? `${a.s479.days_detained ?? "?"} days in custody` : "on bail"}</small>
          </p>
          <Reckoner
            title="s.479 BNSS"
            status={a.s479.status}
            headline={s479Headline(a.s479)}
            when={a.s479.crossing_date ? `${a.s479.threshold} on ${formatDate(a.s479.crossing_date)} · ${countdown(a.s479.crossing_date, today).toLowerCase()}` : ""}
            percent={a.s479.percent}
            working={a.s479.working}
            notes={[...a.s479.gaps, ...a.s479.flags].filter((w) => !w.includes("not yet reviewed"))}
          />
          {!["not_applicable", "chargesheet_filed"].includes(a.default_bail.status) ? (
            <Reckoner
              title="Default bail"
              status={a.default_bail.status}
              headline={DEFAULT_BAIL[a.default_bail.status] || a.default_bail.status.replaceAll("_", " ")}
              when={
                a.default_bail.accrual_date
                  ? ["approaching", "not_yet"].includes(a.default_bail.status)
                    ? `accrues ${formatDate(a.default_bail.accrual_date)} · ${countdown(a.default_bail.accrual_date, today).toLowerCase()}`
                    : `period ran to ${formatDate(a.default_bail.accrual_date)}`
                  : ""
              }
              working={a.default_bail.working}
              notes={[...a.default_bail.gaps, ...a.default_bail.flags]}
            />
          ) : null}
        </div>
      ))}
    </section>
  );
}

function Reckoner({ title, status, headline, when, percent, working, notes }) {
  const alert = ALERT.has(status);
  return (
    <details className={`mn-reckoner ${alert ? "alert" : ""}`}>
      <summary>
        <span className="mn-reckoner-title">{title}</span>
        <span className="mn-reckoner-head">
          {headline}
          {when ? <small>{when}</small> : null}
        </span>
        {percent != null ? (
          <span className="mn-meter" role="meter" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Share of threshold served">
            <span style={{ width: `${Math.min(100, percent)}%` }} />
          </span>
        ) : null}
        <span className="mn-reckoner-more">Working</span>
      </summary>
      <ol className="mn-working">
        {working.map((line) => (
          <li key={line}>{humanDates(line)}</li>
        ))}
      </ol>
      {notes.map((w) => (
        <p key={w} className="mn-warning">
          {humanDates(w)}
        </p>
      ))}
    </details>
  );
}

function BailFacts({ facts }) {
  const gaps = facts.factors.reduce((n, f) => n + f.items.filter((i) => i.value === "Data unavailable").length + f.gaps.length, 0);
  return (
    <details className="mn-part mn-bail" open>
      <summary>
        <h2 className="mn-part-title">
          Bail facts {gaps ? <span>{gaps} gaps</span> : null}
        </h2>
        <ChevronDown size={15} />
      </summary>
      <p className="mn-faint small">{facts.note}</p>
      <div className="mn-facts">
        {facts.factors.map((factor) => (
          <div key={factor.title} className="mn-fact">
            <h4>{factor.title}</h4>
            <dl>
              {factor.items.map((item) => (
                <div key={item.label}>
                  <dt>{item.label}</dt>
                  <dd className={item.value === "Data unavailable" ? "gap" : ""}>{item.value}</dd>
                </div>
              ))}
            </dl>
            {factor.gaps.map((gap) => (
              <p key={gap} className="mn-gap">
                {gap}
              </p>
            ))}
            <small className="mn-fact-source">
              <FileText size={12} /> {factor.source}
            </small>
          </div>
        ))}
      </div>
    </details>
  );
}

/* -- ask this case ----------------------------------------------------------------------- */

function answerCites(quotes, docs) {
  return (quotes || []).map((q) => {
    if (!q.verified) return { kind: "none", quote: q.quote, verification: "missing", label: "Not found in this case's papers" };
    const order = /^Order dated (\d{2})\.(\d{2})\.(\d{4})$/.exec(q.source || "");
    if (order) return { kind: "order", on: `${order[3]}-${order[2]}-${order[1]}`, quote: q.quote, verification: "verified", label: q.source };
    const doc = docs.find((d) => d.name === q.source);
    return doc
      ? { kind: "doc", docId: doc.id, page: q.page || 1, quote: q.quote, verification: "verified", label: `${q.source}, p. ${q.page}` }
      : { kind: "none", quote: q.quote, verification: "verified", label: q.source };
  });
}

function Conversation({ c, openCite, openTab }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState([]);
  const end = useRef(null);
  const docs = useQuery({ queryKey: ["documents", c.id], queryFn: () => api.documents(c.id) });
  const ask = useMutation({
    mutationFn: (q) => api.ask(c.id, q),
    onSuccess: (data, q) => setTurns((t) => [...t, { q, data }]),
    onError: (error, q) => setTurns((t) => [...t, { q, error: String(error.message) }]),
  });
  const brief = useMutation({
    mutationFn: () => api.brief(c.id),
    onSuccess: (data) => setTurns((t) => [...t, { q: "Prepare a hearing brief", brief: data.brief?.markdown || data.summary }]),
    onError: (error) => setTurns((t) => [...t, { q: "Prepare a hearing brief", error: String(error.message) }]),
  });
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, ask.isPending]);

  const suggestions = c.criminal
    ? ["What did the last order direct?", "Is the accused a first-time offender?", "What was recovered?"]
    : ["What did the last order direct?", "What relief is claimed?", "When is the written statement due?"];
  const submit = (q) => {
    if (!q.trim() || ask.isPending) return;
    setQuestion("");
    ask.mutate(q.trim());
  };
  const busy = ask.isPending || brief.isPending;

  return (
    <>
      {turns.length || busy ? (
        <section className="mn-part mn-thread">
          <h2 className="mn-part-title">Asked of this case</h2>
          {turns.map((turn, i) => (
            <Turn key={i} turn={turn} docs={docs.data?.documents || []} openCite={openCite} />
          ))}
          {busy ? (
            <p className="mn-thinking">
              <RefreshCw size={14} className="spin" /> Reading the record and papers…
            </p>
          ) : null}
          <div ref={end} className="mn-thread-end" />
        </section>
      ) : null}

      <div className="mn-case-composer">
        {!turns.length && !busy ? (
          <div className="mn-suggestions">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => submit(s)}>
                {s}
              </button>
            ))}
            <button type="button" onClick={() => brief.mutate()}>
              Hearing brief
            </button>
            <button type="button" onClick={() => openTab("dates")}>
              List of dates
            </button>
          </div>
        ) : null}
        <form
          className="mn-composer"
          onSubmit={(event) => {
            event.preventDefault();
            submit(question);
          }}
        >
          <div className="mn-composer-line">
            <textarea
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask this case"
              aria-label="Ask about this case"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(question);
                }
              }}
            />
            <button type="submit" className="mn-send" disabled={!question.trim() || busy} aria-label="Ask">
              <ArrowUp size={17} />
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

function Turn({ turn, docs, openCite }) {
  const cites = turn.data?.answer ? answerCites(turn.data.quotes, docs) : [];
  return (
    <div className="mn-turn">
      <p className="mn-turn-q">{turn.q}</p>
      {turn.error ? <p className="mn-error">{turn.error}</p> : null}
      {turn.brief ? <div className="mn-answer">{turn.brief}</div> : null}
      {turn.data?.answer ? (
        <>
          <div className="mn-answer">{turn.data.answer}</div>
          {cites.length ? (
            <ul className="mn-quotes">
              {cites.map((cite, i) => (
                <li key={`${cite.quote}-${i}`} className={cite.verification === "missing" ? "bad" : ""}>
                  <CitePill
                    n={i + 1}
                    verification={cite.verification}
                    label={cite.label}
                    onClick={() => (cite.kind === "none" ? null : openCite(cites.filter((x) => x.kind !== "none"), cites.filter((x) => x.kind !== "none").indexOf(cite)))}
                  />
                  <span>
                    “{cite.quote}”
                    <small>{cite.verification === "missing" ? "Not found in this case's papers — do not rely on it" : cite.label}</small>
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
      {turn.data && !turn.data.answer ? (
        <p className="mn-offline">
          The reader isn't connected here ({turn.data.reason.replace(/\.$/, "")}). This is where the papers say it:
        </p>
      ) : null}
      {turn.data ? (
        <MatchList matches={turn.data.matches} openCite={openCite} empty="No page mentions every word of the question. Try fewer words." />
      ) : null}
    </div>
  );
}
