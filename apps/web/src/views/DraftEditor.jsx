import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api.js";

/**
 * An application drafted from the record. The questions are what only the advocate knows;
 * the preview shows each paragraph with where it came from. Nothing is filed: the
 * advocate downloads the .docx and takes it from there.
 */
export function DraftEditor({ c, template, today, onClose }) {
  const [inputs, setInputs] = useState({});
  const [debounced, setDebounced] = useState({});
  useEffect(() => {
    const t = setTimeout(() => setDebounced(inputs), 250);
    return () => clearTimeout(t);
  }, [inputs]);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const query = useQuery({
    queryKey: ["draft-app", c.id, template, debounced, today],
    queryFn: () => api.draft(c.id, template, debounced, today),
    placeholderData: (prev) => prev,
  });
  const download = useMutation({
    mutationFn: () => api.draftDocx(c.id, template, inputs, today),
    onSuccess: ({ blob, name }) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    },
  });
  const d = query.data;
  const set = (key) => (e) => setInputs({ ...inputs, [key]: e.target.value });
  const missing = new Set(d?.missing || []);

  return (
    <div className="mn-scrim" role="presentation" onMouseDown={onClose}>
      <section className="mn-sheet-dialog wide" role="dialog" aria-label="Draft application" onMouseDown={(e) => e.stopPropagation()}>
        <header>
          <div>
            <p className="mn-eyebrow">Draft from the record · you file it</p>
            <h2>{d?.title || "Drafting…"}</h2>
          </div>
          <button type="button" className="mn-icon ghost" aria-label="Close" onClick={onClose}>
            <X size={17} />
          </button>
        </header>
        <div className="mn-drafting">
          <form className="mn-questions" onSubmit={(e) => e.preventDefault()}>
            <p className="mn-faint small">Manu filled what the record says. These are for you.</p>
            {(d?.questions || []).map((q) => (
              <label key={q.key} className={missing.has(q.key) ? "needed" : ""}>
                <span>
                  {q.label}
                  {q.required ? <b> *</b> : <small> optional</small>}
                </span>
                {q.kind === "choice" ? (
                  <select value={inputs[q.key] || ""} onChange={set(q.key)}>
                    <option value="">Choose…</option>
                    {q.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : q.kind === "long" ? (
                  <textarea rows={3} value={inputs[q.key] || ""} onChange={set(q.key)} placeholder={q.hint} />
                ) : (
                  <input value={inputs[q.key] || ""} onChange={set(q.key)} placeholder={q.hint} />
                )}
                {q.kind === "choice" && q.hint ? <small>{q.hint}</small> : null}
              </label>
            ))}
            {d?.flags?.length ? (
              <ul className="mn-draft-notes">
                {d.flags.map((f) => (
                  <li key={f} className="mn-warning">
                    {f}
                  </li>
                ))}
              </ul>
            ) : null}
          </form>
          <article className="mn-paper" aria-label="Preview">
            {(d?.blocks || []).map((b, i) => (
              <div key={i} className={`mn-paper-${b.kind}`}>
                <p>{b.text}</p>
                {b.sources.length ? <span className="mn-src-tag">{b.sources.join(" · ")}</span> : null}
              </div>
            ))}
          </article>
        </div>
        <footer>
          <span className="mn-faint small">
            {d?.status === "ready" ? "Complete. Review it, then download." : `${missing.size} ${missing.size === 1 ? "answer" : "answers"} still needed.`}
          </span>
          {download.error ? <span className="mn-error">{String(download.error.message)}</span> : null}
          <button type="button" className="mn-btn ink" disabled={d?.status !== "ready" || download.isPending} onClick={() => download.mutate()}>
            <Download size={15} /> Download .docx
          </button>
        </footer>
      </section>
    </div>
  );
}
