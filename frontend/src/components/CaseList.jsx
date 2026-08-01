import {
  CATEGORIES,
  CATEGORY_LABELS,
  STATUSES,
  STATUS_LABELS,
  SUBCATEGORIES,
  SUBCATEGORY_LABELS,
} from "../constants";
import { timeAgo } from "../format";

// Two shapes:
//  - default (a bucket like Emergency/Partial): category + status filters,
//    the general-purpose columns.
//  - categoryMode (drilled into one practice area from the home page): the
//    category is fixed, so instead we filter by subcategory and assigned
//    attorney, and the columns show subcategory, attorney, and hearing date
//    — the things staff sort a practice area's caseload by.
export default function CaseList({
  cases,
  loading,
  selectedCallId,
  onSelect,
  categoryFilter,
  statusFilter,
  onCategoryChange,
  onStatusChange,
  categoryMode = false,
  activeCategory,
  subcategoryFilter,
  assignedFilter,
  onSubcategoryChange,
  onAssignedChange,
}) {
  // In category mode `cases` is the whole practice area; the dropdowns offer
  // only values that actually occur in it, and filtering happens here so the
  // options stay stable as filters are applied.
  const present = categoryMode ? cases : [];
  const presentSubs = new Set(present.map((c) => c.case_subcategory).filter(Boolean));
  const subcategoryOptions = (SUBCATEGORIES[activeCategory] || []).filter((s) =>
    presentSubs.has(s.value),
  );
  const attorneyOptions = [...new Set(present.map((c) => c.assigned_to).filter(Boolean))].sort();

  const rows = categoryMode
    ? cases.filter(
        (c) =>
          (!subcategoryFilter || c.case_subcategory === subcategoryFilter) &&
          (!assignedFilter || c.assigned_to === assignedFilter) &&
          (!statusFilter || c.status === statusFilter),
      )
    : cases;

  return (
    <div className="case-list">
      <div className="filters">
        {categoryMode ? (
          <>
            {subcategoryOptions.length > 0 && (
              <select
                value={subcategoryFilter}
                onChange={(e) => onSubcategoryChange(e.target.value)}
                aria-label="Filter by matter type"
              >
                <option value="">All matter types</option>
                {subcategoryOptions.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            )}
            {attorneyOptions.length > 0 && (
              <select
                value={assignedFilter}
                onChange={(e) => onAssignedChange(e.target.value)}
                aria-label="Filter by assigned attorney"
              >
                <option value="">All attorneys</option>
                {attorneyOptions.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            )}
          </>
        ) : (
          <select value={categoryFilter} onChange={(e) => onCategoryChange(e.target.value)}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        )}
        <select value={statusFilter} onChange={(e) => onStatusChange(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>
      </div>

      <div className="table-wrap">
        {loading && rows.length === 0 ? (
          <div className="empty-state">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="empty-state">No calls match these filters.</div>
        ) : (
          <table>
            <thead>
              {categoryMode ? (
                <tr>
                  <th>Case #</th>
                  <th>Matter type</th>
                  <th>Caller</th>
                  <th>Attorney</th>
                  <th>Hearing</th>
                  <th>Status</th>
                </tr>
              ) : (
                <tr>
                  <th>Case #</th>
                  <th>Category</th>
                  <th>Caller</th>
                  <th>Summary</th>
                  <th>Assigned</th>
                  <th>Status</th>
                  <th>Received</th>
                </tr>
              )}
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr
                  key={c.call_id}
                  className={c.call_id === selectedCallId ? "selected" : ""}
                  onClick={() => onSelect(c.call_id)}
                >
                  <td className="case-number">{c.case_number || "—"}</td>

                  {categoryMode ? (
                    <td>
                      {c.case_subcategory
                        ? SUBCATEGORY_LABELS[c.case_subcategory] || c.case_subcategory
                        : "—"}
                    </td>
                  ) : (
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
                  )}

                  <td>
                    <div className="caller-name">{c.caller_name || "Unknown"}</div>
                    <div className="caller-phone">
                      {c.callback_phone || c.from_number || "—"}
                      {c.callback_phone && c.is_phone_valid === 0 && (
                        <span className="flag" title="This phone number doesn't look valid">⚠</span>
                      )}
                    </div>
                  </td>

                  {categoryMode ? (
                    <>
                      <td className="nowrap">{c.assigned_to || "—"}</td>
                      <td className="nowrap">{c.next_hearing_date || "—"}</td>
                    </>
                  ) : (
                    <>
                      <td className="summary-cell">{c.case_summary || "—"}</td>
                      <td className="nowrap">{c.assigned_to || "—"}</td>
                    </>
                  )}

                  <td>
                    <span className={`pill status-${c.status}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                  </td>

                  {!categoryMode && <td className="nowrap">{timeAgo(c.created_at)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
