import AppShell from '../components/AppShell';

function UsagePage() {
  return <AppShell title="Water usage" eyebrow="Usage" active="usage"><section className="content-card empty-feature"><h2>Water usage is being prepared</h2><p>Usage details will be connected when the single-house Water Bill API is available.</p></section></AppShell>;
}
export default UsagePage;
