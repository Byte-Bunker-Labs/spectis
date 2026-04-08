import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginForm from './components/LoginForm';
import Overview from './pages/Overview';
import LiveFeed from './pages/LiveFeed';
import Agents from './pages/Agents';
import Scans from './pages/Scans';
import Servers from './pages/Servers';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('spectis_token');
    setIsAuthenticated(!!token);
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('spectis_token');
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <Layout onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/feed" element={<LiveFeed />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/scans" element={<Scans />} />
        <Route path="/servers" element={<Servers />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;
