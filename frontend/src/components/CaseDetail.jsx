import { useEffect, useState } from "react";
import {
  getRecord,
  listStaff,
  updateAssignment,
  updateCourtStatus,
  updateRecordFields,
  updateRecordStatus,
} from "../api";
import {
  CATEGORIES,
  CATEGORY_LABELS,
  STATUSES,
  STATUS_LABELS,
  SUBCATEGORIES,
  SUBCATEGORY_LABELS,
} from "../constants";
import { daysSince, timeAgo } from "../format";

// `type` drives which input the edit form renders. Order matches the
// read-only grid so a field doesn't move when you switch into edit mode.
const FIELD_ROWS = [
  ["caller_name", "Caller name", "text"],
  ["callback_phone", "Callback phone", "text"],
  ["email", "Email", "text"],
  ["incident_date", "Incident / key date", "text"],
  ["location", "Location", "text"],
  ["opposing_party", "Opposing party", "text"],
  ["key_date_or_deadline", "Deadline / court date", "text"],
  ["represented_already", "Already represented", "bool"],
  ["injured", "Injured", "bool"],
  ["police_report_filed", "Police report filed", "bool"],
];

const VALIDITY_KEYS = { callback_phone: "is_phone_valid", email: "is_email_valid" };

// Past this many days, a hearing date is old enough that reading it to a
// caller without checking could send them to court on the wrong day.
const STALE_AFTER_DAYS = 14;

