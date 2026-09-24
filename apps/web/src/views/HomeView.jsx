import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, ChevronLeft, ChevronRight, CornerDownLeft, FolderOpen, RefreshCw, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { asCnr, countdown, courtLabel, formatDate, formatLongDate, greeting, humanDates, shiftDay } from "../model.js";
import { Labels, Loading, RowLink, SectionHead, navigate } from "./common.jsx";

export function HomeView({ today, cases, upcoming, changeCount, focusSignal }) {
  const [day, setDay] = useState(today);
  const [text, setText] = useState("");
  const input = useRef(null);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["day", day], queryFn: () => api.day(day) });
  const track = useMutation({
    mutationFn: (cnr) => api.track(cnr),
    onSuccess: (result) => {
      queryClient.invalidateQueries();
      setText("");
      navigate(`/c/${result.case_id}`);
    },
  });

  useEffect(() => {
    if (focusSignal) input.current?.focus();
  }, [focusSignal]);

  const entries = query.data?.entries || [];
  const isToday = day === today;
  const cnr = asCnr(text);
  const needle = text.trim().toLowerCase();
  const all = cases.data?.cases || [];
  const matches = needle && !cnr
    ? all.filter((c) => [c.title, c.case_number, c.cnr, c.court].some((v) => String(v || "").toLowerCase().includes(needle)))
    : [];
  const known = cnr ? all.find((c) => c.cnr === cnr) : null;
  const needs = needsYou(upcoming.data?.items, all, today);

  const submit = () => {
    if (known) navigate(`/c/${known.id}`);
    else if (cnr) track.mutate(cnr);
    else if (matches[0]) navigate(`/c/${matches[0].id}`);
  };

  return (
    <section className="mn-sheet">
      <div className="mn-home">
        <p className="mn-eyebrow">
          {greeting()} · {formatLongDate(today)}
        </p>
        <h1 className="mn-display">{headline()}</h1>

        <form
          className={`mn-composer ${cnr ? "has-cnr" : ""}`}
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
              placeholder="Paste a CNR to follow a case, or find one of yours…"
              aria-label="CNR or case to find"
              spellCheck={false}
              autoFocus
            />
            <button type="submit" className="mn-send" aria-label={cnr ? "Follow this case" : "Open"} disabled={(!cnr && !matches.length) || track.isPending}>
              {track.isPending ? <RefreshCw size={16} className="spin" /> : <ArrowUp size={17} />}
            </button>
          </div>
          <div className="mn-composer-foot">
            {cnr ? (
              <span className="mn-chip-flat accent">
                <CornerDownLeft size={13} />
                {known ? `Already following · open ${known.title}` : track.isPending ? "Reading the court…" : `Follow ${cnr} — Manu reads the court and every order`}
              </span>
            ) : (
              <>
                <span className="mn-chip-flat">
                  <FolderOpen size={14} /> {all.length} cases
                </span>
                <span className="mn-chip-flat">
                  <Search size={14} /> title, number or CNR
                </span>
              </>
            )}
            <span className="mn-composer-hint">
              <kbd>↵</kbd> {cnr ? "follow" : "open"}
            </span>
          </div>
          {track.error ? <p className="mn-error">{String(track.error.message)}</p> : null}
        </form>

        {needle && !cnr ? (
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
              <Loading query={query} empty={query.data && !entries.length ? "Nothing listed on this day." : null}>
                <ol className="mn-rows">
                  {entries.map((entry) => (
                    <BoardRow key={entry.id} entry={entry} day={day} />
                  ))}
                </ol>
              </Loading>
            </div>

            {needs.length ? (
              <div className="mn-block">
                <SectionHead tools={<a className="mn-text-btn" href="#/week">This week →</a>}>Needs you</SectionHead>
                <ol className="mn-rows">
                  {needs.map((item) => (
                    <RowLink key={item.id} href={`#/c/${item.case_id}`} label={`Open ${item.case_title}`}>
                      <span className={`mn-when ${item.tone}`}>{item.when}</span>
                      <span className="mn-row-main">
                        <span className="mn-row-title">{item.title}</span>
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
    </section>
  );
}

function headline() {
  return "What's on the board today?";
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

function BoardRow({ entry, day }) {
  const notes = [];
  if (entry.due_by_today?.length) notes.push({ tone: "amber", text: entry.due_by_today.map((o) => `${o.who} ${countdown(o.due, day).toLowerCase()}`).join(", ") });
  if (entry.changed_since?.some((e) => e.kind === "new_order")) notes.push({ tone: "accent", text: "new order" });
  return (
    <RowLink href={`#/c/${entry.id}`} label={`Open ${entry.title}`}>
      <span className="mn-serial">{entry.serial}</span>
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
      </span>
      <span className="mn-row-aside">
        <span className="mono">{entry.case_number || entry.cnr}</span>
        <small>{entry.custody_days != null ? `${entry.custody_days} days in custody` : courtLabel(entry.court)}</small>
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
