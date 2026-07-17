import type { ReactNode } from 'react';

type AppShellProps = {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  actions?: ReactNode;
  active?: 'overview' | 'bills' | 'usage' | 'payments';
};

const Icon = ({ name }: { name: string }) => <span className="nav-icon" aria-hidden="true">{name}</span>;

function AppShell({ title, eyebrow, children, actions, active = 'overview' }: AppShellProps) {
  const go = (path: string) => {
    window.history.pushState({}, '', path);
    window.dispatchEvent(new Event('popstate'));
  };

  return <div className="app-frame">
    <aside className="sidebar">
      <nav className="side-nav" aria-label="Main navigation">
        <button className={active === 'overview' ? 'active' : ''} onClick={() => go('/')}><Icon name="▦" />Dashboard</button>
        <button className={active === 'bills' ? 'active' : ''} onClick={() => go('/bills')}><Icon name="▤" />Bills</button>
      </nav>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1></div>
        <div className="top-actions">{actions ?? <label className="dashboard-search">⌕ <input placeholder="Search bills" aria-label="Search bills" /></label>}</div>
      </header>
      <div className="page-content">{children}</div>
    </main>
  </div>;
}

export default AppShell;
