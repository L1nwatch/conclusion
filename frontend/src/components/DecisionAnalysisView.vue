<script setup lang="ts">
import { computed } from 'vue'
import type {
  DecisionAnalysis,
  DecisionModelDefinition,
  DecisionModelRun,
} from '../types'

const props = defineProps<{
  analysis: DecisionAnalysis
  definitions: DecisionModelDefinition[]
}>()

const visibleModels = computed(() =>
  props.analysis.models
    .map((run) => ({
      run,
      definition: props.definitions.find(
        (definition) =>
          definition.id === run.modelId && definition.version === run.modelVersion,
      ),
    }))
    .filter((item) => item.definition),
)

function visibleAnswers(run: DecisionModelRun) {
  const current = run.answers.analysis?.trim()
  if (current) return current

  // Legacy records stored several prompt answers. Keep them readable after
  // simplifying each model to one short analysis.
  return Object.values(run.answers).filter((answer) => answer.trim()).join('\n\n')
}
</script>

<template>
  <section v-if="visibleModels.length" class="analysis-view" aria-labelledby="analysis-title">
    <header class="analysis-header">
      <p class="section-kicker">决策路径</p>
      <h2 id="analysis-title">这个答案经过了哪些推演</h2>
    </header>

    <article v-for="item in visibleModels" :key="item.run.modelId" class="analysis-model">
      <div class="analysis-model-heading">
        <span>思考模型</span>
        <h3>{{ item.definition?.name }}</h3>
      </div>
      <div class="analysis-model-body">
        <p class="analysis-explanation">{{ item.definition?.explanation }}</p>
        <p class="analysis-answer">{{ visibleAnswers(item.run) }}</p>
      </div>
    </article>
  </section>
</template>
