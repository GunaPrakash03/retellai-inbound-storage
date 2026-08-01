import { useCallback, useEffect, useState } from "react";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import CategoryOverview from "./components/CategoryOverview";
import MessagesView from "./components/MessagesView";
import Sidebar from "./components/Sidebar";
import StaffView from "./components/StaffView";
import { getCategoryCounts, getCounts, getTaxonomy, listRecords } from "./api";
import { BUCKETS, CATEGORY_LABELS, FIRM_NAME, VIEWS } from "./constants";

const CASES_BUCKET = "cases";

export default function App() {
  const [bucket, setBucket] = useState(BUCKETS[0].key);
  const [view, setView] = useState(null); // null = showing a call bucket
  const [cases, setCases] = useState([]);
  const [counts, setCounts] = useState(null);
  const [categoryCounts, setCategoryCounts] = useState(null);
  const [taxonomy, setTaxonomy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  // Which practice area is open within the Cases section. null = the
  // category overview (the home page); a value = that category's case list.
  const [caseCategory, setCaseCategory] = useState(null);
  const [subcategoryFilter, setSubcategoryFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");

  // On the Cases home page: no category picked yet, so show the overview.
  const onCategoryHome = bucket === CASES_BUCKET && view === null && caseCategory === null;

  const refreshCounts = useCallback(() => {
    getCounts().then(setCounts).catch(() => {});
  }, []);

  // The finer taxonomy (case types + subtypes) rarely changes — fetch once.
  useEffect(() => {
    getTaxonomy().then(setTaxonomy).catch(() => setTaxonomy(null));
  }, []);

  const refresh = useCallback(() => {
    refreshCounts();
    if (view !== null) return;

    if (onCategoryHome) {
      getCategoryCounts().then(setCategoryCounts).catch(() => {});
      return;
    }

    setLoading(true);
    // In the Cases section we fetch the whole practice area and filter it in
    // the browser, so the matter-type and attorney dropdowns can offer only
    // values that actually occur — and those options don't collapse when a
    // filter is applied. Other buckets filter server-side as before.
    const filters =
      bucket === CASES_BUCKET
        ? { category: caseCategory, limit: 500 }
        : { category: categoryFilter, status: statusFilter };
    listRecords(bucket, filters)
      .then((data) => {
        setCases(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [bucket, view, onCategoryHome, caseCategory, categoryFilter, statusFilter, refreshCounts]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  function selectBucket(key) {
    setBucket(key);
    setView(null);
    setSelectedCallId(null);
    setCaseCategory(null);
    setCategoryFilter("");
    setSubcategoryFilter("");
    setStatusFilter("");
    setAssignedFilter("");
  }

  function selectView(nextView) {
    setView(nextView);
    setSelectedCallId(null);
  }

  function openCategory(category) {
    setCaseCategory(category);
    setSelectedCallId(null);
    setSubcategoryFilter("");
    setAssignedFilter("");
    setStatusFilter("");
  }

  function backToCategories() {
    setCaseCategory(null);
    setSelectedCallId(null);
  }

  const activeBucket = BUCKETS.find((b) => b.key === bucket);
  const isCasesSection = bucket === CASES_BUCKET;

  // Flat subtype slug -> label, derived from the fetched taxonomy, for display.
  const subtypeLabels = {};
  for (const area of Object.values(taxonomy || {})) {
    for (const subs of Object.values(area.subtypes || {})) {
      for (const s of subs) subtypeLabels[s.value] = s.label;
    }
  }

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
          ) : onCategoryHome ? (
            <CategoryOverview
              counts={categoryCounts}
              loading={categoryCounts === null}
              onSelect={openCategory}
            />
          ) : (
            <div className="bucket-view">
              <div className="bucket-intro">
                {isCasesSection ? (
                  <>
                    <button className="category-back" onClick={backToCategories}>
                      ← All practice areas
                    </button>
                    <h2>{CATEGORY_LABELS[caseCategory] || "Cases"}</h2>
                    <p className="panel-note">Completed intakes in this practice area</p>
                  </>
                ) : (
                  <>
                    <h2>{activeBucket?.label}</h2>
                    <p className="panel-note">{activeBucket?.description}</p>
                  </>
                )}
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
                  categoryMode={isCasesSection}
                  activeCategory={caseCategory}
                  subcategoryFilter={subcategoryFilter}
                  assignedFilter={assignedFilter}
                  onSubcategoryChange={setSubcategoryFilter}
                  onAssignedChange={setAssignedFilter}
                  subtypeLabels={subtypeLabels}
                />
                <CaseDetail
                  bucket={bucket}
                  callId={selectedCallId}
                  onChanged={refresh}
                  taxonomy={taxonomy}
                  subtypeLabels={subtypeLabels}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
