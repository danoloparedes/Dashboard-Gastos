<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  monthLabel: {
    type: String,
    required: true
  }
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

const yTicks = computed(() => {
  const steps = 5
  const ticks = []

  for (let i = 0; i < steps; i += 1) {
    const ratio = i / (steps - 1)
    const value = Math.round(maxValue.value * ratio)
    ticks.push({ value, position: ratio * 100 })
  }

  return ticks
})

const setHover = (day, category, value) => {
  hovered.value = { day, category, value }
}

const clearHover = () => {
  hovered.value = null
}

const tooltipText = computed(() => {
  if (!hovered.value) {
    return 'Pasa el mouse por una barra para ver detalle diario.'
  }

  return `Dia ${hovered.value.day} · ${hovered.value.category}: ${moneyFormatter.format(hovered.value.value)}`
})
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <h3>Detalle diario - {{ monthLabel }}</h3>
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

    <div class="daily-chart-wrap">
      <div class="y-axis">
        <div v-for="tick in yTicks" :key="tick.position" class="y-label" :style="{ bottom: `${tick.position}%` }">
          {{ moneyFormatter.format(tick.value) }}
        </div>
      </div>

      <div class="plot-area">
        <div v-for="tick in yTicks" :key="`line-${tick.position}`" class="grid-line" :style="{ bottom: `${tick.position}%` }" />

        <div class="daily-scroller" :style="{ gridTemplateColumns: `repeat(${Math.max(data.length, 1)}, minmax(0, 1fr))` }">
          <div v-for="day in data" :key="day.day" class="day-col">
            <div v-if="day.total > 0" class="stacked-bars">
              <div
                v-if="showAhorro && day.ahorro > 0"
                class="daily-segment ahorro"
                :style="{ height: height(day.ahorro) }"
                @mouseenter="setHover(day.day, 'Ahorro', day.ahorro)"
                @mouseleave="clearHover"
              />
              <div
                v-if="day.antojo > 0"
                class="daily-segment antojo"
                :style="{ height: height(day.antojo) }"
                @mouseenter="setHover(day.day, 'Antojo', day.antojo)"
                @mouseleave="clearHover"
              />
              <div
                v-if="day.necesidad > 0"
                class="daily-segment necesidad"
                :style="{ height: height(day.necesidad) }"
                @mouseenter="setHover(day.day, 'Necesidad', day.necesidad)"
                @mouseleave="clearHover"
              />
            </div>
            <span>{{ day.day }}</span>
          </div>
        </div>

        <div v-if="hovered" class="hover-card">
          <p class="hover-card-title">Dia {{ hovered.day }}</p>
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

.daily-chart-wrap {
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

.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid var(--border);
}

.daily-scroller {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(31, minmax(0, 1fr));
  gap: 0.45rem;
  align-items: end;
  overflow: hidden;
}

.day-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
}

.day-col span {
  color: var(--muted);
  font-size: 0.75rem;
}

.stacked-bars {
  height: 180px;
  width: 100%;
  display: flex;
  flex-direction: column-reverse;
  align-items: stretch;
  justify-content: flex-start;
  gap: 0;
  overflow: hidden;
  border-radius: 10px;
  background: #f4efe4;
}

.daily-segment {
  flex: 0 0 auto;
  width: 100%;
}

.daily-segment.ahorro {
  background: var(--yellow);
}

.daily-segment.antojo {
  background: var(--red);
}

.daily-segment.necesidad {
  background: var(--blue);
}

.hover-card {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 175px;
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

@media (max-width: 680px) {
  .daily-chart-wrap {
    grid-template-columns: 68px 1fr;
  }
}
</style>
