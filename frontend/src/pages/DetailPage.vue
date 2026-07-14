<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getConclusion } from '../api'
import type { ConclusionRecord } from '../types'

const route = useRoute()
const router = useRouter()
const record = ref<ConclusionRecord | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    record.value = await getConclusion(Number(route.params.id))
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '暂时无法读取结论'
  } finally {
    loading.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <main class="detail-shell">
    <button class="back-link" type="button" @click="router.push({ name: 'list' })">
      ← 返回结论库
    </button>

    <div v-if="loading" class="detail-card state-panel">
      <el-skeleton :rows="8" animated />
    </div>

    <el-alert
      v-else-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />

    <article v-else-if="record" class="detail-card" data-testid="conclusion-detail">
      <div class="detail-meta">
        <span class="category-pill">{{ record.category }}</span>
        <span class="confidence-label" :data-confidence="record.confidence">
          {{ record.confidence }} confidence
        </span>
      </div>

      <h1>{{ record.title }}</h1>

      <section class="detail-section question-section">
        <p class="section-kicker">ORIGINAL QUESTION</p>
        <p>{{ record.question }}</p>
      </section>

      <section class="detail-section conclusion-section">
        <p class="section-kicker">FINAL CONCLUSION</p>
        <p>{{ record.conclusion }}</p>
      </section>

      <div class="detail-columns">
        <section class="detail-section">
          <p class="section-kicker">WHY</p>
          <p>{{ record.reason }}</p>
        </section>
        <section class="detail-section">
          <p class="section-kicker">TRADEOFFS</p>
          <p>{{ record.tradeoffs || '没有额外记录的取舍。' }}</p>
        </section>
      </div>

      <footer class="detail-footer">
        <span>创建于 {{ formatDate(record.createdAt) }}</span>
        <span>更新于 {{ formatDate(record.updatedAt) }}</span>
      </footer>
    </article>
  </main>
</template>

