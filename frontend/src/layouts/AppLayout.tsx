import {
  Files,
  GitCompareArrows,
  LayoutDashboard,
  Menu,
  ScanSearch,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { label: "Overview", to: "/", icon: LayoutDashboard, end: true },
  { label: "Documents", to: "/documents", icon: Files },
  { label: "Facts", to: "/facts", icon: ScanSearch },
  { label: "Relationships", to: "/relationships", icon: GitCompareArrows },
];

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className={`sidebar${menuOpen ? " sidebar--open" : ""}`}>
        <div className="brand">
          <div className="brand__mark" aria-hidden="true">
            F
          </div>
          <div>
            <strong>Fact-O-Check</strong>
            <span>Evidence intelligence</span>
          </div>
          <button
            className="icon-button sidebar__close"
            type="button"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="nav" aria-label="Primary navigation">
          <span className="nav__label">Workspace</span>
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => `nav__link${isActive ? " nav__link--active" : ""}`}
            >
              <Icon size={18} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <span className="phase-pill">Phase 4</span>
          <p>Cross-document fact reasoning</p>
        </div>
      </aside>

      {menuOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <div className="main-column">
        <header className="mobile-header">
          <button
            className="icon-button"
            type="button"
            aria-label="Open navigation"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={20} />
          </button>
          <strong>Fact-O-Check</strong>
          <span />
        </header>
        <main className="main-content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
