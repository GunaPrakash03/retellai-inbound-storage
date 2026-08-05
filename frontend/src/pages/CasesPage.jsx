import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import CaseList from "../components/CaseList";
import CaseDetail from "../components/CaseDetail";
import { listRecords } from "../api";
import { CATEGORY_LABELS, categoryToSlug, slugToCategory } from "../constants";

// /cases, /cases/:area and /cases/:area/:callId all render here. The selected
// case comes from the URL rather than local state, which is what makes a case
// linkable — and what makes Back step through cases instead of leaving the app.
export default function CasesPage() {
  const { area, callId } = useParams();
  const navigate = useNavigate();
  const { taxonomy, refreshCounts } = useOutletContext();

  const category = area ? slugToCategory(area) : null;
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [subcategoryFilter, setSubcategoryFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Filters describe the list you are looking at, so switching practice area
  // has to clear them — otherwise an empty result looks like "no cases here"
  // when it really means "no cases matching a filter you can't see".
  useEffect(() => {
    setSubcategoryFilter("");
    setAssignedFilter("");
    setStatusFilter("");
  }, [area]);

  const refresh = useCallback(() => {
    setLoading(true);
    // Fetch the whole practice area and filter in the browser, so the matter
    // type and attorney dropdowns offer only values that actually occur.
    listRecords("cases", { category, limit: 500 })
      .then((data) => {
        setCases(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  const selectCase = (id) => {
    const base = `/cases/${area || categoryToSlug(cases.find((c) => c.call_id === id)?.case_category)}`;
    navigate(id ? `${base}/${encodeURIComponent(id)}` : base);
  };

  const onChanged = () => {
    refresh();
    refreshCounts();
  };

  return (
    <div className="page-view">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span aria-hidden="true">/</span>
        {area ? (
          <>
            <Link to="/cases">Cases</Link>
            <span aria-hidden="true">/</span>
            <span>{CATEGORY_LABELS[category] || category}</span>
          </>
        ) : (
          <span>Cases</span>
        )}
      </nav>

      <div className="page-head">
        <div>
          <h2>{area ? CATEGORY_LABELS[category] || category : "All cases"}</h2>
          <p className="panel-note">
            {area ? "Completed intakes in this practice area" : "Every completed intake"}
          </p>
        </div>
      </div>

      {error && <div className="error-banner">Couldn't reach the backend: {error}</div>}

      <div className="split">
        <CaseList
          cases={cases}
          loading={loading}
          selectedCallId={callId || null}
          onSelect={selectCase}
          categoryFilter=""
          statusFilter={statusFilter}
          onCategoryChange={() => {}}
          onStatusChange={setStatusFilter}
          categoryMode
          activeCategory={category}
          subcategoryFilter={subcategoryFilter}
          assignedFilter={assignedFilter}
          onSubcategoryChange={setSubcategoryFilter}
          onAssignedChange={setAssignedFilter}
        />
        <CaseDetail
          bucket="cases"
          callId={callId || null}
          onChanged={onChanged}
          taxonomy={taxonomy}
        />
      </div>
    </div>
  );
}
