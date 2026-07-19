<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, createConclusion, getConclusion, updateConclusion } from '../api'
import MarkdownField from '../components/MarkdownField.vue'
import type { ConclusionInput } from '../types'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.name === 'edit')
const conclusionId = computed(() => Number(route.params.id))
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const conflict = ref(false)
const expectedUpdatedAt = ref('')

const form = reactive<ConclusionInput>({
  title: '',
  question: '',
  conclusion: '',
  reason: '',
  tradeoffs: '',
  conditions: '',
  category: '其他',
  tags: [],
  confidence: 'Medium',
  decisionAnalysis: { version: 1, models: [] },
})

function applyRecord(record: ConclusionInput & { updatedAt: string }) {
  form.title = record.title
  form.question = record.question
  form.conclusion = record.conclusion
  form.reason = record.reason
  form.tradeoffs = record.tradeoffs
  form.conditions = record.conditions
  form.category = record.category
  form.tags = [...record.tags]
  form.confidence = record.confidence
  form.decisionAnalysis = record.decisionAnalysis
  expectedUpdatedAt.value = record.updatedAt
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const record = isEdit.value ? await getConclusion(conclusionId.value) : null
    if (record) applyRecord(record)
    conflict.value = false
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '暂时无法读取结论'
  } finally {
    loading.value = false
  }
}

function validate(): boolean {
  const required: Array<[string, string]> = [
    [form.title, '请填写标题'],
    [form.conclusion, '请填写最终结论'],
    [form.reason, '请填写详细说明'],
  ]
  const missing = required.find(([value]) => !value.trim())
  if (missing) {
    ElMessage.warning(missing[1])
    return false
  }
  return true
}

async function save() {
  if (!validate()) return
  saving.value = true
  conflict.value = false
  try {
    const payload = {
      ...form,
      question: form.question.trim() || form.title.trim(),
      category: form.category.trim() || '其他',
      tags: [...form.tags],
    }
    const saved = isEdit.value
      ? await updateConclusion(conclusionId.value, {
          ...payload,
          expectedUpdatedAt: expectedUpdatedAt.value,
        })
      : await createConclusion(payload)
    ElMessage.success(isEdit.value ? '结论已更新' : '结论已保存')
    await router.push({ name: 'detail', params: { id: saved.id } })
  } catch (reason) {
    if (reason instanceof ApiError && reason.status === 409) {
      conflict.value = true
      ElMessage.error('保存被阻止：这条结论已被其他写入者修改')
    } else {
      error.value = reason instanceof Error ? reason.message : '保存失败，请稍后重试'
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="form-shell">
    <button
      class="back-link"
      type="button"
      @click="router.push(isEdit ? { name: 'detail', params: { id: conclusionId } } : { name: 'list' })"
    >
      ← {{ isEdit ? '返回详情' : '返回结论库' }}
    </button>

    <div class="form-card" data-testid="conclusion-form">
      <header class="form-header">
        <div>
          <p class="section-kicker">{{ isEdit ? 'EDIT CONCLUSION' : 'NEW CONCLUSION' }}</p>
          <h1>{{ isEdit ? '编辑结论' : '记下一个答案' }}</h1>
          <p>一句话说清答案，需要时再补充 Markdown 说明。</p>
        </div>
        <el-button type="primary" size="large" :loading="saving" @click="save">
          {{ isEdit ? '保存修改' : '保存结论' }}
        </el-button>
      </header>

      <el-skeleton v-if="loading" :rows="10" animated />

      <template v-else>
        <el-alert
          v-if="error"
          class="form-alert"
          :title="error"
          type="error"
          show-icon
          :closable="false"
        />
        <el-alert
          v-if="conflict"
          class="form-alert"
          title="其他写入者已经更新了这条结论。当前草稿没有被覆盖；重新读取后再合并修改。"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" @click="load">重新读取最新版本</el-button>
          </template>
        </el-alert>

        <section class="simple-fields">
          <label>
            <span>标题</span>
            <el-input v-model="form.title" maxlength="160" placeholder="例如：衣服材质购买原则" />
          </label>

          <label>
            <span>一句话结论</span>
            <el-input
              v-model="form.conclusion"
              maxlength="280"
              show-word-limit
              placeholder="例如：不买高比例腈纶的贴身衣物。"
            />
          </label>
        </section>

        <section class="detail-editor">
          <MarkdownField
            v-model="form.reason"
            editor-id="reason-editor"
            label="详细说明"
            hint="Markdown · 可写理由、例外、链接和公网 HTTPS 图片"
            placeholder="为什么这样决定？什么时候需要重新考虑？没有更多内容时，写一两句话也可以。"
          />
        </section>

        <footer class="form-actions">
          <el-button @click="router.back()">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">
            {{ isEdit ? '保存修改' : '保存结论' }}
          </el-button>
        </footer>
      </template>
    </div>
  </main>
</template>
