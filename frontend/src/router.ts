import { createRouter, createWebHistory } from 'vue-router'

import AgentsView from './views/AgentsView.vue'
import DetectorView from './views/DetectorView.vue'
import LeaderboardView from './views/LeaderboardView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/leaderboard' },
    { path: '/leaderboard', name: 'leaderboard', component: LeaderboardView },
    { path: '/detectors/:name', name: 'detector', component: DetectorView, props: true },
    { path: '/agents', name: 'agents', component: AgentsView },
    { path: '/agents/:id', name: 'agent-run', component: AgentsView },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
