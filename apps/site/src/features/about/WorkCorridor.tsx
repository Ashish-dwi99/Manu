import { useEffect, useRef, useState } from 'react';

/**
 * The work, hung like plates in a gallery corridor.
 *
 * The section pins and the paintings travel sideways as the page scrolls, so
 * the reader walks past them rather than clicking through a carousel. Phones
 * and reduced motion get the same pictures as a plain column.
 */
const PLATES = [
  {
    title: 'Reading the court',
    detail: 'Following a case by its CNR, and noticing every morning what moved: the date, the stage, a new order.',
    image: '/art/plates/manu-plate-court.webp',
    width: 960,
    height: 720,
    alt: 'The Supreme Court of India across its gardens and pools, in ink and watercolour',
  },
  {
    title: 'Reading the order',
    detail: 'Finding each direction in an order, who must do what and by when, in the order’s own words.',
    image: '/art/plates/manu-plate-readers.webp',
    width: 990,
    height: 742,
    alt: 'Young advocates in gowns reading case files together on the steps under a banyan tree',
  },
  {
    title: 'Counting the days',
    detail: 'Custody, Section 479 and default bail as fixed rules with the working shown, never as a guess.',
    image: '/art/plates/manu-plate-banyan.webp',
    width: 1050,
    height: 788,
    alt: 'A banyan tree with hanging roots beside a sandstone colonnade',
  },
  {
    title: 'The day in court',
    detail: 'The cause list, the court hall, how many items are ahead, and the words that were said on the day.',
    image: '/art/plates/manu-plate-bench.webp',
    width: 948,
    height: 711,
    alt: 'Senior advocates in conference on the court steps, notebooks open',
  },
] as const;

export function WorkCorridor() {
  const sectionRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 900px)');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setPinned(desktop.matches && !reduced.matches);
    update();
    desktop.addEventListener('change', update);
    reduced.addEventListener('change', update);
    return () => {
      desktop.removeEventListener('change', update);
      reduced.removeEventListener('change', update);
    };
  }, []);

  /* The corridor: the section is as tall as the track is wide, and scrolling
     through it slides the track across. Measured, not guessed, so a wider
     window simply means a shorter walk. */
  useEffect(() => {
    const section = sectionRef.current;
    const track = trackRef.current;
    if (!section || !track) return;
    if (!pinned) {
      section.style.removeProperty('height');
      track.style.removeProperty('transform');
      return;
    }
    let frame = 0;
    let distance = 0;
    const measure = () => {
      distance = Math.max(0, track.scrollWidth - window.innerWidth + 80);
      section.style.height = `${window.innerHeight + distance}px`;
    };
    const paint = () => {
      frame = 0;
      const top = section.getBoundingClientRect().top;
      const progress = distance ? Math.min(1, Math.max(0, -top / distance)) : 0;
      track.style.transform = `translate3d(${-progress * distance}px, 0, 0)`;
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(paint);
    };
    measure();
    paint();
    const resize = () => {
      measure();
      schedule();
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', resize);
    void document.fonts?.ready.then(resize);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', resize);
    };
  }, [pinned]);

  return (
    <section ref={sectionRef} className={`about-plates${pinned ? ' is-pinned' : ''}`} aria-labelledby="about-plates-title">
      <div className="about-plates__stage">
        <header className="about-plates__head">
          <p className="about-kicker">The work</p>
          <h2 id="about-plates-title">Four things a case diary <em>has to get right.</em></h2>
        </header>

        <div ref={trackRef} className="about-plates__track">
          {PLATES.map((plate, index) => (
            <div key={plate.title} className="about-plate__anchor">
              <figure className="about-plate">
                <span className="about-plate__mat">
                  {/* The first plate is on screen when the page opens, so it
                    * loads at once; the rest wait their turn. */}
                  <img
                    src={plate.image}
                    alt={plate.alt}
                    width={plate.width}
                    height={plate.height}
                    loading={index === 0 ? 'eager' : 'lazy'}
                    fetchPriority={index === 0 ? 'high' : 'auto'}
                    decoding={index === 0 ? 'auto' : 'async'}
                  />
                </span>
                <figcaption>
                  <strong>{plate.title}</strong>
                  <em>{plate.detail}</em>
                </figcaption>
              </figure>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
