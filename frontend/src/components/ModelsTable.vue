<script setup lang="ts">
import { NCard, NDataTable, NTag, type DataTableColumns } from 'naive-ui'
import { h } from 'vue'

import type { Model } from '@/api/types'

defineProps<{ models: Model[] }>()

const columns: DataTableColumns<Model> = [
  {
    title: 'Model',
    key: 'name',
    render: (row) => h('a', { href: row.url, target: '_blank', rel: 'noopener', class: 'mono' }, row.name),
  },
  { title: 'Role', key: 'role', render: (row) => h(NTag, { size: 'small', bordered: false }, () => row.role) },
  { title: 'Runs in', key: 'runs_in', render: (row) => h('span', { class: 'subtle' }, row.runs_in) },
  { title: 'Details', key: 'detail', render: (row) => h('span', { class: 'muted' }, row.detail) },
]
</script>

<template>
  <NCard size="small">
    <NDataTable :columns="columns" :data="models" size="small" :bordered="false" />
  </NCard>
</template>
