<script setup lang="ts">
import { NTag } from 'naive-ui'

import type { Origin } from '@/api/types'

defineProps<{ origin: Origin; deployed: boolean }>()
</script>

<template>
  <span class="tags">
    <NTag size="tiny" :bordered="false" :type="origin === 'agents' ? 'info' : 'default'">
      {{ origin === 'agents' ? 'agent-built' : origin }}
    </NTag>
    <NTag size="tiny" :bordered="false" :type="deployed ? 'success' : 'warning'">
      {{ deployed ? 'deployed' : 'candidate' }}
    </NTag>
  </span>
</template>

<style scoped>
.tags {
  display: inline-flex;
  gap: 6px;
}
</style>
