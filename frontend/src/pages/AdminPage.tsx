import { useEffect, useState } from 'react';
import WaterBillList from "../components/WaterBillList";
import * as XLSX from 'xlsx';
import { getAllWaterBills } from '../services/waterBillService';

  const formatDate = (input?: string | Date) => {
    if (!input) return '';
    const d = typeof input === 'string' ? new Date(input) : input;
    if (Number.isNaN(d.getTime())) {
      const s = String(input);
      return s.split('T')[0] || s;
    }
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  };

function AdminPage() {
  const [verified, setVerified] = useState(false);
  const [checking, setChecking] = useState(true);
  const [keyInput, setKeyInput] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const navigateToHome = () => {
    if (typeof window === 'undefined') return;
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new Event('popstate'));
  };

  useEffect(() => {
    (async () => {
      try {
        const stored = sessionStorage.getItem('adminKey');
        if (!stored) {
          setChecking(false);
          return;
        }

        // verify stored key
        const res = await fetch('http://localhost:3000/water-bill/admin/verify', {
          method: 'GET',
          headers: { 'x-admin-key': stored },
        });

        if (!res.ok) {
          sessionStorage.removeItem('adminKey');
          setChecking(false);
          return;
        }

        setVerified(true);
      } catch (err) {
        try { sessionStorage.removeItem('adminKey'); } catch {}
      } finally {
        setChecking(false);
      }
    })();
  }, []);

  const submitKey = async () => {
    setErrorMsg('');
    if (!keyInput) return setErrorMsg('Enter admin key');

    try {
      const res = await fetch('http://localhost:3000/water-bill/admin/verify', {
        method: 'GET',
        headers: { 'x-admin-key': keyInput },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        return setErrorMsg(err?.message || 'Invalid admin key');
      }

      sessionStorage.setItem('adminKey', keyInput);
      setVerified(true);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to verify admin key');
    }
  };

  const [showPassword, setShowPassword] = useState(false);

  const logout = () => {
    try {
      sessionStorage.removeItem('adminKey');
    } catch {}
    setVerified(false);
    navigateToHome();
  };

  return (
    <div className="container admin-container">
      <div className="admin-header">
        <h1>Admin</h1>
        <div className="admin-header-actions">
          <button className="export-icon" title="Export" onClick={async () => {
            try {
              const data = await getAllWaterBills(false);
              const ws = XLSX.utils.json_to_sheet(data.map((b: any) => ({
                Name: b.customerName,
                Account: b.accountNumber,
                ServiceAddress: b.serviceAddress,
                BillingDate: formatDate(b.billingDate),
                PreviousReading: b.previousReading,
                CurrentReading: b.currentReading,
                WaterCharge: b.waterCharge,
                TotalAmount: b.totalAmount,
              })));
              const wb = XLSX.utils.book_new();
              XLSX.utils.book_append_sheet(wb, ws, 'WaterBills');
              XLSX.writeFile(wb, 'water-bills.xlsx');
            } catch (err) {
              console.error(err);
            }
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
              <path d="M12 3v12" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 11l4 4 4-4" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M5 21h14" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <button onClick={logout} className="icon-logout" title="Logout Admin">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 13v-2H7V8l-5 4 5 4v-3h9z" fill="#fff" />
              <path d="M20 3H10v2h10v14H10v2h10a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" fill="#fff" />
            </svg>
          </button>
        </div>
      </div>

      {/* <p style={{ textAlign: 'center' }}>
        <a href="/">Back to Customer Page</a>
      </p> */}

      {checking ? (
        <div>Checking admin access…</div>
      ) : verified ? (
        <div>
          <WaterBillList initialAdminView={false} />
        </div>
      ) : (
        <div className="login-wrapper">
          <div className="admin-login-card portrait">
            <div className="login-avatar">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5z" fill="rgba(255,255,255,0.9)"/>
                <path d="M4 20c0-4 4-6 8-6s8 2 8 6v1H4v-1z" fill="rgba(255,255,255,0.9)"/>
              </svg>
            </div>
            <div className="login-form">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Password"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') submitKey(); }}
                className="input-password"
              />

              <button
                type="button"
                className="show-password-btn"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-5 0-9.27-3-11-8 1.02-2.6 2.94-4.73 5.31-6.09" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M1 1l22 22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </button>

              {errorMsg && <div style={{ color: '#dc2626', marginBottom: 8 }}>{errorMsg}</div>}

              <div className="login-actions" style={{ flexDirection: 'column', alignItems: 'center' }}>
                <button className="login-btn" onClick={submitKey}>LOGIN</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPage;
