import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, MessageCircle, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api.js";
import { humanDates } from "../model.js";

/**
 * A message Manu drafted and a person sends. Editable, copyable, or opened in WhatsApp
 * with the text filled in — the person chooses the chat and presses send. Manu has no
 * way to send anything itself.
 */
export function DraftSheet({ kind, caseId, today, onClose }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["draft", kind, caseId, today],
    queryFn: () => (kind === "cause-list" ? api.causeListMessage(today) : api.clientUpdate(caseId, today)),
  });
  const draft = query.data;
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);
  const [client, setClient] = useState("");
  useEffect(() => {
    if (draft) {
      setText(draft.text);
      if (kind === "client") setClient((prev) => prev || draft.client || "");
    }
  }, [draft, kind]);
  const save = useMutation({
    mutationFn: () => api.setClient(caseId, client),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["draft"] });
      queryClient.invalidateQueries({ queryKey: ["case"] });
    },
  });
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked: the text is selectable */
    }
  };

  return (
    <div className="mn-scrim" role="presentation" onMouseDown={onClose}>
      <section className="mn-sheet-dialog" role="dialog" aria-label="Draft message" onMouseDown={(e) => e.stopPropagation()}>
        <header>
          <div>
            <p className="mn-eyebrow">Draft · you send it</p>
            <h2>{kind === "cause-list" ? "Morning cause list" : `Client update · ${draft?.title || ""}`}</h2>
          </div>
          <button type="button" className="mn-icon ghost" aria-label="Close" onClick={onClose}>
            <X size={17} />
          </button>
        </header>

        {kind === "client" ? (
          <form
            className="mn-client-form"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <label>
              Client
              <input value={client} onChange={(e) => setClient(e.target.value)} placeholder="Name as you address them" />
            </label>
            <button type="submit" className="mn-btn small" disabled={save.isPending}>
              {save.isSuccess ? <Check size={14} /> : null} Remember for this case
            </button>
          </form>
        ) : null}

        {query.isPending ? <p className="mn-faint">Drafting…</p> : null}
        {query.error ? <p className="mn-error">{String(query.error.message)}</p> : null}
        {draft ? (
          <>
            <textarea className="mn-draft" value={text} onChange={(e) => setText(e.target.value)} aria-label="Message text" spellCheck={false} />
            {draft.gaps?.length ? (
              <ul className="mn-draft-notes">
                {draft.gaps.map((g) => (
                  <li key={g} className="mn-warning">
                    {g}
                  </li>
                ))}
              </ul>
            ) : null}
            <details className="mn-draft-sources">
              <summary>Where these facts come from · {draft.sources.length}</summary>
              <ul>
                {draft.sources.map((s) => (
                  <li key={s}>{humanDates(s)}</li>
                ))}
              </ul>
            </details>
            <footer>
              <span className="mn-faint small">Manu never sends messages. You choose who gets this.</span>
              <button type="button" className="mn-btn" onClick={copy}>
                {copied ? <Check size={15} /> : <Copy size={15} />} {copied ? "Copied" : "Copy"}
              </button>
              <a className="mn-btn ink" href={`https://wa.me/?text=${encodeURIComponent(text)}`} target="_blank" rel="noreferrer">
                <MessageCircle size={15} /> Open in WhatsApp
              </a>
            </footer>
          </>
        ) : null}
      </section>
    </div>
  );
}
