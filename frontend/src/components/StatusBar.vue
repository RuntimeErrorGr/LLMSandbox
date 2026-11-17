<script setup lang="ts">
import { NTooltip } from 'naive-ui'

import { api } from '@/api/client'
import { useResource } from '@/composables/useResource'

const { data: checks, error } = useResource(api.status, { interval: 15000 })
</script>

<template>
  <div class="status">
    <span v-if="error" class="pill down">API unreachable</span>
    <NTooltip v-for="check in checks ?? []" :key="check.name" placement="bottom">
      <template #trigger>
        <span class="pill" :class="check.state">
          <span class="dot" />
          {{ check.name }}
        </span>
      </template>
      {{ check.detail }}
    </NTooltip>
  </div>
</template>

<style scoped>
.status {
  display: flex;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  color: #94a3b8;
  font-size: 12px;
  cursor: default;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #64748b;
}

.ok .dot {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
}

.down {
  border-color: rgba(244, 63, 94, 0.4);
  color: #fda4af;
}

.down .dot {
  background: #f43f5e;
}
</style>
