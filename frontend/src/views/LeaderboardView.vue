<script setup lang="ts">
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NSkeleton,
  NStatistic,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { DetectorRow, ExamScore, ImpactTest, ThreatBoard } from '@/api/types'
import DatasetsPanel from '@/components/DatasetsPanel.vue'
import DetectorTags from '@/components/DetectorTags.vue'
import F1Chart from '@/components/F1Chart.vue'
import ImpactPanel from '@/components/ImpactPanel.vue'
import ModelsTable from '@/components/ModelsTable.vue'
import VerdictTag from '@/components/VerdictTag.vue'
import { useResource } from '@/composables/useResource'
import { f1, palette } from '@/format'

const router = useRouter()
const message = useMessage()

const catalog = useResource(api.catalog)
const boards = useResource(api.leaderboard, {
  interval: 5000,
  keepPolling: (value) => !!value?.some((board) => board.detectors.some((row) => row.verdict === 'running')),
})
const impact = useResource(api.impactTests, {
  interval: 8000,
  keepPolling: (value) => !!value?.some((test: ImpactTest) => test.state === 'running'),
})

const threatById = computed(() => new Map((catalog.data.value?.threats ?? []).map((threat) => [threat.id, threat])))
const datasetByName = computed(() => new Map((catalog.data.value?.datasets ?? []).map((dataset) => [dataset.name, dataset])))
const victim = computed(() => catalog.data.value?.models.find((model) => model.role === 'Victim LLM'))

const stats = computed(() => {
  const rows = (boards.data.value ?? []).flatMap((board) => board.detectors)
  return {
    threats: boards.data.value?.length ?? 0,
    detectors: rows.length,
    agentBuilt: rows.filter((row) => row.origin === 'agents').length,
    passing: rows.filter((row) => row.verdict === 'pass').length,
    exams: (boards.data.value ?? []).reduce((total, board) => total + board.exams.length, 0),
  }
})

async function benchmark(name: string) {
  try {
    await api.benchmark(name)
    message.success(`Benchmark started for ${name}: one sandbox job per exam`)
    window.setTimeout(boards.refresh, 1500)
  } catch (problem) {
    message.error(problem instanceof Error ? problem.message : String(problem))
  }
}

function scoreCell(score: ExamScore | undefined, passF1: number) {
  if (!score) return h('span', { class: 'subtle' }, '—')
  if (score.state === 'running') return h(NTag, { size: 'small', type: 'info', bordered: false }, () => 'running')
  if (score.f1 === null) return h(NTag, { size: 'small', type: 'error', bordered: false }, () => 'run failed')
  const color = score.f1 >= passF1 ? palette.pass : palette.fail
  return h('div', [
    h('strong', { style: { color, fontSize: '15px' } }, f1(score.f1)),
    h('div', { class: 'subtle' }, `caught ${score.caught}/${score.poisoned}`),
    h('div', { class: 'subtle' }, `P ${f1(score.precision)} · R ${f1(score.recall)}`),
  ])
}

function columnsFor(board: ThreatBoard): DataTableColumns<DetectorRow> {
  return [
    { title: '#', key: 'rank', width: 44, render: (_row, index) => h('span', { class: 'subtle' }, index + 1) },
    {
      title: 'Detector',
      key: 'name',
      minWidth: 210,
      render: (row) =>
        h('div', { class: 'detector-cell' }, [
          h(RouterLink, { to: `/detectors/${row.name}`, class: 'mono detector-name' }, () => row.name),
          h(DetectorTags, { origin: row.origin, deployed: row.deployed }),
        ]),
    },
    ...board.exams.map((exam) => ({
      title: exam,
      key: exam,
      minWidth: 170,
      render: (row: DetectorRow) => scoreCell(row.scores.find((score) => score.exam === exam), board.pass_f1),
    })),
    {
      title: 'Mean F1',
      key: 'mean_f1',
      width: 90,
      render: (row) => h('strong', f1(row.mean_f1)),
    },
    { title: 'Verdict', key: 'verdict', width: 130, render: (row) => h(VerdictTag, { verdict: row.verdict }) },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (row) =>
        h(
          NButton,
          { size: 'small', secondary: true, disabled: !row.deployed || row.verdict === 'running', onClick: () => benchmark(row.name) },
          () => 'Benchmark',
        ),
    },
  ]
}

