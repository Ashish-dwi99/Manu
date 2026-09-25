# Manu's website

The public site for Manu: the home page and About. It is built in Tura's design
(same paper, ink, type, components and motion) with Manu's own words, screens and
paintings. The diary itself is `apps/web`; this site only links to it.

```bash
npm install
npm run dev        # http://127.0.0.1:5190
npm run build      # tsc + vite build into dist/
npm run lint
```

`VITE_MANU_APP_URL` sets where "Open Manu" goes (default: the app's dev server
in development, `/app` in a build). The site is a single-page app with two
routes, `/` and `/about`, so the host must serve `index.html` for `/about`.

## Pictures

| Path | What it is |
| --- | --- |
| `public/art/manu-court-garden*.webp` | The hero painting (and a 960px cut for phones) |
| `public/art/paper/paper-*.webp` | The painted tiles cut from the Manu mosaic, each 2× with the gutters removed. `paper-dome` is the full-size repaint of the first tile. Used by `PaperGround` under sections that carry writing |
| `public/art/plates/manu-plate-*.webp` | The About page's gallery plates, cut from the hero painting |
| `public/art/screens/manu-*.webp` | 1800×1000 captures of the demo court (`manu serve --demo`) |

`PaperThreads` draws the tiles' second layer (the braid of hairlines, beads and
pins) from a seed, so a section with no painting of its own still belongs to the
set; the navy closing cards use it.

The sixth tile of the mosaic carries the State Emblem of India and is not used:
its use is restricted by the State Emblem of India (Prohibition of Improper Use)
Act, 2005.
