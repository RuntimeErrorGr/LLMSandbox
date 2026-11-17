<script setup lang="ts">
import type { ChartData, ChartOptions } from 'chart.js'
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'

import type { ImpactMetric, ImpactTest } from '@/api/types'
import { metricLabels, palette } from '@/format'

const props = defineProps<{ test: ImpactTest; metrics: ImpactMetric[] }>()

const data = computed<ChartData<'bar'>>(() => ({
  labels: props.metrics.map((metric) => metricLabels[metric]),
  datasets: props.test.variants.map((variant) => ({
    label: variant.title,
    data: props.metrics.map((metric) => {
      const value = variant[metric]
      return value === null ? null : Number((value * 100).toFixed(1))
    }),
    backgroundColor: palette.variants[variant.key],
    borderRadius: 4,
    maxBarThickness: 56,
  })),
}))

const axisMin = computed(() => {
  if (props.metrics.includes('attack_success_rate')) return 0
  const values = props.test.variants.map((variant) => variant.clean_accuracy).filter((value) => value !== null)
  return values.length ? Math.max(0, Math.floor((Math.min(...values) * 100 - 6) / 5) * 5) : 0
})

const options = computed<ChartOptions<'bar'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: { min: axisMin.value, max: 100, ticks: { callback: (value) => `${value}%` } },
    x: { grid: { display: false } },
  },
  plugins: {
    legend: { position: 'bottom' },
    tooltip: { callbacks: { label: (item) => `${item.dataset.label}: ${item.parsed.y}%` } },
  },
}))
</script>

<template>
  <div class="chart-box">
    <Bar :data="data" :options="options" />
  </div>
</template>
