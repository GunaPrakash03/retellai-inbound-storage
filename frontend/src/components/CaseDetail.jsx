import { useEffect, useState } from "react";
import { getCase, updateStatus } from "../api";
import { CATEGORY_LABELS, STATUSES, STATUS_LABELS } from "../constants";

const FIELD_ROWS = [
  ["caller_name", "Caller name"],
  ["callback_phone", "Callback phone"],
  ["email", "Email"],
  ["incident_date", "Incident / key date"],
  ["location", "Location"],
  ["opposing_party", "Opposing party"],
  ["key_date_or_deadline", "Deadline / court date"],
  ["represented_already", "Already represented"],
  ["injured", "Injured"],
  ["police_report_filed", "Police report filed"],
];

function formatValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (["represented_already", "injured", "police_report_filed"].includes(key)) {
    return value ? "Yes" : "No";
  }
  return value;
}

export default function CaseDetail({ callId, onStatusChanged }) {
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!callId) return;
    setLoading(true);
    setError(null);
    getCase(callId)
      .then(setCaseData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [callId]);

  if (!callId) {
    return (
      <div className="case-detail empty-state">Select a case from the list to see the full record.</div>
    );
  }

  if (loading && !caseData) {
    return <div className="case-detail empty-state">Loading…</div>;
  }

  if (error) {
    return <div className="case-detail empty-state">Couldn't load this case: {error}</div>;
  }

  if (!caseData) return null;

  async function handleStatusChange(e) {
    const status = e.target.value;
    setSavingStatus(true);
    try {
      const updated = await updateStatus(callId, status);
      setCaseData(updated);
      onStatusChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingStatus(false);
    }
  }

  return (
    <div className="case-detail">
      <div className="detail-header">
        <div>
          <span className={`badge cat-${caseData.case_category || "other"}`}>
            {CATEGORY_LABELS[caseData.case_category] || "Uncategorized"}
          </span>
          {!!caseData.emergency_flagged && (
            <span className="flag" title="Safety branch was triggered on this call">
              ⚠ Safety branch triggered
            </span>
          )}
        </div>
        <select value={caseData.status} onChange={handleStatusChange} disabled={savingStatus}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      <p className="case-summary-text">{caseData.case_summary || "No summary captured."}</p>

      <div className="field-grid">
        {FIELD_ROWS.map(([key, label]) => (
          <div className="field-row" key={key}>
            <span className="field-label">{label}</span>
            <span className="field-value">{formatValue(key, caseData[key])}</span>
          </div>
        ))}
      </div>

      {caseData.additional_details && (
        <>
          <h3>Additional details</h3>
          <p className="case-summary-text">{caseData.additional_details}</p>
        </>
      )}

      {caseData.recording_url && (
        <>
          <h3>Recording</h3>
          <audio controls src={caseData.recording_url} style={{ width: "100%" }} />
        </>
      )}

      {caseData.transcript && (
        <>
          <h3>Transcript</h3>
          <pre className="transcript">{caseData.transcript}</pre>
        </>
      )}

      <div className="meta-footer">
        Call ID: {caseData.call_id} · From: {caseData.from_number || "—"} · Received {caseData.created_at}
      </div>
    </div>
  );
}
