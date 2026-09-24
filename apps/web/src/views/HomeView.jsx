import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Check, ChevronLeft, ChevronRight, CornerDownLeft, FolderOpen, MessageCircle, Radio, RefreshCw, Search, UserSearch, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { asCnr, boardHeadline, countdown, courtLabel, formatDate, formatLongDate, greeting, humanDates, shiftDay, timeAgo } from "../model.js";
import { Labels, Loading, RowLink, SectionHead, navigate } from "./common.jsx";
import { DraftSheet } from "./DraftSheet.jsx";

export function HomeView({ today, cases, upcoming, changeCount, focusSignal }) {
  const [day, setDay] = useState(today);
  const [text, setText] = useState("");
  const [mode, setMode] = useState("find");
  const input = useRef(null);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["day", day], queryFn: () => api.day(day) });
  const boards = useQuery({ queryKey: ["boards", today], queryFn: () => api.boards(today), refetchInterval: 60_000, enabled: day === today });
  const track = useMutation({
    mutationFn: (cnr) => api.track(cnr),
    onSuccess: (result) => {
      queryClient.invalidateQueries();
      setText("");
      navigate(`/c/${result.case_id}`);
    },
  });
  const search = useMutation({ mutationFn: (name) => api.findByAdvocate(name) });
  const dueUpdates = useQuery({ queryKey: ["due-updates", today], queryFn: () => api.dueUpdates(today) });
  const [draft, setDraft] = useState(null);

  useEffect(() => {
    if (focusSignal) input.current?.focus();
  }, [focusSignal]);

  const entries = query.data?.entries || [];
  const isToday = day === today;
  const advocate = mode === "advocate";
  const cnr = advocate ? null : asCnr(text);
  const needle = text.trim().toLowerCase();
  const all = cases.data?.cases || [];
  const matches =
    needle && !cnr && !advocate
      ? all.filter((c) => [c.title, c.case_number, c.cnr, c.court].some((v) => String(v || "").toLowerCase().includes(needle)))
      : [];
  const known = cnr ? all.find((c) => c.cnr === cnr) : null;
  const needs = [
    ...needsYou(upcoming.data?.items, all, today),
    ...(dueUpdates.data?.updates || []).map((u) => ({
      id: `update:${u.case_id}`,
      case_id: u.case_id,
      case_title: u.title,
      when: "Client update",
      tone: "",
      title: `Hearing ${u.days_to_hearing === 2 ? "in two days" : "in a week"}: the update is drafted, ready for you to send`,
      sub: `Listed ${formatDate(u.next_date)}`,
      onClick: () => setDraft({ kind: "client", caseId: u.case_id }),
    })),
  ];
  const boardFor = (court) => boards.data?.boards.find((b) => b.court === court);

  const submit = () => {
    if (advocate) {
      if (needle.length >= 3) search.mutate(text.trim());
    } else if (known) navigate(`/c/${known.id}`);
    else if (cnr) track.mutate(cnr);
    else if (matches[0]) navigate(`/c/${matches[0].id}`);
  };
  const switchMode = (next) => {
    setMode(next);
    setText("");
    search.reset();
    input.current?.focus();
  };

  return (
    <section className="mn-sheet">
      <div className="mn-home">
        <p className="mn-eyebrow">
          {greeting()} · {formatLongDate(today)}
        </p>
        <h1 className="mn-display">What's on the board today?</h1>

        <form
          className={`mn-composer ${cnr || advocate ? "has-cnr" : ""}`}
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <div className="mn-composer-line">
            <input
              ref={input}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && advocate) switchMode("find");
              }}
              placeholder={advocate ? "Advocate name as the court prints it, e.g. R. Mehta" : "Paste a CNR to follow a case, or find one of yours…"}
              aria-label={advocate ? "Advocate name" : "CNR or case to find"}
              spellCheck={false}
              autoFocus
            />
            <button
              type="submit"
              className="mn-send"
              aria-label={advocate ? "Find cases" : cnr ? "Follow this case" : "Open"}
              disabled={advocate ? needle.length < 3 || search.isPending : (!cnr && !matches.length) || track.isPending}
            >
              {track.isPending || search.isPending ? <RefreshCw size={16} className="spin" /> : <ArrowUp size={17} />}
            </button>
          </div>
          <div className="mn-composer-foot">
            {advocate ? (
              <>
                <span className="mn-chip-flat accent">
                  <UserSearch size={14} /> Import every case where this advocate appears
                </span>
                <button type="button" className="mn-chip-flat link" onClick={() => switchMode("find")}>
                  <X size={13} /> Cancel
                </button>
              </>
            ) : cnr ? (
              <span className="mn-chip-flat accent">
                <CornerDownLeft size={13} />
                {known ? `Already following · open ${known.title}` : track.isPending ? "Reading the court…" : `Follow ${cnr}. Manu reads the court and every order`}
              </span>
            ) : (
              <>
                <span className="mn-chip-flat">
                  <FolderOpen size={14} /> {all.length} cases
                </span>
                <span className="mn-chip-flat">
                  <Search size={14} /> title, number or CNR
                </span>
                <button type="button" className="mn-chip-flat link" onClick={() => switchMode("advocate")}>
                  <UserSearch size={14} /> Import by advocate name
                </button>
              </>
            )}
            <span className="mn-composer-hint">
              <kbd>↵</kbd> {advocate ? "search" : cnr ? "follow" : "open"}
            </span>
          </div>
          {track.error ? <p className="mn-error">{String(track.error.message)}</p> : null}
          {search.error ? <p className="mn-error">{String(search.error.message)}</p> : null}
        </form>

        {advocate ? (
          search.data ? (
            <ImportResults key={search.data.name} result={search.data} onDone={() => switchMode("find")} />
          ) : null
        ) : needle && !cnr ? (
          <div className="mn-block">
            <SectionHead>Matching cases</SectionHead>
            {matches.length ? (
              <ol className="mn-rows">
                {matches.map((c) => (
                  <CaseRow key={c.id} c={c} today={today} />
                ))}
              </ol>
            ) : (
              <p className="mn-empty">None of your cases match “{text.trim()}”. Paste its 16-character CNR to follow it.</p>
            )}
          </div>
        ) : (
          <>
            <div className="mn-block">
              <SectionHead
                tools={
                  <>
                    {isToday && entries.length ? (
                      <button type="button" className="mn-text-btn" onClick={() => setDraft({ kind: "cause-list" })}>
                        <MessageCircle size={14} /> Cause list message
                      </button>
                    ) : null}
                    <button type="button" className="mn-icon ghost tiny" aria-label="Previous day" onClick={() => setDay(shiftDay(day, -1))}>
                      <ChevronLeft size={15} />
                    </button>
                    <button type="button" className="mn-text-btn" onClick={() => setDay(today)} disabled={isToday}>
                      {isToday ? "Today" : formatDate(day)}
                    </button>
                    <button type="button" className="mn-icon ghost tiny" aria-label="Next day" onClick={() => setDay(shiftDay(day, 1))}>
                      <ChevronRight size={15} />
                    </button>
                  </>
                }
              >
                {isToday ? `Listed today · ${entries.length}` : `Listed ${formatLongDate(day)} · ${entries.length}`}
              </SectionHead>
              {isToday && boards.data?.boards.length ? (
                <div className="mn-boards">
                  {boards.data.boards.map((b) => (
                    <BoardStrip key={b.court} board={b} />
                  ))}
                </div>
              ) : null}
              <Loading query={query} empty={query.data && !entries.length ? "Nothing listed on this day." : null}>
                <ol className="mn-rows">
                  {entries.map((entry) => (
                    <BoardRow key={entry.id} entry={entry} day={day} board={isToday ? boardFor(entry.court) : null} />
                  ))}
                </ol>
              </Loading>
            </div>

            {needs.length ? (
              <div className="mn-block">
                <SectionHead tools={<a className="mn-text-btn" href="#/week">This week →</a>}>Needs you</SectionHead>
                <ol className="mn-rows">
                  {needs.map((item) => (
                    <RowLink
                      key={item.id}
                      href={item.onClick ? undefined : `#/c/${item.case_id}`}
                      onClick={item.onClick}
                      label={item.onClick ? `Draft client update for ${item.case_title}` : `Open ${item.case_title}`}
                    >
                      <span className={`mn-when ${item.tone}`}>{item.when}</span>
                      <span className="mn-row-main">
                        <span className="mn-row-title plain">{item.title}</span>
                        <span className="mn-row-sub">{item.sub}</span>
                      </span>
                      <span className="mn-row-aside mono">{item.case_title}</span>
                    </RowLink>
                  ))}
                </ol>
              </div>
            ) : null}

            {changeCount ? (
              <a className="mn-quiet-link" href="#/changes">
                {changeCount} {changeCount === 1 ? "change" : "changes"} from the courts since yesterday →
              </a>
            ) : null}
          </>
        )}
      </div>
      {draft ? <DraftSheet kind={draft.kind} caseId={draft.caseId} today={today} onClose={() => setDraft(null)} /> : null}
    </section>
  );
}

