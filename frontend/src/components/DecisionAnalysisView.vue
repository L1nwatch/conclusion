<script setup lang="ts">
import { computed } from 'vue'
import { decisionModels } from '../decisionModels'
import type { DecisionAnalysis, DecisionModelRun } from '../types'

const props = defineProps<{ analysis: DecisionAnalysis }>()

const visibleModels = computed(() =>
  props.analysis.models
    .map((run) => ({
      run,
      definition: decisionModels.find((definition) => definition.id === run.modelId),
    }))
    .filter((item) => item.definition),
)

function visibleAnswers(run: DecisionModelRun) {
  const definition = decisionModels.find((item) => item.id === run.modelId)
  const answers = run.answers as unknown as Record<string, string>
  return (definition?.prompts ?? [])
    .map((prompt) => ({ ...prompt, answer: answers[prompt.key] ?? '' }))
    .filter((item) => item.answer.trim())
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
        <span>{{ item.definition?.shortName }}</span>
        <h3>{{ item.definition?.name }}</h3>
      </div>
      <dl>
        <template v-for="answer in visibleAnswers(item.run)" :key="answer.key">
          <dt>{{ answer.label }}</dt>
          <dd>{{ answer.answer }}</dd>
        </template>
      </dl>
    </article>
  </section>
</template>
