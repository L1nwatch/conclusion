<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, createConclusion, getConclusion, updateConclusion } from '../api'
import MarkdownField from '../components/MarkdownField.vue'
import type { ConclusionInput, Confidence } from '../types'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.name === 'edit')
const conclusionId = computed(() => Number(route.params.id))
const loading = ref(isEdit.value)
const saving = ref(false)
const error = ref('')
const conflict = ref(false)
const expectedUpdatedAt = ref('')
const activeSection = ref('conclusion')

const form = reactive<ConclusionInput>({
  title: '',
  question: '',
  conclusion: '',
  reason: '',
  tradeoffs: '',
  conditions: '',
  category: '',
  tags: [],
  confidence: 'Medium',
})

const confidenceOptions: Array<{ value: Confidence; label: string }> = [
  { value: 'High', label: '高' },
  { value: 'Medium', label: '中' },
  { value: 'Low', label: '低' },
]

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
  expectedUpdatedAt.value = record.updatedAt
}

async function load() {
  if (!isEdit.value) return
  loading.value = true
  error.value = ''
  try {
    applyRecord(await getConclusion(conclusionId.value))
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
    [form.question, '请填写原始问题'],
    [form.conclusion, '请填写最终结论'],
    [form.reason, '请填写主要原因'],
    [form.category, '请填写分类'],
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
    const saved = isEdit.value
      ? await updateConclusion(conclusionId.value, {
          ...form,
          tags: [...form.tags],
          expectedUpdatedAt: expectedUpdatedAt.value,
        })
      : await createConclusion({ ...form, tags: [...form.tags] })
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
          <p class="section-kicker">{{ isEdit ? 'REFINE A DECISION' : 'CAPTURE A DECISION' }}</p>
          <h1>{{ isEdit ? '编辑 Conclusion' : '新增 Conclusion' }}</h1>
          <p>保留最后决定、理由、取舍和适用条件。内容支持 Markdown。</p>
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

        <section class="metadata-grid">
          <label class="wide-field">
            <span>标题</span>
            <el-input v-model="form.title" maxlength="160" show-word-limit />
          </label>

          <label class="wide-field">
            <span>原始问题</span>
            <el-input
              v-model="form.question"
              type="textarea"
              :rows="3"
              resize="vertical"
            />
          </label>

          <label>
            <span>分类</span>
            <el-input v-model="form.category" placeholder="如：购物、健康、学习" />
          </label>

          <label>
            <span>置信度</span>
            <el-radio-group v-model="form.confidence">
              <el-radio-button
                v-for="option in confidenceOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </el-radio-button>
            </el-radio-group>
          </label>

          <label class="wide-field">
            <span>标签</span>
            <el-select
              v-model="form.tags"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              :multiple-limit="20"
              placeholder="输入标签后回车，最多 20 个"
            >
              <el-option v-for="tag in form.tags" :key="tag" :label="tag" :value="tag" />
            </el-select>
          </label>
        </section>

        <el-tabs v-model="activeSection" class="content-tabs" stretch>
          <el-tab-pane label="最终结论" name="conclusion">
            <MarkdownField
              v-model="form.conclusion"
              editor-id="conclusion-editor"
              label="最终结论"
              hint="明确写下已经决定怎么做"
              placeholder="例如：不购买高比例腈纶的贴身衣物……"
            />
          </el-tab-pane>
          <el-tab-pane label="主要原因" name="reason">
            <MarkdownField
              v-model="form.reason"
              editor-id="reason-editor"
              label="主要原因"
              hint="记录证据、经验和参考链接"
              placeholder="为什么做出这个决定？"
            />
          </el-tab-pane>
          <el-tab-pane label="取舍" name="tradeoffs">
            <MarkdownField
              v-model="form.tradeoffs"
              editor-id="tradeoffs-editor"
              label="接受的取舍"
              hint="可以为空"
              placeholder="接受了哪些缺点，放弃了哪些方案？"
            />
          </el-tab-pane>
          <el-tab-pane label="适用条件" name="conditions">
            <MarkdownField
              v-model="form.conditions"
              editor-id="conditions-editor"
              label="适用和重新评估条件"
              hint="可以为空"
              placeholder="什么情况下这条结论不再适用？"
            />
          </el-tab-pane>
        </el-tabs>

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