/** One court's display board, and where your matters stand against it. */
function BoardStrip({ board }) {
  const live = board.state === "in_session";
  return (
    <div className={`mn-board ${live ? "live" : ""}`}>
      <span className="mn-board-court">
        <Radio size={14} className={live ? "mn-live" : ""} />
        {courtLabel(board.court)}
        {board.court_hall ? <small>{board.court_hall}</small> : null}
      </span>
      <span className="mn-board-now">{boardHeadline(board)}</span>
      <span className="mn-board-yours">
        {board.yours
          .filter((y) => y.item)
          .map((y) => (
            <a key={y.case_id} href={`#/c/${y.case_id}`} className={y.ahead != null && y.ahead <= 0 ? "passed" : y.ahead != null && y.ahead <= 3 ? "near" : ""}>
              {y.item}
              <small>{y.ahead == null ? "" : y.ahead > 0 ? `${y.ahead} ahead` : y.ahead === 0 ? "on now" : "called"}</small>
            </a>
          ))}
      </span>
      <small className="mn-board-src mono">
        {board.connector ? `via ${board.connector}${board.as_of ? ` · ${timeAgo(board.as_of)}` : ""}` : board.unavailable}
      </small>
    </div>
  );
}

function ImportResults({ result, onDone }) {
  const queryClient = useQueryClient();
  const fresh = result.hits.filter((h) => !h.following);
  const [chosen, setChosen] = useState(() => new Set(fresh.map((h) => h.cnr)));
  const follow = useMutation({
    mutationFn: () => api.importCases([...chosen]),
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
  const toggle = (cnr) =>
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(cnr)) next.delete(cnr);
      else next.add(cnr);
      return next;
    });

  if (!result.hits.length) {
    return (
      <div className="mn-block">
        <p className="mn-empty">
          No case found for “{result.name}”.{" "}
          {result.attempts.length ? `Tried ${result.attempts.map((a) => `${a.connector} (${a.outcome})`).join(", ")}.` : "No connector here can search by advocate."}
        </p>
      </div>
    );
  }
  if (follow.data) {
    const failed = Object.entries(follow.data.failed);
    return (
      <div className="mn-block">
        <SectionHead>Imported</SectionHead>
        <p className="mn-empty">
          Now following {follow.data.followed.length} more {follow.data.followed.length === 1 ? "case" : "cases"}. They are in the sidebar under their courts.
          {failed.length ? ` ${failed.length} could not be read: ${failed.map(([k, v]) => `${k} — ${v}`).join("; ")}` : ""}
        </p>
        <button type="button" className="mn-btn" onClick={onDone}>
          Done
        </button>
      </div>
    );
  }
  return (
    <div className="mn-block">
      <SectionHead
        tools={
          <button type="button" className="mn-btn small ink" disabled={!chosen.size || follow.isPending} onClick={() => follow.mutate()}>
            {follow.isPending ? "Reading the courts…" : `Follow ${chosen.size} ${chosen.size === 1 ? "case" : "cases"}`}
          </button>
        }
      >
        {result.hits.length} found for “{result.name}” · via {result.connector}
      </SectionHead>
      <ul className="mn-rows">
        {result.hits.map((h) => (
          <li key={h.cnr}>
            <label className={`mn-row mn-pick ${h.following ? "done" : ""}`}>
              <input type="checkbox" checked={h.following || chosen.has(h.cnr)} disabled={h.following} onChange={() => toggle(h.cnr)} />
              <span className="mn-row-main">
                <span className="mn-row-title">{h.title || h.cnr}</span>
                <span className="mn-row-sub">
                  {h.following ? "Already following" : h.next_date ? `Next ${formatDate(h.next_date)}` : "No date"} · for {h.advocate}
                </span>
              </span>
              <span className="mn-row-aside">
                <span className="mono">{h.cnr}</span>
                <small>{courtLabel(h.court)}</small>
              </span>
              {h.following ? <Check size={15} className="mn-row-arrow" /> : null}
            </label>
          </li>
        ))}
      </ul>
      {follow.error ? <p className="mn-error">{String(follow.error.message)}</p> : null}
    </div>
  );
}

