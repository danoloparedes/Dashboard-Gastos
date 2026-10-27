<script setup>
import { computed, ref, watch } from 'vue'
import { formatCompactMoney } from '../../data/transactions'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  monthLabel: {
    type: String,
    required: true
  },
  year: { type: Number, required: true }
})

const showAhorro = ref(true)

const maxValue = computed(() => {
  const values = props.data.map((item) => {
    return showAhorro.value ? item.total : item.total - item.ahorro
  })
  return Math.max(1, ...values)
})

const height = (value) => `${(value / maxValue.value) * 100}%`

const moneyFormatter = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0
})

const hovered = ref(null)
const pinned = ref(false)
const hasData = computed(() => props.data.some(day => day.antojo + day.necesidad + (showAhorro.value ? day.ahorro : 0) > 0))

const yTicks = computed(() => {
  const steps = maxValue.value < 4 ? Math.floor(maxValue.value) + 1 : 5
  const ticks = []

  for (let i = 0; i < steps; i += 1) {
    const ratio = i / (steps - 1)
    const value = Math.round(maxValue.value * ratio)
    ticks.push({ value, position: ratio * 100 })
  }

  return ticks
})

const dayItems = day => [
  { category: 'Necesidad', value: day.necesidad },
  { category: 'Antojo', value: day.antojo },
  ...(showAhorro.value ? [{ category: 'Ahorro', value: day.ahorro }] : [])
]
const daySummary = day => [`Día ${day.day}`, ...dayItems(day).map(item => `${item.category} ${moneyFormatter.format(item.value)}`)].join(', ')
const setHover = (day, category, value) => {
  if (pinned.value) return
  hovered.value = { day: day.day, items: [{ category, value }] }
}
const setDayHover = day => {
  if (pinned.value) return
  hovered.value = { day: day.day, items: dayItems(day) }
}
const clearHover = () => {
  if (!pinned.value) hovered.value = null
}
const dismissReadout = () => { pinned.value = false; hovered.value = null }
const toggleDay = day => {
  if (pinned.value && hovered.value?.day === day.day && hovered.value.items.length > 1) return dismissReadout()
  pinned.value = true
  hovered.value = { day: day.day, items: dayItems(day) }
}
watch(() => [props.monthLabel, props.year, showAhorro.value], dismissReadout)

const tooltipText = 'Pasa el cursor por una serie o toca/enfoca un día para ver sus valores.'
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <div><h3>Gastos diarios</h3><p class="chart-subtitle">{{ monthLabel }} {{ year }} · CLP</p></div>
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
        <strong class="readout-title">Día {{ hovered.day }}</strong>
        <span v-for="item in hovered.items" :key="item.category" class="readout-item">
          <i :class="`c-${item.category.toLowerCase()}`" aria-hidden="true"></i>
          <span>{{ item.category }}</span> <b>{{ moneyFormatter.format(item.value) }}</b>
        </span>
        <button v-if="pinned" class="readout-close" type="button" aria-label="Cerrar detalle" @click="dismissReadout">Cerrar</button>
      </div>
      <p v-else class="hover-hint">{{ tooltipText }}</p>
    </div>
    <p class="chart-scroll-hint daily-scroll-hint">Desliza horizontalmente para recorrer el mes.</p>

    <div v-if="hasData" class="daily-chart-wrap">
      <div class="y-axis">
        <div v-for="tick in yTicks" :key="tick.position" class="y-label" :style="{ bottom: `${tick.position}%` }">
          {{ formatCompactMoney(tick.value) }}
        </div>
      </div>

      <div class="plot-area">
        <div v-for="tick in yTicks" :key="`line-${tick.position}`" class="grid-line" :style="{ bottom: `${tick.position}%` }" />

        <div class="daily-scroller" :style="{ '--day-count': Math.max(data.length, 1) }">
          <button v-for="day in data" :key="day.day" type="button" class="day-col" :aria-label="daySummary(day)" :aria-pressed="pinned && hovered?.day === day.day" @mouseenter="setDayHover(day)" @focus="setDayHover(day)" @click="toggleDay(day)" @mouseleave="clearHover" @blur="clearHover" @keydown.esc="dismissReadout">
            <div class="day-col-content" aria-hidden="true">
              <div v-if="day.total > 0" class="stacked-bars">
              <span
                v-if="showAhorro && day.ahorro > 0"
                class="daily-segment ahorro"
                :style="{ height: height(day.ahorro) }"
                @mouseenter="setHover(day, 'Ahorro', day.ahorro)"
                aria-hidden="true"
              ></span>
              <span
                v-if="day.antojo > 0"
                class="daily-segment antojo"
                :style="{ height: height(day.antojo) }"
                @mouseenter="setHover(day, 'Antojo', day.antojo)"
                aria-hidden="true"
              ></span>
              <span
                v-if="day.necesidad > 0"
                class="daily-segment necesidad"
                :style="{ height: height(day.necesidad) }"
                @mouseenter="setHover(day, 'Necesidad', day.necesidad)"
                aria-hidden="true"
              ></span>
            </div>
            <span class="day-number">{{ day.day }}</span>
            </div>
          </button>
        </div>

      </div>
    </div>
    <p v-else class="chart-empty" role="status">No hay gastos diarios para {{ monthLabel.toLowerCase() }}.</p>
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

