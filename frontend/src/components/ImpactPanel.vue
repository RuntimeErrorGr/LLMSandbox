<script setup lang="ts">
import {
  NAlert,
  NButton,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  NForm,
  NFormItem,
  NModal,
  NSelect,
  NSpin,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, ref } from 'vue'

import { api } from '@/api/client'
import type { Dataset, DetectorRow, ImpactMetric, ImpactTest, ImpactVariant, Model, Threat } from '@/api/types'
import ImpactChart from '@/components/ImpactChart.vue'
import { metricLabels, palette, percent } from '@/format'

const props = defineProps<{
  threat: Threat
  tests: ImpactTest[]
  datasets: Dataset[]
  detectors: DetectorRow[]
  victim: Model | undefined
}>()
const emit = defineEmits<{ started: [] }>()
const message = useMessage()

const forThreat = computed(() => props.tests.filter((test) => test.threat === props.threat.id))
const latest = computed(
  () => forThreat.value.find((test) => test.state === 'running') ?? forThreat.value.find((test) => test.state === 'succeeded'),
)
const metrics = computed<ImpactMetric[]>(() =>
  props.threat.impact_metric === 'attack_success_rate' ? ['clean_accuracy', 'attack_success_rate'] : ['clean_accuracy'],
)
const testDataset = computed(() => props.datasets.find((dataset) => dataset.name === latest.value?.test_dataset))

const columns = computed<DataTableColumns<ImpactVariant>>(() => [
  {
    title: 'Model trained on',
    key: 'title',
    render: (row) =>
      h('div', [
        h('div', { class: 'variant' }, [h('span', { class: 'swatch', style: { background: palette.variants[row.key] } }), row.title]),
        h('div', { class: 'mono subtle' }, row.train_dataset),
      ]),
  },
  { title: 'Training samples', key: 'train_samples', render: (row) => row.train_samples ?? '—' },
  ...metrics.value.map((metric) => ({
    title: metricLabels[metric],
    key: metric,
    render: (row: ImpactVariant) =>
      row.state === 'running' ? h(NSpin, { size: 14 }) : h('strong', percent(row[metric])),
  })),
])

const showForm = ref(false)
const starting = ref(false)
const suspectOptions = computed(() =>
  props.datasets
    .filter((dataset) => dataset.role === 'suspect' && dataset.threat === props.threat.id)
    .map((dataset) => ({ label: `${dataset.name} · ${dataset.recipe}`, value: dataset.name })),
)
const cleanOptions = computed(() =>
  props.datasets.filter((dataset) => dataset.role === 'clean').map((dataset) => ({ label: dataset.name, value: dataset.name })),
)
const detectorOptions = computed(() =>
  props.detectors.filter((detector) => detector.deployed).map((detector) => ({ label: detector.name, value: detector.name })),
)
const form = ref({ suspect: '', clean: 'sst2_train', detector: '' })

function openForm() {
  form.value = {
    suspect: suspectOptions.value[0]?.value ?? '',
    clean: 'sst2_train',
    detector: detectorOptions.value[0]?.value ?? '',
  }
  showForm.value = true
}

async function start() {
  starting.value = true
  try {
    await api.startImpact(form.value)
    message.success('Impact test started: one scan and three trainings, about 20 minutes on CPU')
    showForm.value = false
    emit('started')
  } catch (problem) {
    message.error(problem instanceof Error ? problem.message : String(problem))
  } finally {
    starting.value = false
  }
}
</script>

<template>
  <div class="impact">
    <div class="impact-head">
      <div>
        <h3>Impact on the victim LLM</h3>
        <p class="muted">
          The same LLM is fine-tuned three times: on clean data, on the poisoned dataset, and on the poisoned
          dataset after the detector removed what it flagged.
        </p>
      </div>
      <NButton secondary size="small" :disabled="latest?.state === 'running'" @click="openForm">Run impact test</NButton>
    </div>

    <NEmpty v-if="!latest" description="No impact test for this threat yet" />
    <template v-else>
      <NAlert v-if="latest.state === 'running'" type="info" :bordered="false" class="running">
        Impact test #{{ latest.id }} is running: {{ latest.step }}
      </NAlert>
      <div class="impact-grid">
        <ImpactChart :test="latest" :metrics="metrics" />
        <div class="stack">
          <NDataTable :columns="columns" :data="latest.variants" size="small" :bordered="false" />
          <NDescriptions :column="1" label-placement="left" size="small" bordered label-style="white-space: nowrap; width: 120px">
            <NDescriptionsItem v-if="!latest.trigger" label="Reading the chart">
              Label flipping adds noise rather than a hidden rule, so its cost shows in clean accuracy; the axis is zoomed
              to make the differences visible.
            </NDescriptionsItem>
            <NDescriptionsItem label="Victim LLM">
              <span class="mono">{{ victim?.name }}</span>
              <div class="subtle">{{ victim?.detail }}</div>
            </NDescriptionsItem>
            <NDescriptionsItem label="Evaluated on">
              <span class="mono">{{ latest.test_dataset }}</span>
              <span class="subtle"> · {{ testDataset?.samples }} unseen samples · {{ testDataset?.source }}</span>
            </NDescriptionsItem>
            <NDescriptionsItem v-if="latest.trigger" label="Attack">
              trigger <NTag size="tiny" type="error" :bordered="false">{{ latest.trigger }}</NTag> → predicted
              <strong>{{ latest.target_label }}</strong>; attack success rate = share of other-class test samples
              predicted <strong>{{ latest.target_label }}</strong> once the trigger is inserted
            </NDescriptionsItem>
            <NDescriptionsItem label="Cleaning">
              <span class="mono">{{ latest.detector }}</span> removed {{ latest.removed ?? '—' }} samples
              <span v-if="latest.poisoned">({{ latest.removed_poisoned }} of {{ latest.poisoned }} poisoned samples caught)</span>
            </NDescriptionsItem>
          </NDescriptions>
        </div>
      </div>
    </template>

    <NModal v-model:show="showForm" preset="card" title="Run an impact test" style="width: 560px">
      <NForm label-placement="top">
        <NFormItem label="Poisoned dataset (model B)">
          <NSelect v-model:value="form.suspect" :options="suspectOptions" />
        </NFormItem>
        <NFormItem label="Clean dataset (model A)">
          <NSelect v-model:value="form.clean" :options="cleanOptions" />
        </NFormItem>
        <NFormItem label="Detector that cleans the data (model C)">
          <NSelect v-model:value="form.detector" :options="detectorOptions" />
        </NFormItem>
      </NForm>
      <template #footer>
        <div class="row" style="justify-content: flex-end">
          <NButton @click="showForm = false">Cancel</NButton>
          <NButton type="primary" :loading="starting" :disabled="!form.suspect || !form.detector" @click="start">
            Start
          </NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.impact {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.impact-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 16px;
}

.impact-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.impact-head p {
  margin: 0;
  font-size: 13px;
}

.impact-grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(420px, 1.3fr);
  gap: 24px;
}

.running {
  margin-bottom: 14px;
}

:deep(.variant) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

:deep(.swatch) {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
</style>
