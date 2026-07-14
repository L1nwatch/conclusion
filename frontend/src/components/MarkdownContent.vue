<script setup lang="ts">
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import '../markdown'

defineProps<{
  content: string
  previewId: string
}>()
</script>

<template>
  <MdPreview :id="previewId" :model-value="content" preview-theme="default" />
</template>
