import { CATEGORIES } from "../constants";

// The home page: the firm's practice areas as a list. Each row shows how
// many completed cases sit under it; clicking one drills into that
// category's case list. Every category is shown, even at zero, so the full
// set of practice areas is always visible.
export default function CategoryOverview({ counts, loading, onSelect }) {
  const total = Object.values(counts || {}).reduce((a, b) => a + b, 0);

  return (
    <div className="category-overview">
      <div className="bucket-intro">
        <h2>Cases by practice area</h2>
        <p className="panel-note">
          {loading ? "Loading…" : `${total} case${total === 1 ? "" : "s"} across ${CATEGORIES.length} practice areas`}
        </p>
      </div>

      <ul className="category-grid">
        {CATEGORIES.map((c) => {
          const n = (counts && counts[c.value]) || 0;
          return (
            <li key={c.value}>
              <button
                className="category-card"
                onClick={() => onSelect(c.value)}
                disabled={loading}
              >
                <span className={`category-swatch cat-${c.value}`} aria-hidden="true" />
                <span className="category-name">{c.label}</span>
                <span className={`category-count${n === 0 ? " zero" : ""}`}>{n}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
