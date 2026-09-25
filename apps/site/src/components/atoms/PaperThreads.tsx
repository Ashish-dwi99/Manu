import { useId, useMemo } from 'react';

import { useReveal } from '@/hooks/useReveal';
import { cn } from '@/lib/cn';

/**
 * The threads from the painted tiles, drawn rather than painted.
 *
 * Every tile in the set carries the same second layer over its watercolour: a
 * loose braid of hairlines crossing the paper, a few beads on them, and pins
 * standing up out of the braid. This draws that layer from a seed, so a section
 * with no painting of its own still sits in the family, and the same seed
 * always gives the same picture (it never reshuffles between renders).
 *
 * `band` is where the braid runs, as fractions of the height. `tone="navy"`
 * lifts the colours for a dark ground.
 */

type Tone = 'paper' | 'navy';

type PaperThreadsProps = {
  seed?: number;
  tone?: Tone;
  strands?: number;
  pins?: number;
  ring?: boolean;
  band?: readonly [number, number];
  className?: string;
};

const WIDTH = 1600;
const HEIGHT = 900;

const INKS: Record<Tone, { threads: string[]; wash: string[]; halo: number }> = {
  paper: { threads: ['#8db8d5', '#a9b9c2', '#e2ae72', '#8db8d5', '#c9b99c'], wash: ['#b9d4e3', '#f0cfa4'], halo: 0.16 },
  navy: { threads: ['#9cc6dd', '#6f93ab', '#df9d53', '#b7d6e2', '#88a3b4'], wash: ['#356f96', '#945135'], halo: 0.22 },
};

