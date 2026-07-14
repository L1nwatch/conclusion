import { createRouter, createWebHistory } from 'vue-router'
import DetailPage from './pages/DetailPage.vue'
import ListPage from './pages/ListPage.vue'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'list', component: ListPage },
    { path: '/conclusions/:id', name: 'detail', component: DetailPage },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

