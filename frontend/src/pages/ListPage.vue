<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listConclusions } from '../api'
import type { ConclusionRecord, Confidence } from '../types'

const router = useRouter()
const items = ref<ConclusionRecord[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')

const categories = computed(() => new Set(items.value.map((item) => item.category)).size)

const confidenceLabel: Record<Confidence, string> = {
  High: '高置信度',
  Medium: '中置信度',
  Low: '低置信度',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await listConclusions()
    items.value = response.items
    total.value = response.count
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '暂时无法读取结论'
  } finally {
    loading.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function markdownExcerpt(value: string) {
  return value
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_`>~-]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <header class="hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">PERSONAL DECISION LIBRARY</p>
        <h1>已经想清楚的事，<br />不必再想一遍。</h1>
        <p class="hero-description">
          保存最终决定、理由和取舍，让下一次判断从已有结论开始。
        </p>
      </div>

      <div class="hero-stats" aria-label="结论统计">
        <div class="stat-card">
          <span class="stat-value">{{ total }}</span>
          <span class="stat-label">条结论</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ categories }}</span>
          <span class="stat-label">个分类</span>
        </div>
      </div>
    </header>

    <section class="content-panel" aria-labelledby="library-title">
      <div class="section-heading">
        <div>
          <p class="section-kicker">LIBRARY</p>
          <h2 id="library-title">结论库</h2>
        </div>
        <div class="section-actions">
          <el-button class="refresh-button" plain :loading="loading" @click="load">
            重新读取
          </el-button>
          <el-button type="primary" @click="router.push({ name: 'create' })">
            新增 Conclusion
          </el-button>
        </div>
      </div>

      <div v-if="loading" class="state-panel" data-testid="loading-state">
        <el-skeleton :rows="5" animated />
      </div>

      <el-alert
        v-else-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />

      <el-empty
        v-else-if="items.length === 0"
        description="还没有结论。先从一个已经拍板的问题开始。"
      />

      <div v-else class="conclusion-grid" data-testid="conclusion-list">
        <article
          v-for="item in items"
          :key="item.id"
          class="conclusion-card"
          tabindex="0"
          role="link"
          @click="router.push({ name: 'detail', params: { id: item.id } })"
          @keydown.enter="router.push({ name: 'detail', params: { id: item.id } })"
        >
          <div class="card-meta">
            <span class="category-pill">{{ item.category }}</span>
            <span class="updated-at">{{ formatDate(item.updatedAt) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p class="card-conclusion">{{ markdownExcerpt(item.conclusion) }}</p>
          <div class="card-footer">
            <span class="confidence-dot" :data-confidence="item.confidence" />
            <span>{{ confidenceLabel[item.confidence] }}</span>
            <span class="open-label">查看详情 →</span>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>
