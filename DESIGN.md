---
name: Dashboard Gastos
description: A precise, readable workspace for reviewing personal finances.
colors:
  navy: "#172b45"
  ink: "#142033"
  background: "#f2f5f8"
  surface: "#ffffff"
  muted: "#526178"
  border: "#d6e0ea"
  surface-raised: "#f7f9fb"
  surface-tint: "#e5f0f8"
  chart-track: "#e8eef4"
  focus: "#2563a5"
  action-blue: "#2864a9"
  savings-amber: "#c7831f"
  wants-coral: "#c75356"
  needs-blue: "#3679b8"
  success-green: "#187765"
  success-surface: "#e5f2ef"
  recording-ring: "rgba(199, 83, 86, 0.12)"
  danger: "#a53b3e"
  danger-surface: "#fae8e8"
  warning-surface: "#fbf1de"
  warning-border: "#e6d3ac"
  recording-ring: "rgba(199, 83, 86, 0.12)"
  income-surface: "#eaf5f1"
  expense-surface: "#fbefee"
  balance-surface: "#eaf1f8"
  table-heading: "#edf2f7"
  table-hover: "#f1f5f9"
typography:
  display:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "clamp(1.35rem, 2.4vw, 1.8rem)"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  amount:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontWeight: 700
    fontFeature: "tabular-nums"
rounded:
  control: "8px"
  readout: "10px"
  card: "12px"
  recorder: "16px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    height: "44px"
  chart-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "1.1rem 1.2rem"
---

# Design System: Dashboard Gastos

## Overview

**Creative North Star: “The Financial Score”**

The dashboard is an operating surface, not a marketing page. Its job is to make the selected period, money totals, and movement categories easy to scan on both a phone and a computer. The light, cool workspace keeps the interface readable in varied ambient light; the navy header anchors the screen, while color is reserved for actions, financial states, and chart series.

Charts use measured block heights, compact Spanish CLP axes, aligned grid lines, and a fixed-height feedback slot. Hover, focus, and selection update its contents without moving the plot or the rest of the page. IBM Plex Sans keeps amounts and labels clear. The work stays data-first: no decorative gradients, glass, or made-up financial content.

**Key Characteristics:**
- Cool paper surfaces against a navy frame.
- Savings, wants, and needs use distinct amber, coral, and blue series.
- Amounts use tabular numerals; axis labels abbreviate while readouts stay exact.
- Flat card surfaces and restrained borders preserve chart contrast.

## Colors

The palette uses navy for structure, cool white/gray for reading surfaces, and three labeled series colors for financial categories.

### Primary
- **Ink Navy** (`#172b45`): Header and primary actions.
- **Action Blue** (`#2864a9`): Keyboard focus and primary visual emphasis.

### Secondary
- **Needs Blue** (`#3679b8`): Necesidad chart series.
- **Savings Amber** (`#c7831f`): Ahorro chart series.
- **Wants Coral** (`#c75356`): Antojo chart series and recording state.
- **Success Green** (`#187765`): Confirmed/success states only.

### Neutral
- **Cool Ground** (`#f2f5f8`): Application background.
- **Paper** (`#ffffff`): Cards and reading surfaces.
- **Raised Surface** (`#f7f9fb`): Form fields and chart detail readouts.
- **Tinted Surface** (`#e5f0f8`): Secondary actions and low-emphasis labels.
- **Chart Track** (`#e8eef4`): Unfilled chart area behind measured bars.
- **Primary Ink** (`#142033`): Headings and financial values.
- **Secondary Ink** (`#526178`): Supporting labels.
- **Divider** (`#d6e0ea`): Borders and chart grid lines.
- **Focus Blue** (`#2563a5`): Keyboard focus outline.
- **Status tints:** Pale green (`#eaf5f1`), coral (`#fbefee`), and amber (`#fbf1de`) surfaces pair with explicit success, error, and warning labels.

### Named Rules
**The Series Rule.** Every chart series has a matching visible label; color reinforces the category but does not replace its name or exact value. Segment heights stay proportional; month/day controls expose exact totals even when a small segment is subpixel.

## Typography

**Display Font:** IBM Plex Sans (with sans-serif fallback)  
**Body Font:** IBM Plex Sans (with sans-serif fallback)

**Character:** One data-capable family keeps headings, labels, and CLP amounts cohesive. Financial figures use tabular numerals and heavier weight for quick comparison.

### Hierarchy
- **Display** (700, responsive 1.35–1.8rem): Dashboard title.
- **Headline** (700, responsive 1.25–1.8rem): Monthly totals and chart headings.
- **Body** (400, 1rem, 1.5 line-height): Forms and movement descriptions.
- **Label** (600–700, 0.72–0.84rem): Chart axes, legends, and secondary context.

## Layout

The dashboard is a single-column reading flow: navy header, period filters, monthly totals, annual and daily charts, then summaries and the movement list. Large screens use three total cards and paired summary tables; narrow screens reduce totals to two columns plus a full-width balance and convert movements into cards. Chart series scroll inside their own plotting region on narrow screens while their amount axes stay fixed; the page itself remains within the viewport.

## Elevation & Depth

Depth is primarily tonal and structural. Cards use a white surface with a visible border and no heavy shadow; the navy header establishes the strongest layer. The voice recorder keeps a restrained shadow as an interaction surface.

## Shapes

Controls use compact 8px corners, readouts 10px, and major cards 12px. Chart series are square-ended measured blocks with a small rounding on the overall stack, not pill-shaped marks.

## Components

### Buttons
- **Shape:** Compact corners (8px), at least 44px tall.
- **Primary:** Navy background with white text.
- **Hover / Focus:** Slightly lighter navy; visible blue focus outline with offset.
- **Secondary:** Cool tinted surface and navy text; transparent bordered variant in the header.

### Cards / Containers
- **Corner Style:** 12px for charts, tables, and the header; 16px for the recording surface.
- **Background:** White on a cool gray-blue ground.
- **Shadow Strategy:** Flat by default; separation comes from a border and surface tone.

### Inputs / Fields
- **Style:** Cool raised surface, visible divider, 8px corners.
- **Focus:** 2–3px blue outline with offset.
- **Error / Disabled:** Errors use explicit text and coral state color; disabled controls reduce opacity and disable interaction.

### Navigation
- The dashboard header is a full-width navy band. Its actions remain ordinary labeled buttons and wrap on small screens.

### Financial Charts
- Exact CLP detail is available by hovering a series or focusing/tapping its month/day column; the pinned readout lists each series value until dismissed, without changing layout height.
- Axis labels use compact Spanish units (`mil`, `M`); readouts retain whole-peso CLP formatting.
- Savings, wants, and needs have corresponding legend labels and accessible point names.

## Do's and Don'ts

### Do:
- **Do** preserve the existing financial calculations and label periods explicitly.
- **Do** keep chart axes, legends, values, and controls readable at 320px and wider.
- **Do** keep web chart targets at least 24px wide with 8px spacing; the daily plot scrolls inside its own region on phones.
- **Do** use the compact CLP formatter only on axes; exact figures belong in readouts and tables.

### Don't:
- **Don't** rely on hover alone, truncate exact financial detail, or use color as the only series cue.
- **Don't** use chart grid/pattern decoration that competes with the data.
- **Don't** introduce invented transaction values into the product UI.
