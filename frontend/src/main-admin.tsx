import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './lib/chartSetup';
import './styles/variables.css';
import './styles/global.css';
import './styles/report.css';
import Admin from './pages/Admin';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Admin />
  </StrictMode>,
);
