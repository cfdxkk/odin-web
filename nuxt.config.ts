export default defineNuxtConfig({
  compatibilityDate: '2026-09-23',
  devtools: { enabled: false },
  css: ['~/assets/awakening.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'ODIN AWAKENING — 唤醒雷霆',
      meta: [
        { name: 'description', content: '唤醒奥丁。一场以日蚀、扫描、武备与跃迁构成的实时深空仪式。亲手探索战列巡洋舰的钢铁之躯。非官方 Star Citizen 互动艺术作品。' },
        { name: 'theme-color', content: '#08090b' },
      ],
      link: [
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/images/odin-founders-icon-v0.11.47.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/images/odin-founders-touch-v0.11.47.png' },
      ],
    },
  },
  vite: { build: { chunkSizeWarningLimit: 1100 } },
})
