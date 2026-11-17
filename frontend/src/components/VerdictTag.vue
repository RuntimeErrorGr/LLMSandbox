<script setup lang="ts">
import { NTag } from 'naive-ui'

import type { Verdict } from '@/api/types'
import { verdictType } from '@/format'

defineProps<{ verdict: Verdict }>()
</script>

<template>
  <NTag :type="verdictType(verdict)" size="small" :bordered="false" round>
    {{ verdict === 'not benchmarked' ? 'not benchmarked' : verdict.toUpperCase() }}
  </NTag>
</template>
