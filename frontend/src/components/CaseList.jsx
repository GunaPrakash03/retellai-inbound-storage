import { CATEGORIES, CATEGORY_LABELS, STATUSES, STATUS_LABELS } from "../constants";

function timeAgo(isoString) {
  if (!isoString) return "—";
  const then = new Date(isoString.replace(" ", "T") + "Z").getTime();
  const diffMin = Math.round((Date.now() - then) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

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
        {loading ? (
          <div className="empty-state">Loading cases…</div>
        ) : cases.length === 0 ? (
          <div className="empty-state">No cases match these filters.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Caller</th>
                <th>Summary</th>
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
                  <td>
                    <span className={`badge cat-${c.case_category || "other"}`}>
                      {CATEGORY_LABELS[c.case_category] || "Uncategorized"}
                    </span>
                    {!!c.emergency_flagged && <span className="flag" title="Safety branch was triggered on this call">⚠</span>}
                  </td>
                  <td>
                    <div className="caller-name">{c.caller_name || "Unknown"}</div>
                    <div className="caller-phone">{c.callback_phone || c.from_number || "—"}</div>
                  </td>
                  <td className="summary-cell">{c.case_summary || "—"}</td>
                  <td>
                    <span className={`pill status-${c.status}`}>{STATUS_LABELS[c.status] || c.status}</span>
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
