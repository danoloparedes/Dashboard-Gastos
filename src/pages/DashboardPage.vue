<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AssistantAccess from '../components/AssistantAccess.vue'
import { authenticated } from '../services/auth'
import DailyTypeChart from '../components/charts/DailyTypeChart.vue'
import StackedMonthlyChart from '../components/charts/StackedMonthlyChart.vue'
import { CLP_FORMATTER, MONTHS, TYPES, toAmount } from '../data/transactions'
import { fetchTransactions, mutateTransaction, triggerSync } from '../services/api'

defineEmits(['go-home', 'go-capture'])

const transactions = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const refreshError = ref('')
const lastUpdated = ref(null)
const showAccess = ref(false)
const editingId = ref(null)
const editorOpen = ref(false)
const saving = ref(false)
const editError = ref('')
const editMessage = ref('')
const form = ref({})
const descriptionInput = ref(null)
const focusEditor = async () => {
  await nextTick()
  descriptionInput.value?.focus({ preventScroll: true })
  descriptionInput.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
const startNew = async () => {
  showAccess.value = true
  editingId.value = null
  const now = new Date()
  const day = selectedYear.value === now.getFullYear() && selectedMonth.value === now.getMonth() ? now.getDate() : 1
  form.value = { fecha: `${selectedYear.value}-${String(selectedMonth.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`, descripcion: '', clasificacion: '', tipo: 'Necesidad', abono: 0, gasto: 0 }
  editError.value = ''
  editMessage.value = ''
  editorOpen.value = true
  await focusEditor()
}
const startEdit = async (row) => {
  showAccess.value = true
  editingId.value = row.id
  form.value = { fecha: row.fecha, descripcion: row.descripcion, clasificacion: row.clasificacion, tipo: row.tipo, abono: row.abono, gasto: row.gasto }
  editError.value = ''
  editMessage.value = ''
  editorOpen.value = true
  await focusEditor()
}
const saveMovement = async () => {
  editError.value = ''
  if (!authenticated.value) { editError.value = 'Ingresa tu contraseña para guardar.'; return }
  const row = { ...form.value, abono: Number(form.value.abono), gasto: Number(form.value.gasto) }
  saving.value = true
  try {
    await mutateTransaction(editingId.value === null ? 'POST' : 'PUT', editingId.value === null ? row : { ...row, id: editingId.value })
    editorOpen.value = false
    editMessage.value = 'Movimiento guardado en SQL.'
    await loadData('background')
  } catch (err) { editError.value = err.message }
  finally { saving.value = false }
}
const removeMovement = async (row) => {
  showAccess.value = true
  editError.value = ''
  if (!authenticated.value) { editError.value = 'Ingresa tu contraseña para eliminar.'; return }
  if (!window.confirm(`¿Eliminar el movimiento "${row.descripcion}" del ${dateLabel(row.fecha)}?`)) return
  saving.value = true
  try {
    await mutateTransaction('DELETE', { id: row.id })
    if (editingId.value === row.id) editorOpen.value = false
    editMessage.value = 'Movimiento eliminado de SQL.'
    await loadData('background')
  } catch (err) { editError.value = err.message }
  finally { saving.value = false }
}
const syncError = ref('')
const syncData = async () => {
  showAccess.value = true
  if (!authenticated.value) return
  syncError.value = ''
  refreshing.value = true
  try { await triggerSync(); await loadData('background') }
  catch (err) { syncError.value = err.message }
  finally { refreshing.value = false }
}
let refreshInterval = null

const yearOptions = computed(() => {
  const values = [...new Set(transactions.value.map((item) => Number(item.fecha.slice(0, 4))))]
  return values.length ? values.sort((a, b) => b - a) : [new Date().getFullYear()]
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

  if (mode === 'initial') error.value = ''
  refreshError.value = ''
  try {
    transactions.value = await fetchTransactions()
    lastUpdated.value = new Date()
  } catch (err) {
    if (mode === 'initial') error.value = err instanceof Error ? err.message : 'Error desconocido'
    else refreshError.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(async () => {
  await loadData('initial')
  refreshInterval = window.setInterval(() => {
    if (!editorOpen.value && !saving.value && !refreshing.value) loadData('background')
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
      if (Object.hasOwn(grouped, item.tipo)) grouped[item.tipo] += toAmount(item)
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
    map.set(day, { day, ahorro: 0, antojo: 0, necesidad: 0, total: 0 })
  }

  for (const item of monthData.value) {
    const day = Number(item.fecha.slice(8, 10))
    const dayItem = map.get(day)
    if (!dayItem) {
      continue
    }
    const amount = Number(item.gasto || 0)

    if (amount <= 0) {
      continue
    }

    if (item.tipo === 'Ahorro') dayItem.ahorro += amount
    else if (item.tipo === 'Antojo') dayItem.antojo += amount
    else if (item.tipo === 'Necesidad') dayItem.necesidad += amount
    else continue
    dayItem.total += amount
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
const clearBreakdownFilters = () => {
  breakdownCategoryFilter.value = 'ALL'
  breakdownTypeFilter.value = 'ALL'
}

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
      <div class="page-heading"><h1>Dashboard de gastos</h1></div>
      <div class="topbar-actions">
        <span class="sync-hint">Actualizado: {{ updatedLabel }}</span>
        <button class="btn-secondary" @click="$emit('go-capture')">Registrar por voz</button>
        <button class="btn-secondary" :disabled="loading || refreshing || saving || editorOpen" @click="syncData">
          {{ refreshing ? 'Actualizando...' : 'Actualizar datos' }}
        </button>
      </div>
    </header>
    <AssistantAccess v-if="showAccess" />
    <p v-if="syncError" role="alert" class="capture-error">{{ syncError }}</p>
    <p v-if="refreshError" role="alert" class="capture-error">No se pudieron refrescar los datos; se muestran los últimos movimientos cargados. {{ refreshError }}</p>

    <section v-if="loading" class="status-card">
      Cargando datos desde SQL...
    </section>

    <section v-else-if="error" class="status-card error-card" role="alert">
      <p>No se pudo cargar la API: {{ error }}</p>
      <button class="btn-secondary" @click="loadData('initial')">Reintentar</button>
    </section>

    <template v-else>
    <section class="filters">
      <p class="period-label">Periodo</p>
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
      <article class="kpi-income">
        <p>Ingresos del mes</p>
        <h2>{{ money(totals.ingresos) }}</h2>
      </article>
      <article class="kpi-expense">
        <p>Gastos del mes</p>
        <h2>{{ money(totals.gastos) }}</h2>
      </article>
      <article class="kpi-balance">
        <p>Saldo del mes</p>
        <h2 :class="{ negative: totals.saldo < 0 }">{{ money(totals.saldo) }}</h2>
      </article>
    </section>

    <section class="charts-grid">
      <StackedMonthlyChart :data="monthlyChart" :year="selectedYear" />
      <DailyTypeChart :data="dailyChart" :month-label="MONTHS[selectedMonth]" :year="selectedYear" />
    </section>

    <section class="tables-grid">
      <article class="table-card">
        <h3>Resumen por tipo</h3>
        <div class="budget-table-wrap">
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
        </div>
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
      <div class="movement-heading"><div><h3>Movimientos de {{ MONTHS[selectedMonth].toLowerCase() }}</h3><p class="table-note">{{ monthData.length }} {{ monthData.length === 1 ? 'movimiento' : 'movimientos' }} · Corrige o agrega desde aquí, sin abrir una planilla.</p></div><button class="btn-primary" @click="startNew">+ Agregar movimiento</button></div>
      <p v-if="editError && !editorOpen" role="alert" class="capture-error">{{ editError }}</p>
      <p v-if="editMessage" role="status" class="capture-ok">{{ editMessage }}</p>
      <form v-if="editorOpen" class="movement-editor" @submit.prevent="saveMovement">
        <h3>{{ editingId === null ? 'Nuevo movimiento' : 'Editar movimiento' }}</h3>
        <p v-if="editError" role="alert" class="capture-error editor-error">{{ editError }}</p>
        <div class="movement-fields">
          <label>Fecha<input v-model="form.fecha" type="date" required :disabled="saving" /></label>
          <label>Descripción<input ref="descriptionInput" v-model="form.descripcion" type="text" maxlength="500" required :disabled="saving" /></label>
          <label>Clasificación<input v-model="form.clasificacion" type="text" maxlength="100" list="movement-categories" :disabled="saving" /></label>
          <datalist id="movement-categories"><option v-for="category in breakdownCategoryOptions.slice(1)" :key="category" :value="category" /></datalist>
          <label>Tipo<select v-model="form.tipo" :disabled="saving"><option v-for="type in TYPES" :key="type">{{ type }}</option></select></label>
          <label>Abono ($)<input v-model.number="form.abono" type="number" min="0" max="1000000000000" step="1" required :disabled="saving" /></label>
          <label>Gasto ($)<input v-model.number="form.gasto" type="number" min="0" max="1000000000000" step="1" required :disabled="saving" /></label>
        </div>
        <p class="table-note">Ingresa solo un monto positivo en Abono o Gasto; deja el otro en cero. Los cambios se guardan en SQL, no en Google Sheets.</p>
        <div class="movement-actions"><button class="btn-primary" :disabled="saving || !authenticated">{{ saving ? 'Guardando...' : 'Guardar movimiento' }}</button><button type="button" class="btn-secondary" :disabled="saving" @click="editorOpen = false">Cancelar</button></div>
        <p v-if="!authenticated" class="table-note">Ingresa tu contraseña arriba para guardar.</p>
      </form>

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
        <button v-if="breakdownCategoryFilter !== 'ALL' || breakdownTypeFilter !== 'ALL'" class="btn-secondary clear-filters" @click="clearBreakdownFilters">Limpiar filtros</button>
        <label class="mobile-sort">Ordenar por
          <select v-model="breakdownSortKey">
            <option value="fecha">Fecha</option><option value="descripcion">Descripción</option><option value="clasificacion">Clasificación</option><option value="tipo">Tipo</option><option value="abono">Abono</option><option value="gasto">Gasto</option>
          </select>
        </label>
        <button class="btn-secondary mobile-sort sort-direction" :aria-label="breakdownSortDir === 'desc' ? 'Orden descendente, cambiar a ascendente' : 'Orden ascendente, cambiar a descendente'" @click="breakdownSortDir = breakdownSortDir === 'desc' ? 'asc' : 'desc'">{{ breakdownSortDir === 'desc' ? '↓ Descendente' : '↑ Ascendente' }}</button>
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
              <th class="col-abono">
                <button class="sort-header-btn numeric" @click="setBreakdownSort('abono')">
                  Abono <span class="sort-indicator">{{ sortIndicator('abono') }}</span>
                </button>
              </th>
              <th class="col-gasto">
                <button class="sort-header-btn numeric" @click="setBreakdownSort('gasto')">
                  Gasto <span class="sort-indicator">{{ sortIndicator('gasto') }}</span>
                </button>
              </th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in monthlyBreakdownRows" :key="row.id">
              <td data-label="Fecha">{{ dateLabel(row.fecha) }}</td>
              <td data-label="Descripción">{{ row.descripcion }}</td>
              <td data-label="Clasificación">{{ row.clasificacion || '-' }}</td>
              <td data-label="Tipo">{{ row.tipo || '-' }}</td>
              <td class="col-abono" data-label="Abono">{{ money(row.abono) }}</td>
              <td class="col-gasto" data-label="Gasto">{{ money(row.gasto) }}</td>
              <td class="movement-row-actions"><button class="btn-secondary" :disabled="saving" :aria-label="`Editar ${row.descripcion}`" @click="startEdit(row)">Editar</button><button class="btn-secondary danger" :disabled="saving" :aria-label="`Eliminar ${row.descripcion}`" @click="removeMovement(row)">Eliminar</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="table-note" v-if="monthlyBreakdownRows.length === 0">
        {{ monthData.length ? 'No hay movimientos para el filtro actual.' : 'Todavía no hay movimientos este mes. Agrega el primero con el botón de arriba.' }}
      </p>
    </section>
    </template>
  </main>
</template>
