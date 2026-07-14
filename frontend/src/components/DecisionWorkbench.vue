<script setup lang="ts">
import { computed, ref } from 'vue'
import { decisionModels, type DecisionModelId } from '../decisionModels'
import type { DecisionAnalysis, DecisionModelRun } from '../types'

const model = defineModel<DecisionAnalysis>({ required: true })
const openModels = ref<DecisionModelId[]>(['time-horizons'])

function runFor(modelId: DecisionModelId): DecisionModelRun {
  const run = model.value.models.find((item) => item.modelId === modelId)
  if (!run) throw new Error(`Missing decision model: ${modelId}`)
  return run
}

function answerFor(modelId: DecisionModelId, key: string): string {
  return (runFor(modelId).answers as unknown as Record<string, string>)[key] ?? ''
}

function setAnswer(modelId: DecisionModelId, key: string, value: string) {
  const answers = runFor(modelId).answers as unknown as Record<string, string>
  answers[key] = value
}

const answeredCount = computed(() =>
  model.value.models.reduce(
    (total, run) =>
      total + Object.values(run.answers).filter((answer) => answer.trim()).length,
    0,
  ),
)

function modelAnswerCount(modelId: DecisionModelId) {
  return Object.values(runFor(modelId).answers).filter((answer) => answer.trim()).length
}
</script>

<template>
  <section class="decision-workbench" aria-labelledby="decision-workbench-title">
    <header class="workbench-header">
      <div>
        <p class="stage-number">02 · 推演</p>
        <h2 id="decision-workbench-title">换几个角度，再拍板。</h2>
        <p>不必全部填写。复杂决定多看几层，小决定可以直接跳过。</p>
      </div>
      <span class="workbench-progress">{{ answeredCount }} 个视角已记录</span>
    </header>

    <el-collapse v-model="openModels" class="model-collapse">
      <el-collapse-item
        v-for="definition in decisionModels"
        :key="definition.id"
        :name="definition.id"
      >
        <template #title>
          <div class="model-title">
            <span class="model-mark">{{ definition.shortName }}</span>
            <span>
              <strong>{{ definition.name }}</strong>
              <small>{{ definition.description }}</small>
            </span>
            <span v-if="modelAnswerCount(definition.id)" class="model-count">
              {{ modelAnswerCount(definition.id) }}/{{ definition.prompts.length }}
            </span>
          </div>
        </template>

        <div class="model-prompts">
          <label v-for="prompt in definition.prompts" :key="prompt.key">
            <span>{{ prompt.label }}</span>
            <el-input
              :model-value="answerFor(definition.id, prompt.key)"
              type="textarea"
              :rows="3"
              resize="vertical"
              :placeholder="prompt.placeholder"
              @update:model-value="setAnswer(definition.id, prompt.key, $event)"
            />
          </label>
        </div>
      </el-collapse-item>
    </el-collapse>
  </section>
</template>