function seededRandom(seed: number) {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

/** A smooth path through the points: Catmull-Rom, written out as cubic Béziers. */
function smoothPath(points: Array<[number, number]>) {
  let d = `M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const [x0, y0] = points[Math.max(0, i - 1)];
    const [x1, y1] = points[i];
    const [x2, y2] = points[i + 1];
    const [x3, y3] = points[Math.min(points.length - 1, i + 2)];
    const c1x = x1 + (x2 - x0) / 6;
    const c1y = y1 + (y2 - y0) / 6;
    const c2x = x2 - (x3 - x1) / 6;
    const c2y = y2 - (y3 - y1) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  }
  return d;
}

function paint(seed: number, tone: Tone, strands: number, pins: number, ring: boolean, band: readonly [number, number]) {
  const random = seededRandom(seed);
  const ink = INKS[tone];
  const top = band[0] * HEIGHT;
  const span = (band[1] - band[0]) * HEIGHT;
  const middle = top + span / 2;

  // One spine for the whole braid, so the strands travel together and cross.
  const spineFrequency = 0.55 + random() * 0.5;
  const spinePhase = random() * Math.PI * 2;
  const spine = (x: number) => middle + Math.sin((x / WIDTH) * Math.PI * 2 * spineFrequency + spinePhase) * span * 0.34;

  const threads = Array.from({ length: strands }, (_, index) => {
    const amplitude = span * (0.08 + random() * 0.16);
    const frequency = 0.8 + random() * 1.1;
    const phase = random() * Math.PI * 2;
    const offset = (random() - 0.5) * span * 0.26;
    const y = (x: number) => spine(x) + Math.sin((x / WIDTH) * Math.PI * 2 * frequency + phase) * amplitude + offset;
    const points: Array<[number, number]> = [];
    for (let step = 0; step <= 24; step += 1) {
      const x = -60 + (step / 24) * (WIDTH + 120);
      points.push([x, y(x)]);
    }
    const color = ink.threads[index % ink.threads.length];
    const beads = Array.from({ length: 1 + Math.floor(random() * 2) }, () => {
      const x = WIDTH * (0.08 + random() * 0.86);
      return { x, y: y(x), r: 4.5 + random() * 3.2 };
    });
    return {
      d: smoothPath(points),
      color,
      width: 0.9 + random() * 0.6,
      opacity: tone === 'navy' ? 0.5 + random() * 0.3 : 0.45 + random() * 0.3,
      beads,
      y,
    };
  });

  // Pins stand straight up out of the braid and end in a bead.
  const standing = Array.from({ length: pins }, () => {
    const thread = threads[Math.floor(random() * threads.length)];
    const x = WIDTH * (0.12 + random() * 0.8);
    const base = thread.y(x);
    const height = 70 + random() * 190;
    return { x, base, tip: Math.max(24, base - height), color: thread.color };
  });

  const circle = ring
    ? { cx: WIDTH * (0.72 + random() * 0.14), cy: middle - span * 0.35, r: HEIGHT * (0.26 + random() * 0.12) }
    : null;

  const washes = Array.from({ length: 3 }, (_, index) => ({
    cx: WIDTH * (0.15 + random() * 0.7),
    cy: middle + (random() - 0.5) * span,
    rx: 180 + random() * 260,
    ry: 90 + random() * 120,
    color: ink.wash[index % ink.wash.length],
  }));

  return { threads, standing, circle, washes, halo: ink.halo };
}

export function PaperThreads({
  seed = 7,
  tone = 'paper',
  strands = 7,
  pins = 3,
  ring = false,
  band = [0.5, 0.86],
  className,
}: PaperThreadsProps) {
  const ref = useReveal<HTMLDivElement>();
  const blurId = `threads-blur-${useId().replace(/:/g, '')}`;
  const [bandTop, bandBottom] = band;
  const art = useMemo(
    () => paint(seed, tone, strands, pins, ring, [bandTop, bandBottom]),
    [seed, tone, strands, pins, ring, bandTop, bandBottom],
  );

  return (
    <div ref={ref} className={cn('paper-threads', `paper-threads--${tone}`, className)} aria-hidden="true">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id={blurId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="46" />
          </filter>
        </defs>
        <g className="paper-threads__wash" filter={`url(#${blurId})`}>
          {art.washes.map((wash, index) => (
            <ellipse key={index} cx={wash.cx} cy={wash.cy} rx={wash.rx} ry={wash.ry} fill={wash.color} />
          ))}
        </g>
        {art.circle ? (
          <circle className="paper-threads__line" pathLength={1} cx={art.circle.cx} cy={art.circle.cy} r={art.circle.r} fill="none" stroke={INKS[tone].threads[1]} strokeWidth="1.1" opacity=".5" />
        ) : null}
        {art.threads.map((thread, index) => (
          <path
            key={index}
            className="paper-threads__line"
            pathLength={1}
            d={thread.d}
            fill="none"
            stroke={thread.color}
            strokeWidth={thread.width}
            strokeLinecap="round"
            opacity={thread.opacity}
            style={{ transitionDelay: `${index * 90}ms` }}
          />
        ))}
        {art.standing.map((pin, index) => (
          <g key={index} className="paper-threads__bead" style={{ transitionDelay: `${700 + index * 120}ms` }}>
            <line x1={pin.x} y1={pin.base} x2={pin.x} y2={pin.tip} stroke={pin.color} strokeWidth="1" opacity=".6" />
            <circle cx={pin.x} cy={pin.tip} r="5.5" fill={pin.color} />
            <circle cx={pin.x} cy={pin.base} r="3.4" fill={pin.color} opacity=".8" />
          </g>
        ))}
        {art.threads.flatMap((thread, index) =>
          thread.beads.map((bead, beadIndex) => (
            <g key={`${index}-${beadIndex}`} className="paper-threads__bead" style={{ transitionDelay: `${600 + (index + beadIndex) * 70}ms` }}>
              <circle cx={bead.x} cy={bead.y} r={bead.r + 6} fill={thread.color} opacity={art.halo} />
              <circle cx={bead.x} cy={bead.y} r={bead.r} fill={thread.color} />
            </g>
          )),
        )}
      </svg>
    </div>
  );
}
