<script setup lang="ts">
import { NCard, NTag } from 'naive-ui'

import type { Catalog } from '@/api/types'

defineProps<{ catalog: Catalog }>()

const files = [
  ['main.py', 'the detector, written by the Security Specialist'],
  ['module.yaml', 'name, kind: detector, threat, description, params with defaults'],
  ['cronjob.yaml', 'suspended job template rendered from the hardened template'],
  ['kustomization.yaml', 'packs main.py and module.yaml into a ConfigMap'],
]
</script>

<template>
  <div class="stack">
    <NCard title="Supported threats" size="small">
      <div class="threats">
        <div v-for="threat in catalog.threats" :key="threat.id" class="threat">
          <div class="row">
            <strong>{{ threat.title }}</strong>
            <NTag size="tiny" :bordered="false" class="mono">{{ threat.id }}</NTag>
          </div>
          <p class="muted">{{ threat.summary }}</p>
          <div class="subtle">
            Exams: <span v-for="exam in threat.exams" :key="exam.dataset" class="mono exam">{{ exam.dataset }}</span>
            · pass bar F1 ≥ {{ threat.pass_f1 }}
          </div>
        </div>
      </div>
    </NCard>

    <NCard title="What the agents generate" size="small">
      <p class="muted intro">
        One folder per detector, <span class="mono">modules/&lt;name&gt;/</span>. After your approval it is opened as a pull
        request; after the merge ArgoCD deploys it to <span class="mono">sandbox-modules</span>.
      </p>
      <table class="grid-table">
        <tr v-for="[file, meaning] in files" :key="file">
          <td class="mono">{{ file }}</td>
          <td class="muted">{{ meaning }}</td>
        </tr>
      </table>
    </NCard>

    <NCard title="Module contract" size="small">
      <div class="contract">
        <div>
          <div class="label">sandbox_sdk</div>
          <table class="grid-table">
            <tr v-for="item in catalog.sdk_functions" :key="item.name">
              <td class="mono">{{ item.name }}</td>
              <td class="muted">{{ item.meaning }}</td>
            </tr>
          </table>
        </div>
        <div>
          <div class="label">Dataset row</div>
          <table class="grid-table">
            <tr v-for="item in catalog.dataset_schema" :key="item.field">
              <td class="mono">{{ item.field }}</td>
              <td class="mono subtle">{{ item.type }}</td>
              <td class="muted">{{ item.meaning }}</td>
            </tr>
          </table>
          <div class="label">result.json</div>
          <table class="grid-table">
            <tr v-for="item in catalog.result_schema" :key="item.field">
              <td class="mono">{{ item.field }}</td>
              <td class="mono subtle">{{ item.type }}</td>
              <td class="muted">{{ item.meaning }}</td>
            </tr>
          </table>
        </div>
      </div>
      <p class="subtle rules">
        Sandbox rules enforced by the policy checker and CI: no network, sockets, subprocess or eval; models only through
        sdk.model_path; non-root, read-only filesystem, CPU and memory limits; answer keys are never mounted.
      </p>
    </NCard>
  </div>
</template>

<style scoped>
.threats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.threat p {
  margin: 6px 0;
  font-size: 13px;
  line-height: 1.5;
}

.exam {
  margin-right: 8px;
}

.intro {
  margin-top: 0;
  font-size: 13px;
}

.contract {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.label {
  margin: 4px 0 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}

.grid-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  margin-bottom: 14px;
}

.grid-table td {
  padding: 5px 12px 5px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
  vertical-align: top;
}

.rules {
  margin-bottom: 0;
}
</style>
