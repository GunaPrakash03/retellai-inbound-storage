import { BUCKETS, VIEWS } from "../constants";

function NavButton({ active, label, description, count, urgent, onClick }) {
  const showCount = typeof count === "number";
  return (
    <button
      className={`nav-item${active ? " active" : ""}${urgent && count > 0 ? " urgent" : ""}`}
      title={description}
      onClick={onClick}
    >
      <span className="nav-label">{label}</span>
      {showCount && <span className="nav-count">{count}</span>}
    </button>
  );
}

export default function Sidebar({ bucket, view, counts, onSelectBucket, onSelectView }) {
  return (
    <nav className="sidebar">
      <div className="nav-group">
        <h2 className="nav-heading">Calls</h2>
        {BUCKETS.map((b) => (
          <NavButton
            key={b.key}
            active={view === null && bucket === b.key}
            label={b.label}
            description={b.description}
            count={counts?.[b.table]}
            urgent={b.urgent}
            onClick={() => onSelectBucket(b.key)}
          />
        ))}
      </div>

      <div className="nav-group">
        <h2 className="nav-heading">Office</h2>
        <NavButton
          active={view === VIEWS.MESSAGES}
          label="Messages"
          description="Callback messages taken when a transfer didn't connect"
          count={counts?.messages_undelivered}
          urgent
          onClick={() => onSelectView(VIEWS.MESSAGES)}
        />
        <NavButton
          active={view === VIEWS.STAFF}
          label="Staff Directory"
          description="Who calls can be transferred to"
          onClick={() => onSelectView(VIEWS.STAFF)}
        />
      </div>
    </nav>
  );
}
