import './App.css';
import { useEffect, useState } from 'react';
import ImportPanel from './components/ImportPanel';
import WaterBillForm from './components/WaterBillForm';
import AdminPage from './pages/AdminPage';

function App() {
  const getRoute = () => {
    if (typeof window === 'undefined') {
      return 'home';
    }

    const pathname = window.location.pathname;
    const hash = window.location.hash;

    if (pathname === '/admin' || pathname === '/admin/' || hash === '#/admin') {
      return 'admin';
    }

    return 'home';
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

  if (route === 'admin') {
    return <AdminPage />;
  }

  return (
    <div className="container">
      <h1>Water Bill Management System</h1>

      <ImportPanel />
      <WaterBillForm />

      <p style={{ textAlign: 'center', marginTop: 18 }} />
    </div>
  );
}

export default App;