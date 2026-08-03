import { useEffect, useState } from "react";
import HearingTable from "../components/HearingTable";
import { getHearings } from "../api";

// The full court calendar. Unlike the home page panel this can show hearings
// that have already happened — a past date with no status update is the thing
// most worth chasing, and hiding it is how it gets missed.
export default function HearingsPage() {
  const [hearings, setHearings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showPast, setShowPast] = useState(false);

  useEffect(() => {
    setLoading(true);
    getHearings({ limit: 200, upcomingOnly: !showPast })
      .then(setHearings)
      .catch(() => setHearings([]))
      .finally(() => setLoading(false));
  }, [showPast]);

  return (
    <div className="page-view">
      <div className="page-head">
        <div>
          <h2>Court calendar</h2>
          <p className="panel-note">Cases with a hearing date, soonest first</p>
        </div>
        <div className="page-head-actions">
          <label className="toggle">
            <input
              type="checkbox"
              checked={showPast}
              onChange={(e) => setShowPast(e.target.checked)}
            />
            Include past hearings
          </label>
        </div>
      </div>

      <HearingTable
        hearings={hearings}
        loading={loading}
        emptyText={
          showPast
            ? "No cases have a hearing date on file."
            : "No upcoming hearings. Tick “Include past hearings” to see earlier dates."
        }
      />
    </div>
  );
}
