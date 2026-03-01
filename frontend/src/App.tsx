import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CompanyDetail from './pages/CompanyDetail';
import Admin from './pages/Admin';
import Documents from './pages/Documents';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/company/:id" element={<CompanyDetail />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/documents" element={<Documents />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

