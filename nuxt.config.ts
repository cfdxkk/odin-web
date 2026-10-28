export default defineNuxtConfig({
  compatibilityDate: '2026-09-23',
  devtools: { enabled: false },
  css: ['~/assets/atlas.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'ODIN ATLAS — 沉默之中，自有雷霆',
      meta: [
        { name: 'description', content: '一份关于力量、尺度与机械秩序的交互式舰船档案。探索 Anvil Odin 奥丁的三维机构、舰内世界与概念影像。非官方粉丝创作。' },
        { name: 'theme-color', content: '#eaeae2' },
      ],
      link: [
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/images/odin-founders-icon-v0.11.47.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/images/odin-founders-touch-v0.11.47.png' },
      ],
    },
  },
  vite: { build: { chunkSizeWarningLimit: 1100 } },
})
