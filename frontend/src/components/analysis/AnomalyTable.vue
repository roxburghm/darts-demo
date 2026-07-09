<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AnomalyRegion } from '@/api/types'
import { formatTimestamp } from '@/utils/formatters'
import { getSeverityColor } from '@/utils/color'

const props = defineProps<{
  regions: AnomalyRegion[]
  explanations: Map<string, string>
}>()

const expandedRows = ref<Set<number>>(new Set())

function toggleRow(i: number) {
  const next = new Set(expandedRows.value)
  if (next.has(i)) next.delete(i)
  else next.add(i)
  expandedRows.value = next
}

function getExplanation(region: AnomalyRegion): string {
  return props.explanations.get(`${region.metric}|${region.start}|${region.end}`) ?? ''
}

const summary = computed(() => {
  const byS: Record<string, number> = { high: 0, medium: 0, low: 0 }
  for (const r of props.regions) {
    byS[r.severity] = (byS[r.severity] ?? 0) + 1
  }
  return { total_regions: props.regions.length, by_severity: byS }
})

const emit = defineEmits<{
  'region-click': [start: string, end: string]
}>()

type SortField = 'start' | 'severity' | 'metric' | 'score'
const sortField = ref<SortField>('start')
const sortAsc = ref(true)

const severityOrder: Record<string, number> = { high: 3, medium: 2, low: 1 }

const sortedRegions = computed(() => {
  const regions = [...props.regions]
  regions.sort((a, b) => {
    let cmp = 0
    switch (sortField.value) {
      case 'start':
        cmp = a.start.localeCompare(b.start)
        break
      case 'severity':
        cmp = (severityOrder[a.severity] ?? 0) - (severityOrder[b.severity] ?? 0)
        break
      case 'metric':
        cmp = a.metric.localeCompare(b.metric)
        break
      case 'score':
        cmp = a.avg_score - b.avg_score
        break
    }
    return sortAsc.value ? cmp : -cmp
  })
  return regions
})

function toggleSort(field: SortField) {
  if (sortField.value === field) {
    sortAsc.value = !sortAsc.value
  } else {
    sortField.value = field
    sortAsc.value = field === 'severity' ? false : true
  }
}
</script>

<template>
  <div class="anomaly-table">
    <div class="table-header">
      <h3>Anomalies</h3>
      <div class="summary-badges">
        <span v-if="summary.by_severity.high" class="severity-badge severity-high">
          {{ summary.by_severity.high }} High
        </span>
        <span v-if="summary.by_severity.medium" class="severity-badge severity-medium">
          {{ summary.by_severity.medium }} Med
        </span>
        <span v-if="summary.by_severity.low" class="severity-badge severity-low">
          {{ summary.by_severity.low }} Low
        </span>
        <span class="text-muted" style="font-size: 0.75rem;">
          {{ summary.total_regions }} regions
        </span>
      </div>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="chevron-header"></th>
            <th class="sortable" @click="toggleSort('start')">
              Time {{ sortField === 'start' ? (sortAsc ? '\u2191' : '\u2193') : '' }}
            </th>
            <th class="sortable" @click="toggleSort('metric')">
              Metric {{ sortField === 'metric' ? (sortAsc ? '\u2191' : '\u2193') : '' }}
            </th>
            <th class="sortable" @click="toggleSort('severity')">
              Severity {{ sortField === 'severity' ? (sortAsc ? '\u2191' : '\u2193') : '' }}
            </th>
            <th class="sortable" @click="toggleSort('score')">
              Score {{ sortField === 'score' ? (sortAsc ? '\u2191' : '\u2193') : '' }}
            </th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(region, i) in sortedRegions" :key="i">
            <tr
              class="table-row"
              @click="emit('region-click', region.start, region.end)"
            >
              <td class="chevron-cell" @click.stop="toggleRow(i)">
                <span class="chevron" :class="{ expanded: expandedRows.has(i) }">&#9656;</span>
              </td>
              <td class="mono" style="font-size: 0.75rem;">
                {{ formatTimestamp(region.start) }}
              </td>
              <td>{{ region.metric }}</td>
              <td>
                <span
                  class="severity-dot"
                  :style="{ backgroundColor: getSeverityColor(region.severity) }"
                />
                {{ region.severity }}
              </td>
              <td class="mono">{{ region.avg_score.toFixed(2) }}</td>
              <td class="mono text-muted">{{ region.point_count }}</td>
            </tr>
            <tr v-if="expandedRows.has(i)" class="explanation-row">
              <td :colspan="6" class="explanation-cell" :style="{ borderLeftColor: getSeverityColor(region.severity) }">
                {{ getExplanation(region) }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.anomaly-table {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.table-header h3 {
  font-size: 0.9rem;
  font-weight: 600;
}

.summary-badges {
  display: flex;
  gap: var(--space-xs);
  align-items: center;
}

.severity-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
}

.severity-high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.severity-medium {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}

.severity-low {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.table-scroll {
  flex: 1;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

thead th {
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  padding: var(--space-xs) var(--space-sm);
  text-align: left;
  font-weight: 600;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: var(--text-primary);
}

td {
  padding: var(--space-xs) var(--space-sm);
  border-bottom: 1px solid var(--border-subtle);
}

.table-row {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.table-row:hover {
  background: var(--bg-elevated);
}

.severity-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}

.chevron-header {
  width: 24px;
  padding: 0;
}

.chevron-cell {
  width: 24px;
  padding: var(--space-xs) 4px;
  cursor: pointer;
  text-align: center;
}

.chevron {
  display: inline-block;
  font-size: 0.7rem;
  color: var(--text-muted);
  transition: transform 0.15s ease;
}

.chevron.expanded {
  transform: rotate(90deg);
}

.chevron-cell:hover .chevron {
  color: var(--text-primary);
}

.explanation-row td {
  border-bottom: 1px solid var(--border-subtle);
}

.explanation-cell {
  padding: var(--space-sm) var(--space-sm) var(--space-sm) 32px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
  border-left: 3px solid;
  background: var(--bg-elevated);
}
</style>
