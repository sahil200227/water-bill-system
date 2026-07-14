import { useEffect, useState } from 'react';
import * as XLSX from 'xlsx';
import WaterBillList from '../components/WaterBillList';
import AppShell from '../components/AppShell';
import { getAllWaterBills } from '../services/waterBillService';

const formatDate = (value?: string | Date) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).split('T')[0] : date.toLocaleDateString('en-GB');
};

function AdminPage() {
  const [verified, setVerified] = useState(false);
  const [checking, setChecking] = useState(true);
  const [keyInput, setKeyInput] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const stored = sessionStorage.getItem('adminKey');
        if (!stored) return;
        const res = await fetch('http://localhost:3000/water-bill/admin/verify', { headers: { 'x-admin-key': stored } });
        if (res.ok) setVerified(true); else sessionStorage.removeItem('adminKey');
      } catch { sessionStorage.removeItem('adminKey'); }
      finally { setChecking(false); }
    })();
  }, []);

  const submitKey = async () => {
    setErrorMsg('');
    if (!keyInput) return setErrorMsg('Enter an administrator key.');
    try {
      const res = await fetch('http://localhost:3000/water-bill/admin/verify', { headers: { 'x-admin-key': keyInput } });
      if (!res.ok) return setErrorMsg((await res.json().catch(() => null))?.message || 'Invalid administrator key.');
      sessionStorage.setItem('adminKey', keyInput);
      setVerified(true);
    } catch { setErrorMsg('Failed to verify the administrator key.'); }
  };

  const logout = () => {
    sessionStorage.removeItem('adminKey');
    setVerified(false);
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new Event('popstate'));
  };

  const exportBills = async () => {
    try {
      const data = await getAllWaterBills(false);
      const ws = XLSX.utils.json_to_sheet(data.map((b: any) => ({ Name: b.customerName, Account: b.accountNumber, ServiceAddress: b.serviceAddress, BillingDate: formatDate(b.billingDate), PreviousReading: b.previousReading, CurrentReading: b.currentReading, WaterCharge: b.waterCharge, TotalAmount: b.totalAmount })));
      const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, 'WaterBills'); XLSX.writeFile(wb, 'water-bills.xlsx');
    } catch (err) { console.error(err); }
  };

  const actions = verified ? <div className="admin-toolbar"><button className="primary-button" onClick={exportBills}>Export data</button><button className="logout-button" onClick={logout}>Sign out</button></div> : undefined;

  return <AppShell title="Water bill records" eyebrow="Administration" active="bills" actions={actions}>
    {checking ? <div className="loading-state">Checking administrator access...</div> : verified ? <section className="content-card bills-panel"><WaterBillList /></section> :
      <div className="login-layout"><div className="admin-login-card">
        <div className="login-avatar">⌁</div><h2>Administrator sign in</h2><p className="login-copy">Enter your administrator key to view and manage billing records.</p>
        <div className="login-form"><input type={showPassword ? 'text' : 'password'} placeholder="Administrator key" value={keyInput} onChange={(e) => setKeyInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submitKey()} className="input-password" />
          <button type="button" className="show-password-btn" onClick={() => setShowPassword((value) => !value)} aria-label="Show or hide password">{showPassword ? '◉' : '○'}</button>
          {errorMsg && <div className="login-error">{errorMsg}</div>}<div className="login-actions"><button className="login-btn" onClick={submitKey}>SIGN IN</button></div>
        </div>
      </div></div>}
  </AppShell>;
}

export default AdminPage;
