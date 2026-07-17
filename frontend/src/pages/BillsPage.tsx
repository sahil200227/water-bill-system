import { useEffect, useRef, useState } from 'react';
import AppShell from '../components/AppShell';
import { formatMoney } from '../data/householdBills';
import { extractBillFromPdf, getOcrWaterBills, saveBillOcr } from '../services/waterBillService';

type OcrBill = {
  _id?: string;
  document_type?: string;
  provider?: { provider_name?: string };
  account_and_bill?: { bill_date?: string; due_date?: string };
  balance_details?: { amount_due?: string };
};

type Toast = { type: 'success' | 'error'; message: string };

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
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = (type: Toast['type'], message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4500);
  };

  const loadBills = async () => {
    try {
      const result = await getOcrWaterBills();
      setBills(result);
    } catch (error) {
      console.error('Failed to load OCR bills:', error);
    }
  };

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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset input so same file can be re-uploaded if needed
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (!file) return;

    setUploading(true);
    try {
      // Step 1: Extract structured data from the bill using AI
      const extracted = await extractBillFromPdf(file);

      // Step 2: Save extracted data to NestJS backend
      await saveBillOcr(extracted as Record<string, unknown>);

      // Step 3: Refresh bills table
      await loadBills();

      showToast('success', `✓ "${file.name}" extracted and saved successfully.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      showToast('error', `✗ Upload failed: ${message}`);
    } finally {
      setUploading(false);
    }
  };

  const visibleBills = filter === 'All' ? bills : bills.filter(bill => categoryName(bill.document_type) === filter);
  const monthLabel = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  return (
    <AppShell
      title="Bills"
      active="bills"
      actions={
        <div className="bills-actions">
          <button type="button">⇩ Export</button>
          <button type="button">⎙ Print</button>
          {/* Hidden file input — PDF and images supported */}
          <input
            ref={fileInputRef}
            id="bill-upload-input"
            type="file"
            accept=".pdf,image/png,image/jpeg,image/jpg"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            className="upload-button"
            type="button"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            aria-label="Upload bill PDF for AI extraction"
            style={{ opacity: uploading ? 0.7 : 1, cursor: uploading ? 'not-allowed' : 'pointer' }}
          >
            {uploading ? '⏳ Extracting…' : '⇧ Upload'}
          </button>
        </div>
      }
    >
      {/* Inline toast notification */}
      {toast && (
        <div
          role="alert"
          style={{
            margin: '0 0 12px 0',
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 500,
            background: toast.type === 'success' ? '#d1fae5' : '#fee2e2',
            color: toast.type === 'success' ? '#065f46' : '#991b1b',
            border: `1px solid ${toast.type === 'success' ? '#6ee7b7' : '#fca5a5'}`,
          }}
        >
          {toast.message}
        </div>
      )}

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
              {visibleBills.length === 0 && !uploading && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: '#6b7280', fontSize: '14px' }}>
                    No bills yet. Click <strong>⇧ Upload</strong> to extract a water bill PDF.
                  </td>
                </tr>
              )}
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


