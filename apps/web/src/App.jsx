import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, CalendarDays, Gavel, ListChecks, Moon, Plus, RefreshCw, Scale, Sun, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "./api.js";
import { indiaDateKey } from "./model.js";
import { CaseView } from "./views/CaseView.jsx";
import { ChangesView } from "./views/ChangesView.jsx";
import { DayView } from "./views/DayView.jsx";
import { DueView } from "./views/DueView.jsx";

const NAV = [
  { id: "day", label: "Diary", icon: CalendarDays },
  { id: "changes", label: "What changed", icon: Bell },
  { id: "due", label: "Due", icon: ListChecks },
];

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
  const [section, setSection] = useState("day");
  const [lens, setLens] = useState(() => readPref("manu.lens", "advocate"));
  const [theme, setTheme] = useState(() => readPref("manu.theme", "dark"));
  const [day, setDay] = useState(() => indiaDateKey());
  const [openCase, setOpenCase] = useState(null);
  const [adding, setAdding] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => writePref("manu.lens", lens), [lens]);
  useEffect(() => writePref("manu.theme", theme), [theme]);

  const watch = useMutation({
    mutationFn: api.watch,
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const today = indiaDateKey();
  const shared = { lens, today, onOpenCase: setOpenCase };

  return (
    <div className={`manu-shell ${theme === "light" ? "themeLight" : ""}`}>
      <aside className="manu-sidebar">
        <header>
          <span className="manu-mark" aria-hidden="true">M</span>
          <div>
            <strong>Manu</strong>
            <small>{lens === "judge" ? "Judge's desk" : "Advocate's diary"}</small>
          </div>
        </header>

        <button type="button" className="manu-create" onClick={() => setAdding(true)}>
          <Plus size={15} /> Follow a case
        </button>

        <nav aria-label="Diary">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`manu-nav ${section === id ? "active" : ""}`}
              aria-current={section === id ? "page" : undefined}
              onClick={() => {
                setSection(id);
                setOpenCase(null);
              }}
            >
              <Icon size={16} /> {label}
            </button>
          ))}
        </nav>

        <div className="manu-lens" role="radiogroup" aria-label="View as">
          <span>View as</span>
          <div>
            <button type="button" role="radio" aria-checked={lens === "advocate"} className={lens === "advocate" ? "on" : ""} onClick={() => setLens("advocate")}>
              <Scale size={14} /> Advocate
            </button>
            <button type="button" role="radio" aria-checked={lens === "judge"} className={lens === "judge" ? "on" : ""} onClick={() => setLens("judge")}>
              <Gavel size={14} /> Judge
            </button>
          </div>
        </div>

        <footer>
          <button type="button" className="manu-quiet" onClick={() => watch.mutate()} disabled={watch.isPending}>
            <RefreshCw size={14} className={watch.isPending ? "spin" : ""} />
            {watch.isPending ? "Reading the courts…" : "Check courts now"}
          </button>
          {watch.data ? (
            <small className="manu-muted">
              Checked {watch.data.checked}, {watch.data.changed.length} changed
              {Object.keys(watch.data.failed).length ? `, ${Object.keys(watch.data.failed).length} unreachable` : ""}.
            </small>
          ) : null}
          {watch.error ? <small className="manu-error">{String(watch.error.message)}</small> : null}
          <button
            type="button"
            className="manu-icon"
            aria-label={theme === "light" ? "Use dark theme" : "Use light theme"}
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </footer>
      </aside>

      <main className="manu-main">
        {openCase ? (
          <CaseView caseId={openCase} onBack={() => setOpenCase(null)} {...shared} />
        ) : section === "day" ? (
          <DayView day={day} setDay={setDay} {...shared} />
        ) : section === "changes" ? (
          <ChangesView {...shared} />
        ) : (
          <DueView {...shared} />
        )}
      </main>

      {adding ? <FollowCase onClose={() => setAdding(false)} onOpenCase={setOpenCase} /> : null}
    </div>
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
    <div className="manu-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="manu-dialog"
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
          <button type="button" className="manu-icon" aria-label="Close" onClick={onClose}>
            <X size={15} />
          </button>
        </header>
        <p className="manu-muted">
          Enter the 16-character CNR from the case status page or any order. Manu reads the court every morning and tells you
          what changed.
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
        {track.error ? <p className="manu-error">{String(track.error.message)}</p> : null}
        <footer>
          <button type="button" className="manu-quiet" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="manu-create" disabled={cnr.replace(/-/g, "").length < 16 || track.isPending}>
            {track.isPending ? "Reading the court…" : "Follow"}
          </button>
        </footer>
      </form>
    </div>
  );
}
