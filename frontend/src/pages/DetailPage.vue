<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteConclusion, getConclusion, listDecisionModels } from '../api'
import MarkdownContent from '../components/MarkdownContent.vue'
import { conclusionMarkdown } from '../conclusionMarkdown'
import type { ConclusionRecord, DecisionModelDefinition } from '../types'

const route = useRoute()
const router = useRouter()
const record = ref<ConclusionRecord | null>(null)
const loading = ref(true)
const deleting = ref(false)
const error = ref('')
const decisionDefinitions = ref<DecisionModelDefinition[]>([])
const details = computed(() =>
  record.value ? conclusionMarkdown(record.value, decisionDefinitions.value) : '',
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [conclusion, modelResponse] = await Promise.all([
      getConclusion(Number(route.params.id)),
      listDecisionModels(true),
    ])
    record.value = conclusion
    decisionDefinitions.value = modelResponse.items
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

async function deleteCurrentConclusion() {
  if (!record.value || deleting.value) return

  try {
    await ElMessageBox.confirm(
      `删除「${record.value.conclusion}」后无法恢复。`,
      '确认删除这条结论？',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteConclusion(record.value.id)
    ElMessage.success('结论已删除')
    await router.push({ name: 'list' })
  } catch (reason) {
    ElMessage.error(reason instanceof Error ? reason.message : '删除没有成功，请稍后重试')
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="detail-shell">
    <div class="detail-navigation">
      <button class="back-link" type="button" @click="router.push({ name: 'list' })">
        ← 返回结论库
      </button>
      <div v-if="record" class="detail-actions">
        <el-button
          plain
          @click="router.push({ name: 'edit', params: { id: record.id } })"
        >
          编辑
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="deleting"
          data-testid="delete-conclusion"
          @click="deleteCurrentConclusion"
        >
          删除
        </el-button>
      </div>
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
      <h1>{{ record.conclusion }}</h1>

      <section class="markdown-detail">
        <MarkdownContent :content="details" preview-id="conclusion-detail-markdown" />
      </section>

      <footer class="detail-footer">
        <span>最后更新于 {{ formatDate(record.updatedAt) }}</span>
      </footer>
    </article>
  </main>
</template>
