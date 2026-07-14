import './App.css';
import { useEffect, useState } from 'react';
import BillsPage from './pages/BillsPage';
import OverviewPage from './pages/OverviewPage';
import UsagePage from './pages/UsagePage';
import PaymentsPage from './pages/PaymentsPage';

function App() {
  const getRoute = () => {
    if (typeof window === 'undefined') return 'overview';

    const { pathname, hash } = window.location;
    if (pathname === '/bills' || pathname === '/bills/' || pathname === '/admin' || pathname === '/admin/' || hash === '#/bills' || hash === '#/admin') return 'bills';
    if (pathname === '/usage' || pathname === '/usage/' || hash === '#/usage') return 'usage';
    if (pathname === '/payments' || pathname === '/payments/' || hash === '#/payments') return 'payments';
    return 'overview';
  };

  const [route, setRoute] = useState(getRoute());

  useEffect(() => {
    const onRouteChange = () => setRoute(getRoute());
    window.addEventListener('popstate', onRouteChange);
    window.addEventListener('hashchange', onRouteChange);
    return () => {
      window.removeEventListener('popstate', onRouteChange);
      window.removeEventListener('hashchange', onRouteChange);
    };
  }, []);

  if (route === 'bills') return <BillsPage />;
  if (route === 'usage') return <UsagePage />;
  if (route === 'payments') return <PaymentsPage />;
  return <OverviewPage />;
}

export default App;
