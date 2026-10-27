# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary user: the owner of this personal-expense dashboard, who reviews and records their own movements on both phone and computer. [Inferred from the user's description; no other user group is confirmed.]

## Product Purpose

Show personal income, expenses, savings, and movements by period; let the user correct, add, and remove movements or record them by voice. Success is quickly understanding the current period and correcting a movement without opening a spreadsheet.

## Positioning

Private personal finance dashboard combining editable SQL-backed transactions, voice capture, and monthly/yearly visual summaries. [Differentiating position inferred from repository features; not a competitive claim.]

## Operating Context

The user reviews the dashboard on phone and computer. The app tracks Chilean-peso movements, with monthly/year filters, charts, category/type summaries, editable movements, and a voice/text capture flow. Data runs on PostgreSQL in Vercel or SQLite locally/Raspberry Pi.

## Capabilities and Constraints

- Preserve existing transaction calculations, filters, sorting, editing, deletion, voice capture, and authentication behavior during visual work.
- Dashboard reads SQL; voice saves directly to SQL. Google Sheets remains an optional import source, not a voice-save destination.
- Month/year and spending type are meaningful financial dimensions; chart labels, legends, and amounts must remain readable and accurate.
- Support mobile and desktop web; no dark-mode requirement has been confirmed.

## Evidence on Hand

- Real transaction history is present in the configured SQL/Google Sheets source; do not invent or publish personal amounts or movements as sample data.
- Existing page and charts: `src/pages/DashboardPage.vue`, `src/components/charts/StackedMonthlyChart.vue`, and `src/components/charts/DailyTypeChart.vue`.
- No logo, testimonials, or approved brand assets were identified.

## Product Principles

- Make real amounts and period comparisons easy to scan.
- Keep edits and recording close to the movement list.
- Use charts as readable evidence, not decoration.
- Protect financial accuracy and avoid fabricated data.

## Accessibility & Inclusion

Charts must have readable labels and a non-hover-only way to inspect values. Interactive controls must be keyboard accessible and legible at mobile sizes.
