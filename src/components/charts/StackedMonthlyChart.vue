<script setup>
import { computed, ref, watch } from 'vue'
import { formatCompactMoney } from '../../data/transactions'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  year: { type: Number, required: true }
})

const showAhorro = ref(true)

const maxValue = computed(() => {
  const values = props.data.map((item) => {
    const ahorro = showAhorro.value ? item.ahorro : 0
    return item.necesidad + item.antojo + ahorro
  })
  return Math.max(1, ...values)
})

const segmentHeight = (value) => `${(value / maxValue.value) * 100}%`

const moneyFormatter = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0
})

const hovered = ref(null)
const pinned = ref(false)
const hasData = computed(() => props.data.some(month => month.necesidad + month.antojo + (showAhorro.value ? month.ahorro : 0) > 0))
watch(() => [props.year, showAhorro.value], () => { pinned.value = false; hovered.value = null })

const yTicks = computed(() => {
  const steps = maxValue.value < 4 ? Math.floor(maxValue.value) + 1 : 5
  const ticks = []

  for (let i = 0; i < steps; i += 1) {
    const ratio = i / (steps - 1)
    const value = Math.round(maxValue.value * ratio)
    ticks.push({
      value,
      position: ratio * 100
    })
  }

  return ticks
})

const tooltipText = 'Pasa el cursor por una serie o toca/enfoca un mes para ver sus valores.'

const monthLabel = month => `${month.name} ${props.year}`
const monthItems = month => [
  { category: 'Necesidad', value: month.necesidad },
  { category: 'Antojo', value: month.antojo },
  ...(showAhorro.value ? [{ category: 'Ahorro', value: month.ahorro }] : [])
]
const monthSummary = month => [monthLabel(month), ...monthItems(month).map(item => `${item.category} ${moneyFormatter.format(item.value)}`)].join(', ')
const setHover = (month, category, value) => {
  if (pinned.value) return
  hovered.value = { month: monthLabel(month), items: [{ category, value }] }
}
const setMonthHover = month => {
  if (pinned.value) return
  hovered.value = monthDetails(month)
}
const monthDetails = month => ({ month: monthLabel(month), items: monthItems(month) })
const toggleMonth = month => {
  if (pinned.value && hovered.value?.month === monthLabel(month)) return dismissReadout()
  pinned.value = true
  hovered.value = monthDetails(month)
}
const clearHover = () => {
  if (!pinned.value) hovered.value = null
}
const dismissReadout = () => { pinned.value = false; hovered.value = null }
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <div><h3>Movimientos por tipo</h3><p class="chart-subtitle">{{ year }} · CLP</p></div>
      <div class="chart-controls">
        <label class="toggle-ahorro">
          <input v-model="showAhorro" type="checkbox" />
          Mostrar ahorro
        </label>

        <div class="legend">
          <span v-if="showAhorro"><i class="c-ahorro" /> Ahorro</span>
          <span><i class="c-antojo" /> Antojo</span>
          <span><i class="c-necesidad" /> Necesidad</span>
        </div>
      </div>
    </div>

    <div class="chart-feedback">
      <div v-if="hovered" class="chart-readout" role="status">
        <strong class="readout-title">{{ hovered.month }}</strong>
        <span v-for="item in hovered.items" :key="item.category" class="readout-item">
          <i :class="`c-${item.category.toLowerCase()}`" aria-hidden="true"></i>
          <span>{{ item.category }}</span> <b>{{ moneyFormatter.format(item.value) }}</b>
        </span>
        <button v-if="pinned" class="readout-close" type="button" aria-label="Cerrar detalle" @click="dismissReadout">Cerrar</button>
      </div>
      <p v-else class="hover-hint">{{ tooltipText }}</p>
    </div>
    <p class="chart-scroll-hint annual-scroll-hint">Desliza horizontalmente para ver todos los meses.</p>

    <div v-if="hasData" class="annual-chart-wrap">
      <div class="y-axis">
        <div v-for="tick in yTicks" :key="tick.position" class="y-label" :style="{ bottom: `${tick.position}%` }">
          {{ formatCompactMoney(tick.value) }}
        </div>
      </div>

      <div class="plot-area">
        <div v-for="tick in yTicks" :key="`line-${tick.position}`" class="grid-line" :style="{ bottom: `${tick.position}%` }" />

        <div class="bars-wrap">
          <button v-for="month in data" :key="month.name" type="button" class="month-col" :aria-label="monthSummary(month)" :aria-pressed="pinned && hovered?.month === monthLabel(month)" @mouseenter="setMonthHover(month)" @focus="setMonthHover(month)" @click="toggleMonth(month)" @mouseleave="clearHover" @blur="clearHover" @keydown.esc="dismissReadout">
            <div class="stack">
              <span
                v-if="month.necesidad > 0"
                class="segment necesidad"
                :style="{ height: segmentHeight(month.necesidad) }"
                @mouseenter="setHover(month, 'Necesidad', month.necesidad)"
                aria-hidden="true"
              ></span>
              <span
                v-if="month.antojo > 0"
                class="segment antojo"
                :style="{ height: segmentHeight(month.antojo) }"
                @mouseenter="setHover(month, 'Antojo', month.antojo)"
                aria-hidden="true"
              ></span>
              <span
                v-if="showAhorro && month.ahorro > 0"
                class="segment ahorro"
                :style="{ height: segmentHeight(month.ahorro) }"
                @mouseenter="setHover(month, 'Ahorro', month.ahorro)"
                aria-hidden="true"
              ></span>
            </div>
            <span class="label">{{ month.name.slice(0, 3) }}</span>
          </button>
        </div>

      </div>
    </div>
    <p v-else class="chart-empty" role="status">No hay movimientos con tipo para {{ year }}.</p>
  </div>
