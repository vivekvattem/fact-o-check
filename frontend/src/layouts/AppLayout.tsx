import {
  Files,
  GitCompareArrows,
  LayoutDashboard,
  Menu,
  ScanSearch,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

const navigation = [
  { label: "Overview", to: "/overview", icon: LayoutDashboard, end: true },
  { label: "Documents", to: "/documents", icon: Files },
  { label: "Facts", to: "/facts", icon: ScanSearch },
  { label: "Relationships", to: "/relationships", icon: GitCompareArrows },
];

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    closeButton.current?.focus();
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") { setMenuOpen(false); menuButton.current?.focus(); }
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [menuOpen]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside id="workspace-navigation" className={`sidebar${menuOpen ? " sidebar--open" : ""}`}>
        <div className="brand">
          <Link className="brand__home" to="/" onClick={() => setMenuOpen(false)}>
            <div className="brand__mark" aria-hidden="true">
              F
            </div>
            <div>
              <strong>Fact-O-Check</strong>
              <span>Evidence intelligence</span>
            </div>
          </Link>
          <button
            className="icon-button sidebar__close"
            ref={closeButton}
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
          <span className="phase-pill">Evidence workspace</span>
          <p>Facts, grounded in evidence.</p>
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
            ref={menuButton}
            aria-expanded={menuOpen}
            aria-controls="workspace-navigation"
            type="button"
            aria-label="Open navigation"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={20} />
          </button>
          <Link className="mobile-brand" to="/">Fact-O-Check</Link>
          <span />
        </header>
        <main className="main-content" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