/** What needs a person: liberty dates first, then directions overdue or due within 3 days. */
function needsYou(items, cases, today) {
  const out = [];
  for (const c of cases) {
    for (const label of c.labels || []) {
      if (label.code === "479 ALERT" || label.code === "URGENT") {
        out.push({
          id: `label:${c.id}:${label.code}`,
          case_id: c.id,
          case_title: c.title,
          when: label.code,
          tone: label.tone === "red" ? "red" : "amber",
          title: humanDates(label.reason),
          sub: courtLabel(c.court),
          rank: 0,
        });
      }
    }
  }
  for (const item of items || []) {
    if (item.kind === "hearing") continue;
    const soon = item.overdue || item.due <= shiftDay(today, 3);
    if (!soon) continue;
    out.push({
      id: item.id,
      case_id: item.case_id,
      case_title: item.case_title,
      when: countdown(item.due, today),
      tone: item.overdue ? "red" : item.due === today ? "amber" : "",
      title: `${item.who}: ${item.what}`,
      sub: `Due ${formatDate(item.due)}`,
      rank: item.overdue ? 1 : 2,
    });
  }
  return out.sort((a, b) => a.rank - b.rank).slice(0, 8);
}

function BoardRow({ entry, day, board }) {
  const notes = [];
  if (entry.due_by_today?.length) notes.push({ tone: "amber", text: entry.due_by_today.map((o) => `${o.who} ${countdown(o.due, day).toLowerCase()}`).join(", ") });
  if (entry.changed_since?.some((e) => e.kind === "new_order")) notes.push({ tone: "accent", text: "new order" });
  const item = entry.listing?.item;
  const mine = board?.yours.find((y) => y.case_id === entry.id);
  return (
    <RowLink href={`#/c/${entry.id}`} label={`Open ${entry.title}`}>
      <span className={`mn-item ${mine?.ahead != null && mine.ahead <= 3 && mine.ahead >= 0 ? "near" : ""}`} title={item ? `Item ${item} on the cause list` : "Item number not published"}>
        {item || entry.serial}
        <small>{item ? "item" : ""}</small>
      </span>
      <span className="mn-row-main">
        <span className="mn-row-title">
          {entry.title}
          <Labels labels={entry.labels} />
        </span>
        <span className="mn-row-sub">
          {entry.next_purpose || "Purpose not recorded"}
          {notes.map((n) => (
            <span key={n.text} className={`mn-note ${n.tone}`}>
              {n.text}
            </span>
          ))}
        </span>
        {entry.last_note ? (
          <span className="mn-row-memo" title={`Your note, ${formatDate(entry.last_note.on)}`}>
            {entry.last_note.text}
          </span>
        ) : null}
      </span>
      <span className="mn-row-aside">
        <span className="mono">{entry.case_number || entry.cnr}</span>
        <small>
          {entry.custody_days != null ? `${entry.custody_days} days in custody` : entry.listing?.court_hall || courtLabel(entry.court)}
        </small>
      </span>
    </RowLink>
  );
}

export function CaseRow({ c, today }) {
  return (
    <RowLink href={`#/c/${c.id}`} label={`Open ${c.title}`}>
      <span className="mn-row-main">
        <span className="mn-row-title">
          {c.title}
          <Labels labels={c.labels} />
        </span>
        <span className="mn-row-sub">
          {c.next_date ? `${formatDate(c.next_date)} · ${countdown(c.next_date, today)}` : "No date yet"}
          {c.next_purpose ? ` · ${c.next_purpose}` : ""}
        </span>
      </span>
      <span className="mn-row-aside">
        <span className="mono">{c.cnr}</span>
        <small>{courtLabel(c.court)}</small>
      </span>
    </RowLink>
  );
}
