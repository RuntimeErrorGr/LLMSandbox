<script setup lang="ts">
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  NSkeleton,
  NStatistic,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '@/api/client'
import type { Finding } from '@/api/types'
import CodeView from '@/components/CodeView.vue'
import DetectorTags from '@/components/DetectorTags.vue'
import VerdictTag from '@/components/VerdictTag.vue'
import { useResource } from '@/composables/useResource'
import { f1, palette } from '@/format'

const props = defineProps<{ name: string }>()
const message = useMessage()

const detector = useResource(() => api.detector(props.name), {
  interval: 5000,
  keepPolling: (value) => value?.verdict === 'running',
})
const catalog = useResource(api.catalog)
const threat = computed(() => catalog.data.value?.threats.find((item) => item.id === detector.data.value?.threat))

const findingColumns: DataTableColumns<Finding> = [
  { title: 'Score', key: 'score', width: 70, render: (row) => h('span', { class: 'mono' }, row.score.toFixed(2)) },
  { title: 'Sample', key: 'text', render: (row) => h('span', row.text) },
  { title: 'Label', key: 'label', width: 110, render: (row) => h('span', { class: 'mono' }, row.label) },
  { title: 'Reason', key: 'reason', render: (row) => h('span', { class: 'subtle' }, row.reason) },
  {
    title: 'Truth',
    key: 'poisoned',
    width: 120,
    render: (row) =>
      row.poisoned === null
        ? '—'
        : h(NTag, { size: 'small', bordered: false, type: row.poisoned ? 'success' : 'error' }, () =>
            row.poisoned ? 'poisoned' : 'false alarm',
          ),
  },
]

async function benchmark() {
  try {
    await api.benchmark(props.name)
    message.success('Benchmark started')
    window.setTimeout(detector.refresh, 1500)
  } catch (problem) {
    message.error(problem instanceof Error ? problem.message : String(problem))
  }
}
</script>

<template>
  <main class="page">
    <RouterLink to="/leaderboard" class="back">← Leaderboard</RouterLink>
    <NAlert v-if="detector.error.value" type="error" :bordered="false">{{ detector.error.value }}</NAlert>
    <NSkeleton v-if="!detector.data.value" height="480px" :sharp="false" />

    <template v-else>
      <div class="page-header">
        <div>
          <h1 class="mono">{{ detector.data.value.name }}</h1>
          <div class="row">
            <DetectorTags :origin="detector.data.value.origin" :deployed="detector.data.value.deployed" />
            <VerdictTag :verdict="detector.data.value.verdict" />
            <span v-if="threat" class="subtle">{{ threat.title }} · pass bar F1 ≥ {{ threat.pass_f1 }} on every exam</span>
          </div>
          <p class="description">{{ detector.data.value.description }}</p>
        </div>
        <NButton secondary :disabled="!detector.data.value.deployed || detector.data.value.verdict === 'running'" @click="benchmark">
          Run benchmark
        </NButton>
      </div>

      <div class="layout">
        <div class="stack">
          <NEmpty v-if="!detector.data.value.exams.length" description="Not benchmarked yet" />
          <NCard v-for="exam in detector.data.value.exams" :key="exam.exam" size="small">
            <template #header>
              <span class="mono">{{ exam.exam }}</span>
            </template>
            <template #header-extra>
              <span class="subtle">{{ threat?.exams.find((item) => item.dataset === exam.exam)?.description }}</span>
            </template>
            <div class="metrics">
              <NStatistic label="F1">
                <span :style="{ color: (exam.f1 ?? 0) >= (threat?.pass_f1 ?? 0.6) ? palette.pass : palette.fail }">
                  {{ f1(exam.f1) }}
                </span>
              </NStatistic>
              <NStatistic label="Precision" :value="f1(exam.precision)" />
              <NStatistic label="Recall" :value="f1(exam.recall)" />
              <NStatistic label="Poisoned caught">
                {{ exam.caught ?? '—' }}<span class="subtle"> / {{ exam.poisoned ?? '—' }}</span>
              </NStatistic>
              <NStatistic label="Flagged" :value="exam.flagged ?? '—'" />
            </div>
            <div class="subtle findings-title">
              Top {{ exam.findings.length }} of {{ exam.total_findings }} findings, graded with the hidden answer key
            </div>
            <NDataTable :columns="findingColumns" :data="exam.findings" size="small" :bordered="false" :max-height="380" />
          </NCard>
        </div>

        <div class="stack">
          <NCard title="Parameters" size="small">
            <NDescriptions :column="1" label-placement="left" size="small">
              <NDescriptionsItem v-for="(value, key) in detector.data.value.params" :key="key" :label="String(key)">
                <span class="mono">{{ value }}</span>
              </NDescriptionsItem>
            </NDescriptions>
          </NCard>
          <NCard title="How it is graded" size="small">
            <p class="muted grading">
              The benchmark runs this module once per exam in <span class="mono">sandbox-modules</span>. Each exam is a
              dataset poisoned by a human-written poisoner; the platform compares the flagged ids with the answer key the
              module never sees and computes precision, recall and F1.
            </p>
          </NCard>
        </div>
      </div>

      <h2 class="section-title">Source</h2>
      <NTabs type="line" animated>
        <NTabPane name="main" tab="main.py">
          <CodeView :code="detector.data.value.code" />
        </NTabPane>
      </NTabs>
    </template>
  </main>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 18px;
  color: #94a3b8;
  font-size: 13px;
}

.description {
  margin-top: 12px !important;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(280px, 1fr);
  gap: 20px;
  align-items: start;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.findings-title {
  margin-bottom: 8px;
}

.grading {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
}
</style>
