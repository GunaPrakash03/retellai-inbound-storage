import { Link } from "react-router-dom";
import { CATEGORY_LABELS, categoryToSlug } from "../constants";
import { daysUntil, formatHearingDate, hearingCountdown } from "../format";

// Shared by the home page's court calendar and the full /hearings page.
// A hearing today or already past is the whole point of the panel, so those
// rows are marked rather than left to be spotted by reading dates.
export default function HearingTable({ hearings, loading, emptyText }) {
  if (loading) return <p className="panel-note">Loading…</p>;
  if (!hearings.length) return <p className="panel-note">{emptyText}</p>;

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Hearing</th>
            <th>When</th>
            <th>Case</th>
            <th>Client</th>
            <th>Matter</th>
            <th>Attorney</th>
            <th>Court status</th>
          </tr>
        </thead>
        <tbody>
          {hearings.map((h) => {
            const n = daysUntil(h.next_hearing_date);
            const soon = n !== null && n <= 7;
            const label = hearingCountdown(h.next_hearing_date);
            return (
              <tr key={h.call_id}>
                <td className="hearing-date">{formatHearingDate(h.next_hearing_date)}</td>
                <td>
                  {label ? (
                    <span className={`days-pill${soon ? " soon" : ""}`}>{label}</span>
                  ) : (
                    <span className="days-pill unknown" title="Unrecognised date format">
                      check date
                    </span>
                  )}
                </td>
                <td>
                  <Link
                    className="case-number-link"
                    to={`/cases/${categoryToSlug(h.case_category)}/${encodeURIComponent(h.call_id)}`}
                  >
                    {h.case_number || "—"}
                  </Link>
                </td>
                <td className="strong">{h.caller_name || "—"}</td>
                <td>
                  {CATEGORY_LABELS[h.case_category] || h.case_category || "—"}
                </td>
                <td>{h.hearing_attorney || <span className="dim">Unassigned</span>}</td>
                <td className="dim">{h.court_status || "No status on file"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
