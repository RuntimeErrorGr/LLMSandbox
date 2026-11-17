<script setup lang="ts">
import type { ChartData, ChartOptions } from 'chart.js'
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'

import { thresholdLine } from '@/charts'
import { palette } from '@/format'

export interface Series {
  name: string
  values: (number | null)[]
}

const props = defineProps<{ exams: string[]; series: Series[]; passF1: number }>()

const data = computed<ChartData<'bar'>>(() => ({
  labels: props.exams,
  datasets: props.series.map((item, index) => ({
    label: item.name,
    data: item.values,
    backgroundColor: palette.series[index % palette.series.length],
    borderRadius: 4,
    maxBarThickness: 44,
  })),
}))

const options: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: { min: 0, max: 1, ticks: { stepSize: 0.2 }, title: { display: true, text: 'F1 score' } },
    x: { grid: { display: false } },
  },
  plugins: {
    legend: { position: 'bottom' },
    tooltip: {
      callbacks: { label: (item) => `${item.dataset.label}: F1 ${Number(item.parsed.y).toFixed(2)}` },
    },
  },
}

const plugins = computed(() => [thresholdLine(props.passF1, `pass bar ${props.passF1}`)])
</script>

<template>
  <div class="chart-box">
    <Bar :data="data" :options="options" :plugins="plugins" />
  </div>
</template>
