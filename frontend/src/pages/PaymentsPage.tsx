import AppShell from '../components/AppShell';

function PaymentsPage() {
  return <AppShell title="Payments" eyebrow="Payments" active="payments"><section className="content-card empty-feature"><h2>Payments are being prepared</h2><p>Payment information will be shown once the Electricity and Water Bill APIs are connected.</p></section></AppShell>;
}
export default PaymentsPage;
