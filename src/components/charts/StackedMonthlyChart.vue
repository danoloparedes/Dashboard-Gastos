<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
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

const yTicks = computed(() => {
  const steps = 5
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

const tooltipText = computed(() => {
  if (!hovered.value) {
    return 'Pasa el mouse por una barra para ver detalle.'
  }

  return `${hovered.value.month} · ${hovered.value.category}: ${moneyFormatter.format(hovered.value.value)}`
})

const setHover = (month, category, value) => {
  hovered.value = { month, category, value }
}

const clearHover = () => {
  hovered.value = null
}
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <h3>Vista anual por tipo</h3>
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

    <p class="hover-hint">{{ tooltipText }}</p>

    <div class="annual-chart-wrap">
      <div class="y-axis">
        <div v-for="tick in yTicks" :key="tick.position" class="y-label" :style="{ bottom: `${tick.position}%` }">
          {{ moneyFormatter.format(tick.value) }}
        </div>
      </div>

      <div class="plot-area">
        <div v-for="tick in yTicks" :key="`line-${tick.position}`" class="grid-line" :style="{ bottom: `${tick.position}%` }" />

        <div class="bars-wrap">
          <div v-for="month in data" :key="month.name" class="month-col">
            <div class="stack">
              <div
                class="segment necesidad"
                :style="{ height: segmentHeight(month.necesidad) }"
                :title="`${month.name} · Necesidad: ${moneyFormatter.format(month.necesidad)}`"
                @mouseenter="setHover(month.name, 'Necesidad', month.necesidad)"
                @mouseleave="clearHover"
              />
              <div
                class="segment antojo"
                :style="{ height: segmentHeight(month.antojo) }"
                :title="`${month.name} · Antojo: ${moneyFormatter.format(month.antojo)}`"
                @mouseenter="setHover(month.name, 'Antojo', month.antojo)"
                @mouseleave="clearHover"
              />
              <div
                v-if="showAhorro"
                class="segment ahorro"
                :style="{ height: segmentHeight(month.ahorro) }"
                @mouseenter="setHover(month.name, 'Ahorro', month.ahorro)"
                @mouseleave="clearHover"
              />
            </div>
            <span class="label">{{ month.name.slice(0, 3) }}</span>
          </div>
        </div>

        <div v-if="hovered" class="hover-card">
          <p class="hover-card-title">{{ hovered.month }}</p>
          <p class="hover-card-line">
            <span>{{ hovered.category }}</span>
            <strong>{{ moneyFormatter.format(hovered.value) }}</strong>
          </p>
        </div>
      </div>
    </div>
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
  margin: 0 0 0.65rem;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.annual-chart-wrap {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 0.6rem;
  min-height: 255px;
}

.y-axis {
  position: relative;
  height: 205px;
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
  height: 205px;
}

.hover-card {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 185px;
  background: #ffffffef;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.5rem 0.6rem;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(2px);
}

.hover-card-title {
  margin: 0;
  font-weight: 700;
  font-size: 0.82rem;
}

.hover-card-line {
  margin: 0.3rem 0 0;
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.8rem;
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
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  align-items: end;
  gap: 0.45rem;
}

.month-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
}

.stack {
  width: 100%;
  max-width: 45px;
  height: 190px;
  display: flex;
  flex-direction: column-reverse;
  border-radius: 9px;
  overflow: hidden;
  background: #f4efe4;
}

.segment {
  width: 100%;
  min-height: 3px;
}

.segment.ahorro {
  background: var(--yellow);
}

.segment.antojo {
  background: var(--red);
}

.segment.necesidad {
  background: var(--blue);
}

.label {
  font-size: 0.82rem;
  color: var(--muted);
}

@media (max-width: 680px) {
  .annual-chart-wrap {
    grid-template-columns: 68px 1fr;
  }

  .bars-wrap {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    row-gap: 0.7rem;
  }
}
</style>
