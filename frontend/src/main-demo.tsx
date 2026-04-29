import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './lib/chartSetup';
import './styles/variables.css';
import './styles/global.css';
import './styles/report.css';
import Demo from './pages/Demo';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Demo />
  </StrictMode>,
);
