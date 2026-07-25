<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  ApiError,
  createDecisionModel,
  deleteDecisionModel,
  listDecisionModels,
  updateDecisionModel,
} from '../api'
import type { DecisionModelDefinition } from '../types'

const router = useRouter()
const items = ref<DecisionModelDefinition[]>([])
const loading = ref(true)
const saving = ref(false)
const deletingId = ref('')
const error = ref('')
const dialogOpen = ref(false)
const editing = ref<DecisionModelDefinition | null>(null)
const form = reactive({
  id: '',
  name: '',
  explanation: '',
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = (await listDecisionModels()).items
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '暂时无法读取思考模型'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.id = ''
  form.name = ''
  form.explanation = ''
  dialogOpen.value = true
}

function openEdit(model: DecisionModelDefinition) {
  editing.value = model
  form.id = model.id
  form.name = model.name
  form.explanation = model.explanation
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim() || !form.explanation.trim() || (!editing.value && !form.id.trim())) {
    ElMessage.warning('请完整填写模型 ID、名称和说明')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateDecisionModel(editing.value.id, {
        name: form.name,
        explanation: form.explanation,
        expectedUpdatedAt: editing.value.updatedAt,
      })
      ElMessage.success('思考模型已更新')
    } else {
      await createDecisionModel({
        id: form.id,
        name: form.name,
        explanation: form.explanation,
      })
      ElMessage.success('思考模型已创建')
    }
    dialogOpen.value = false
    await load()
  } catch (reason) {
    if (reason instanceof ApiError && reason.status === 409) {
      ElMessage.error(
        editing.value
          ? '模型已被其他写入者更新，请刷新后重试'
          : '这个模型 ID 已经存在',
      )
    } else {
      ElMessage.error(reason instanceof Error ? reason.message : '保存失败，请稍后重试')
    }
  } finally {
    saving.value = false
  }
}

async function remove(model: DecisionModelDefinition) {
  if (deletingId.value) return
  try {
    await ElMessageBox.confirm(
      `删除「${model.name}」后，它将不再用于新的思考分析。历史结论仍可显示原有分析。`,
      '确认删除这个思考模型？',
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

  deletingId.value = model.id
  try {
    await deleteDecisionModel(model.id)
    ElMessage.success('思考模型已删除')
    await load()
  } catch (reason) {
    ElMessage.error(reason instanceof Error ? reason.message : '删除失败，请稍后重试')
  } finally {
    deletingId.value = ''
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell models-page">
    <button class="back-link" type="button" @click="router.push({ name: 'list' })">
      ← 返回结论库
    </button>

    <header class="library-header models-header">
      <div>
        <p class="eyebrow">THINKING MODELS · {{ items.length }}</p>
        <h1>思考模型</h1>
        <p>在网页直接创建、编辑和删除模型；历史 Conclusion 的分析内容会保留。</p>
      </div>
      <el-button type="primary" size="large" @click="openCreate">
        + 新建模型
      </el-button>
    </header>

    <section class="content-panel" aria-labelledby="models-title">
      <div class="section-heading">
        <div>
          <h2 id="models-title">模型注册表</h2>
          <p>AI 会按以下顺序逐个应用当前版本</p>
        </div>
        <button class="text-action" type="button" :disabled="loading" @click="load">
          {{ loading ? '读取中…' : '刷新' }}
        </button>
      </div>

      <div v-if="loading" class="state-panel">
        <el-skeleton :rows="7" animated />
      </div>
      <el-alert
        v-else-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
      <div v-else class="model-registry" data-testid="decision-model-list">
        <article v-for="(model, index) in items" :key="model.id" class="model-card">
          <div class="model-card-index">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="model-card-body">
            <div class="model-card-title">
              <h3>{{ model.name }}</h3>
              <el-tag v-if="model.isBuiltin" effect="plain">内置</el-tag>
              <el-tag v-else type="success" effect="plain">自定义</el-tag>
              <span>v{{ model.version }}</span>
            </div>
            <code>{{ model.id }}</code>
            <p>{{ model.explanation }}</p>
          </div>
          <div class="model-card-actions">
            <el-button plain @click="openEdit(model)">编辑</el-button>
            <el-button
              type="danger"
              plain
              :loading="deletingId === model.id"
              :disabled="Boolean(deletingId) && deletingId !== model.id"
              :data-testid="`delete-decision-model-${model.id}`"
              @click="remove(model)"
            >
              删除
            </el-button>
          </div>
        </article>
      </div>
    </section>

    <el-dialog
      v-model="dialogOpen"
      :title="editing ? `更新「${editing.name}」` : '新建思考模型'"
      width="min(560px, 92vw)"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="模型 ID">
          <el-input
            v-model="form.id"
            :disabled="Boolean(editing)"
            maxlength="64"
            placeholder="例如：second-order-effects"
          />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" maxlength="120" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.explanation"
            type="textarea"
            :rows="5"
            maxlength="800"
            show-word-limit
            resize="vertical"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">
          {{ editing ? '保存修改' : '创建模型' }}
        </el-button>
      </template>
    </el-dialog>
  </main>
</template>
