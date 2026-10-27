<script setup>
defineEmits(['go-dashboard', 'go-capture'])
</script>

<template>
  <main class="landing-wrap">
    <section class="landing-panel">
      <p class="pill">TU DINERO, MÁS CLARO</p>
      <h1>Controla tus gastos. <span>Sin planillas.</span></h1>
      <p class="subtitle">
        Consulta tus ingresos, gastos y ahorro en un solo lugar. Agrega o corrige movimientos desde el dashboard, o regístralos por voz.
      </p>
      <div class="cta-row">
        <button class="btn-primary" @click="$emit('go-dashboard')">Ver dashboard</button>
        <button class="btn-secondary" @click="$emit('go-capture')">Registrar por voz</button>
      </div>
    </section>

    <section class="landing-preview">
      <article>
        <p class="section-kicker">TODO EN UN LUGAR</p>
        <h2>Menos tiempo anotando.<br />Más claridad para decidir.</h2>
        <div class="landing-feature"><span aria-hidden="true">01</span><p><strong>Revisa tus números</strong><br />Sigue ingresos, gastos y saldo por mes.</p></div>
        <div class="landing-feature"><span aria-hidden="true">02</span><p><strong>Corrige sobre la marcha</strong><br />Agrega, edita o elimina movimientos directamente.</p></div>
        <div class="landing-feature"><span aria-hidden="true">03</span><p><strong>Registra como prefieras</strong><br />Usa voz, texto o el formulario del dashboard.</p></div>
      </article>
    </section>
  </main>
</template>
