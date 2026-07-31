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

export function getCounts() {
  return request("/counts");
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

export function updateAssignment(bucket, callId, assignedTo) {
  return request(`/${bucket}/${encodeURIComponent(callId)}/assignment`, {
    method: "PATCH",
    body: JSON.stringify({ assigned_to: assignedTo || null }),
  });
}

export function updateCourtStatus(bucket, callId, { courtStatus, nextHearingDate }) {
  return request(`/${bucket}/${encodeURIComponent(callId)}/court-status`, {
    method: "PATCH",
    body: JSON.stringify({
      court_status: courtStatus || null,
      next_hearing_date: nextHearingDate || null,
    }),
  });
}

// ---- staff ----

export function listStaff() {
  return request("/staff");
}

export function createStaff(payload) {
  return request("/staff", { method: "POST", body: JSON.stringify(payload) });
}

export function updateStaff(staffId, payload) {
  return request(`/staff/${encodeURIComponent(staffId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteStaff(staffId) {
  return request(`/staff/${encodeURIComponent(staffId)}`, { method: "DELETE" });
}

// ---- messages ----

export function listMessages(delivered) {
  const qs = delivered === undefined ? "" : `?delivered=${delivered}`;
  return request(`/messages${qs}`);
}

export function markMessageDelivered(messageId, delivered) {
  return request(`/messages/${encodeURIComponent(messageId)}`, {
    method: "PATCH",
    body: JSON.stringify({ delivered }),
  });
}
