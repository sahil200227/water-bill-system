import ImportPanel from '../components/ImportPanel';
import WaterBillForm from '../components/WaterBillForm';
import AppShell from '../components/AppShell';

function OverviewPage() {
  return <AppShell title="Water billing overview" eyebrow="Dashboard" active="overview">
    <section className="summary-grid">
      <article className="metric-card"><span className="metric-icon blue">●</span><div><p>Bill entries</p><strong>Manage records</strong><small>Create and maintain water bills</small></div></article>
      <article className="metric-card"><span className="metric-icon mint">○</span><div><p>Meter readings</p><strong>Usage based</strong><small>Totals are calculated automatically</small></div></article>
      <article className="metric-card"><span className="metric-icon gold">₹</span><div><p>Quick import</p><strong>CSV or Excel</strong><small>Bring existing billing data in</small></div></article>
    </section>
    <section className="content-card bill-entry-card">
      <div className="card-heading"><div><h2>Create a water bill</h2><p>Add the customer, meter readings, and billing dates.</p></div><ImportPanel /></div>
      <WaterBillForm />
    </section>
  </AppShell>;
}

export default OverviewPage;
