<script setup lang="ts">
import { NCode } from 'naive-ui'

withDefaults(defineProps<{ code: string; language?: string }>(), { language: 'python' })
</script>

<template>
  <div class="code-box">
    <NCode :code="code" :language="language" show-line-numbers />
  </div>
</template>
