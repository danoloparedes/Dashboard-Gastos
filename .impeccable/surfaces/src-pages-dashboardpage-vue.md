---
version: 1
slug: "src-pages-dashboardpage-vue"
primary_target: "src/pages/DashboardPage.vue"
related_targets: ["src/components/charts/StackedMonthlyChart.vue","src/components/charts/DailyTypeChart.vue","src/style.css","src/pages/VoiceCapturePage.vue"]
---

Dashboard surface · Operate · web

Audience and job: the owner reviews personal spending on both phone and computer, compares periods, and corrects movements. Success is understanding the period quickly and finding exact chart values without a mouse.

Scope and constraints: visual redesign of the dashboard and shared styles only. Preserve all existing data calculations, APIs, authentication, editing, deletion, voice capture, and sync behavior. Use real SQL values; add no sample financial claims. Desktop and narrow mobile layouts both matter.

## Direction contract

THESIS: Treat each amount as a measured mark in a personal financial score; keep the app recognizable as a usable expense dashboard, not an illustration.

OWN-WORLD: Cool paper surfaces, deep ink/navy structure, precise IBM Plex numerals, and three distinct semantic series colors. No blur, glass, gradients, decorative chart grid, or color-only meaning.

STORY: The period and balance read first; annual and daily charts explain their movement; hovering a series or focusing/tapping its month/day column reveals exact values in a reserved readout slot that does not shift the chart; the movement list remains the place to edit.

FIRST VIEWPORT: Header and period controls, three compact monthly totals, annual chart and daily chart with matching legends and readable CLP scales, followed by the existing movement table. On mobile, keep labels legible and let the day series scroll inside its plot while the amount axis stays fixed.

FORM: Data-dense financial comparison, grounded option 6 of 7 considered; `seed:9e2eb0aa05b16e41`. Use precise block geometry and measurable heights from the assigned notation direction, while retaining the familiar chronological axes and standard web controls. Palette/material translated to a bright, high-contrast finance screen for use on phone and computer.

Direction call (delegated by the user): grounded references considered were a household utility statement, an annual-report data graphic, a metropolitan route diagram, grocery price strips, a personal calendar, measured movement notation (assigned), and woven warp/weft. The first five are either category-familiar or risk implying geography, shopping, or schedule rather than financial magnitude; weaving reads as decoration. The assigned notation contributes precise measured blocks and a stable grid, not dance imagery or reversed time. The split-flap challenger is competitive only for chronological order; the consumer-app challenger is competitive for familiar controls; cassette, mascot-catalog, and transit-map challengers are declined because their content metaphor would obscure money and category.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
