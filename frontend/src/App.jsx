import { useCallback, useEffect, useState } from "react";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import { listCases } from "./api";

export default function App() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const refresh = useCallback(() => {
    setLoading(true);
    listCases({ category: categoryFilter, status: statusFilter })
      .then((data) => {
        setCases(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [categoryFilter, statusFilter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Case Intake</h1>
        <span className="subtitle">Calls captured by the Retell voice agent</span>
      </header>

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
        <CaseDetail callId={selectedCallId} onStatusChanged={refresh} />
      </div>
    </div>
  );
}