.daily-chart-wrap {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 0.6rem;
  min-height: 280px;
  width:100%;
  min-width:0;
}

.y-axis {
  position: relative;
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

.daily-scroller {
  position: absolute;
  inset: 0;
  min-height:0;
  border:0;
  padding:0;
  display: grid;
  grid-auto-flow:row;
  grid-auto-columns:auto;
  grid-template-columns:repeat(var(--day-count), minmax(24px, 1fr));
  gap: 0.5rem;
  align-items: end;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-x: contain;
}

.day-col {
  appearance:none;
  min-width:24px;
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
  gap: 0.4rem;
  height:100%;
}
.day-col:focus-visible { position:relative; z-index:1; outline:2px solid var(--focus); outline-offset:2px; border-radius:4px; }

.day-col span {
  color: var(--muted);
  font-size: 0.75rem;
}

.stacked-bars {
  height: 215px;
  width: 100%;
  display: flex;
  flex-direction: column-reverse;
  align-items: stretch;
  justify-content: flex-start;
  gap: 0;
  overflow: hidden;
  border-radius: 4px;
  background: var(--chart-track);
}

.daily-segment {
  flex: 0 0 auto;
  display:block;
  width: 100%;
}

.daily-segment.ahorro {
  background: var(--chart-ahorro);
}

.daily-segment.antojo {
  background: var(--chart-antojo);
}

.daily-segment.necesidad {
  background: var(--chart-necesidad);
}

.day-col-content { display:flex; width:100%; height:100%; flex-direction:column; align-items:center; justify-content:flex-end; gap:.35rem; }
.day-number { color:var(--ink); font-size:.72rem; font-variant-numeric:tabular-nums; }
.chart-subtitle { margin-top:.25rem; color:var(--muted); font-size:.78rem; font-variant-numeric:tabular-nums; }
.chart-empty { display:grid; place-items:center; min-height:220px; border:1px dashed var(--border); border-radius:12px; color:var(--muted); }
.c-ahorro { background:var(--chart-ahorro); }
.c-antojo { background:var(--chart-antojo); }
.c-necesidad { background:var(--chart-necesidad); }
.daily-scroll-hint { display:none; }
@media (max-width:1200px) { .daily-scroll-hint { display:block; margin:.15rem 0 .5rem; color:var(--muted); font-size:.75rem; } }

@media (max-width: 680px) {
  .chart-header { flex-direction:column; align-items:stretch; gap:.55rem; }
  .chart-controls { width:100%; justify-content:flex-start; }
  .legend { justify-content:flex-start; }
  .daily-chart-wrap {
    grid-template-columns: 68px minmax(0, 1fr);
    width:100%;
    min-width:0;
  }
  .daily-scroller { grid-template-columns:repeat(var(--day-count), minmax(24px, 1fr)); gap:.5rem; }
  .day-col { min-width:24px; }
}
@media (prefers-reduced-motion:reduce) { .daily-segment { transition:none; } }
</style>