function series(board: ThreatBoard) {
  return board.detectors.map((row) => ({
    name: row.name,
    values: board.exams.map((exam) => row.scores.find((score) => score.exam === exam)?.f1 ?? null),
  }))
}
</script>

<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h1>Detector leaderboard</h1>
        <p>
          Every detector is graded on exams: datasets that were poisoned on purpose, with answer keys the detector never
          sees. A detector passes a threat only if it reaches the pass bar on every exam.
        </p>
      </div>
      <NButton type="primary" @click="router.push('/agents')">Build a detector</NButton>
    </div>

    <NAlert v-if="boards.error.value" type="error" :bordered="false">{{ boards.error.value }}</NAlert>

    <div class="stats">
      <NCard size="small"><NStatistic label="Threats covered" :value="stats.threats" /></NCard>
      <NCard size="small"><NStatistic label="Benchmark exams" :value="stats.exams" /></NCard>
      <NCard size="small">
        <NStatistic label="Detectors" :value="stats.detectors">
          <template #suffix><span class="subtle">{{ stats.agentBuilt }} agent-built</span></template>
        </NStatistic>
      </NCard>
      <NCard size="small">
        <NStatistic label="Passing" :value="stats.passing">
          <template #suffix><span class="subtle">of {{ stats.detectors }}</span></template>
        </NStatistic>
      </NCard>
      <NCard size="small">
        <NStatistic label="Victim LLM">
          <span class="mono victim">{{ victim?.name ?? '—' }}</span>
        </NStatistic>
      </NCard>
    </div>

    <NSkeleton v-if="!boards.data.value" height="420px" :sharp="false" />

    <div v-else class="stack">
      <NCard v-for="board in boards.data.value" :key="board.threat" class="threat">
        <template #header>
          <div class="threat-title">
            <span>{{ board.title }}</span>
            <span class="mono subtle">{{ board.threat }}</span>
          </div>
        </template>
        <template #header-extra>
          <NTag :bordered="false" type="warning" size="small">pass bar: F1 ≥ {{ board.pass_f1 }} on every exam</NTag>
        </template>

        <p class="muted summary">{{ threatById.get(board.threat)?.summary }}</p>

        <div class="board-grid">
          <NDataTable
            :columns="columnsFor(board)"
            :data="board.detectors"
            :row-key="(row: DetectorRow) => row.name"
            size="small"
            :bordered="false"
          />
          <F1Chart :exams="board.exams" :series="series(board)" :pass-f1="board.pass_f1" />
        </div>

        <div class="exams">
          <div v-for="exam in threatById.get(board.threat)?.exams ?? []" :key="exam.dataset" class="exam">
            <div class="mono">{{ exam.dataset }}</div>
            <div class="subtle">{{ exam.description }}</div>
            <div class="subtle">
              {{ datasetByName.get(exam.dataset)?.poisoned }} poisoned of {{ datasetByName.get(exam.dataset)?.samples }}
              · source {{ datasetByName.get(exam.dataset)?.source }} · made by {{ exam.poisoner }}
            </div>
          </div>
        </div>

        <ImpactPanel
          v-if="threatById.get(board.threat) && catalog.data.value"
          :threat="threatById.get(board.threat)!"
          :tests="impact.data.value ?? []"
          :datasets="catalog.data.value.datasets"
          :detectors="board.detectors"
          :victim="victim"
          @started="impact.refresh"
        />
      </NCard>
    </div>

    <template v-if="catalog.data.value">
      <h2 class="section-title">Datasets</h2>
      <DatasetsPanel :datasets="catalog.data.value.datasets" :schema="catalog.data.value.dataset_schema" />
      <h2 class="section-title">Models</h2>
      <ModelsTable :models="catalog.data.value.models" />
    </template>
  </main>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) minmax(0, 1.6fr);
  gap: 14px;
  margin-bottom: 22px;
}

.victim {
  font-size: 15px;
}

.threat-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 17px;
  font-weight: 600;
}

.summary {
  margin: 0 0 18px;
  font-size: 13.5px;
}

.board-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 1fr);
  gap: 24px;
  align-items: start;
}

.exams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.exam {
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  background: #0f141a;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

:deep(.detector-cell) {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

:deep(.detector-name) {
  font-size: 13px;
  font-weight: 600;
  white-space: normal;
  overflow-wrap: anywhere;
}
</style>
