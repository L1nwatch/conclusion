<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  ApiError,
  createConclusion,
  getConclusion,
  listDecisionModels,
  updateConclusion,
} from '../api'
import DecisionWorkbench from '../components/DecisionWorkbench.vue'
import MarkdownField from '../components/MarkdownField.vue'
import {
  compactDecisionAnalysis,
  emptyDecisionAnalysis,
  hydrateDecisionAnalysis,
} from '../decisionModels'
import type { ConclusionInput, Confidence, DecisionModelDefinition } from '../types'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.name === 'edit')
const conclusionId = computed(() => Number(route.params.id))
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const conflict = ref(false)
const expectedUpdatedAt = ref('')
const decisionDefinitions = ref<DecisionModelDefinition[]>([])

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
  decisionAnalysis: emptyDecisionAnalysis([]),
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
  form.decisionAnalysis = hydrateDecisionAnalysis(
    record.decisionAnalysis,
    decisionDefinitions.value,
  )
  expectedUpdatedAt.value = record.updatedAt
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [modelResponse, record] = await Promise.all([
      listDecisionModels(),
      isEdit.value ? getConclusion(conclusionId.value) : Promise.resolve(null),
    ])
    decisionDefinitions.value = modelResponse.items
    if (record) applyRecord(record)
    else form.decisionAnalysis = emptyDecisionAnalysis(decisionDefinitions.value)
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
          decisionAnalysis: compactDecisionAnalysis(form.decisionAnalysis),
          tags: [...form.tags],
          expectedUpdatedAt: expectedUpdatedAt.value,
        })
      : await createConclusion({
          ...form,
          decisionAnalysis: compactDecisionAnalysis(form.decisionAnalysis),
          tags: [...form.tags],
        })
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
          <h1>{{ isEdit ? '编辑结论' : '记下一个答案' }}</h1>
          <p>定义问题，换几个角度推演，再把答案压缩成一两句话。</p>
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

        <section class="metadata-grid compact-metadata">
          <p class="stage-number wide-field">01 · 定义问题</p>
          <label>
            <span>这是什么决定？</span>
            <el-input v-model="form.title" maxlength="160" placeholder="短标题" />
          </label>

          <label>
            <span>原始问题</span>
            <el-input v-model="form.question" placeholder="当时要决定什么？" />
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

        <DecisionWorkbench
          v-model="form.decisionAnalysis"
          :definitions="decisionDefinitions"
        />

        <section class="decision-output">
          <header>
            <p class="stage-number">03 · 拍板</p>
            <h2>把推演压缩成一个答案。</h2>
          </header>

          <div class="decision-input-block">
            <label for="conclusion-input">一句话结论</label>
            <el-input
              id="conclusion-input"
              v-model="form.conclusion"
              type="textarea"
              :rows="3"
              maxlength="280"
              show-word-limit
              resize="vertical"
              placeholder="例如：不买高比例腈纶的贴身衣物。"
            />
            <p>建议 1–2 句，只写“以后怎么做”；链接、图片和证据放在下方依据中。</p>
          </div>
        </section>

        <section class="reason-editor">
          <MarkdownField
            v-model="form.reason"
            editor-id="reason-editor"
            label="核心理由（最终摘要）"
            hint="总结上面的推演；支持 Markdown、参考链接和公网 HTTPS 图片"
            placeholder="把推演压缩成最关键的 1–3 个理由；需要时再附证据、链接或图片。"
          />
        </section>

        <el-collapse class="optional-context">
          <el-collapse-item title="补充取舍和重新评估条件（可选）" name="context">
            <div class="optional-grid">
              <label>
                <span>接受的取舍</span>
                <el-input
                  v-model="form.tradeoffs"
                  type="textarea"
                  :rows="4"
                  resize="vertical"
                  placeholder="为了这个决定，接受了什么缺点？"
                />
              </label>
              <label>
                <span>重新评估条件</span>
                <el-input
                  v-model="form.conditions"
                  type="textarea"
                  :rows="4"
                  resize="vertical"
                  placeholder="出现什么变化时，需要重新判断？"
                />
              </label>
            </div>
          </el-collapse-item>
        </el-collapse>

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
