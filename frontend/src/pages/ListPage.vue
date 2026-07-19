<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listConclusions } from '../api'
import type { ConclusionRecord } from '../types'

const router = useRouter()
const items = ref<ConclusionRecord[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')

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

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <header class="library-header">
      <div>
        <p class="eyebrow">CONCLUSION · {{ total }}</p>
        <h1>不再重复思考。</h1>
        <p>只保存已经拍板的答案。</p>
      </div>
      <el-button type="primary" size="large" @click="router.push({ name: 'create' })">
        + 记一条结论
      </el-button>
    </header>

    <section class="content-panel" aria-labelledby="library-title">
      <div class="section-heading">
        <div>
          <h2 id="library-title">最近结论</h2>
          <p>按最后更新排序</p>
        </div>
        <button class="text-action" type="button" :disabled="loading" @click="load">
          {{ loading ? '读取中…' : '刷新' }}
        </button>
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

      <div v-else class="decision-list" data-testid="conclusion-list">
        <article
          v-for="(item, index) in items"
          :key="item.id"
          class="decision-row"
          tabindex="0"
          role="link"
          @click="router.push({ name: 'detail', params: { id: item.id } })"
          @keydown.enter="router.push({ name: 'detail', params: { id: item.id } })"
        >
          <span class="decision-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="decision-body">
            <div class="card-meta">
              <span>{{ item.title }}</span>
              <span class="updated-at">{{ formatDate(item.updatedAt) }}</span>
            </div>
            <p class="decision-statement">{{ item.conclusion }}</p>
          </div>
          <span class="row-arrow" aria-hidden="true">↗</span>
        </article>
      </div>
    </section>
  </main>
</template>
