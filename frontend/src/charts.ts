import {
  BarElement,
  CategoryScale,
  Chart,
  Legend,
  LinearScale,
  Tooltip,
  type Plugin,
} from 'chart.js'

import { palette } from './format'

Chart.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip)
Chart.defaults.color = '#94a3b8'
Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.12)'
Chart.defaults.font.family = 'Inter, "Segoe UI", system-ui, sans-serif'
Chart.defaults.font.size = 12
Chart.defaults.plugins.legend.labels.boxWidth = 12
Chart.defaults.plugins.legend.labels.boxHeight = 12

export function thresholdLine(value: number, label: string): Plugin<'bar'> {
  return {
    id: 'thresholdLine',
    afterDatasetsDraw(chart) {
      const { ctx, chartArea, scales } = chart
      const y = scales.y.getPixelForValue(value)
      ctx.save()
      ctx.strokeStyle = palette.warning
      ctx.lineWidth = 1.5
      ctx.setLineDash([6, 4])
      ctx.beginPath()
      ctx.moveTo(chartArea.left, y)
      ctx.lineTo(chartArea.right, y)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = palette.warning
      ctx.font = '11px Inter, system-ui, sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(label, chartArea.right, y - 6)
      ctx.restore()
    },
  }
}
