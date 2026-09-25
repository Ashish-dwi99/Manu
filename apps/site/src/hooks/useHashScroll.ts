import { useEffect } from 'react';
import { useLenis } from 'lenis/react';

/** Clearance for the fixed header, so a section lands below it rather than under it. */
const HEADER_CLEARANCE = 96;

/**
 * Scroll to `#section` after the page has rendered it.
 *
 * A link like `/#questions` from another page is a full load: the browser looks
 * for the anchor before React has drawn it, finds nothing, and leaves the page
 * at the top. So the page does the jump itself once it exists — and again after
 * the images settle, since a hero that grows late would push the section down.
 */
export function useHashScroll() {
  const lenis = useLenis();

  useEffect(() => {
    const jump = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      const top = target.getBoundingClientRect().top + window.scrollY - HEADER_CLEARANCE;
      if (lenis) lenis.scrollTo(top, { immediate: true });
      else window.scrollTo({ top });
    };
    const frame = requestAnimationFrame(jump);
    window.addEventListener('load', jump, { once: true });
    window.addEventListener('hashchange', jump);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('load', jump);
      window.removeEventListener('hashchange', jump);
    };
  }, [lenis]);
}
