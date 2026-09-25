import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
// Tura's faces, so the two products read as one family: Baloo 2 for the
// wordmark, Averia Serif Libre for display, Roboto Flex for everything else.
import '@fontsource/baloo-2/700.css';
import '@fontsource/averia-serif-libre/latin-300.css';
import '@fontsource/averia-serif-libre/latin-300-italic.css';
import '@fontsource-variable/roboto-flex/wght.css';

import { App } from '@/App';
import '@/styles/global.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
