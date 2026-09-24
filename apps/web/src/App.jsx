import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  ListChecks,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  RefreshCw,
  SquarePen,
  Sun,
} from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "./api.js";
import { countdown, formatDate, groupByCourt, indiaDateKey } from "./model.js";
import { CaseView } from "./views/CaseView.jsx";
import { HomeView } from "./views/HomeView.jsx";
import { ChangesView, WeekView } from "./views/Lists.jsx";
import { Mark, navigate } from "./views/common.jsx";

function readPref(key, fallback) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function writePref(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private window */
  }
}

/** Routes live in the hash, so the browser's back button walks the diary. */
function parseRoute(hash) {
  const parts = String(hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "c" && parts[1]) return { view: "case", id: parts[1] };
  if (parts[0] === "week") return { view: "week" };
  if (parts[0] === "changes") return { view: "changes" };
  return { view: "today" };
}

export function App() {
  const today = indiaDateKey();
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  const [theme, setTheme] = useState(() => readPref("manu.theme", "light"));
  const [railOpen, setRailOpen] = useState(() => readPref("manu.rail", "open") === "open");
  const [phoneRail, setPhoneRail] = useState(false);
  const [composerFocus, setComposerFocus] = useState(0);
  const [collapsed, setCollapsed] = useState(() => new Set());
  const queryClient = useQueryClient();

  useEffect(() => {
    const onHash = () => {
      setRoute(parseRoute(window.location.hash));
      setPhoneRail(false);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => writePref("manu.theme", theme), [theme]);
  useEffect(() => writePref("manu.rail", railOpen ? "open" : "closed"), [railOpen]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const cases = useQuery({ queryKey: ["cases", today], queryFn: () => api.cases(today) });
  const changes = useQuery({ queryKey: ["changes"], queryFn: api.changes });
  const upcoming = useQuery({ queryKey: ["upcoming", today], queryFn: () => api.upcoming(today) });
  const watch = useMutation({ mutationFn: api.watch, onSuccess: () => queryClient.invalidateQueries() });

  const changeCount = (changes.data?.events || []).filter((e) => e.kind !== "tracked").length;
  const dueCount = (upcoming.data?.items || []).filter((i) => i.kind !== "hearing").length;
  const courts = groupByCourt(cases.data?.cases);
  const followCase = () => {
    navigate("/");
    setComposerFocus((n) => n + 1);
  };
  const toggleCourt = (court) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(court)) next.delete(court);
      else next.add(court);
      return next;
    });

  const shared = { today, cases, changes, upcoming };

  return (
    <div className={`mn ${theme === "dark" ? "dark" : ""} ${railOpen ? "" : "rail-closed"} ${phoneRail ? "phone-rail" : ""}`}>
      <aside className="mn-rail" aria-label="Manu">
        <div className="mn-brand">
          <a href="#/" className="mn-logo" aria-label="Manu, today">
            <Mark />
            <strong>manu</strong>
          </a>
          <button type="button" className="mn-icon ghost" aria-label="Hide sidebar" onClick={() => setRailOpen(false)}>
            <PanelLeftClose size={17} />
          </button>
        </div>

        <nav className="mn-nav-list">
          <button type="button" className="mn-nav primary" onClick={followCase}>
            <SquarePen size={17} />
            <span>Follow a case</span>
          </button>
          <NavLink href="#/" icon={CalendarDays} label="Today" on={route.view === "today"} />
          <NavLink href="#/week" icon={ListChecks} label="This week" count={dueCount} on={route.view === "week"} />
          <NavLink href="#/changes" icon={Bell} label="What changed" count={changeCount} on={route.view === "changes"} />
        </nav>

        <div className="mn-rail-section">
          <span>Courts</span>
          <span className="mn-rail-section-tools">
            <span>{cases.data?.cases.length ?? ""}</span>
            <button type="button" className="mn-icon ghost tiny" aria-label="Follow a case" onClick={followCase}>
              <Plus size={15} />
            </button>
          </span>
        </div>
        <div className="mn-tree">
          {courts.map((group) => {
            const shut = collapsed.has(group.court);
            return (
              <div key={group.court} className="mn-tree-group">
                <button type="button" className="mn-tree-court" aria-expanded={!shut} onClick={() => toggleCourt(group.court)}>
                  {shut ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                  {shut ? <Folder size={15} /> : <FolderOpen size={15} />}
                  <span>{group.court}</span>
                  <small>{group.cases.length}</small>
                </button>
                {shut ? null : (
                  <div className="mn-tree-cases">
                    {group.cases.map((c) => (
                      <a
                        key={c.id}
                        href={`#/c/${c.id}`}
                        className={`mn-tree-case ${route.id === c.id ? "on" : ""}`}
                        aria-current={route.id === c.id ? "page" : undefined}
                      >
                        <span>
                          {c.labels?.some((l) => l.code === "479 ALERT" || l.code === "URGENT") ? <i className="mn-dot red" aria-label="Liberty at stake" /> : null}
                          {c.title}
                        </span>
                        <small>
                          {c.next_date ? `${formatDate(c.next_date)} · ${countdown(c.next_date, today)}` : c.stage === "disposed" ? "Disposed" : "No date yet"}
                        </small>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="mn-rail-foot">
          <button type="button" className="mn-nav" onClick={() => watch.mutate()} disabled={watch.isPending}>
            <RefreshCw size={17} className={watch.isPending ? "spin" : ""} />
            <span>{watch.isPending ? "Reading the courts…" : "Check courts now"}</span>
          </button>
          {watch.data ? (
            <p className="mn-rail-note">
              Checked {watch.data.checked}; {watch.data.changed.length} changed
              {Object.keys(watch.data.failed).length ? `; ${Object.keys(watch.data.failed).length} could not be read` : ""}.
            </p>
          ) : null}
          <button type="button" className="mn-nav" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            <span>{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
        </div>
      </aside>

      <div className="mn-rail-scrim" onClick={() => setPhoneRail(false)} aria-hidden="true" />

      <main className="mn-stage">
        <div className="mn-stage-tools">
          {!railOpen ? (
            <button type="button" className="mn-icon ghost wide-only" aria-label="Show sidebar" onClick={() => setRailOpen(true)}>
              <PanelLeftOpen size={17} />
            </button>
          ) : null}
          <button type="button" className="mn-icon ghost phone-only" aria-label="Open menu" onClick={() => setPhoneRail(true)}>
            <Menu size={18} />
          </button>
        </div>
        {route.view === "case" ? (
          <CaseView key={route.id} caseId={route.id} {...shared} />
        ) : route.view === "changes" ? (
          <ChangesView {...shared} />
        ) : route.view === "week" ? (
          <WeekView {...shared} />
        ) : (
          <HomeView focusSignal={composerFocus} changeCount={changeCount} dueCount={dueCount} {...shared} />
        )}
      </main>
    </div>
  );
}

function NavLink({ href, icon: Icon, label, count, on }) {
  return (
    <a href={href} className={`mn-nav ${on ? "on" : ""}`} aria-current={on ? "page" : undefined}>
      <Icon size={17} />
      <span>{label}</span>
      {count ? <span className="count">{count}</span> : null}
    </a>
  );
}
