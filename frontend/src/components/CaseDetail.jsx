import { useEffect, useState } from "react";
import { getRecord, listStaff, updateAssignment, updateCourtStatus, updateRecordStatus } from "../api";
import { CATEGORY_LABELS, STATUSES, STATUS_LABELS } from "../constants";
import { daysSince, timeAgo } from "../format";

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

const VALIDITY_KEYS = { callback_phone: "is_phone_valid", email: "is_email_valid" };

// Past this many days, a hearing date is old enough that reading it to a
// caller without checking could send them to court on the wrong day.
const STALE_AFTER_DAYS = 14;

function formatValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (["represented_already", "injured", "police_report_filed"].includes(key)) {
    return value ? "Yes" : "No";
  }
  return value;
}

export default function CaseDetail({ bucket, callId, onChanged }) {
  const [caseData, setCaseData] = useState(null);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [courtDraft, setCourtDraft] = useState({ courtStatus: "", nextHearingDate: "" });

  useEffect(() => {
    listStaff().then(setStaff).catch(() => setStaff([]));
  }, []);

  useEffect(() => {
    if (!callId) {
      setCaseData(null);
      return;
    }
    // Ignore out-of-order responses: clicking case A then case B quickly
    // must never leave A's slower response on screen as if it were B —
    // staff could save a court status onto the wrong caller's file.
    let stale = false;
    setLoading(true);
    setError(null);
    getRecord(bucket, callId)
      .then((data) => {
        if (stale) return;
        setCaseData(data);
        setCourtDraft({
          courtStatus: data.court_status || "",
          nextHearingDate: data.next_hearing_date || "",
        });
      })
      .catch((e) => {
        if (!stale) setError(e.message);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [bucket, callId]);

  if (!callId) {
    return <div className="case-detail empty-state">Select a call to see the full record.</div>;
  }
  if (loading && !caseData) return <div className="case-detail empty-state">Loading…</div>;
  if (error) return <div className="case-detail empty-state">Couldn't load this call: {error}</div>;
  if (!caseData) return null;

  async function run(fn) {
    setSaving(true);
    try {
      setCaseData(await fn());
      onChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const staleDays = daysSince(caseData.court_status_updated);
  const isStale =
    caseData.court_status_updated && staleDays !== null && staleDays >= STALE_AFTER_DAYS;

  // Only active staff can take new work, but whoever is already on the case
  // stays listed even once deactivated or removed from the directory —
  // dropping them would silently render an assigned case as "Unassigned".
  const assignable = staff.filter((s) => s.active);
  if (caseData.assigned_to && !assignable.some((s) => s.name === caseData.assigned_to)) {
    const former = staff.find((s) => s.name === caseData.assigned_to);
    assignable.unshift(former || { id: "__former", name: caseData.assigned_to, active: 0 });
  }

  return (
    <div className="case-detail">
      <div className="detail-header">
        <div className="detail-heading">
          {caseData.case_number && (
            <div className="case-number-badge">Case #{caseData.case_number}</div>
          )}
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
        </div>
        <select
          value={caseData.status}
          disabled={saving}
          onChange={(e) => run(() => updateRecordStatus(bucket, callId, e.target.value))}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>
      </div>

      <p className="case-summary-text">{caseData.case_summary || "No summary captured."}</p>

      <h3>Handling</h3>
      <div className="handling-block">
        <label className="inline-field">
          <span className="field-label">Assigned to</span>
          <select
            value={caseData.assigned_to || ""}
            disabled={saving}
            onChange={(e) => run(() => updateAssignment(bucket, callId, e.target.value))}
          >
            <option value="">Unassigned</option>
            {assignable.map((s) => (
              <option key={s.id} value={s.name}>
                {s.name}{s.role ? ` — ${s.role}` : ""}
                {s.active ? "" : " (inactive)"}
              </option>
            ))}
          </select>
        </label>
        {staff.length === 0 && (
          <p className="panel-note">
            No one in the staff directory yet — add people there to assign cases.
          </p>
        )}
      </div>

      <h3>Court status</h3>
      {isStale && (
        <div className="stale-warning">
          Last confirmed {staleDays} days ago. Verify before telling a caller — the
          agent reads this back over the phone.
        </div>
      )}
      <div className="handling-block">
        <label className="inline-field">
          <span className="field-label">Status</span>
          <input
            value={courtDraft.courtStatus}
            disabled={saving}
            placeholder="e.g. Hearing postponed"
            onChange={(e) => setCourtDraft({ ...courtDraft, courtStatus: e.target.value })}
          />
        </label>
        <label className="inline-field">
          <span className="field-label">Next hearing</span>
          <input
            type="date"
            value={courtDraft.nextHearingDate}
            disabled={saving}
            onChange={(e) => setCourtDraft({ ...courtDraft, nextHearingDate: e.target.value })}
          />
        </label>
        <div className="inline-actions">
          <button
            disabled={saving}
            onClick={() => run(() => updateCourtStatus(bucket, callId, courtDraft))}
          >
            {saving ? "Saving…" : "Save court status"}
          </button>
          {caseData.court_status_updated && (
            <span className="panel-note">
              Updated {timeAgo(caseData.court_status_updated)}
            </span>
          )}
        </div>
      </div>

      <h3>Intake details</h3>
      <div className="field-grid">
        {FIELD_ROWS.map(([key, label]) => {
          const validityKey = VALIDITY_KEYS[key];
          const isInvalid = validityKey && caseData[key] && caseData[validityKey] === 0;
          return (
            <div className="field-row" key={key}>
              <span className="field-label">{label}</span>
              <span className="field-value">
                {formatValue(key, caseData[key])}
                {isInvalid && (
                  <span
                    className="flag"
                    title={`This ${label.toLowerCase()} doesn't look valid — may need a callback to confirm`}
                  >
                    ⚠ invalid
                  </span>
                )}
              </span>
            </div>
          );
        })}
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
        Call ID: {caseData.call_id} · From: {caseData.from_number || "—"} · Received{" "}
        {caseData.created_at}
      </div>
    </div>
  );
}
