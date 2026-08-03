import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import HearingTable from "../components/HearingTable";
import { getCategoryCounts, getHearings } from "../api";
import { CATEGORIES, categoryToSlug } from "../constants";
import { daysUntil, formatHearingDate } from "../format";

// The home page. Practice areas first — that's how the firm thinks about its
// work — then the court calendar underneath, since a hearing date is a
// deadline rather than a place to start browsing.
export default function HomePage() {
  const { counts } = useOutletContext();
  const [categoryCounts, setCategoryCounts] = useState(null);
  const [hearings, setHearings] = useState([]);
  const [loadingHearings, setLoadingHearings] = useState(true);

  useEffect(() => {
    getCategoryCounts().then(setCategoryCounts).catch(() => setCategoryCounts({}));
  }, []);

  useEffect(() => {
    getHearings({ limit: 25 })
      .then(setHearings)
      .catch(() => setHearings([]))
      .finally(() => setLoadingHearings(false));
  }, []);

  const total = Object.values(categoryCounts || {}).reduce((a, b) => a + b, 0);
  const today = hearings.filter((h) => daysUntil(h.next_hearing_date) === 0);
  const overdue = hearings.filter((h) => {
    const n = daysUntil(h.next_hearing_date);
    return n !== null && n < 0;
  });
  const next = hearings.find((h) => (daysUntil(h.next_hearing_date) ?? -1) >= 0);

  return (
    <div className="page-view">
      <div className="page-head">
        <div>
          <h2>Today at a glance</h2>
          <p className="panel-note">Calls captured by the intake line</p>
        </div>
      </div>

      <div className="stat-row">
        <div className={`stat${counts?.emergency_flags ? " alarm" : ""}`}>
          <span className="stat-key">Review first</span>
          <span className="stat-value">{counts?.emergency_flags ?? "—"}</span>
          <span className="stat-meta">Emergency branch fired</span>
        </div>
        <div className={`stat${today.length || overdue.length ? " alarm" : ""}`}>
          <span className="stat-key">Next hearing</span>
          <span className="stat-value">
            {next ? formatHearingDate(next.next_hearing_date).replace(/ \d{4}$/, "") : "—"}
          </span>
          <span className="stat-meta">
            {next
              ? `${next.caller_name || "Unnamed"} · ${
                  daysUntil(next.next_hearing_date) === 0
                    ? "today"
                    : `in ${daysUntil(next.next_hearing_date)} days`
                }`
              : "None scheduled"}
          </span>
        </div>
        <div className="stat">
          <span className="stat-key">Total cases</span>
          <span className="stat-value">{counts?.cases ?? "—"}</span>
          <span className="stat-meta">Completed intakes</span>
        </div>
        <div className="stat">
          <span className="stat-key">Incomplete intake</span>
          <span className="stat-value">{counts?.partial_calls ?? "—"}</span>
          <span className="stat-meta">Dropped before finishing</span>
        </div>
      </div>

      <h3 className="section-head">Practice areas</h3>
      <p className="panel-note">
        {categoryCounts === null
          ? "Loading…"
          : `${total} case${total === 1 ? "" : "s"} across ${CATEGORIES.length} practice areas`}
      </p>
      <ul className="category-grid">
        {CATEGORIES.map((c) => {
          const n = (categoryCounts && categoryCounts[c.value]) || 0;
          return (
            <li key={c.value}>
              <Link
                className={`category-card${n === 0 ? " empty" : ""}`}
                to={`/cases/${categoryToSlug(c.value)}`}
              >
                <span className="category-name">{c.label}</span>
                <span className={`category-count${n === 0 ? " zero" : ""}`}>{n}</span>
                <span className="category-meta">
                  {n === 0 ? "No cases yet" : `${n} case${n === 1 ? "" : "s"}`}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>

      <h3 className="section-head">
        Court calendar
        <Link className="section-link" to="/hearings">
          View all
        </Link>
      </h3>

      {/* Said plainly rather than hidden: a section that disappears when empty
          reads as "nothing to worry about", which is not the same as "checked,
          and there is nothing today". */}
      <div className={`today-strip${today.length ? " has" : ""}`}>
        <span className="today-label">
          Today · {formatHearingDate(new Date().toISOString().slice(0, 10))}
        </span>
        <span>
          {today.length
            ? `${today.length} hearing${today.length === 1 ? "" : "s"} scheduled`
            : "No hearings scheduled"}
        </span>
      </div>

      {overdue.length > 0 && (
        <div className="today-strip has">
          <span className="today-label">Past due</span>
          <span>
            {overdue.length} hearing{overdue.length === 1 ? "" : "s"} with no update since the date
            passed
          </span>
        </div>
      )}

      <HearingTable
        hearings={hearings}
        loading={loadingHearings}
        emptyText="No cases have a hearing date on file."
      />
    </div>
  );
}
