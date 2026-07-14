import { createRouter, createWebHistory } from 'vue-router'
import ListPage from './pages/ListPage.vue'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'list', component: ListPage },
    {
      path: '/conclusions/new',
      name: 'create',
      component: () => import('./pages/FormPage.vue'),
    },
    {
      path: '/conclusions/:id/edit',
      name: 'edit',
      component: () => import('./pages/FormPage.vue'),
    },
    {
      path: '/conclusions/:id',
      name: 'detail',
      component: () => import('./pages/DetailPage.vue'),
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
