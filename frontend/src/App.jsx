import { useCallback, useEffect, useState } from "react";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import { listRecords } from "./api";
import { BUCKETS } from "./constants";

export default function App() {
  const [bucket, setBucket] = useState(BUCKETS[0].key);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const refresh = useCallback(() => {
    setLoading(true);
    listRecords(bucket, { category: categoryFilter, status: statusFilter })
      .then((data) => {
        setCases(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [bucket, categoryFilter, statusFilter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  function handleBucketChange(key) {
    setBucket(key);
    setSelectedCallId(null);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Case Intake</h1>
        <span className="subtitle">Calls captured by the Retell voice agent</span>
      </header>

      <nav className="bucket-nav">
        {BUCKETS.map((b) => (
          <button
            key={b.key}
            className={b.key === bucket ? "active" : ""}
            title={b.description}
            onClick={() => handleBucketChange(b.key)}
          >
            {b.label}
          </button>
        ))}
      </nav>

      {error && <div className="error-banner">Couldn't reach the backend: {error}</div>}

      <div className="app-body">
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
        <CaseDetail bucket={bucket} callId={selectedCallId} onStatusChanged={refresh} />
      </div>
    </div>
  );
}
