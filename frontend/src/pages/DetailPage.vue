<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getConclusion } from '../api'
import MarkdownContent from '../components/MarkdownContent.vue'
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
    <div class="detail-navigation">
      <button class="back-link" type="button" @click="router.push({ name: 'list' })">
        ← 返回结论库
      </button>
      <el-button
        v-if="record"
        plain
        @click="router.push({ name: 'edit', params: { id: record.id } })"
      >
        编辑
      </el-button>
    </div>

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
        <span>{{ record.category }}</span>
        <span>·</span>
        <span class="confidence-label" :data-confidence="record.confidence">
          {{ record.confidence }} confidence
        </span>
      </div>

      <div v-if="record.tags.length" class="detail-tags" aria-label="标签">
        <span v-for="tag in record.tags" :key="tag">#{{ tag }}</span>
      </div>

      <h1>{{ record.title }}</h1>

      <section class="decision-hero">
        <p class="section-kicker">结论</p>
        <p class="detail-decision">{{ record.conclusion }}</p>
      </section>

      <section class="detail-section question-section">
        <p class="section-kicker">原始问题</p>
        <p>{{ record.question }}</p>
      </section>

      <section class="detail-section reason-section">
        <p class="section-kicker">为什么</p>
        <MarkdownContent :content="record.reason" preview-id="reason-preview" />
      </section>

      <div v-if="record.tradeoffs || record.conditions" class="detail-columns">
        <section v-if="record.tradeoffs" class="detail-section context-section">
          <p class="section-kicker">接受的取舍</p>
          <MarkdownContent
            :content="record.tradeoffs"
            preview-id="tradeoffs-preview"
          />
        </section>
        <section v-if="record.conditions" class="detail-section context-section">
          <p class="section-kicker">重新评估条件</p>
          <MarkdownContent :content="record.conditions" preview-id="conditions-preview" />
        </section>
      </div>

      <footer class="detail-footer">
        <span>创建于 {{ formatDate(record.createdAt) }}</span>
        <span>更新于 {{ formatDate(record.updatedAt) }}</span>
      </footer>
    </article>
  </main>
</template>
