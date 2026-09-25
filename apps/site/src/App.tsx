import { useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router';
import { ReactLenis } from 'lenis/react';

import { AboutPage } from '@/features/about/AboutPage';
import { MarketingPage } from '@/features/marketing/MarketingPage';

const TITLES: Record<string, string> = {
  '/': 'Manu · The case diary that reads the court for you',
  '/about': 'About · Manu, from Sankhya AI Labs',
};

/** A new page starts at its top and says which page it is in the tab. */
function usePageChange() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    document.title = TITLES[pathname] ?? TITLES['/'];
    if (!hash) window.scrollTo(0, 0);
  }, [pathname, hash]);
}

export function App() {
  usePageChange();
  return (
    <Routes>
      <Route path="/" element={<ReactLenis root options={{ lerp: 0.085, smoothWheel: true }}><MarketingPage /></ReactLenis>} />
      <Route path="/about" element={<ReactLenis root options={{ lerp: 0.085, smoothWheel: true }}><AboutPage /></ReactLenis>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
