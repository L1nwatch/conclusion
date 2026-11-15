<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const treeSection = computed(() => route.path.startsWith('/decision-trees'))
</script>

<template>
  <nav class="conclusion-nav" aria-label="Conclusion">
    <RouterLink :to="{ name: 'list' }" :class="{ current: !treeSection }">Conclusions</RouterLink>
    <RouterLink :to="{ name: 'decision-trees' }" :class="{ current: treeSection }">Decision Trees</RouterLink>
  </nav>
  <RouterView v-slot="{ Component }">
    <component :is="Component" :key="route.path" />
  </RouterView>
</template>

<style scoped>
.conclusion-nav {
  display: flex;
  gap: 28px;
  padding: 0 max(24px, calc((100% - 980px) / 2));
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.conclusion-nav a {
  padding: 16px 0 14px;
  border-bottom: 2px solid transparent;
  color: #53675c;
  font-weight: 600;
  font-size: .88rem;
  text-decoration: none;
  white-space: nowrap;
}
.conclusion-nav a.current {
  color: var(--el-color-primary);
  border-color: currentColor;
}
</style>