// Which fields staff have hand-corrected. Stored as a JSON array of column
// names; treat anything unparseable as "none edited" rather than breaking
// the whole detail pane over a display-only badge.
function parseManualEdits(raw) {
  if (!raw) return new Set();
  try {
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

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
  const [courtDraft, setCourtDraft] = useState({
    courtStatus: "",
    nextHearingDate: "",
    hearingAttorney: "",
  });
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saveError, setSaveError] = useState(null);

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
    // Never carry a half-typed correction across to another caller's record.
    setEditing(false);
    setDraft(null);
    setSaveError(null);
    getRecord(bucket, callId)
      .then((data) => {
        if (stale) return;
        setCaseData(data);
        setCourtDraft({
          courtStatus: data.court_status || "",
          nextHearingDate: data.next_hearing_date || "",
          hearingAttorney: data.hearing_attorney || "",
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

  // A failed save reports through saveError, not error: `error` means "this
  // record wouldn't load" and replaces the whole pane, which on a save would
  // throw away the corrections still sitting in the form.
  async function run(fn) {
    setSaving(true);
    setSaveError(null);
    try {
      setCaseData(await fn());
      onChanged?.();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function startEditing() {
    const seed = {
      case_category: caseData.case_category || "",
      case_subcategory: caseData.case_subcategory || "",
      case_summary: caseData.case_summary || "",
    };
    for (const [key, , type] of FIELD_ROWS) {
      seed[key] = type === "bool" ? !!caseData[key] : caseData[key] ?? "";
    }
    setDraft(seed);
    setEditing(true);
  }

  function saveEdits() {
    // Diff against what's on screen and send only what actually changed, so
    // merely opening the form doesn't mark every field as hand-corrected —
    // a manually-corrected field stops accepting webhook updates for good.
    const changed = {};
    for (const [key, value] of Object.entries(draft)) {
      const original = FIELD_ROWS.find(([k]) => k === key)?.[2] === "bool"
        ? !!caseData[key]
        : caseData[key] ?? "";
      if (value !== original) changed[key] = value === "" ? null : value;
    }
    if (Object.keys(changed).length === 0) {
      setEditing(false);
      return;
    }
    return run(async () => {
      const updated = await updateRecordFields(bucket, callId, changed);
      setEditing(false);
      return updated;
    });
  }

  const edited = parseManualEdits(caseData.manual_edits);
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
            {caseData.case_subcategory && (
              <span className="subcategory-badge">
                {SUBCATEGORY_LABELS[caseData.case_subcategory] || caseData.case_subcategory}
              </span>
            )}
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

      {saveError && <div className="error-banner">Couldn't save: {saveError}</div>}

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
        <label className="inline-field">
          <span className="field-label">Hearing attorney</span>
          {/* Who appears at the hearing — not always the assigned attorney,
              since court coverage gets handed off. Free text so it can hold
              someone outside the staff directory (covering counsel). */}
          <input
            value={courtDraft.hearingAttorney}
            disabled={saving}
            placeholder="Who's appearing"
            list="hearing-attorney-options"
            onChange={(e) => setCourtDraft({ ...courtDraft, hearingAttorney: e.target.value })}
          />
          <datalist id="hearing-attorney-options">
            {staff.filter((s) => s.active).map((s) => (
              <option key={s.id} value={s.name} />
            ))}
          </datalist>
        </label>
        <div className="inline-actions">
          <button
            disabled={saving}
            onClick={() => run(() => updateCourtStatus(bucket, callId, courtDraft))}
          >
            {saving ? "Saving…" : "Save court status"}
          </button>
          {caseData.hearing_attorney && (
            <span className="panel-note">
              Appearing: <strong>{caseData.hearing_attorney}</strong>
            </span>
          )}
          {caseData.court_status_updated && (
            <span className="panel-note">
              Updated {timeAgo(caseData.court_status_updated)}
            </span>
          )}
        </div>
      </div>

      <div className="section-heading">
        <h3>Intake details</h3>
        {!editing && (
          <button className="link-button" disabled={saving} onClick={startEditing}>
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="field-grid editing">
          <div className="field-row">
            <span className="field-label">Category</span>
            <select
              value={draft.case_category}
              disabled={saving}
              onChange={(e) =>
                // Changing category clears a now-mismatched subcategory in
                // the form; the backend does the same on save, this just
                // keeps the dropdown from showing a stale choice meanwhile.
                setDraft({ ...draft, case_category: e.target.value, case_subcategory: "" })
              }
            >
              <option value="">Uncategorized</option>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {(SUBCATEGORIES[draft.case_category] || []).length > 0 && (
            <div className="field-row">
              <span className="field-label">Matter type</span>
              <select
                value={draft.case_subcategory}
                disabled={saving}
                onChange={(e) => setDraft({ ...draft, case_subcategory: e.target.value })}
              >
                <option value="">Not specified</option>
                {SUBCATEGORIES[draft.case_category].map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          )}

          {FIELD_ROWS.map(([key, label, type]) => (
            <div className="field-row" key={key}>
              <span className="field-label">{label}</span>
              {type === "bool" ? (
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={draft[key]}
                    disabled={saving}
                    onChange={(e) => setDraft({ ...draft, [key]: e.target.checked })}
                  />
                  {draft[key] ? "Yes" : "No"}
                </label>
              ) : (
                <input
                  value={draft[key]}
                  disabled={saving}
                  onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                />
              )}
            </div>
          ))}

          <div className="field-row full">
            <span className="field-label">Summary</span>
            <textarea
              rows={3}
              value={draft.case_summary}
              disabled={saving}
              onChange={(e) => setDraft({ ...draft, case_summary: e.target.value })}
            />
          </div>

          <div className="inline-actions">
            <button disabled={saving} onClick={saveEdits}>
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button className="link-button" disabled={saving} onClick={() => setEditing(false)}>
              Cancel
            </button>
            <span className="panel-note">
              Corrections stick — a re-delivered call won't overwrite them.
            </span>
          </div>
        </div>
      ) : (
        <div className="field-grid">
          {FIELD_ROWS.map(([key, label]) => {
            const validityKey = VALIDITY_KEYS[key];
            const isInvalid = validityKey && caseData[key] && caseData[validityKey] === 0;
            return (
              <div className="field-row" key={key}>
                <span className="field-label">{label}</span>
                <span className="field-value">
                  {formatValue(key, caseData[key])}
                  {edited.has(key) && (
                    <span className="corrected" title="Corrected by staff; protected from webhook updates">
                      edited
                    </span>
                  )}
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
      )}

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
