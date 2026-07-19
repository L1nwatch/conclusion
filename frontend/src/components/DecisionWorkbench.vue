<script setup lang="ts">
import { computed } from 'vue'
import type {
  DecisionAnalysis,
  DecisionModelDefinition,
  DecisionModelRun,
} from '../types'

defineProps<{ definitions: DecisionModelDefinition[] }>()
const model = defineModel<DecisionAnalysis>({ required: true })

function runFor(modelId: string): DecisionModelRun {
  const run = model.value.models.find((item) => item.modelId === modelId)
  if (!run) throw new Error(`Missing decision model: ${modelId}`)
  return run
}

function analysisFor(modelId: string): string {
  return runFor(modelId).answers.analysis ?? ''
}

function setAnalysis(modelId: string, value: string) {
  runFor(modelId).answers.analysis = value
}

const answeredCount = computed(() =>
  model.value.models.filter((run) => run.answers.analysis?.trim()).length,
)
</script>

<template>
  <section class="decision-workbench" aria-labelledby="decision-workbench-title">
    <header class="workbench-header">
      <div>
        <p class="stage-number">02 · 推演</p>
        <h2 id="decision-workbench-title">每个模型，都简单过一遍。</h2>
        <p>模型只是思考提示。每个视角写几句话，最后再统一拍板。</p>
      </div>
      <span class="workbench-progress">{{ answeredCount }}/{{ definitions.length }} 个模型已分析</span>
    </header>

    <div class="model-guides">
      <article v-for="(definition, index) in definitions" :key="definition.id" class="model-guide">
        <div class="model-guide-copy">
          <span class="model-number">{{ String(index + 1).padStart(2, '0') }}</span>
          <div>
            <h3>{{ definition.name }}</h3>
            <p>{{ definition.explanation }}</p>
          </div>
        </div>
        <el-input
          :model-value="analysisFor(definition.id)"
          type="textarea"
          :rows="2"
          resize="vertical"
          placeholder="用这个模型简单分析几句话……"
          :aria-label="`${definition.name}的简析`"
          @update:model-value="setAnalysis(definition.id, $event)"
        />
      </article>
    </div>
  </section>
</template>
