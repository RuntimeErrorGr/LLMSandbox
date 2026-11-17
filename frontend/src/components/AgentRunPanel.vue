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
  NTabPane,
  NTabs,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '@/api/client'
import type { AgentAction, AgentEvent, DesignParam } from '@/api/types'
import CodeView from '@/components/CodeView.vue'
import F1Chart from '@/components/F1Chart.vue'
import PipelineStages from '@/components/PipelineStages.vue'
import { useResource } from '@/composables/useResource'
import { f1, palette, statusLabel, statusType, timeAgo } from '@/format'

const props = defineProps<{ id: number }>()
const emit = defineEmits<{ changed: [] }>()
const message = useMessage()
const dialog = useDialog()

const run = useResource(() => api.agentRun(props.id), {
  interval: 3000,
  keepPolling: (value) => value?.status === 'running',
})
watch(() => props.id, run.refresh)

const value = computed(() => run.data.value)
const benchmarkSeries = computed(() => {
  const scores = value.value?.benchmark?.scores ?? []
  return [{ name: value.value?.detector ?? 'candidate', values: scores.map((score) => score.f1) }]
})

const paramColumns: DataTableColumns<DesignParam> = [
  { title: 'Parameter', key: 'name', render: (row) => h('span', { class: 'mono' }, row.name) },
  { title: 'Default', key: 'default', render: (row) => h('span', { class: 'mono' }, String(row.default)) },
  { title: 'Meaning', key: 'description', render: (row) => h('span', { class: 'muted' }, row.description) },
]

const eventColumns: DataTableColumns<AgentEvent> = [
  { title: 'Time', key: 'time', width: 90, render: (row) => h('span', { class: 'mono subtle' }, row.time) },
  { title: 'Stage', key: 'stage', width: 110, render: (row) => h('span', { class: 'mono' }, row.stage) },
  {
    title: 'Result',
    key: 'ok',
    width: 80,
    render: (row) => h(NTag, { size: 'tiny', bordered: false, type: row.ok ? 'success' : 'error' }, () => (row.ok ? 'ok' : 'failed')),
  },
  { title: 'Message', key: 'message' },
]

async function act(action: AgentAction) {
  try {
    await api.agentAction(props.id, action)
    message.success(action === 'approve' ? 'Approved: the agents are opening the pull request' : `Run ${action}ed`)
    emit('changed')
    window.setTimeout(run.refresh, 800)
  } catch (problem) {
    message.error(problem instanceof Error ? problem.message : String(problem))
  }
}

function confirmApprove() {
  dialog.warning({
    title: 'Open a pull request?',
    content:
      'The agents will push a branch with this module and open a pull request. CI runs the policy checker again; after you merge, ArgoCD deploys the detector.',
    positiveText: 'Approve',
    negativeText: 'Cancel',
    onPositiveClick: () => act('approve'),
  })
}
</script>

