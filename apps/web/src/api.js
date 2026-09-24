const BASE = import.meta.env.VITE_MANU_API || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  day: (on, lens) => request(`/api/diary/day?on=${on}&lens=${lens}`),
  upcoming: (on) => request(`/api/diary/upcoming?on=${on}&days=14`),
  changes: () => request(`/api/diary/changes?limit=150`),
  cases: (on, lens) => request(`/api/cases?on=${on}&lens=${lens}`),
  case: (id, on, lens) => request(`/api/cases/${id}?on=${on}&lens=${lens}`),
  track: (cnr) => request(`/api/cases`, { method: "POST", body: JSON.stringify({ cnr }) }),
  setObligation: (caseId, obligationId, status) =>
    request(`/api/cases/${caseId}/obligations/${obligationId}`, { method: "POST", body: JSON.stringify({ status }) }),
  watch: () => request(`/api/watch/run`, { method: "POST" }),
};
