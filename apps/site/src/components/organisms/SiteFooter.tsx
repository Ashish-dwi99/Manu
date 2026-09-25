import { Link } from 'react-router';

import { APP_URL, COMPANY, CONTACT_EMAIL } from '@/config/site';

/**
 * Tura's footer: short link columns on a pale blue card, and the wordmark
 * pinned to the card's bottom-left corner so the rounded edge crops it.
 */
export function SiteFooter() {
  return (
    <>
      <footer className="site-footer">
        <div className="site-footer__top">
          <div className="site-footer__wordmark" aria-hidden="true">manu</div>
          <div className="site-footer__nav">
            <p>Product</p>
            <a href="/#product">The diary</a>
            <a href="/#how-it-works">How it works</a>
            <a href="/#screens">Screens</a>
            <a href={APP_URL}>Open Manu</a>
          </div>
          <div className="site-footer__nav">
            <p>Trust</p>
            <a href="/#sources">Sources</a>
            <a href="/#liberty">Liberty</a>
            <a href="/#principles">What Manu will not do</a>
            <a href="/#questions">Questions</a>
          </div>
          <div className="site-footer__nav">
            <p>Company</p>
            <Link to="/about">About</Link>
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          </div>
        </div>
        <div className="site-footer__bottom" />
      </footer>
      <p className="site-footer__legal">
        © {new Date().getFullYear()} {COMPANY}. Manu prepares; people act. Nothing on this site is legal advice.
      </p>
    </>
  );
}
