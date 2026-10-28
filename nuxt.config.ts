export default defineNuxtConfig({
  compatibilityDate: '2026-09-23',
  devtools: { enabled: false },
  css: ['~/assets/folio.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'ODIN MONOGRAPH — 雷霆，有形。',
      meta: [
        {
          name: 'description',
          content:
            '一册可以触摸的奥丁设定集。以蚀刻、线稿与素模重构舰影，逐层展开武备，走进钢铁之中的空间。非官方 Star Citizen 互动艺术作品。',
        },
        { name: 'theme-color', content: '#f1f0eb' },
      ],
      link: [
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '32x32',
          href: '/images/odin-founders-icon-v0.11.47.png',
        },
        {
          rel: 'apple-touch-icon',
          sizes: '180x180',
          href: '/images/odin-founders-touch-v0.11.47.png',
        },
      ],
    },
  },
  vite: { build: { chunkSizeWarningLimit: 1100 } },
})
