import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  BookOpen,
  CalendarDays,
  ChevronDown,
  Gavel,
  ListChecks,
  Moon,
  Plus,
  RefreshCw,
  Scale,
  Sun,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "./api.js";
import { countdown, formatDate, indiaDateKey } from "./model.js";
import { CaseView } from "./views/CaseView.jsx";
import { HomeView } from "./views/HomeView.jsx";
import { ChangesView, DueView } from "./views/Lists.jsx";

const LENSES = {
  advocate: { icon: Scale, title: "Advocate's diary", hint: "Your cases, what changed, what's due" },
  judge: { icon: Gavel, title: "Judge's desk", hint: "Cause list, liberty, bail facts" },
};

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

export function App() {
  const today = indiaDateKey();
  const [section, setSection] = useState("home");
  const [lens, setLens] = useState(() => readPref("manu.lens", "advocate"));
  const [theme, setTheme] = useState(() => readPref("manu.theme", "light"));
  const [day, setDay] = useState(today);
  const [openCase, setOpenCase] = useState(null);
  const [adding, setAdding] = useState(false);
  const [lensOpen, setLensOpen] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => writePref("manu.lens", lens), [lens]);
  useEffect(() => writePref("manu.theme", theme), [theme]);

  const cases = useQuery({ queryKey: ["cases", today, lens], queryFn: () => api.cases(today, lens) });
  const changes = useQuery({ queryKey: ["changes"], queryFn: api.changes });
  const upcoming = useQuery({ queryKey: ["upcoming", today], queryFn: () => api.upcoming(today) });
  const watch = useMutation({ mutationFn: api.watch, onSuccess: () => queryClient.invalidateQueries() });

  const changeCount = (changes.data?.events || []).filter((e) => e.kind !== "tracked").length;
  const dueCount = (upcoming.data?.items || []).filter((i) => i.kind !== "hearing").length;
  const go = (next) => {
    setSection(next);
    setOpenCase(null);
  };
  const Lens = LENSES[lens];
  const shared = { lens, today, onOpenCase: setOpenCase, go };

  return (
    <div className={`mn ${theme === "dark" ? "dark" : ""}`}>
      <aside className="mn-rail">
        <div className="mn-brand">
          <strong>manu</strong>
          <small>{lens === "judge" ? "for the bench" : "for advocates"}</small>
        </div>

        <div className="mn-lens">
          <button type="button" aria-haspopup="menu" aria-expanded={lensOpen} onClick={() => setLensOpen(!lensOpen)}>
            <Lens.icon size={17} />
            <span>
              {Lens.title}
              <small>{Lens.hint}</small>
            </span>
            <ChevronDown size={16} />
          </button>
          {lensOpen ? (
            <div className="mn-lens-menu" role="menu">
              {Object.entries(LENSES).map(([id, item]) => (
                <button
                  key={id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={lens === id}
                  onClick={() => {
                    setLens(id);
                    setLensOpen(false);
                  }}
                >
                  <item.icon size={17} />
                  <span>
                    {item.title}
                    <small>{item.hint}</small>
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <button type="button" className="mn-new" onClick={() => setAdding(true)}>
          <Plus size={18} /> <span>Follow a case</span>
        </button>

        <nav aria-label="Manu">
          <NavItem
            icon={CalendarDays}
            label={lens === "judge" ? "Cause list" : "Today"}
            on={section === "home" && !openCase}
            onClick={() => go("home")}
          />
          <NavItem icon={Bell} label="What changed" count={changeCount} on={section === "changes" && !openCase} onClick={() => go("changes")} />
          <NavItem icon={ListChecks} label="Due this week" count={dueCount} on={section === "due" && !openCase} onClick={() => go("due")} />
        </nav>

        <div className="mn-rail-section">
          <span>Cases</span>
          <span>{cases.data?.cases.length ?? ""}</span>
        </div>
        {[...(cases.data?.cases || [])].sort((a, b) => (a.next_date || "9999").localeCompare(b.next_date || "9999")).map((c) => (
          <button key={c.id} type="button" className={`mn-case-link ${openCase === c.id ? "on" : ""}`} onClick={() => setOpenCase(c.id)}>
            <span>{c.title}</span>
            <small>
              {c.next_date ? `${formatDate(c.next_date)} · ${countdown(c.next_date, today)}` : c.stage === "disposed" ? "Disposed" : "No date yet"}
            </small>
          </button>
        ))}

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
          <a className="mn-nav" href="https://github.com/Ashish-dwi99/Manu" target="_blank" rel="noreferrer">
            <BookOpen size={17} />
            <span>About Manu</span>
          </a>
        </div>
      </aside>

      <main className="mn-page">
        {openCase ? (
          <CaseView key={openCase} caseId={openCase} onBack={() => setOpenCase(null)} {...shared} />
        ) : section === "changes" ? (
          <ChangesView query={changes} {...shared} />
        ) : section === "due" ? (
          <DueView query={upcoming} {...shared} />
        ) : (
          <HomeView day={day} setDay={setDay} changeCount={changeCount} dueCount={dueCount} {...shared} />
        )}
      </main>

      {adding ? <FollowCase onClose={() => setAdding(false)} onOpenCase={setOpenCase} /> : null}
    </div>
  );
}

function NavItem({ icon: Icon, label, count, on, onClick }) {
  return (
    <button type="button" className={`mn-nav ${on ? "on" : ""}`} aria-current={on ? "page" : undefined} onClick={onClick}>
      <Icon size={17} />
      <span>{label}</span>
      {count ? <span className="count">{count}</span> : null}
    </button>
  );
}

function FollowCase({ onClose, onOpenCase }) {
  const [cnr, setCnr] = useState("");
  const queryClient = useQueryClient();
  const track = useMutation({
    mutationFn: () => api.track(cnr),
    onSuccess: (result) => {
      queryClient.invalidateQueries();
      onClose();
      onOpenCase(result.case_id);
    },
  });
  return (
    <div className="mn-scrim" role="presentation" onMouseDown={onClose}>
      <form
        className="mn-dialog"
        role="dialog"
        aria-labelledby="follow-title"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault();
          track.mutate();
        }}
      >
        <header>
          <h2 id="follow-title">Follow a case</h2>
          <button type="button" className="mn-icon" aria-label="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </header>
        <p className="mn-soft">
          Enter the 16-character CNR from the case status page or any order. Manu reads the court every morning and tells you
          what changed and what you have to do.
        </p>
        <label>
          CNR
          <input
            autoFocus
            value={cnr}
            onChange={(event) => setCnr(event.target.value.toUpperCase())}
            placeholder="DLSE010001232024"
            maxLength={24}
            spellCheck={false}
          />
        </label>
        {track.error ? <p className="mn-error">{String(track.error.message)}</p> : null}
        <footer>
          <button type="button" className="mn-btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="mn-btn ink" disabled={cnr.replace(/-/g, "").length < 16 || track.isPending}>
            {track.isPending ? "Reading the court…" : "Follow"}
          </button>
        </footer>
      </form>
    </div>
  );
}
