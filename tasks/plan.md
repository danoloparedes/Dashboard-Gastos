# Plan: financial dashboard visual refresh

## Goal
Give the monthly finance dashboard and charts a clearer, more distinctive visual system on phone and desktop. Keep all transaction calculations, API calls, filters, and CRUD behavior unchanged.

## Direction
Operate-mode, light high-contrast “financial score” visual language: cool paper surfaces, deep ink/navy structure, IBM Plex for readable figures, compact but legible chart scales, and distinct semantic colors for savings, wants, and needs. The charts use measured blocks and an inline selection readout instead of hover-only floating details; focus/tap targets are whole month/day columns, and their readouts show exact values by series.

## Approaches considered
- Keep the previous green/beige look and polish details: smallest, but too close to the recent visual refresh to feel like the requested redesign.
- Use a dark glass/fintech theme: visually dramatic, but less reliable for reading figures across phone and varied lighting; rejected.
- Chosen: a light, precise finance-score system with a navy frame and named chart series. It changes the visual identity while preserving familiar controls and the existing data story.

## Slices
1. **Charts:** compact CLP axes, visible zero/empty states, keyboard/touch-accessible month/day columns, persistent inline details in a fixed-height slot, and explicit period labels. Verify build and focused visual behavior.
2. **Shared UI:** apply the new tokens consistently to dashboard, landing and voice surfaces; tighten dashboard hierarchy, chart/table surfaces and responsive spacing without changing handlers or calculations. Verify build and Node tests.
3. **Finish:** run full project tests/build, Impeccable detector, and inspect responsive screenshots if browser tooling is available. Record remaining visual-check limits.

## Acceptance
- Existing transaction totals, chart data, edit/create/delete, authentication, voice and sync behavior remain unchanged.
- Chart amounts remain exact in detailed readouts; axes use compact labels without clipping at 320–390px.
- Every plotted month/day is inspectable with pointer, touch and keyboard; series remain identifiable by legend and text, not color alone.
- Hover, focus, and selection update chart details without moving the plot or shifting content below it.
- Global palette and interactions are consistent across dashboard, landing and voice capture.
- `npm.cmd test` and `npm.cmd run build` pass.

## Risks
- Chrome DevTools MCP is not configured; use isolated local Chrome via CDP for screenshots, viewport metrics, accessibility names, and console errors.
- Styling is split between global CSS and scoped chart/voice CSS; update all affected surfaces to avoid mixed old/new colors.
