import { cn } from '@/lib/cn';

/**
 * A painted sheet to write on.
 *
 * The five tiles cut from the Manu set: pale paper with one drawing in a
 * corner and the threads across it. A section that carries writing sits on
 * one; the drawing is anchored to its own corner so the words keep the
 * empty paper, and the section's ground is the tiles' own paper colour, so
 * the edge of the picture never shows.
 */
export type PaperTile = 'dome' | 'scales' | 'threads' | 'grove' | 'circuit';

const TILES: Record<PaperTile, { src: string; width: number; height: number; position: string }> = {
  dome: { src: '/art/paper/paper-dome.webp', width: 1672, height: 941, position: 'left bottom' },
  scales: { src: '/art/paper/paper-scales.webp', width: 1518, height: 750, position: 'right center' },
  threads: { src: '/art/paper/paper-threads.webp', width: 1518, height: 584, position: 'center' },
  grove: { src: '/art/paper/paper-grove.webp', width: 1518, height: 584, position: 'right bottom' },
  circuit: { src: '/art/paper/paper-circuit.webp', width: 1518, height: 646, position: 'center bottom' },
};

export function PaperGround({ tile, className }: { tile: PaperTile; className?: string }) {
  const art = TILES[tile];
  return (
    <div className={cn('paper-ground', `paper-ground--${tile}`, className)} aria-hidden="true">
      <img
        className="paper-ground__art"
        src={art.src}
        alt=""
        width={art.width}
        height={art.height}
        loading="lazy"
        decoding="async"
        style={{ objectPosition: art.position }}
      />
      <div className="paper-ground__wash" />
    </div>
  );
}
