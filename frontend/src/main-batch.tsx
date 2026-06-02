import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import Batch from './pages/Batch';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Batch />
  </StrictMode>,
);
