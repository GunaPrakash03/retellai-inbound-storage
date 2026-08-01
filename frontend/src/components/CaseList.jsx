import { CATEGORIES, CATEGORY_LABELS, STATUSES, STATUS_LABELS, SUBCATEGORY_LABELS } from "../constants";
import { timeAgo } from "../format";

export default function CaseList({
  cases,
  loading,
  selectedCallId,
  onSelect,
  categoryFilter,
  statusFilter,
  onCategoryChange,
  onStatusChange,
}) {
  return (
    <div className="case-list">
      <div className="filters">
        <select value={categoryFilter} onChange={(e) => onCategoryChange(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => onStatusChange(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="table-wrap">
        {loading && cases.length === 0 ? (
          <div className="empty-state">Loading…</div>
        ) : cases.length === 0 ? (
          <div className="empty-state">No calls match these filters.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Case #</th>
                <th>Category</th>
                <th>Caller</th>
                <th>Summary</th>
                <th>Assigned</th>
                <th>Status</th>
                <th>Received</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr
                  key={c.call_id}
                  className={c.call_id === selectedCallId ? "selected" : ""}
                  onClick={() => onSelect(c.call_id)}
                >
                  <td className="case-number">{c.case_number || "—"}</td>
                  <td>
                    <span className={`badge cat-${c.case_category || "other"}`}>
                      {CATEGORY_LABELS[c.case_category] || "Uncategorized"}
                    </span>
                    {c.case_subcategory && (
                      <div className="subcategory-line">
                        {SUBCATEGORY_LABELS[c.case_subcategory] || c.case_subcategory}
                      </div>
                    )}
                    {!!c.emergency_flagged && (
                      <span className="flag" title="Safety branch was triggered on this call">⚠</span>
                    )}
                  </td>
                  <td>
                    <div className="caller-name">{c.caller_name || "Unknown"}</div>
                    <div className="caller-phone">
                      {c.callback_phone || c.from_number || "—"}
                      {c.callback_phone && c.is_phone_valid === 0 && (
                        <span className="flag" title="This phone number doesn't look valid">⚠</span>
                      )}
                    </div>
                  </td>
                  <td className="summary-cell">{c.case_summary || "—"}</td>
                  <td className="nowrap">{c.assigned_to || "—"}</td>
                  <td>
                    <span className={`pill status-${c.status}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                  </td>
                  <td className="nowrap">{timeAgo(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
