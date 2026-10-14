<script setup lang="ts">
const props = withDefaults(defineProps<{ locale: 'zh' | 'en'; artwork?: 'paper' | 'night' }>(), { artwork: 'night' })
const emit = defineEmits<{ overview: [] }>()
const text = computed(() => props.locale === 'zh' ? {
  thanks: '感谢来访。', body: '为 Star Citizen 社区制作。感谢所有提出建议、分享反馈的人。',
  creator: '制作 / cfdxkk', sources: '官方资料',
  source: 'GitHub 源代码', community: 'Star Citizen 社区制作徽章', top: '返回舰船总览',
  image: 'Odin 航行在层叠山峦之间的印刷风格插画',
} : {
  thanks: 'Thanks for visiting.', body: 'Made for the Star Citizen community. Thank you to everyone who shared ideas and feedback.',
  creator: 'Created by cfdxkk', sources: 'Official source',
  source: 'Source on GitHub', community: 'Star Citizen Made by the Community badge', top: 'Back to the ship',
  image: 'A print illustration of Odin among layered mountain ridges',
})
</script>

<template>
  <footer id="footer" class="site-footer odin-footer" :class="`footer-${artwork}`" aria-labelledby="footer-title">
    <figure class="footer-landscape">
      <FooterPrint v-if="artwork === 'night'" :alt="text.image" />
      <img v-else src="/images/odin-mountain-footer-v0.13.0.webp" :alt="text.image" width="2048" height="683" loading="lazy" decoding="async" />
    </figure>
    <div class="footer-content">
      <div class="footer-intro">
        <h2 id="footer-title">{{ text.thanks }}</h2>
        <p>{{ text.body }}</p>
        <span class="eyebrow">{{ text.creator }} / 2026</span>
        <div class="identity-stripe" aria-hidden="true"><i /><i /><i /><i /></div>
      </div>
      <div class="footer-sources">
        <h2>{{ text.sources }}</h2>
        <a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">Anvil Odin <span aria-hidden="true">↗</span></a>
      </div>
      <div class="footer-colophon">
        <a class="footer-source" href="https://github.com/cfdxkk/odin-web" target="_blank" rel="noopener noreferrer">{{ text.source }} <span aria-hidden="true">↗</span></a>
        <div class="footer-marks">
          <span class="community-mark"><img src="/images/made-by-the-community.png" :alt="text.community" width="56" height="56" loading="lazy" /></span>
          <a class="footer-top" href="#overview" :aria-label="text.top" @click.prevent="emit('overview')">↑</a>
        </div>
      </div>
    </div>
  </footer>
</template>
