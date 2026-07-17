import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import { formatMoney } from '../data/householdBills';
import { getOcrWaterBills } from '../services/waterBillService';

type OcrBill = {
  _id?: string;
  document_type?: string;
  provider?: { provider_name?: string };
  account_and_bill?: { bill_date?: string; due_date?: string };
  balance_details?: { amount_due?: string };
};

const CATEGORIES = ['All', 'Electricity', 'Water', 'Internet', 'Phone', 'Security', 'Pest control'];
const POLL_INTERVAL_MS = 30_000;

function amount(value?: string) {
  const parsed = Number.parseFloat(value?.replace(/[^0-9.-]/g, '') ?? '');
  return Number.isFinite(parsed) ? parsed : 0;
}

function categoryName(value?: string) {
  const source = value?.toLowerCase() ?? '';
  return CATEGORIES.find(category => category !== 'All' && source.includes(category.toLowerCase())) ?? 'Water';
}

function BillsPage() {
  const [bills, setBills] = useState<OcrBill[]>([]);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const result = await getOcrWaterBills();
        if (mounted) setBills(result);
      } catch (error) {
        console.error('Failed to load OCR bills:', error);
      }
    };
    void load();
    const interval = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const visibleBills = filter === 'All' ? bills : bills.filter(bill => categoryName(bill.document_type) === filter);
  const monthLabel = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  return (
    <AppShell
      title="Bills"
      active="bills"
      actions={<div className="bills-actions"><button type="button">⇩ Export</button><button type="button">⎙ Print</button><button className="upload-button" type="button">⇧ Upload</button></div>}
    >
      <section className="bills-list-page compact-bills-page">
        <div className="bills-filter-bar">
          <div className="pill-group">
            {CATEGORIES.map(category => <button key={category} className={filter === category ? 'selected' : ''} onClick={() => setFilter(category)}>{category}</button>)}
          </div>
        </div>
        <button className="month-picker" type="button" aria-label="Billing month">▣&nbsp; {monthLabel}⌄</button>
        <section className="utility-table-card">
          <table className="utility-table">
            <thead><tr><th>Utility</th><th>Provider</th><th>Period</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>
              {visibleBills.map((bill, index) => {
                const dueDate = bill.account_and_bill?.due_date ? new Date(bill.account_and_bill.due_date) : null;
                const overdue = dueDate !== null && !Number.isNaN(dueDate.getTime()) && dueDate < new Date();
                return <tr key={bill._id ?? index}>
                  <td><span className="utility-icon water" aria-hidden="true">◈</span><span>{categoryName(bill.document_type)}</span></td>
                  <td>{bill.provider?.provider_name || '—'}</td>
                  <td>{bill.account_and_bill?.bill_date || '—'}</td>
                  <td className="amount">{formatMoney(amount(bill.balance_details?.amount_due))}</td>
                  <td>{dueDate && <span className={`status ${overdue ? 'overdue' : 'due'}`}>{overdue ? 'Overdue' : 'Due'}</span>}</td>
                </tr>;
              })}
            </tbody>
          </table>
        </section>
      </section>
    </AppShell>
  );
}

export default BillsPage;
