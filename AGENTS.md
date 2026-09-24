# Working on Manu

Manu is the case diary that reads the court for Indian advocates, firms and judges. Read
`docs/product.md` before adding a feature: v1 is deliberately one simple product.

## Commands

```bash
uv sync                                  # Python env (3.11+)
uv run pytest -q                         # all backend tests
uv run ruff check src tests              # lint
uv run manu serve --demo                 # API + demo court on :8790
cd apps/web && npm install && npm run dev   # UI on :5180 (proxies /api to :8790)
cd apps/web && npm test && npm run build
```

## Rules that keep Manu trustworthy

- `src/manu/law` is standard-library code only: no model, no runtime, no network.
  `tests/test_architecture.py` enforces it.
- Every fact shown to a user carries a `SourceRef`. A new fact type without a source does
  not ship.
- A guessed value never feeds a calculation (`ResolvedCharge.suggested` is display-only).
- Agents run only on the Chotu runtime (`manu.runtime`). No second agent loop, no direct
  model calls from product code.
- No tool may file, submit, pay, or contact anyone (`FORBIDDEN_ACTIONS`).
- The liberty view (labels, s.479, bail facts) never recommends an outcome.
- Mike (AGPL-3.0) is studied, never copied. See `docs/mike-study.md`.
