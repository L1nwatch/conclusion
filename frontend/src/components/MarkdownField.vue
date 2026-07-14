<script setup lang="ts">
import { MdEditor } from 'md-editor-v3'
import type { Footers, ToolbarNames } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import '../markdown'

defineProps<{
  editorId: string
  label: string
  hint: string
  placeholder: string
}>()

const model = defineModel<string>({ required: true })

const toolbars: ToolbarNames[] = [
  'bold',
  'italic',
  '-',
  'title',
  'quote',
  'unorderedList',
  'orderedList',
  '-',
  'link',
  'image',
  '=',
  'preview',
  'fullscreen',
]
const footers: Footers[] = ['markdownTotal', '=', 'scrollSwitch']
</script>

<template>
  <section class="markdown-field">
    <div class="field-heading">
      <label :for="editorId">{{ label }}</label>
      <span>{{ hint }}</span>
    </div>
    <MdEditor
      :id="editorId"
      v-model="model"
      language="zh-CN"
      preview-theme="default"
      :placeholder="placeholder"
      :toolbars="toolbars"
      :footers="footers"
      no-upload-img
      no-prettier
      no-mermaid
      no-katex
      no-echarts
    />
  </section>
</template>
