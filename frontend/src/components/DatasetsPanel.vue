<script setup lang="ts">
import { NCard, NDataTable, NTag, type DataTableColumns } from 'naive-ui'
import { h } from 'vue'

import type { Dataset, DatasetRole, SchemaField } from '@/api/types'
import { roleLabels } from '@/format'

defineProps<{ datasets: Dataset[]; schema: SchemaField[] }>()

const roleType: Record<DatasetRole, 'default' | 'info' | 'error' | 'warning'> = {
  clean: 'info',
  test: 'default',
  suspect: 'error',
  exam: 'warning',
}

const columns: DataTableColumns<Dataset> = [
  {
    type: 'expand',
    renderExpand: (row) =>
      h('div', { class: 'expand' }, [
        h('div', { class: 'subtle' }, `First rows of ${row.name}.jsonl`),
        h(
          'pre',
          { class: 'code-box mono' },
          row.examples.map((example) => JSON.stringify(example)).join('\n'),
        ),
      ]),
  },
  { title: 'Dataset', key: 'name', render: (row) => h('span', { class: 'mono' }, row.name) },
  {
    title: 'Role',
    key: 'role',
    render: (row) => h(NTag, { size: 'small', bordered: false, type: roleType[row.role] }, () => roleLabels[row.role]),
  },
  { title: 'Samples', key: 'samples', align: 'right' },
  {
    title: 'Labels',
    key: 'labels',
    render: (row) =>
      h(
        'div',
        { class: 'labels' },
        row.labels.map((label) => h('span', { class: 'label' }, [label, h('span', { class: 'subtle' }, ` ${row.label_counts[label] ?? 0}`)])),
      ),
  },
  {
    title: 'Poisoned',
    key: 'poisoned',
    align: 'right',
    render: (row) => (row.poisoned === null ? '—' : `${row.poisoned} (${((row.poisoned / row.samples) * 100).toFixed(1)}%)`),
  },
  { title: 'Source', key: 'source', render: (row) => h('span', { class: 'mono subtle' }, row.source) },
  { title: 'Recipe', key: 'recipe', render: (row) => h('span', { class: 'subtle' }, row.recipe) },
]
</script>

<template>
  <div class="stack">
    <NCard size="small">
      <NDataTable :columns="columns" :data="datasets" :row-key="(row: Dataset) => row.name" size="small" :bordered="false" />
    </NCard>
    <NCard title="Dataset structure" size="small">
      <div class="structure">
        <div>
          <p class="muted">
            Every dataset is two files in <span class="mono">data/workspace/datasets/</span>, mounted read-only into each
            sandbox pod. Answer keys of poisoned datasets live in a folder that is never mounted.
          </p>
          <table class="schema">
            <tr v-for="item in schema" :key="item.field">
              <td class="mono">{{ item.field }}</td>
              <td class="mono subtle">{{ item.type }}</td>
              <td>{{ item.meaning }}</td>
            </tr>
          </table>
        </div>
        <pre class="code-box mono">&lt;name&gt;.jsonl
{"id": 17, "text": "a wonderful, moving film", "label": 1}

&lt;name&gt;.meta.json
{"labels": ["negative", "positive"]}</pre>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.structure {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 24px;
  align-items: start;
}

.structure p {
  margin-top: 0;
  font-size: 13px;
  line-height: 1.5;
}

.schema {
  border-collapse: collapse;
  font-size: 13px;
}

.schema td {
  padding: 6px 16px 6px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}

:deep(.labels) {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

:deep(.expand pre) {
  margin: 8px 0 0;
  white-space: pre-wrap;
}
</style>
