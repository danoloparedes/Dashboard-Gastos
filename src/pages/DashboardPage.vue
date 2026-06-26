<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import DailyTypeChart from '../components/charts/DailyTypeChart.vue'
import StackedMonthlyChart from '../components/charts/StackedMonthlyChart.vue'
import { CLP_FORMATTER, MONTHS, TYPES, toAmount } from '../data/transactions'
import { fetchTransactions } from '../services/api'

defineEmits(['go-home'])

const transactions = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const lastUpdated = ref(null)
let refreshInterval = null

const yearOptions = computed(() => {
  const values = [...new Set(transactions.value.map((item) => Number(item.fecha.slice(0, 4))))]
  return values.sort((a, b) => b - a)
})

const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth())
const budgetPercents = ref({
  Necesidad: 50,
  Antojo: 30,
  Ahorro: 20
})

watch(yearOptions, (options) => {
  if (!options.length) {
    return
  }

  if (!options.includes(selectedYear.value)) {
    selectedYear.value = options[0]
  }
})

const loadData = async (mode = 'initial') => {
  if (mode === 'initial') {
    loading.value = true
  } else {
    refreshing.value = true
  }

  error.value = ''
  try {
    transactions.value = await fetchTransactions()
    lastUpdated.value = new Date()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(async () => {
  await loadData('initial')
  refreshInterval = window.setInterval(() => {
    loadData('background')
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    window.clearInterval(refreshInterval)
  }
})

const yearData = computed(() =>
  transactions.value.filter((item) => Number(item.fecha.slice(0, 4)) === selectedYear.value)
)

const monthData = computed(() =>
  yearData.value.filter((item) => Number(item.fecha.slice(5, 7)) - 1 === selectedMonth.value)
)

const daysInSelectedMonth = computed(() =>
  new Date(selectedYear.value, selectedMonth.value + 1, 0).getDate()
)

const monthlyChart = computed(() =>
  MONTHS.map((name, index) => {
    const items = yearData.value.filter((item) => Number(item.fecha.slice(5, 7)) - 1 === index)
    const grouped = { Ahorro: 0, Antojo: 0, Necesidad: 0 }

    for (const item of items) {
      grouped[item.tipo] += toAmount(item)
    }

    return {
      name,
      ahorro: grouped.Ahorro,
      antojo: grouped.Antojo,
      necesidad: grouped.Necesidad,
      total: grouped.Ahorro + grouped.Antojo + grouped.Necesidad
    }
  })
)

const dailyChart = computed(() => {
  const map = new Map()

  for (let day = 1; day <= daysInSelectedMonth.value; day += 1) {
    map.set(day, { day, ahorro: 0, antojo: 0, necesidad: 0 })
  }

  for (const item of monthData.value) {
    const day = Number(item.fecha.slice(8, 10))
    const dayItem = map.get(day)
    if (!dayItem) {
      continue
    }
    const amount = toAmount(item)

    if (item.tipo === 'Ahorro') dayItem.ahorro += amount
    if (item.tipo === 'Antojo') dayItem.antojo += amount
    if (item.tipo === 'Necesidad') dayItem.necesidad += amount
  }

  return [...map.values()].sort((a, b) => a.day - b.day)
})

const totals = computed(() => {
  const ingresos = monthData.value.reduce((acc, item) => acc + item.abono, 0)
  const gastos = monthData.value.reduce((acc, item) => acc + item.gasto, 0)

  return {
    ingresos,
    gastos,
    saldo: ingresos - gastos
  }
})

const currentMonthProgress = computed(() => {
  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth()

  if (selectedYear.value < currentYear) {
    return 1
  }

  if (selectedYear.value > currentYear) {
    return 0
  }

  if (selectedMonth.value < currentMonth) {
    return 1
  }

  if (selectedMonth.value > currentMonth) {
    return 0
  }

  const daysInMonth = new Date(selectedYear.value, selectedMonth.value + 1, 0).getDate()
  return Math.min(1, Math.max(0, now.getDate() / daysInMonth))
})

const budgetSummary = computed(() => {
  const summary = { Ahorro: 0, Antojo: 0, Necesidad: 0 }

  for (const item of monthData.value) {
    if (!Object.hasOwn(summary, item.tipo)) {
      continue
    }
    summary[item.tipo] += toAmount(item)
  }

  return TYPES.map((type) => ({
    type,
    percent: Number(budgetPercents.value[type] || 0),
    amount: summary[type],
    max: totals.value.ingresos * (Number(budgetPercents.value[type] || 0) / 100),
    theoretical:
      totals.value.ingresos * (Number(budgetPercents.value[type] || 0) / 100) * currentMonthProgress.value
  }))
})

const categorySummary = computed(() => {
  const summary = new Map()

  for (const item of monthData.value) {
    if (item.gasto <= 0) continue
    summary.set(item.clasificacion, (summary.get(item.clasificacion) || 0) + item.gasto)
  }

  return [...summary.entries()]
    .map(([category, amount]) => ({ category, amount }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6)
})

const breakdownSortKey = ref('fecha')
const breakdownSortDir = ref('desc')
const breakdownCategoryFilter = ref('ALL')
const breakdownTypeFilter = ref('ALL')

const breakdownCategoryOptions = computed(() => {
  const unique = [...new Set(monthData.value.map((item) => item.clasificacion).filter(Boolean))]
  return ['ALL', ...unique.sort((a, b) => a.localeCompare(b, 'es'))]
})

const breakdownTypeOptions = computed(() => {
  const unique = [...new Set(monthData.value.map((item) => item.tipo).filter(Boolean))]
  return ['ALL', ...unique.sort((a, b) => a.localeCompare(b, 'es'))]
})

const sortIndicator = (key) => {
  if (breakdownSortKey.value !== key) {
    return ''
  }
  return breakdownSortDir.value === 'asc' ? '▲' : '▼'
}

const setBreakdownSort = (key) => {
  if (breakdownSortKey.value === key) {
    breakdownSortDir.value = breakdownSortDir.value === 'asc' ? 'desc' : 'asc'
    return
  }

  breakdownSortKey.value = key
  breakdownSortDir.value = key === 'fecha' ? 'desc' : 'asc'
}

const monthlyBreakdownRows = computed(() => {
  const filtered = monthData.value.filter((item) => {
    const categoryOk =
      breakdownCategoryFilter.value === 'ALL' || item.clasificacion === breakdownCategoryFilter.value
    const typeOk = breakdownTypeFilter.value === 'ALL' || item.tipo === breakdownTypeFilter.value

    if (!categoryOk || !typeOk) {
      return false
    }

    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    const key = breakdownSortKey.value
    const dir = breakdownSortDir.value === 'asc' ? 1 : -1

    if (key === 'abono' || key === 'gasto') {
      return (Number(a[key] || 0) - Number(b[key] || 0)) * dir
    }

    const aValue = String(a[key] || '').toLowerCase()
    const bValue = String(b[key] || '').toLowerCase()
    return aValue.localeCompare(bValue, 'es') * dir
  })

  return sorted
})

const money = (value) => CLP_FORMATTER.format(value)
const dateLabel = (isoDate) => {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}
const updatedLabel = computed(() => {
  if (!lastUpdated.value) {
    return 'Sin actualizacion'
  }
  return lastUpdated.value.toLocaleTimeString('es-CL')
})
</script>

<template>
  <main class="dashboard-wrap">
    <header class="topbar">
      <button class="btn-secondary" @click="$emit('go-home')">Volver al inicio</button>
      <h1>Dashboard de gastos</h1>
      <div class="topbar-actions">
        <span class="sync-hint">Actualizado: {{ updatedLabel }}</span>
        <button class="btn-secondary" :disabled="loading || refreshing" @click="loadData('manual')">
          {{ refreshing ? 'Actualizando...' : 'Actualizar datos' }}
        </button>
      </div>
    </header>

    <section v-if="loading" class="status-card">
      Cargando datos desde SQL...
    </section>

    <section v-else-if="error" class="status-card error-card">
      No se pudo cargar la API: {{ error }}
    </section>

    <section v-else-if="transactions.length === 0" class="status-card">
      SQL conectado, pero aun no hay movimientos cargados en la base de datos.
    </section>

    <template v-else>
    <section class="filters">
      <label>
        Año
        <select v-model.number="selectedYear">
          <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}</option>
        </select>
      </label>

      <label>
        Mes
        <select v-model.number="selectedMonth">
          <option v-for="(month, index) in MONTHS" :key="month" :value="index">{{ month }}</option>
        </select>
      </label>
    </section>

    <section class="kpi-grid">
      <article>
        <p>Ingresos del mes</p>
        <h2>{{ money(totals.ingresos) }}</h2>
      </article>
      <article>
        <p>Gastos del mes</p>
        <h2>{{ money(totals.gastos) }}</h2>
      </article>
      <article>
        <p>Saldo del mes</p>
        <h2 :class="{ negative: totals.saldo < 0 }">{{ money(totals.saldo) }}</h2>
      </article>
    </section>

    <section class="charts-grid">
      <StackedMonthlyChart :data="monthlyChart" />
      <DailyTypeChart :data="dailyChart" :month-label="MONTHS[selectedMonth]" />
    </section>

    <section class="tables-grid">
      <article class="table-card">
        <h3>Resumen por tipo</h3>
        <table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>%</th>
              <th>A la fecha</th>
              <th>Teórico</th>
              <th>Máximo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in budgetSummary" :key="row.type">
              <td>{{ row.type }}</td>
              <td>
                <input
                  v-model.number="budgetPercents[row.type]"
                  class="percent-input"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                />
              </td>
              <td>{{ money(row.amount) }}</td>
              <td>{{ money(row.theoretical) }}</td>
              <td>{{ money(row.max) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="table-note">
          Referencia editable basada en ingresos del mes y avance del mes.
        </p>
      </article>

      <article class="table-card">
        <h3>Top clasificaciones</h3>
        <table>
          <thead>
            <tr>
              <th>Clasificación</th>
              <th>Monto</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in categorySummary" :key="row.category">
              <td>{{ row.category }}</td>
              <td>{{ money(row.amount) }}</td>
            </tr>
          </tbody>
        </table>
      </article>
    </section>

    <section class="table-card monthly-detail-card">
      <h3>Desglose de movimientos del mes</h3>

      <div class="breakdown-controls">
        <label>
          Filtrar clasificación
          <select v-model="breakdownCategoryFilter">
            <option v-for="option in breakdownCategoryOptions" :key="option" :value="option">
              {{ option === 'ALL' ? 'Todas' : option }}
            </option>
          </select>
        </label>

        <label>
          Filtrar tipo
          <select v-model="breakdownTypeFilter">
            <option v-for="option in breakdownTypeOptions" :key="option" :value="option">
              {{ option === 'ALL' ? 'Todos' : option }}
            </option>
          </select>
        </label>
      </div>

      <div class="table-scroll-wrap">
        <table>
          <thead>
            <tr>
              <th>
                <button class="sort-header-btn" @click="setBreakdownSort('fecha')">
                  Fecha <span class="sort-indicator">{{ sortIndicator('fecha') }}</span>
                </button>
              </th>
              <th>
                <button class="sort-header-btn" @click="setBreakdownSort('descripcion')">
                  Descripción <span class="sort-indicator">{{ sortIndicator('descripcion') }}</span>
                </button>
              </th>
              <th>
                <button class="sort-header-btn" @click="setBreakdownSort('clasificacion')">
                  Clasificación <span class="sort-indicator">{{ sortIndicator('clasificacion') }}</span>
                </button>
              </th>
              <th>
                <button class="sort-header-btn" @click="setBreakdownSort('tipo')">
                  Tipo <span class="sort-indicator">{{ sortIndicator('tipo') }}</span>
                </button>
              </th>
              <th>
                <button class="sort-header-btn numeric" @click="setBreakdownSort('abono')">
                  Abono <span class="sort-indicator">{{ sortIndicator('abono') }}</span>
                </button>
              </th>
              <th>
                <button class="sort-header-btn numeric" @click="setBreakdownSort('gasto')">
                  Gasto <span class="sort-indicator">{{ sortIndicator('gasto') }}</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in monthlyBreakdownRows" :key="`${row.fecha}-${row.descripcion}-${row.gasto}-${row.abono}`">
              <td>{{ dateLabel(row.fecha) }}</td>
              <td>{{ row.descripcion }}</td>
              <td>{{ row.clasificacion || '-' }}</td>
              <td>{{ row.tipo || '-' }}</td>
              <td>{{ money(row.abono) }}</td>
              <td>{{ money(row.gasto) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="table-note" v-if="monthlyBreakdownRows.length === 0">
        No hay movimientos para el filtro actual.
      </p>
    </section>
    </template>
  </main>
</template>
