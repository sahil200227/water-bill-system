import { useEffect, useMemo, useState } from 'react';
import AppShell from '../components/AppShell';
import { getAllWaterBills, recordWaterBillPayment } from '../services/waterBillService';

type Payment = { amount?: number; method?: string; reference?: string; paidAt?: string };
type WaterBill = { id?: string; _id?: string; customerName?: string; accountNumber?: string; totalAmount?: number; dueDate?: string; payments?: Payment[] };

const value = (input: unknown) => Number(input) || 0;
const paid = (bill: WaterBill) => (bill.payments ?? []).reduce((sum, payment) => sum + value(payment.amount), 0);
const balance = (bill: WaterBill) => Math.max(value(bill.totalAmount) - paid(bill), 0);
const money = (amount: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(amount);
const paymentStatus = (bill: WaterBill) => balance(bill) === 0 ? 'Paid' : paid(bill) > 0 ? 'Partially paid' : new Date(bill.dueDate || '2999-01-01') < new Date() ? 'Overdue' : 'Pending';

function PaymentsPage() {
  const [bills, setBills] = useState<WaterBill[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('Cash');
  const [reference, setReference] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const loadBills = async () => {
    try {
      setLoading(true);
      const data = await getAllWaterBills();
      const records = Array.isArray(data) ? data : [];
      setBills(records);
      setSelectedId((current) => current || String(records[0]?._id || records[0]?.id || ''));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load water bills.');
    } finally { setLoading(false); }
  };

  useEffect(() => { void loadBills(); }, []);
  const selectedBill = bills.find((bill) => String(bill._id || bill.id) === selectedId);
  const totals = useMemo(() => bills.reduce((summary, bill) => ({ billed: summary.billed + value(bill.totalAmount), paid: summary.paid + paid(bill), remaining: summary.remaining + balance(bill) }), { billed: 0, paid: 0, remaining: 0 }), [bills]);

  const submitPayment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedBill || !selectedId) return;
    try {
      setSaving(true);
      setMessage('');
      const updated = await recordWaterBillPayment(selectedId, { amount: value(amount), method, reference });
      setBills((current) => current.map((bill) => String(bill._id || bill.id) === selectedId ? updated : bill));
      setAmount('');
      setReference('');
      setMessage('Payment recorded successfully.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to record payment.');
    } finally { setSaving(false); }
  };

  return <AppShell title="Payments" eyebrow="Collections" active="payments">
    <section className="payment-summary">
      <article><span>Total billed</span><strong>{money(totals.billed)}</strong></article><article><span>Collected</span><strong>{money(totals.paid)}</strong></article><article><span>Remaining balance</span><strong>{money(totals.remaining)}</strong></article>
    </section>
    <section className="payment-layout">
      <form className="content-card payment-form" onSubmit={submitPayment}><div className="card-heading"><div><h2>Record payment</h2><p>Apply a full or partial payment to a water bill.</p></div></div>
        <label htmlFor="payment-bill">Water bill</label><select id="payment-bill" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={loading || bills.length === 0}>{bills.map((bill, index) => <option key={bill._id || bill.id || index} value={String(bill._id || bill.id)}>{bill.customerName || 'Unnamed customer'} — {bill.accountNumber || 'No account'} ({money(balance(bill))} due)</option>)}</select>
        {selectedBill && <div className="selected-bill-balance"><span>Bill amount <strong>{money(value(selectedBill.totalAmount))}</strong></span><span>Already paid <strong>{money(paid(selectedBill))}</strong></span><span>Remaining balance <strong>{money(balance(selectedBill))}</strong></span></div>}
        <label htmlFor="payment-amount">Payment amount</label><input id="payment-amount" type="number" min="0.01" max={selectedBill ? balance(selectedBill) : undefined} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required disabled={!selectedBill} />
        <label htmlFor="payment-method">Payment method</label><select id="payment-method" value={method} onChange={(event) => setMethod(event.target.value)}><option>Cash</option><option>UPI</option><option>Bank transfer</option><option>Card</option></select>
        <label htmlFor="payment-reference">Reference number <small>(optional)</small></label><input id="payment-reference" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Transaction or receipt number" />
        <button className="primary-button" type="submit" disabled={saving || !selectedBill || balance(selectedBill) === 0}>{saving ? 'Recording…' : 'Record payment'}</button>{message && <p className="payment-message">{message}</p>}
      </form>
      <section className="content-card payment-status-card"><div className="card-heading"><div><h2>Payment status</h2><p>Balances update automatically when a payment is recorded.</p></div></div>
        {loading ? <div className="loading-state">Loading payment status…</div> : <div className="table-wrap"><table className="bills-table payment-table"><thead><tr><th>Customer</th><th>Bill amount</th><th>Paid</th><th>Remaining</th><th>Status</th></tr></thead><tbody>{bills.map((bill, index) => <tr key={bill._id || bill.id || index}><td>{bill.customerName || '—'}<small className="account-number">{bill.accountNumber || ''}</small></td><td>{money(value(bill.totalAmount))}</td><td>{money(paid(bill))}</td><td>{money(balance(bill))}</td><td><span className={`payment-status ${paymentStatus(bill).toLowerCase().replace(' ', '-')}`}>{paymentStatus(bill)}</span></td></tr>)}</tbody></table>{bills.length === 0 && <div className="empty-state">No water bills are available for payment.</div>}</div>}
      </section>
    </section>
  </AppShell>;
}

export default PaymentsPage;
