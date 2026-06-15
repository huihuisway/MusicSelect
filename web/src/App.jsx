import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import DayDetail from './pages/DayDetail';
import History from './pages/History';
import WeekDetail from './pages/WeekDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/day/:date" element={<DayDetail />} />
          <Route path="/history" element={<History />} />
          <Route path="/history/:week" element={<WeekDetail />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
