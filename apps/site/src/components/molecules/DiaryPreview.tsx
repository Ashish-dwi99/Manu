import { useEffect, useRef } from 'react';

import { ButtonLink } from '@/components/atoms/ButtonLink';
import { APP_URL } from '@/config/site';

/**
 * The first look at the product, under the hero.
 *
 * The argument sits centred above a painted stage, and the real Today screen
 * rises onto it: tilted back as it enters, flat by the time it is in full view.
 */
export function DiaryPreview() {
  const stageRef = useRef<HTMLDivElement>(null);
  const screenRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stage = stageRef.current;
    const screen = screenRef.current;
    if (!stage || !screen) return;
    // Phones get the screen flat: a tilt at that width reads as a wobble.
    if (window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 640px)').matches) return;
    let frame = 0;
    const paint = () => {
      frame = 0;
      const rect = stage.getBoundingClientRect();
      const viewport = window.innerHeight;
      // 0 when the stage's top reaches the bottom of the screen, 1 when it is 20% down.
      const progress = Math.min(1, Math.max(0, (viewport - rect.top) / (viewport * 0.8)));
      const eased = 1 - Math.pow(1 - progress, 3);
      screen.style.transform = `perspective(1600px) rotateX(${(1 - eased) * 16}deg) translateY(${(1 - eased) * 60}px) scale(${0.94 + eased * 0.06})`;
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
    <div className="course-preview">
      <header className="course-preview__head">
        <h2>
          The record says what happened.
          <em>Your diary should say what to do next.</em>
        </h2>
        <p>
          Today that means refreshing the court&rsquo;s site, downloading orders and asking juniors what was said.
          Manu keeps one diary instead: what is listed today, what changed overnight, and what somebody has to do by
          when, every line pointing back to the order it came from.
        </p>
        <ButtonLink href={APP_URL}>Open Manu</ButtonLink>
      </header>

      <div ref={stageRef} className="course-preview__stage">
        <img className="course-preview__paint" src="/art/paper/paper-threads.webp" alt="" width="1518" height="584" loading="lazy" decoding="async" />
        <div ref={screenRef} className="course-preview__screen">
          <img
            src="/art/screens/manu-today.webp"
            alt="Manu's Today screen: three matters listed in ASJ-03 Saket with their item numbers and liberty labels, and the court's display board showing it is at item 10"
            width="1800"
            height="1000"
            loading="lazy"
            decoding="async"
          />
        </div>
      </div>
    </div>
  );
}
