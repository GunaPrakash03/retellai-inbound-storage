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

// Which fields to show comes from the record itself: the backend returns an
// `intake` list of {name, label, kind, must_ask, value} for this record's
// practice area, generated from the same spec the agent prompt and the
// database schema come from. Nothing here enumerates field names, so a
// question added to the prompt shows up without a frontend change.
//
// Two are left out of the grid because they have their own UI: the summary
// is the paragraph at the top of the pane, and additional details is the
// free-text block near the bottom.
const OWN_UI = new Set(["case_summary", "additional_details"]);

const intakeRows = (data) => (data?.intake || []).filter((f) => !OWN_UI.has(f.name));

const VALIDITY_KEYS = { callback_phone: "is_phone_valid", email: "is_email_valid" };

// Booleans are three-state — yes, no, or never captured. The prompt treats a
// question that was never asked as a different fact from a "no", so the edit
// control has to be able to say so; a checkbox can only say yes or no.
const BOOL_OPTIONS = [
  { value: "", label: "Not asked" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

const boolToDraft = (v) => (v === null || v === undefined || v === "" ? "" : v ? "true" : "false");
const draftToBool = (v) => (v === "" ? null : v === "true");

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

function formatValue(field) {
  const { kind, value } = field;
  if (value === null || value === undefined || value === "") return "—";
  if (kind === "bool") return value ? "Yes" : "No";
  return value;
}

export default function CaseDetail({ bucket, callId, onChanged, taxonomy }) {
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
      additional_details: caseData.additional_details || "",
    };
    for (const f of intakeRows(caseData)) {
      seed[f.name] = f.kind === "bool" ? boolToDraft(f.value) : f.value ?? "";
    }
    setDraft(seed);
    setEditing(true);
  }

  function saveEdits() {
    // Diff against what's on screen and send only what actually changed, so
    // merely opening the form doesn't mark every field as hand-corrected —
    // a manually-corrected field stops accepting webhook updates for good.
    const kinds = Object.fromEntries(intakeRows(caseData).map((f) => [f.name, f.kind]));
    const changed = {};
    for (const [key, value] of Object.entries(draft)) {
      const isBool = kinds[key] === "bool";
      const original = isBool ? boolToDraft(caseData[key]) : caseData[key] ?? "";
      if (value === original) continue;
      changed[key] = isBool ? draftToBool(value) : value === "" ? null : value;
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
  const rows = intakeRows(caseData);
  // Must-ask questions the call never captured — the prompt requires these
  // before the agent may close, so a non-empty list means someone has to
  // follow up. An "unknown" the caller actually gave doesn't appear here.
  const missing = caseData.missing_must_ask || [];
  const missingLabels = missing
    .map((name) => rows.find((f) => f.name === name)?.label || name)
    .join(", ");
  // Matter types for the drafted category, preferring the backend's list
  // (fetched once into `taxonomy`) over the bundled fallback in constants.
  const matterTypes =
    (editing && draft && (taxonomy?.[draft.case_category]?.types || SUBCATEGORIES[draft.case_category])) ||
    [];
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
            {!!caseData.time_sensitive && (
              <span className="flag" title="A deadline came up on this call — check the dates before anything else">
                ⏱ Time sensitive
              </span>
            )}
            {!!caseData.whistleblower_limited_disclosure && (
              <span className="flag" title="Whistleblower who chose not to give details — do not press for more">
                Limited disclosure
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

      {missing.length > 0 && (
        <div className="stale-warning">
          {missing.length} required question{missing.length === 1 ? "" : "s"} never
          captured: {missingLabels}. Worth confirming on the follow-up call.
        </div>
      )}

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

          {matterTypes.length > 0 && (
            <div className="field-row">
              <span className="field-label">Matter type</span>
              <select
                value={draft.case_subcategory}
                disabled={saving}
                onChange={(e) => setDraft({ ...draft, case_subcategory: e.target.value })}
              >
                <option value="">Not specified</option>
                {matterTypes.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          )}

          {rows.map((f) => (
            <div className="field-row" key={f.name}>
              <span className="field-label">{f.label}</span>
              {f.kind === "bool" ? (
                <select
                  value={draft[f.name]}
                  disabled={saving}
                  onChange={(e) => setDraft({ ...draft, [f.name]: e.target.value })}
                >
                  {BOOL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={draft[f.name]}
                  disabled={saving}
                  onChange={(e) => setDraft({ ...draft, [f.name]: e.target.value })}
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
          {rows.map((f) => {
            const validityKey = VALIDITY_KEYS[f.name];
            const isInvalid = validityKey && f.value && caseData[validityKey] === 0;
            const notAsked = f.must_ask && missing.includes(f.name);
            return (
              <div className="field-row" key={f.name}>
                <span className="field-label">{f.label}</span>
                <span className="field-value">
                  {formatValue(f)}
                  {edited.has(f.name) && (
                    <span className="corrected" title="Corrected by staff; protected from webhook updates">
                      edited
                    </span>
                  )}
                  {notAsked && (
                    <span className="flag" title="The prompt requires this question, and the call never captured an answer">
                      not asked
                    </span>
                  )}
                  {isInvalid && (
                    <span
                      className="flag"
                      title={`This ${f.label.toLowerCase()} doesn't look valid — may need a callback to confirm`}
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
