import { useCallback, useEffect, useState } from "react";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import MessagesView from "./components/MessagesView";
import Sidebar from "./components/Sidebar";
import StaffView from "./components/StaffView";
import { getCounts, listRecords } from "./api";
import { BUCKETS, FIRM_NAME, VIEWS } from "./constants";

export default function App() {
  const [bucket, setBucket] = useState(BUCKETS[0].key);
  const [view, setView] = useState(null); // null = showing a call bucket
  const [cases, setCases] = useState([]);
  const [counts, setCounts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const refreshCounts = useCallback(() => {
    getCounts().then(setCounts).catch(() => {});
  }, []);

  const refresh = useCallback(() => {
    refreshCounts();
    if (view !== null) return;
    setLoading(true);
    listRecords(bucket, { category: categoryFilter, status: statusFilter })
      .then((data) => {
        setCases(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [bucket, view, categoryFilter, statusFilter, refreshCounts]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  function selectBucket(key) {
    setBucket(key);
    setView(null);
    setSelectedCallId(null);
  }

  function selectView(nextView) {
    setView(nextView);
    setSelectedCallId(null);
  }

  const activeBucket = BUCKETS.find((b) => b.key === bucket);

  return (
    <div className="app">
      <header className="app-header">
        <span className="firm-mark" aria-hidden="true">⚖</span>
        <div className="firm-identity">
          <span className="firm-name">{FIRM_NAME}</span>
          <span className="app-title">Case Intake</span>
        </div>
        <span className="subtitle">Calls captured by the intake line</span>
      </header>

      <div className="app-body">
        <Sidebar
          bucket={bucket}
          view={view}
          counts={counts}
          onSelectBucket={selectBucket}
          onSelectView={selectView}
        />

        <main className="workspace">
          {error && <div className="error-banner">Couldn't reach the backend: {error}</div>}

          {view === VIEWS.MESSAGES ? (
            <MessagesView onChanged={refreshCounts} />
          ) : view === VIEWS.STAFF ? (
            <StaffView />
          ) : (
            <div className="bucket-view">
              <div className="bucket-intro">
                <h2>{activeBucket?.label}</h2>
                <p className="panel-note">{activeBucket?.description}</p>
              </div>
              <div className="split">
                <CaseList
                  cases={cases}
                  loading={loading}
                  selectedCallId={selectedCallId}
                  onSelect={setSelectedCallId}
                  categoryFilter={categoryFilter}
                  statusFilter={statusFilter}
                  onCategoryChange={setCategoryFilter}
                  onStatusChange={setStatusFilter}
                />
                <CaseDetail bucket={bucket} callId={selectedCallId} onChanged={refresh} />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
