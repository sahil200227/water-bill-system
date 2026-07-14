import { useEffect, useMemo, useState } from 'react';
import AppShell from '../components/AppShell';
import { getAllWaterBills } from '../services/waterBillService';

type WaterBill = {
  id?: string;
  _id?: string;
  customerName?: string;
  accountNumber?: string;
  billingDate?: string;
  previousReading?: number;
  currentReading?: number;
  waterCharge?: number;
};

const numeric = (value: unknown) => Number(value) || 0;
const usedWater = (bill: WaterBill) => Math.max(numeric(bill.currentReading) - numeric(bill.previousReading), 0);
const billAmount = (bill: WaterBill) => usedWater(bill) * numeric(bill.waterCharge);
const number = (value: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value);
const currency = (value: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value);
const date = (value?: string) => value ? new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

function UsagePage() {
  const [bills, setBills] = useState<WaterBill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadBills = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getAllWaterBills();
      setBills(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load water usage records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadBills(); }, []);

  const totals = useMemo(() => bills.reduce((summary, bill) => ({
    previous: summary.previous + numeric(bill.previousReading),
    current: summary.current + numeric(bill.currentReading),
    used: summary.used + usedWater(bill),
    amount: summary.amount + billAmount(bill),
  }), { previous: 0, current: 0, used: 0, amount: 0 }), [bills]);

  const actions = <button className="secondary-button usage-refresh" type="button" onClick={loadBills} disabled={loading}>{loading ? 'Loading…' : 'Refresh data'}</button>;

  return <AppShell title="Water usage" eyebrow="Usage" active="usage" actions={actions}>
    <section className="usage-intro"><div><h2>Actual water usage</h2><p>Calculated automatically from the saved previous and current meter readings.</p></div><span>{bills.length} record{bills.length === 1 ? '' : 's'}</span></section>
    {loading ? <div className="loading-state">Loading water usage…</div> : error ? <div className="empty-state">Unable to load usage: {error}</div> : <>
      <section className="usage-grid" aria-label="Water usage totals">
        <article className="usage-card"><h2>Previous readings</h2><p className="usage-value">{number(totals.previous)}<span>units</span></p><small>Total of saved starting meter readings</small></article>
        <article className="usage-card"><h2>Current readings</h2><p className="usage-value">{number(totals.current)}<span>units</span></p><small>Total of saved ending meter readings</small></article>
        <article className="usage-card highlight"><h2>Total water used</h2><p className="usage-value">{number(totals.used)}<span>units</span></p><small>Current reading − previous reading</small></article>
        <article className="usage-card"><h2>Total water charge</h2><p className="usage-value amount">{currency(totals.amount)}</p><small>Water used × charge per unit</small></article>
      </section>
      <section className="content-card usage-detail-card">
        <div className="list-heading"><div><h2>Usage by bill record</h2><p>Every value below is calculated from the readings entered for that bill.</p></div></div>
        {bills.length === 0 ? <div className="empty-state">No water bill records yet. Save a bill to see its usage here.</div> : <div className="table-wrap"><table className="bills-table usage-table"><thead><tr><th>Customer</th><th>Billing date</th><th>Previous reading</th><th>Current reading</th><th>Water used</th><th>Charge / unit</th><th>Calculated amount</th></tr></thead><tbody>{bills.map((bill, index) => <tr key={bill._id || bill.id || index}><td>{bill.customerName || '—'}<small className="account-number">{bill.accountNumber || ''}</small></td><td>{date(bill.billingDate)}</td><td>{number(numeric(bill.previousReading))}</td><td>{number(numeric(bill.currentReading))}</td><td className="water-used">{number(usedWater(bill))} units</td><td>{currency(numeric(bill.waterCharge))}</td><td>{currency(billAmount(bill))}</td></tr>)}</tbody></table></div>}
      </section>
    </>}
  </AppShell>;
}

export default UsagePage;
