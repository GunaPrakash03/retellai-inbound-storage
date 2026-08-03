import { NavLink, useLocation } from "react-router-dom";
import { BUCKETS } from "../constants";

// A real link, so the browser's own affordances work — middle-click to open a
// bucket in a new tab, copy link address, back and forward.
//
// `forceActive` exists for Cases alone: it lives at "/" but also owns every
// /cases/... path, and NavLink can express only one of those. Left to its own
// matching, `to="/"` without `end` counts as active on every route in the app.
function NavItem({ to, end, label, description, count, urgent, forceActive }) {
  const showCount = typeof count === "number";
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `nav-item${forceActive ?? isActive ? " active" : ""}${
          urgent && count > 0 ? " urgent" : ""
        }`
      }
      title={description}
    >
      <span className="nav-label">{label}</span>
      {showCount && <span className="nav-count">{count}</span>}
    </NavLink>
  );
}

export default function Sidebar({ counts }) {
  const { pathname } = useLocation();
  const onCases = pathname === "/" || pathname.startsWith("/cases");

  return (
    <nav className="sidebar">
      <div className="nav-group">
        <h2 className="nav-heading">Calls</h2>
        {BUCKETS.map((b) => (
          <NavItem
            key={b.key}
            to={b.key === "cases" ? "/" : `/${b.key}`}
            end={b.key !== "cases"}
            forceActive={b.key === "cases" ? onCases : undefined}
            label={b.label}
            description={b.description}
            count={counts?.[b.table]}
            urgent={b.urgent}
          />
        ))}
      </div>

      <div className="nav-group">
        <h2 className="nav-heading">Office</h2>
        <NavItem
          to="/hearings"
          label="Court Calendar"
          description="Cases with an upcoming hearing date"
        />
        <NavItem
          to="/messages"
          label="Messages"
          description="Callback messages taken when a transfer didn't connect"
          count={counts?.messages_undelivered}
          urgent
        />
        <NavItem
          to="/staff"
          label="Staff Directory"
          description="Who calls can be transferred to"
        />
      </div>
    </nav>
  );
}
