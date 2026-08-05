import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { getCounts, getTaxonomy } from "./api";
import { FIRM_NAME } from "./constants";

// The app shell: masthead, sidebar, and whichever page the URL resolves to.
// Counts and the taxonomy live here rather than in each page — both are used
// by several pages and neither changes often, so fetching them per page would
// mean the same request three times on one navigation.
export default function Layout() {
  const [counts, setCounts] = useState(null);
  const [taxonomy, setTaxonomy] = useState(null);

  const refreshCounts = useCallback(() => {
    getCounts().then(setCounts).catch(() => {});
  }, []);

  useEffect(() => {
    getTaxonomy().then(setTaxonomy).catch(() => setTaxonomy(null));
  }, []);

  useEffect(() => {
    refreshCounts();
    const interval = setInterval(refreshCounts, 15000);
    return () => clearInterval(interval);
  }, [refreshCounts]);

  return (
    <div className="app">
      <header className="app-header">
        <span className="firm-mark" aria-hidden="true">§</span>
        <div className="firm-identity">
          <span className="firm-name">{FIRM_NAME}</span>
          <span className="app-title">Case Intake</span>
        </div>
        <span className="subtitle">Calls captured by the intake line</span>
      </header>

      <div className="app-body">
        <Sidebar counts={counts} />
        <main className="workspace">
          <Outlet context={{ counts, taxonomy, refreshCounts }} />
        </main>
      </div>
    </div>
  );
}
