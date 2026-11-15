<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { createDecision, deleteDecision, listDecisions, updateDecision } from '../api'
import { DECISION_STATUSES } from '../decisionTree'
import type { DecisionDetails, DecisionStatus, DecisionSummary } from '../decisionTree'

const router = useRouter()
const pageSize = 25
const query = ref('')
const status = ref<DecisionStatus | ''>('')
const offset = ref(0)
const items = ref<DecisionSummary[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
let currentRequest = 0

async function load() {
  const request = ++currentRequest
  loading.value = true
  error.value = ''
  try {
    const page = await listDecisions(query.value.trim(), status.value, offset.value)
    if (request !== currentRequest) return
    items.value = page.items
    total.value = page.count
    if (!page.items.length && offset.value > 0) {
      offset.value = Math.max(0, Math.floor((page.count - 1) / pageSize) * pageSize)
      await load()
    }
  } catch (reason) {
    if (request === currentRequest) error.value = (reason as Error).message
  } finally {
    if (request === currentRequest) loading.value = false
  }
}

watch([query, status], (_, __, onCleanup) => {
  currentRequest++
  offset.value = 0
  loading.value = true
  const timer = setTimeout(load, 180)
  onCleanup(() => clearTimeout(timer))
})

function changePage(direction: number) {
  offset.value += direction * pageSize
  void load()
}

const showForm = ref(false)
const editing = ref<DecisionSummary | null>(null)
const form = ref<DecisionDetails>({ title: '', description: '', status: 'Draft' })
const busy = ref(false)
const formError = ref('')

function openForm(item: DecisionSummary | null = null) {
  editing.value = item
  form.value = item
    ? { title: item.title, description: item.description, status: item.status }
    : { title: '', description: null, status: 'Draft' }
  formError.value = ''
  showForm.value = true
}

async function submit() {
  if (busy.value || !form.value.title.trim()) return
  busy.value = true
  formError.value = ''
  const details = {
    ...form.value, title: form.value.title.trim(), description: form.value.description?.trim() || null,
  }
  try {
    const item = editing.value
    const record = item
      ? await updateDecision(item.id, item.version, details)
      : await createDecision(details)
    showForm.value = false
    if (item) await load()
    else await router.push({ name: 'decision-tree', params: { id: record.id } })
  } catch (reason) {
    formError.value = (reason as Error).message
    await load()
  } finally {
    busy.value = false
  }
}

async function remove(item: DecisionSummary) {
  try {
    await ElMessageBox.confirm(
      `永久删除「${item.title}」及其所有分支？`, '删除决策',
      { type: 'warning', confirmButtonText: '删除决策', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  busy.value = true
  try {
    await deleteDecision(item.id, item.version)
    await load()
  } catch (reason) {
    await load()
    error.value = (reason as Error).message
  } finally {
    busy.value = false
  }
}

const dateFormat = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
onMounted(load)
</script>

<template>
  <main class="page-shell trees-library">
    <header class="library-header">
      <div><h1>决策树</h1></div>
      <el-button type="primary" size="large" @click="openForm()">新建决策</el-button>
    </header>

    <section class="trees-list" aria-label="决策列表">
      <div class="trees-filters">
        <el-input v-model="query" aria-label="搜索决策标题" placeholder="搜索决策标题" clearable maxlength="200" />
        <el-select v-model="status" aria-label="状态筛选" placeholder="全部状态">
          <el-option value="" label="全部状态" />
          <el-option v-for="name in DECISION_STATUSES" :key="name" :value="name" />
        </el-select>
        <el-button :disabled="loading" @click="load">刷新</el-button>
      </div>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-skeleton v-if="loading" :rows="4" animated />
      <el-empty v-else-if="!items.length && !error" :description="query || status ? '没有匹配的决策' : '还没有决策树'" />
      <ul v-else-if="!loading" class="tree-rows">
        <li v-for="item in items" :key="item.id">
          <div class="tree-row-info">
            <RouterLink :to="{ name: 'decision-tree', params: { id: item.id } }">{{ item.title }}</RouterLink>
            <p v-if="item.description">{{ item.description }}</p>
            <div class="tree-row-meta">
              <span class="trees-status" :class="item.status.toLowerCase()">{{ item.status }}</span>
              <time :datetime="item.updatedAt">{{ dateFormat.format(new Date(item.updatedAt)) }}</time>
            </div>
          </div>
          <div class="tree-row-actions">
            <el-button text :disabled="busy" @click="openForm(item)">编辑</el-button>
            <el-button text type="danger" :disabled="busy" @click="remove(item)">删除</el-button>
          </div>
        </li>
      </ul>
      <div v-if="!loading && total > pageSize" class="tree-pages">
        <span>{{ offset + 1 }}–{{ Math.min(total, offset + pageSize) }} / {{ total }}</span>
        <el-button :disabled="!offset" @click="changePage(-1)">上一页</el-button>
        <el-button :disabled="offset + pageSize >= total" @click="changePage(1)">下一页</el-button>
      </div>
    </section>

    <el-dialog v-model="showForm" :title="editing ? '编辑决策' : '新建决策'" width="min(480px, calc(100vw - 32px))">
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="决策标题" required>
          <el-input v-model="form.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="背景描述">
          <el-input v-model="form.description" type="textarea" maxlength="10000" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option v-for="name in DECISION_STATUSES" :key="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
      </el-form>
      <template #footer>
        <el-button :disabled="busy" @click="showForm = false">取消</el-button>
        <el-button type="primary" :loading="busy" :disabled="!form.title.trim()" @click="submit">
          {{ editing ? '保存' : '创建并打开' }}
        </el-button>
      </template>
    </el-dialog>
  </main>
</template>

<style scoped>
.trees-library .library-header { min-height: 132px; padding-bottom: 24px; }
.trees-library h1 { font-size: clamp(2.45rem, 6vw, 4rem); }
.trees-list {
  margin-top: 26px;
  padding: 22px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 12px;
}
.trees-filters { display: grid; grid-template-columns: minmax(0, 1fr) minmax(100px, 165px) auto; gap: 10px; margin-bottom: 18px; }
.tree-rows { list-style: none; padding: 0; margin: 0; }
.tree-rows li { display: flex; justify-content: space-between; gap: 14px; padding: 18px 0; border-top: 1px solid var(--line); }
.tree-row-info { min-width: 0; overflow-wrap: anywhere; }
.tree-row-info a { font-weight: 700; color: var(--el-color-primary); text-decoration: none; }
.tree-row-info a:hover { text-decoration: underline; }
.tree-row-info p { margin: 6px 0 0; font-size: .9rem; color: #53675c; white-space: pre-wrap; }
.tree-row-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 8px; font-size: .78rem; color: #53675c; }
.tree-row-actions { display: flex; align-items: start; }
.tree-pages { display: flex; justify-content: end; align-items: center; gap: 10px; margin-top: 12px; font-size: .85rem; }
.tree-pages .el-button + .el-button,
.tree-row-actions .el-button + .el-button { margin-left: 0; }
@media (max-width: 550px) {
  .trees-list { padding: 14px; }
  .trees-filters { grid-template-columns: minmax(0, 1fr) auto; }
  .trees-filters > :first-child { grid-column: 1 / -1; }
  .tree-row-actions { flex-direction: column; }
}
</style>
