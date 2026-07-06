import './App.css';
import ImportPanel from './components/ImportPanel';
import WaterBillForm from './components/WaterBillForm';

function App() {
  return (
    <div className="container">
      <h1>Water Bill Management System</h1>

      <ImportPanel />
      <WaterBillForm />
    </div>
  );
}

export default App;