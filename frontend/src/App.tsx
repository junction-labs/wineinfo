import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import WineCatalog from './pages/WineCatalog';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<WineCatalog />} />
      </Routes>
    </Router>
  );
}