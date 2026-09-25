import { useEffect, useRef } from 'react';

import { PaperThreads } from '@/components/atoms/PaperThreads';

/**
 * Why Manu exists, read as it is written.
 *
 * The opening sentence inks in word by word as it crosses the screen, and the
 * phrase that carries the whole argument gets a saffron brush stroke painted
 * under it once the sentence is complete. The rest is set as a short note.
 */
const LEAD = 'A hearing is lost to a date nobody saw move. A direction is missed because the order was never opened. And for someone in custody, a right can fall due';
const MARKED = 'while the file sits unread.';

export function LabNote() {
  const leadRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const lead = leadRef.current;
    if (!lead) return;
    const words = Array.from(lead.querySelectorAll<HTMLElement>('[data-word]'));
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      words.forEach((word) => { word.style.opacity = '1'; });
      lead.dataset.inked = 'true';
      return;
    }
    let frame = 0;
    const paint = () => {
      frame = 0;
      const rect = lead.getBoundingClientRect();
      const start = window.innerHeight * 0.88;
      const end = window.innerHeight * 0.38;
      const progress = Math.min(1, Math.max(0, (start - rect.top) / (start - end + rect.height * 0.4)));
      const lit = progress * words.length;
      words.forEach((word, index) => {
        word.style.opacity = String(0.16 + 0.84 * Math.min(1, Math.max(0, lit - index)));
      });
      lead.dataset.inked = progress >= 0.98 ? 'true' : 'false';
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(paint);
    };
    paint();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, []);

  return (
    <section className="about-note" aria-labelledby="about-note-title">
      <PaperThreads tone="navy" seed={11} strands={7} pins={0} band={[0.8, 1.04]} className="about-note__threads" />
      <div className="about-note__inner">
        <p className="about-kicker about-kicker--inverse" id="about-note-title">A note from the lab</p>

        <p ref={leadRef} className="about-note__lead" data-inked="false">
          <span className="about-note__quote" aria-hidden="true">“</span>
          {LEAD.split(' ').map((word, index) => <span data-word key={`${word}-${index}`}>{word} </span>)}
          <mark>
            {MARKED.split(' ').map((word, index) => <span data-word key={`m-${word}-${index}`}>{word}{index < MARKED.split(' ').length - 1 ? ' ' : ''}</span>)}
            <svg className="about-note__stroke" viewBox="0 0 600 40" preserveAspectRatio="none" aria-hidden="true">
              <path d="M6 26 C 90 14, 180 34, 290 22 S 470 12, 594 24" />
            </svg>
          </mark>
        </p>

        <div className="about-note__body">
          <p>
            None of this is for want of law. The record already says what happened and what must happen next. It is
            spread across portals, PDFs and people&rsquo;s memories, and nobody has the time to read all of it every
            morning.
          </p>
          <p>
            So we built Manu to read it: every case, every morning, with the exact words on every line. It decides
            nothing. It makes sure that the people who do decide, on either side of the bar and on the bench, are
            reading the same page.
          </p>
        </div>
      </div>
    </section>
  );
}
