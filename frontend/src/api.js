const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return null;
  return res.json();
}

export function listCases({ category, status } = {}) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request(`/cases${qs ? `?${qs}` : ""}`);
}

export function getCase(callId) {
  return request(`/cases/${encodeURIComponent(callId)}`);
}

export function updateStatus(callId, status) {
  return request(`/cases/${encodeURIComponent(callId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
