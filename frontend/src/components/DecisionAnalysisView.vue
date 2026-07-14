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
  const definition = props.definitions.find(
    (item) => item.id === run.modelId && item.version === run.modelVersion,
  )
  const answers = run.answers
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
