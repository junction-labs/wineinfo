import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminPanel from './pages/AdminPanel';
import WineCatalog from './pages/WineCatalog';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<WineCatalog />} />
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Router>
  );
}