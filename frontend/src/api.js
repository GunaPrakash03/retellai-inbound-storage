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

export function listRecords(bucket, { category, status } = {}) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request(`/${bucket}${qs ? `?${qs}` : ""}`);
}

export function getRecord(bucket, callId) {
  return request(`/${bucket}/${encodeURIComponent(callId)}`);
}

export function updateRecordStatus(bucket, callId, status) {
  return request(`/${bucket}/${encodeURIComponent(callId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
