import { useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '../components/AppShell';
import { formatMoney } from '../data/householdBills';
import { getOcrWaterBills } from '../services/waterBillService';

type OcrBill = {
  _id?: string;
  document_type?: string;
  provider?: { provider_name?: string; provider_address?: string };
  customer?: { customer_name?: string; customer_id?: string; service_location?: string };
  account_and_bill?: {
    bill_number?: string;
    bill_date?: string;
    due_date?: string;
    account_number?: string;
    account_type?: string;
  };
  balance_details?: {
    amount_due?: string;
    total_current_billing?: string;
    previous_balance?: string;
    adjustments?: string;
    less_payments_received?: string;
    penalties?: string;
    deposit_applied?: string;
  };
  meter_details?: unknown[];
  success?: boolean;
};

const POLL_INTERVAL_MS = 30_000;
const DEFAULT_CATEGORIES = ['Electricity', 'Water', 'Internet', 'Phone', 'Security', 'Pest Control'];

function amount(value?: string) {
  const parsed = Number.parseFloat(value?.replace(/[^0-9.-]/g, '') ?? '');
  return Number.isFinite(parsed) ? parsed : 0;
}

function dateValue(value?: string) {
  const parsed = value ? new Date(value) : null;
  return parsed && !Number.isNaN(parsed.getTime()) ? parsed : null;
}

function title(value?: string) {
  return value?.trim() || 'Bill';
}

function matchCategory(cats: string[], documentType?: string, providerName?: string) {
  const sources = [title(documentType), providerName ?? ''].map(s => s.toLowerCase());
  return cats.find(cat => sources.some(src => src.includes(cat.toLowerCase()))) ?? null;
}

/* ─── Category modal ────────────────────────────────────────────────────── */
type ModalMode = 'add' | 'edit';
interface CategoryModalProps {
  mode: ModalMode;
  initial: string;
  existing: string[];
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

function CategoryModal({ mode, initial, existing, onConfirm, onCancel }: CategoryModalProps) {
  const [value, setValue] = useState(initial);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const trimmed = value.trim();
  const isDuplicate = existing
    .filter(e => e.toLowerCase() !== initial.toLowerCase())
    .some(e => e.toLowerCase() === trimmed.toLowerCase());
  const isValid = trimmed.length > 0 && !isDuplicate;

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValid) onConfirm(trimmed);
    if (e.key === 'Escape') onCancel();
  };

  return (
    <div
      className="cat-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cat-modal-title"
      onClick={e => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className="cat-modal">
        <h3 id="cat-modal-title">{mode === 'add' ? 'Add Category' : 'Edit Category'}</h3>
        <p className="cat-modal-subtitle">
          {mode === 'add'
            ? 'Enter a name for the new bill category.'
            : 'Update the category name below.'}
        </p>
        <label htmlFor="cat-modal-input" className="cat-modal-label">Category name</label>
        <input
          id="cat-modal-input"
          ref={inputRef}
          className={`cat-modal-input${isDuplicate ? ' cat-modal-input--error' : ''}`}
          type="text"
          value={value}
          maxLength={40}
          placeholder="e.g. Gas, Insurance…"
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
        />
        {isDuplicate && (
          <p className="cat-modal-error">A category with this name already exists.</p>
        )}
        <div className="cat-modal-actions">
          <button className="cat-modal-btn cat-modal-btn--cancel" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="cat-modal-btn cat-modal-btn--confirm"
            disabled={!isValid}
            onClick={() => onConfirm(trimmed)}
          >
            {mode === 'add' ? 'Add' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─────────────────────────────────────────────────────────── */
function OverviewPage() {
  const [bills, setBills] = useState<OcrBill[]>([]);
  const [showAll, setShowAll] = useState(false);
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES);
  const [modal, setModal] = useState<{ mode: ModalMode; target: string } | null>(null);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const openAdd = () => { setPendingDelete(null); setModal({ mode: 'add', target: '' }); };
  const openEdit = (name: string) => { setPendingDelete(null); setModal({ mode: 'edit', target: name }); };

  const handleConfirmModal = (newName: string) => {
    if (!modal) return;
    if (modal.mode === 'add') {
      setCategories(prev => [...prev, newName]);
    } else {
      setCategories(prev => prev.map(c => (c === modal.target ? newName : c)));
    }
    setModal(null);
  };

  const requestDelete = (name: string) => { setModal(null); setPendingDelete(name); };
  const confirmDelete = (name: string) => { setCategories(prev => prev.filter(c => c !== name)); setPendingDelete(null); };
  const cancelDelete = () => setPendingDelete(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const result = await getOcrWaterBills();
        if (mounted) setBills(Array.isArray(result) ? result : []);
      } catch (error) {
        console.error('Failed to load OCR bills:', error);
      }
    };
    void load();
    const interval = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => { mounted = false; window.clearInterval(interval); };
  }, []);

  const data = useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sorted = [...bills].sort((a, b) =>
      (dateValue(b.account_and_bill?.due_date)?.getTime() ?? 0) -
      (dateValue(a.account_and_bill?.due_date)?.getTime() ?? 0),
    );
    const totalFor = (month: number, year: number) => bills
      .filter(bill => {
        const date = dateValue(bill.account_and_bill?.bill_date);
        return date?.getMonth() === month && date.getFullYear() === year;
      })
      .reduce((total, bill) => total + amount(bill.balance_details?.amount_due), 0);
    const previous = new Date(now.getFullYear(), now.getMonth() - 1, 1);

    const categoryTotals = new Map<string, number>();
    bills.forEach(bill => {
      const name =
        matchCategory(categories, bill.document_type, bill.provider?.provider_name) ??
        matchCategory(categories, undefined, bill.provider?.provider_name) ??
        (categories[0] ?? 'Other');
      categoryTotals.set(name, (categoryTotals.get(name) ?? 0) + amount(bill.balance_details?.amount_due));
    });

    const months = Array.from({ length: 6 }, (_, index) => {
      const month = new Date(now.getFullYear(), now.getMonth() - (5 - index), 1);
      return {
        label: month.toLocaleString('en-US', { month: 'short' }),
        total: totalFor(month.getMonth(), month.getFullYear()),
      };
    });

    return {
      thisMonth: totalFor(now.getMonth(), now.getFullYear()),
      lastMonth: totalFor(previous.getMonth(), previous.getFullYear()),
      dueSoon: bills
        .filter(bill => {
          const due = dateValue(bill.account_and_bill?.due_date);
          return due !== null && due >= today;
        })
        .reduce((total, bill) => total + amount(bill.balance_details?.amount_due), 0),
      tracked: new Set(bills.map(bill => bill.provider?.provider_name).filter(Boolean)).size,
      categoryRows: categories.map(
        name => [name, categoryTotals.has(name) ? categoryTotals.get(name)! : null] as [string, number | null],
      ),
      months,
      sorted,
    };
  }, [bills, categories]);

  const maxMonthTotal = Math.max(...data.months.map(m => m.total), 1);
  const genericUpcoming = categories.map(category => ({
    category,
    bill: data.sorted.find(
      bill => (matchCategory(categories, bill.document_type, bill.provider?.provider_name) ?? (categories[0] ?? 'Other')) === category,
    ),
  }));
  const visibleBills = showAll ? genericUpcoming : genericUpcoming.slice(0, 3);

  return (
    <AppShell title="Dashboard" active="overview">
      {modal && (
        <CategoryModal
          mode={modal.mode}
          initial={modal.target}
          existing={categories}
          onConfirm={handleConfirmModal}
          onCancel={() => setModal(null)}
        />
      )}

      <section className="dashboard-summary" aria-label="Bill summary">
        <article><p>This month</p><strong>{data.thisMonth > 0 && formatMoney(data.thisMonth)}</strong><small /></article>
        <article><p>Last month</p><strong>{data.lastMonth > 0 && formatMoney(data.lastMonth)}</strong><small /></article>
        <article><p>Due soon</p><strong>{data.dueSoon > 0 && formatMoney(data.dueSoon)}</strong><small /></article>
        <article><p>Tracked</p><strong>{data.tracked > 0 && data.tracked}</strong><small>{data.tracked > 0 && 'utilities'}</small></article>
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-card spend-card">
          <div className="section-title"><h2>Monthly spend</h2>{bills.length > 0 && <span>last 6 months</span>}</div>
          <div className="chart" aria-label="Monthly spend bar chart">
            <div className="chart-bars">
              {bills.length > 0 && data.months.map(month => <span key={month.label} style={{ height: `${(month.total / maxMonthTotal) * 100}%` }} />)}
            </div>
            <div className="chart-labels">{bills.length > 0 && data.months.map(month => <span key={month.label}>{month.label}</span>)}</div>
          </div>
        </article>

        <article className="dashboard-card category-card">
          <div className="section-title">
            <h2>Bill Categories</h2>
            <button className="cat-add-btn" id="add-category-btn" aria-label="Add new bill category" onClick={openAdd}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="13" height="13" aria-hidden="true">
                <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
              </svg>
              Add
            </button>
          </div>
          <div className="category-list" aria-label="Bill categories">
            {data.categoryRows.map(([name, total]) => {
              const isDeleting = pendingDelete === name;
              return (
                <div key={name} className={`category-row${isDeleting ? ' category-row--deleting' : ''}`}>
                  <span className="category-name">{name}</span>
                  {isDeleting ? (
                    <div className="cat-delete-confirm">
                      <span className="cat-delete-prompt">Remove?</span>
                      <button className="cat-confirm-btn cat-confirm-btn--yes" onClick={() => confirmDelete(name)}>Yes</button>
                      <button className="cat-confirm-btn cat-confirm-btn--no" onClick={cancelDelete}>No</button>
                    </div>
                  ) : (
                    <div className="category-row-right">
                      <strong>{total !== null ? formatMoney(total) : '—'}</strong>
                      <div className="category-actions">
                        <button className="cat-action-btn edit-btn" title={`Edit ${name}`} aria-label={`Edit ${name}`} onClick={() => openEdit(name)}>
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                            <path d="M13.586 3.586a2 2 0 1 1 2.828 2.828l-.793.793-2.828-2.828.793-.793ZM11.379 5.793 3 14.172V17h2.828l8.38-8.379-2.83-2.828Z" />
                          </svg>
                        </button>
                        <button className="cat-action-btn delete-btn" title={`Delete ${name}`} aria-label={`Delete ${name}`} onClick={() => requestDelete(name)}>
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                            <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 3.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </article>

        <section className="upcoming-section">
          <div className="section-title">
            <h2>Upcoming bills</h2>
            <button className="view-all-btn" onClick={() => setShowAll(value => !value)}>{showAll ? 'Show Less' : 'View All'}</button>
          </div>
          <div className="upcoming-list" aria-label="Upcoming bills">
            {visibleBills.map(({ category, bill }, index) => {
              const due = dateValue(bill?.account_and_bill?.due_date);
              const overdue = due !== null && due < new Date();
              return <article key={bill?._id ?? category ?? index}>
                <span className="utility-icon water" aria-hidden="true">◈</span>
                <div className="upcoming-info"><strong>{category}</strong><small className="upcoming-provider">{bill ? <>{bill.provider?.provider_name}{due && ` · due ${due.toLocaleDateString()}`}</> : 'Provider · due —'}</small></div>
                <b>{bill ? formatMoney(amount(bill.balance_details?.amount_due)) : '—'}</b>
                {due && <span className={`status ${overdue ? 'overdue' : 'due'}`}>{overdue ? 'Overdue' : 'Due'}</span>}
              </article>;
            })}
          </div>
        </section>
      </section>
    </AppShell>
  );
}

export default OverviewPage;