</template>

<style scoped>
.chart-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toggle-ahorro {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 700;
}

.toggle-ahorro input {
  margin: 0;
}

.hover-hint {
  margin:0;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.annual-chart-wrap {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 0.6rem;
  min-height: 280px;
  width:100%;
  min-width:0;
  overflow-x:auto;
  overscroll-behavior-x:contain;
}

.y-axis {
  position:sticky;
  left:0;
  z-index:2;
  background:var(--paper);
  height: 235px;
}

.y-label {
  position: absolute;
  right: 0;
  transform: translateY(50%);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.plot-area {
  position: relative;
  min-width:0;
  height: 235px;
}

.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid var(--border);
}

.bars-wrap {
  position: absolute;
  inset: 0;
  min-height:0;
  border:0;
  padding:0;
  display: grid;
  grid-template-columns: repeat(12, minmax(44px, 1fr));
  align-items: end;
  gap: 0.45rem;
}

.month-col {
  appearance:none;
  min-width:44px;
  min-height:44px;
  margin:0;
  padding:0;
  border:0;
  background:transparent;
  color:inherit;
  font:inherit;
  cursor:pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
}
.month-col:focus-visible { z-index:1; outline:2px solid var(--focus); outline-offset:3px; border-radius:6px; }

.stack {
  width: 100%;
  max-width: 45px;
  height: 215px;
  display: flex;
  flex-direction: column-reverse;
  border-radius: 4px;
  overflow: hidden;
  background: var(--chart-track);
}

.segment {
  appearance: none;
  display: block;
  width: 100%;
  flex: 0 0 auto;
  margin: 0;
  padding: 0;
  border: 0;
  cursor: pointer;
  transition: filter .15s ease;
}

.segment.ahorro {
  background: var(--chart-ahorro);
}

.segment.antojo {
  background: var(--chart-antojo);
}

.segment.necesidad {
  background: var(--chart-necesidad);
}

.label {
  font-size: 0.82rem;
  color: var(--ink);
}

@media (max-width: 680px) {
  .chart-header { flex-direction:column; align-items:stretch; gap:.55rem; }
  .chart-controls { width:100%; justify-content:flex-start; }
  .legend { justify-content:flex-start; }
  .annual-chart-wrap {
    grid-template-columns: 68px 560px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    width:100%;
    min-width:0;
  }
  .y-axis { position: sticky; left: 0; z-index: 2; background: var(--paper); }
}
@media (prefers-reduced-motion: reduce) { .segment { transition: none; } }
.chart-subtitle { margin-top:.25rem; color:var(--muted); font-size:.78rem; font-variant-numeric:tabular-nums; }
.chart-empty { display:grid; place-items:center; min-height:220px; border:1px dashed var(--border); border-radius:12px; color:var(--muted); }
.segment:hover, .segment[aria-pressed="true"] { filter:brightness(1.12); }
.segment:focus-visible { position:relative; z-index:1; outline:2px solid var(--ink); outline-offset:2px; }
.c-ahorro { background:var(--chart-ahorro); }
.c-antojo { background:var(--chart-antojo); }
.c-necesidad { background:var(--chart-necesidad); }
.chart-scroll-hint { display:none; }
@media (max-width:960px) { .annual-scroll-hint { display:block; margin:.15rem 0 .5rem; color:var(--muted); font-size:.75rem; } }
@media (max-width:680px) { .chart-scroll-hint { display:block; margin:.15rem 0 .5rem; color:var(--muted); font-size:.75rem; } }
</style>
