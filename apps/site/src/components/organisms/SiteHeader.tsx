import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation } from 'react-router';

import { Brand } from '@/components/atoms/Brand';
import { APP_URL } from '@/config/site';

/** The home page's sections, then About; the diary itself is the pill on the end. */
const SECTIONS = [
  ['Product', '/#product'],
  ['How it works', '/#how-it-works'],
  ['Liberty', '/#liberty'],
  ['Questions', '/#questions'],
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const onAbout = pathname === '/about';

  return (
    <header className="site-header">
      <nav className="site-nav" aria-label="Main navigation">
        <Brand />
        <div className="site-nav__links">
          {SECTIONS.map(([label, href]) => <a href={href} key={href}>{label}</a>)}
          <Link to="/about" aria-current={onAbout ? 'page' : undefined}>About</Link>
          <a className="site-nav__login" href={APP_URL}>Open Manu</a>
        </div>
        <button className="site-nav__toggle" type="button" aria-expanded={open} aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen((value) => !value)}>
          {open ? <X size={19} /> : <Menu size={19} />}
        </button>
      </nav>
      {open ? (
        <div className="mobile-menu">
          {SECTIONS.map(([label, href]) => <a href={href} key={href} onClick={() => setOpen(false)}>{label}</a>)}
          <Link to="/about" aria-current={onAbout ? 'page' : undefined} onClick={() => setOpen(false)}>About</Link>
          <a href={APP_URL}>Open Manu <span>↗</span></a>
        </div>
      ) : null}
    </header>
  );
}