<template>
  <NSkeleton v-if="!value" height="520px" :sharp="false" />
  <div v-else class="stack">
    <NCard size="small">
      <div class="run-head">
        <div>
          <div class="row">
            <span class="run-id mono">#{{ value.id }}</span>
            <NTag :type="statusType(value.status)" :bordered="false" size="small">{{ statusLabel(value.status) }}</NTag>
            <span v-if="value.attempt" class="subtle">attempt {{ value.attempt }} of {{ value.max_attempts }}</span>
            <span class="subtle">· started {{ timeAgo(value.created_at) }}</span>
          </div>
          <p class="request">{{ value.request }}</p>
          <div v-if="value.detector" class="row">
            <span class="mono">{{ value.detector }}</span>
            <NTag v-if="value.threat" size="tiny" :bordered="false">{{ value.threat }}</NTag>
            <RouterLink v-if="value.status === 'pr_opened'" :to="`/detectors/${value.detector}`" class="subtle">
              view on the leaderboard →
            </RouterLink>
          </div>
        </div>
        <div class="actions">
          <template v-if="value.status === 'awaiting_approval'">
            <NButton type="primary" @click="confirmApprove">Approve and open PR</NButton>
            <NButton secondary type="error" @click="act('reject')">Reject</NButton>
          </template>
          <NButton v-if="['interrupted', 'error'].includes(value.status)" secondary @click="act('continue')">
            Continue from checkpoint
          </NButton>
          <NButton v-if="value.pr_url" tag="a" :href="value.pr_url" target="_blank" secondary type="primary">
            Open pull request
          </NButton>
        </div>
      </div>
      <NAlert v-if="value.detail" type="error" :bordered="false" class="alert">{{ value.detail }}</NAlert>
      <NAlert v-if="value.guard?.blocked" type="error" :bordered="false" class="alert" title="Blocked by the guard">
        {{ value.guard.reason }} ({{ value.guard.layer }}, {{ value.guard.category }})
      </NAlert>
    </NCard>

    <div class="run-grid">
      <NCard title="Pipeline" size="small">
        <PipelineStages :stages="value.stages" />
      </NCard>

      <NCard size="small" class="tabs-card">
        <NTabs type="line" animated>
          <NTabPane name="design" tab="Design">
            <NEmpty v-if="!value.design" description="The Architect has not finished yet" />
            <div v-else class="stack">
              <div>
                <h3 class="design-title">{{ value.design.title }}</h3>
                <p class="muted">{{ value.design.method }}</p>
              </div>
              <ol class="steps">
                <li v-for="step in value.design.steps" :key="step">{{ step }}</li>
              </ol>
              <NDataTable :columns="paramColumns" :data="value.design.params" size="small" :bordered="false" />
              <NDescriptions v-if="value.spec" :column="3" label-placement="top" size="small" bordered>
                <NDescriptionsItem label="CPU request / limit">
                  <span class="mono">{{ value.spec.cpu_request }} / {{ value.spec.cpu_limit }}</span>
                </NDescriptionsItem>
                <NDescriptionsItem label="Memory request / limit">
                  <span class="mono">{{ value.spec.memory_request }} / {{ value.spec.memory_limit }}</span>
                </NDescriptionsItem>
                <NDescriptionsItem label="Timeout">
                  <span class="mono">{{ value.spec.timeout_seconds }} s</span>
                </NDescriptionsItem>
              </NDescriptions>
              <p v-if="value.spec?.summary" class="muted">{{ value.spec.summary }}</p>
            </div>
          </NTabPane>

          <NTabPane name="code" :tab="value.code ? `main.py · ${value.code.split('\n').length} lines` : 'main.py'">
            <NEmpty v-if="!value.code" description="The Security Specialist has not written code yet" />
            <CodeView v-else :code="value.code" />
          </NTabPane>

          <NTabPane name="benchmark" tab="Benchmark">
            <NEmpty v-if="!value.benchmark" description="Not benchmarked yet" />
            <div v-else class="stack">
              <div class="row">
                <NTag :type="value.benchmark.passed ? 'success' : 'error'" :bordered="false">
                  {{ value.benchmark.passed ? 'PASSED' : 'FAILED' }}
                </NTag>
                <span class="subtle">needs F1 ≥ {{ value.benchmark.pass_f1 }} on every exam, measured in sandbox-playground</span>
              </div>
              <div class="scores">
                <div v-for="score in value.benchmark.scores" :key="score.exam" class="score">
                  <div class="mono subtle">{{ score.exam }}</div>
                  <div
                    class="score-value"
                    :style="{ color: (score.f1 ?? 0) >= value.benchmark.pass_f1 ? palette.pass : palette.fail }"
                  >
                    {{ f1(score.f1) }}
                  </div>
                </div>
              </div>
              <F1Chart
                :exams="value.benchmark.scores.map((score) => score.exam)"
                :series="benchmarkSeries"
                :pass-f1="value.benchmark.pass_f1"
              />
            </div>
          </NTabPane>

          <NTabPane name="checks" tab="Feedback">
            <NEmpty v-if="!value.checks.length && !value.feedback" description="No problems reported" />
            <div v-else class="stack">
              <ul v-if="value.checks.length" class="checks">
                <li v-for="problem in value.checks" :key="problem" class="mono">{{ problem }}</li>
              </ul>
              <div v-if="value.feedback">
                <div class="subtle">Last feedback sent to the Security Specialist</div>
                <pre class="code-box mono feedback">{{ value.feedback }}</pre>
              </div>
            </div>
          </NTabPane>

          <NTabPane name="log" tab="Event log">
            <NDataTable :columns="eventColumns" :data="value.events" size="small" :bordered="false" />
          </NTabPane>
        </NTabs>
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.run-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}

.run-id {
  font-size: 15px;
  font-weight: 600;
}

.request {
  margin: 10px 0;
  font-size: 15px;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.alert {
  margin-top: 12px;
}

.run-grid {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.design-title {
  margin: 0 0 6px;
  font-size: 16px;
}

.steps {
  margin: 0;
  padding-left: 20px;
  line-height: 1.7;
  font-size: 13.5px;
}

.scores {
  display: flex;
  gap: 14px;
}

.score {
  padding: 10px 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  min-width: 150px;
}

.score-value {
  font-size: 26px;
  font-weight: 650;
}

.checks {
  margin: 0;
  padding-left: 18px;
  color: #fda4af;
  line-height: 1.7;
}

.feedback {
  white-space: pre-wrap;
  margin-top: 6px;
}
</style>
