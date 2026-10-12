export default defineNuxtConfig({
  compatibilityDate: '2026-09-23',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'ODIN — Anvil 奥丁 · Fan Art',
      meta: [
        { name: 'description', content: 'Anvil Odin 奥丁战列巡洋舰粉丝艺术展示。实时三维舰船、电影式镜头与自由探索。非 Star Citizen 官方网站。' },
        { name: 'theme-color', content: '#F4F2ED' },
      ],
      link: [
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/images/odin-founders-icon-v0.11.47.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/images/odin-founders-touch-v0.11.47.png' },
      ],
    },
  },
  vite: { build: { chunkSizeWarningLimit: 1100 } },
})
