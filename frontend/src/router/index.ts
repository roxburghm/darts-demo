import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/upload',
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/UploadView.vue'),
    },
    {
      path: '/preview/:sessionId',
      name: 'preview',
      component: () => import('@/views/PreviewView.vue'),
      props: true,
    },
    {
      path: '/configure/:sessionId',
      name: 'configure',
      component: () => import('@/views/ConfigureView.vue'),
      props: true,
    },
    {
      path: '/models/:sessionId',
      name: 'models',
      component: () => import('@/views/ModelSelectView.vue'),
      props: true,
    },
    {
      path: '/analysis/:sessionId',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue'),
      props: true,
    },
  ],
})

export default router
