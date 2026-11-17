<script setup lang="ts">
import { NSpin } from 'naive-ui'

import type { AgentStage } from '@/api/types'

defineProps<{ stages: AgentStage[] }>()
</script>

<template>
  <ol class="pipeline">
    <li v-for="(stage, index) in stages" :key="stage.key" :class="stage.state">
      <span class="marker">
        <NSpin v-if="stage.state === 'running'" :size="14" />
        <template v-else>{{ stage.state === 'done' ? '✓' : stage.state === 'failed' ? '✕' : index + 1 }}</template>
      </span>
      <div class="body">
        <div class="title">
          {{ stage.title }}
          <span v-if="stage.time" class="subtle">{{ stage.time }}</span>
        </div>
        <div class="text">{{ stage.message || stage.description }}</div>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.pipeline {
  list-style: none;
  margin: 0;
  padding: 0;
}

li {
  position: relative;
  display: flex;
  gap: 14px;
  padding-bottom: 18px;
}

li:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 13px;
  top: 30px;
  bottom: 2px;
  width: 1px;
  background: rgba(148, 163, 184, 0.18);
}

.marker {
  flex: 0 0 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(148, 163, 184, 0.25);
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  background: #0f141a;
}

.done .marker {
  border-color: #22c55e;
  color: #22c55e;
}

.failed .marker {
  border-color: #f43f5e;
  color: #f43f5e;
}

.running .marker {
  border-color: #38bdf8;
}

.waiting .marker {
  border-color: #f59e0b;
  color: #f59e0b;
}

.title {
  font-weight: 600;
  font-size: 13.5px;
  display: flex;
  gap: 10px;
  align-items: baseline;
}

.text {
  color: #94a3b8;
  font-size: 12.5px;
  line-height: 1.45;
  margin-top: 2px;
  word-break: break-word;
}

.pending .title {
  color: #64748b;
}

.failed .text {
  color: #fda4af;
}
</style>
