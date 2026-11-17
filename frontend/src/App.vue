<script setup lang="ts">
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import yaml from 'highlight.js/lib/languages/yaml'
import { darkTheme, NConfigProvider, NDialogProvider, NMessageProvider } from 'naive-ui'
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import StatusBar from './components/StatusBar.vue'
import { themeOverrides } from './theme'
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('python', python)
hljs.registerLanguage('yaml', yaml)

const route = useRoute()
const section = computed(() => (route.path.startsWith('/agents') ? 'agents' : 'leaderboard'))
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides" :hljs="hljs">
    <NMessageProvider>
      <NDialogProvider>
        <header class="topbar">
          <div class="topbar-inner">
            <RouterLink to="/leaderboard" class="brand">
              <span class="brand-mark">LS</span>
              <span>
                <strong>LLM Sandbox</strong>
                <small>Poisoning detection lab</small>
              </span>
            </RouterLink>
            <nav class="nav">
              <RouterLink to="/leaderboard" class="nav-link" :class="{ active: section === 'leaderboard' }">
                Leaderboard
              </RouterLink>
              <RouterLink to="/agents" class="nav-link" :class="{ active: section === 'agents' }">
                Agents
              </RouterLink>
            </nav>
            <StatusBar />
          </div>
        </header>
        <RouterView />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(11, 15, 20, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 12px 32px;
  display: flex;
  align-items: center;
  gap: 40px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #e2e8f0;
}

.brand:hover {
  text-decoration: none;
}

.brand strong {
  display: block;
  font-size: 15px;
  letter-spacing: -0.01em;
}

.brand small {
  display: block;
  color: #64748b;
  font-size: 11.5px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.nav {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 7px 14px;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
}

.nav-link:hover {
  color: #e2e8f0;
  background: rgba(148, 163, 184, 0.08);
  text-decoration: none;
}

.nav-link.active {
  color: #e2e8f0;
  background: rgba(56, 189, 248, 0.12);
}
</style>
