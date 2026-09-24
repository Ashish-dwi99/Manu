const BASE = import.meta.env.VITE_MANU_API || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      /* not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  day: (on) => request(`/api/diary/day?on=${on}`),
  upcoming: (on) => request(`/api/diary/upcoming?on=${on}&days=7`),
  changes: () => request(`/api/diary/changes?limit=150`),
  cases: (on) => request(`/api/cases?on=${on}`),
  case: (id, on) => request(`/api/cases/${id}?on=${on}`),
  order: (caseId, on) => request(`/api/cases/${caseId}/orders/${on}`),
  track: (cnr) => request(`/api/cases`, json("POST", { cnr })),
  setObligation: (caseId, id, status) => request(`/api/cases/${caseId}/obligations/${id}`, json("POST", { status })),
  watch: () => request(`/api/watch/run`, json("POST")),
  runtime: () => request(`/api/runtime`),
  documents: (caseId) => request(`/api/cases/${caseId}/documents`),
  upload: (caseId, file) => {
    const body = new FormData();
    body.append("file", file);
    return request(`/api/cases/${caseId}/documents`, { method: "POST", body });
  },
  search: (caseId, q) => request(`/api/cases/${caseId}/search?q=${encodeURIComponent(q)}`),
  page: (docId, page) => request(`/api/documents/${docId}/pages/${page}`),
  dates: (caseId) => request(`/api/cases/${caseId}/list-of-dates`),
  datesDocxUrl: (caseId) => `${BASE}/api/cases/${caseId}/list-of-dates.docx`,
  addNote: (caseId, text, on) => request(`/api/cases/${caseId}/notes`, json("POST", { text, on })),
  deleteNote: (caseId, noteId) => request(`/api/cases/${caseId}/notes/${noteId}`, { method: "DELETE" }),
  boards: (on) => request(`/api/boards?on=${on}`),
  findByAdvocate: (name) => request(`/api/import/advocate?name=${encodeURIComponent(name)}`),
  importCases: (cnrs) => request(`/api/cases/import`, json("POST", { cnrs })),
  limitationRules: () => request(`/api/law/limitation`),
  limitation: (body) => request(`/api/law/limitation`, json("POST", body)),
  addDeadline: (caseId, body) => request(`/api/cases/${caseId}/deadlines`, json("POST", body)),
  causeListMessage: (on) => request(`/api/messages/cause-list?on=${on}`),
  dueUpdates: (on) => request(`/api/messages/due?on=${on}`),
  clientUpdate: (caseId, on) => request(`/api/cases/${caseId}/messages/client-update?on=${on}`),
  setClient: (caseId, name) => request(`/api/cases/${caseId}/client`, json("PUT", { name })),
  researchSearch: (q) => request(`/api/research/search?q=${encodeURIComponent(q)}`),
  judgment: (source, docId) => request(`/api/research/judgments/${encodeURIComponent(source)}/${encodeURIComponent(docId)}`),
  checkCitations: (text) => request(`/api/research/check`, json("POST", { text })),
  research: (caseId, question) => request(`/api/cases/${caseId}/research`, json("POST", { question })),
  addAuthority: (caseId, source, docId, paragraph) =>
    request(`/api/cases/${caseId}/authorities`, json("POST", { source, doc_id: docId, paragraph })),
  deleteAuthority: (caseId, id) => request(`/api/cases/${caseId}/authorities/${id}`, { method: "DELETE" }),
  draftTemplates: (caseId) => request(`/api/cases/${caseId}/drafts`),
  draft: (caseId, template, inputs, on) => request(`/api/cases/${caseId}/drafts/${template}`, json("POST", { inputs, on })),
  draftDocx: async (caseId, template, inputs, on) => {
    const response = await fetch(`${BASE}/api/cases/${caseId}/drafts/${template}/docx`, json("POST", { inputs, on }));
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `${response.status}`);
    const name = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "")?.[1] || "draft.docx";
    return { blob: await response.blob(), name };
  },
  brief: (caseId) => request(`/api/cases/${caseId}/brief`, json("POST")),
  ask: (caseId, question) => request(`/api/cases/${caseId}/ask`, json("POST", { question })),
};
