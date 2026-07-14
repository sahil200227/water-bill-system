import { useEffect, useState } from "react";
import {
  getAllWaterBills,
  updateWaterBill,
  deleteWaterBill,
} from "../services/waterBillService";

type WaterBill = {
  id?: string;
  _id?: string;
  customerName?: string;
  accountNumber?: string;
  serviceAddress?: string;
  billingDate?: string;
  dueDate?: string;
  previousReading?: number;
  currentReading?: number;
  waterCharge?: number;
  totalAmount?: number;
  isPrivate?: boolean;
  deleted?: boolean;
};

type Props = {
  initialAdminView?: boolean;
};

function WaterBillList({ initialAdminView = false }: Props) {
  const formatDate = (input?: string | Date) => {
    if (!input) return '';
    const d = typeof input === 'string' ? new Date(input) : input;
    if (Number.isNaN(d.getTime())) {
      // fallback: try ISO split
      const s = String(input);
      return s.split('T')[0] || s;
    }
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  };
  const [bills, setBills] = useState<WaterBill[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adminView, setAdminView] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<{ customerName: string; currentReading: number }>({ customerName: '', currentReading: 0 });
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const load = async (showHidden = adminView) => {
    try {
      setLoading(true);
      const data = await getAllWaterBills(showHidden);
      setBills(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setAdminView(initialAdminView);
    load(initialAdminView);
  }, []);

  const filtered = bills.filter((b) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      String(b.customerName || '').toLowerCase().includes(q) ||
      String(b.accountNumber || '').toLowerCase().includes(q) ||
      String(b.serviceAddress || '').toLowerCase().includes(q)
    );
  });

  const handleDelete = async (id?: string) => {
    if (!id) return;
    if (!confirm("Delete this water bill?")) return;
    try {
      await deleteWaterBill(id);
      setBills((s) => s.filter((b) => (b._id || b.id) !== id));
      setToast({ type: 'success', message: 'Deleted successfully' });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Delete failed';
      setToast({ type: 'error', message: msg });
      setTimeout(() => setToast(null), 3000);
    }
  };

  

  const handleEdit = (bill: WaterBill) => {
    const id = bill._id || bill.id;
    if (!id) return;
    setEditingId(id);
    setEditValues({ customerName: bill.customerName || '', currentReading: Number(bill.currentReading || 0) });
  };

  const saveEdit = async () => {
    if (!editingId) return;
    try {
      // compute total based on previousReading and waterCharge from the bill being edited
      const bill = bills.find((b) => (b._id || b.id) === editingId);
      const prev = Number(bill?.previousReading ?? 0);
      const current = Number(editValues.currentReading || 0);
      const charge = Number(bill?.waterCharge ?? 0);
      const usedUnits = Math.max(current - prev, 0);
      const total = usedUnits * charge;

      const payload: Record<string, unknown> = {
        customerName: editValues.customerName,
        currentReading: current,
        totalAmount: total,
      };
      const updated = await updateWaterBill(editingId, payload);
      setBills((s) => s.map((b) => ((b._id || b.id) === editingId ? updated : b)));
      setToast({ type: 'success', message: 'Updated successfully' });
      setTimeout(() => setToast(null), 3000);
      setEditingId(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Update failed';
      setToast({ type: 'error', message: msg });
      setTimeout(() => setToast(null), 3000);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  if (loading) return <div className="loading-state">Loading water bills...</div>;
  if (error) return <div className="empty-state">Unable to load records: {error}</div>;

  return (
    <div>
      <div className="list-heading">
        <div><h2>All water bills</h2><p>Search, update, or remove customer billing records.</p></div>
        <div>
            <input
              className="search-box"
              placeholder="Search by name, account, address…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="empty-state">No records found.</div>
      ) : (
        <div className="table-wrap"><table className="bills-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Account</th>
              <th>Service Address</th>
              <th>Billing Date</th>
              <th>Previous</th>
              <th>Current</th>
              <th>Water Charge</th>
              <th>Total</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((b) => {
              const id = b._id || b.id;
              return (
                <tr key={id}>
                  <td>
                    {editingId === id ? (
                      <input value={editValues.customerName} onChange={(e) => setEditValues((s) => ({ ...s, customerName: e.target.value }))} />
                    ) : (
                      <>
                        {b.customerName}
                        {b.isPrivate && <span style={{ marginLeft: 8, color: '#b973ff', fontSize: 12 }}> (Private)</span>}
                        {b.deleted && <span style={{ marginLeft: 8, color: '#c0392b', fontSize: 12 }}> (Deleted)</span>}
                      </>
                    )}
                  </td>
                  <td>{b.accountNumber}</td>
                  <td>{b.serviceAddress}</td>
                  <td>{formatDate(b.billingDate)}</td>
                  <td>{b.previousReading}</td>
                  <td>{editingId === id ? (
                    <input value={String(editValues.currentReading)} onChange={(e) => setEditValues((s) => ({ ...s, currentReading: Number(e.target.value || 0) }))} style={{ width: 120 }} />
                  ) : b.currentReading}</td>
                  <td style={{ minWidth: 140 }}>
                    <div className="charge-control">
                      <button className="icon-btn small" title="Decrease" onClick={async () => {
                        const idLocal = id;
                        if (!idLocal) return;
                        const newCharge = Math.max(Number(b.waterCharge ?? 0) - 1, 0);
                        try {
                          const updated = await updateWaterBill(String(idLocal), { waterCharge: newCharge });
                          setBills((s) => s.map((x) => ((x._id || x.id) === idLocal ? updated : x)));
                          setToast({ type: 'success', message: 'Water charge decreased' });
                          setTimeout(() => setToast(null), 3000);
                        } catch (err) {
                          setToast({ type: 'error', message: err instanceof Error ? err.message : 'Failed' });
                          setTimeout(() => setToast(null), 3000);
                        }
                      }}>-</button>
                      <div className="charge-value">{b.waterCharge}</div>
                      <button className="icon-btn small" title="Increase" onClick={async () => {
                        const idLocal = id;
                        if (!idLocal) return;
                        const newCharge = Number(b.waterCharge ?? 0) + 1;
                        try {
                          const updated = await updateWaterBill(String(idLocal), { waterCharge: newCharge });
                          setBills((s) => s.map((x) => ((x._id || x.id) === idLocal ? updated : x)));
                          setToast({ type: 'success', message: 'Water charge increased' });
                          setTimeout(() => setToast(null), 3000);
                        } catch (err) {
                          setToast({ type: 'error', message: err instanceof Error ? err.message : 'Failed' });
                          setTimeout(() => setToast(null), 3000);
                        }
                      }}>+</button>
                    </div>
                  </td>
                  <td>{(() => {
                    if (editingId === id) {
                      const prev = Number(b.previousReading ?? 0);
                      const curr = Number(editValues.currentReading || 0);
                      const charge = Number(b.waterCharge ?? 0);
                      const used = Math.max(curr - prev, 0);
                      return used * charge;
                    }
                    return b.totalAmount;
                  })()}</td>
                  <td>
                    {editingId === id ? (
                      <>
                        <button className="icon-btn" title="Save" onClick={saveEdit}>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9 16.2l-3.5-3.5L4 14.2 9 19l11-11-1.5-1.5L9 16.2z" fill="#fff"/>
                          </svg>
                        </button>
                        <button className="icon-btn" title="Cancel" onClick={cancelEdit} style={{ background: '#bfbfbf' }}>
                          ✕
                        </button>
                      </>
                    ) : (
                      <>
                        <button className="icon-btn" title="Edit" onClick={() => handleEdit(b)}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" fill="#fff" />
                        <path d="M20.71 7.04a1.003 1.003 0 0 0 0-1.42l-2.34-2.34a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z" fill="#fff" />
                      </svg>
                    </button>
                        <button className="icon-btn danger" title="Delete" onClick={() => handleDelete(id)}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12z" fill="#fff"/>
                        <path d="M19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="#fff"/>
                      </svg>
                    </button>
                        {/* hard delete removed per request */}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      )}
      {toast && (
        <div className={`toast ${toast.type === 'success' ? 'success' : 'error'}`}>{toast.message}</div>
      )}
    </div>
  );
}

export default WaterBillList;
