<script setup lang="ts">
import { NButton, NCard, NEmpty, NInput, NTag, useMessage } from 'naive-ui'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { AgentRunSummary } from '@/api/types'
import AgentRunPanel from '@/components/AgentRunPanel.vue'
import ContractPanel from '@/components/ContractPanel.vue'
import { useResource } from '@/composables/useResource'
import { statusLabel, statusType, timeAgo } from '@/format'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const catalog = useResource(api.catalog)
const runs = useResource(api.agentRuns, {
  interval: 5000,
  keepPolling: (value) => !!value?.some((run: AgentRunSummary) => run.status === 'running'),
})
const selected = computed(() => (route.params.id ? Number(route.params.id) : null))

const request = ref('')
const starting = ref(false)

async function start() {
  starting.value = true
  try {
    const { id } = await api.startAgentRun(request.value)
    message.success('The agents started; the guard checks the request first')
    request.value = ''
    await runs.refresh()
    router.push(`/agents/${id}`)
  } catch (problem) {
    message.error(problem instanceof Error ? problem.message : String(problem))
  } finally {
    starting.value = false
  }
}
</script>

<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h1>Agents</h1>
        <p>
          Describe a detector. The Architect designs it, the Security Specialist writes it and the DevOps Specialist
          packages it. It must pass the policy checks, a smoke test and the benchmark exams in the sandbox before it
          reaches you for approval.
        </p>
      </div>
    </div>

    <div class="layout">
      <aside class="stack">
        <NCard title="New detector" size="small">
          <NInput
            v-model:value="request"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 8 }"
            placeholder="Build a clean-label detector that …"
          />
          <div class="examples">
            <div class="subtle">Examples</div>
            <button
              v-for="example in catalog.data.value?.example_requests ?? []"
              :key="example"
              class="example"
              type="button"
              @click="request = example"
            >
              {{ example }}
            </button>
          </div>
          <NButton
            type="primary"
            block
            :loading="starting"
            :disabled="request.trim().length < 10"
            @click="start"
          >
            Start the agents
          </NButton>
          <div class="subtle hint">About 5 to 25 minutes on CPU, depending on the number of attempts.</div>
        </NCard>

        <NCard title="Runs" size="small" content-style="padding: 0">
          <NEmpty v-if="!runs.data.value?.length" description="No runs yet" class="empty" />
          <ul class="runs">
            <li
              v-for="item in runs.data.value ?? []"
              :key="item.id"
              :class="{ active: item.id === selected }"
              @click="router.push(`/agents/${item.id}`)"
            >
              <div class="row run-line">
                <span class="mono">#{{ item.id }}</span>
                <NTag :type="statusType(item.status)" size="tiny" :bordered="false">{{ statusLabel(item.status) }}</NTag>
                <span class="subtle when">{{ timeAgo(item.created_at) }}</span>
              </div>
              <div class="mono detector">{{ item.detector ?? 'designing…' }}</div>
              <div class="subtle request">{{ item.request }}</div>
            </li>
          </ul>
        </NCard>
      </aside>

      <section>
        <AgentRunPanel v-if="selected" :id="selected" @changed="runs.refresh" />
        <ContractPanel v-else-if="catalog.data.value" :catalog="catalog.data.value" />
      </section>
    </div>
  </main>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.examples {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0 14px;
}

.example {
  text-align: left;
  padding: 7px 10px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 6px;
  background: transparent;
  color: #cbd5e1;
  font: inherit;
  font-size: 12.5px;
  line-height: 1.4;
  cursor: pointer;
}

.example:hover {
  border-color: rgba(56, 189, 248, 0.5);
  color: #e2e8f0;
}

.hint {
  margin-top: 8px;
}

.runs {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 560px;
  overflow: auto;
}

.runs li {
  padding: 12px 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  cursor: pointer;
}

.runs li:hover {
  background: rgba(148, 163, 184, 0.05);
}

.runs li.active {
  background: rgba(56, 189, 248, 0.09);
  box-shadow: inset 2px 0 0 #38bdf8;
}

.run-line {
  gap: 8px;
}

.when {
  margin-left: auto;
}

.detector {
  margin-top: 4px;
}

.request {
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty {
  padding: 24px;
}
</style>
