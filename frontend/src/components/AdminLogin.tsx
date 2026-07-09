import { useState, useEffect } from 'react';

function AdminLogin() {
  const [show, setShow] = useState(false);
  const [key, setKey] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      setIsAdmin(Boolean(sessionStorage.getItem('adminKey')));
    } catch {
      setIsAdmin(false);
    }
  }, []);

  const navigateToRoute = (route: 'home' | 'admin') => {
    if (typeof window === 'undefined') return;

    const targetPath = route === 'admin' ? '/admin' : '/';
    window.history.pushState({}, '', targetPath);
    window.dispatchEvent(new Event('popstate'));
  };

  const open = () => setShow(true);
  const close = () => setShow(false);

  const submit = () => {
    setErrorMsg('');
    // verify key with backend before storing
    (async () => {
      try {
        if (!key) return setErrorMsg('Enter admin key');
        const res = await fetch('http://localhost:3000/water-bill/admin/verify', {
          method: 'GET',
          headers: { 'x-admin-key': key },
        });
        if (!res.ok) {
          const err = await res.json().catch(() => null);
          return setErrorMsg(err?.message || 'Invalid admin key');
        }

        sessionStorage.setItem('adminKey', key);
        setIsAdmin(true);
        setShow(false);
        navigateToRoute('admin');
      } catch (err) {
        console.error(err);
        setErrorMsg('Failed to verify admin key');
      }
    })();
  };

  const logout = () => {
    try {
      sessionStorage.removeItem('adminKey');
      setIsAdmin(false);
      navigateToRoute('home');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: 'inline-block' }}>
      {!isAdmin ? (
        <>
          <button onClick={open} style={{ marginRight: 8 }}>Admin Login</button>
          {show && (
            <div style={{ position: 'fixed', left: 0, right: 0, top: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ background: '#fff', padding: 20, borderRadius: 8, boxShadow: '0 6px 20px rgba(0,0,0,0.1)' }}>
                <h3>Admin Login</h3>
                <input placeholder="Enter admin key" value={key} onChange={(e) => setKey(e.target.value)} />
                {errorMsg && <div style={{ color: '#dc2626', marginTop: 8 }}>{errorMsg}</div>}
                <div style={{ marginTop: 12 }}>
                  <button onClick={submit} style={{ marginRight: 8 }}>Submit</button>
                  <button onClick={close}>Cancel</button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <button onClick={logout}>Logout Admin</button>
      )}
    </div>
  );
}

export default AdminLogin;
