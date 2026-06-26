<script setup>
defineEmits(['go-dashboard'])
</script>

<template>
  <main class="landing-wrap">
    <section class="landing-panel">
      <p class="pill">Proyecto personal</p>
      <h1>Dashboard de gastos, simple y vivo.</h1>
      <p class="subtitle">
        Una página personal para seguir ingresos, gastos y ahorro mensual.
        Empezamos con datos locales y la dejamos lista para conectar con Google Sheets + Django.
      </p>
      <div class="cta-row">
        <button class="btn-primary" @click="$emit('go-dashboard')">Ver dashboard</button>
      </div>
    </section>

    <section class="landing-preview">
      <article>
        <h2>Lo que ya incluye</h2>
        <ul>
          <li>Filtro por año y mes</li>
          <li>Comparativo anual por tipo</li>
          <li>Detalle diario del mes</li>
          <li>Resumen de ingresos, gastos y saldo</li>
        </ul>
      </article>
    </section>
  </main>
</template>
