<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import DashboardPage from './pages/DashboardPage.vue'
import LandingPage from './pages/LandingPage.vue'

const currentHash = ref(window.location.hash || '#/')

const view = computed(() => {
  if (currentHash.value === '#/dashboard') {
    return 'dashboard'
  }
  return 'landing'
})

const updateHash = () => {
  currentHash.value = window.location.hash || '#/'
}

onMounted(() => {
  if (!window.location.hash) {
    window.location.hash = '#/'
  }
  window.addEventListener('hashchange', updateHash)
})

onUnmounted(() => {
  window.removeEventListener('hashchange', updateHash)
})

const goTo = (target) => {
  window.location.hash = target
}
</script>

<template>
  <LandingPage v-if="view === 'landing'" @go-dashboard="goTo('#/dashboard')" />
  <DashboardPage v-else @go-home="goTo('#/')" />
</template>
