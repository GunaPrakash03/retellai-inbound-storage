import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useOutletContext, useParams } from "react-router-dom";
import CaseList from "../components/CaseList";
import CaseDetail from "../components/CaseDetail";
import { listRecords } from "../api";
import { BUCKETS } from "../constants";

// The non-case buckets: partial, emergency, spam, unwanted, out of scope.
// Unlike cases these aren't sorted by practice area, so they filter
// server-side by category and status as before.
export default function BucketPage() {
  const { bucket, callId } = useParams();
  const navigate = useNavigate();
  const { taxonomy, subtypeLabels, refreshCounts } = useOutletContext();

  const active = BUCKETS.find((b) => b.key === bucket);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    setCategoryFilter("");
    setStatusFilter("");
  }, [bucket]);

  const refresh = useCallback(() => {
    if (!active) return;
    setLoading(true);
    listRecords(bucket, { category: categoryFilter, status: statusFilter })
      .then((data) => {
        setRecords(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [active, bucket, categoryFilter, statusFilter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  // An unknown bucket is a mistyped URL, not an empty list — send it home
  // rather than rendering a page that looks like a bucket with no records.
  if (!active) return <Navigate to="/" replace />;

  const onChanged = () => {
    refresh();
    refreshCounts();
  };

  return (
    <div className="page-view">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span aria-hidden="true">/</span>
        <span>{active.label}</span>
      </nav>

      <div className="page-head">
        <div>
          <h2>{active.label}</h2>
          <p className="panel-note">{active.description}</p>
        </div>
      </div>

      {error && <div className="error-banner">Couldn't reach the backend: {error}</div>}

      <div className="split">
        <CaseList
          cases={records}
          loading={loading}
          selectedCallId={callId || null}
          onSelect={(id) =>
            navigate(id ? `/${bucket}/${encodeURIComponent(id)}` : `/${bucket}`)
          }
          categoryFilter={categoryFilter}
          statusFilter={statusFilter}
          onCategoryChange={setCategoryFilter}
          onStatusChange={setStatusFilter}
          categoryMode={false}
          activeCategory={null}
          subcategoryFilter=""
          assignedFilter=""
          onSubcategoryChange={() => {}}
          onAssignedChange={() => {}}
          subtypeLabels={subtypeLabels}
        />
        <CaseDetail
          bucket={bucket}
          callId={callId || null}
          onChanged={onChanged}
          taxonomy={taxonomy}
          subtypeLabels={subtypeLabels}
        />
      </div>
    </div>
  );
}
