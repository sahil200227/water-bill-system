import type { ReactNode } from 'react';

type AppShellProps = { title: string; eyebrow: string; children: ReactNode; actions?: ReactNode; active?: 'overview' | 'bills' | 'usage' | 'payments' };
const Icon = ({ children }: { children: ReactNode }) => <span className="nav-icon">{children}</span>;

function AppShell({ title, eyebrow, children, actions, active = 'overview' }: AppShellProps) {
  const go = (path: string) => { window.history.pushState({}, '', path); window.dispatchEvent(new Event('popstate')); };
  return <div className="app-frame"><aside className="sidebar">
    <button className="brand" onClick={() => go('/')} aria-label="WaterWorks home"><span className="brand-mark">W</span><span>WaterWorks</span></button>
    <nav className="side-nav" aria-label="Main navigation">
      <button className={active === 'overview' ? 'active' : ''} onClick={() => go('/')}><Icon>⌂</Icon>Overview</button>
      <button className={active === 'bills' ? 'active' : ''} onClick={() => go('/bills')}><Icon>▤</Icon>Bills</button>
      <button className={active === 'usage' ? 'active' : ''} onClick={() => go('/usage')}><Icon>◌</Icon>Usage</button>
      <button className={active === 'payments' ? 'active' : ''} onClick={() => go('/payments')}><Icon>◷</Icon>Payments</button>
    </nav>
    <div className="sidebar-footer"><span className="avatar">AD</span><span><strong>Administrator</strong><small>Water billing</small></span></div>
  </aside><main className="main-area"><header className="topbar"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div><div className="top-actions">{actions}</div></header><div className="page-content">{children}</div></main></div>;
}
export default AppShell;
