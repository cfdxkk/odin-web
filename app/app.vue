<script setup lang="ts">
import { MODES, isPlaying, nextPlayback } from '~/lib/odin-motion'
const viewer = ref<{ seek: (t: number) => void; reset: () => void }>()
const ready = ref(false), progress = ref(0), explore = ref(false), deployed = ref(true), lowPower = ref(false)
const playback = ref({ userPaused: false, scrubbing: false })
const playing = computed(() => isPlaying(playback.value))
const togglePlayback = () => { playback.value = nextPlayback(playback.value, 'toggle') }
const beginScrub = () => { playback.value = nextPlayback(playback.value, 'scrub-start') }
const endScrub = () => { playback.value = nextPlayback(playback.value, 'scrub-end') }
const filmTime = ref(0), error = ref(''), showAbout = ref(false)
const aboutDialog = ref<HTMLDialogElement>()
watch(showAbout, value => { if (value) aboutDialog.value?.showModal(); else aboutDialog.value?.close() })
const chapters = MODES
const chapterIndex = computed(() => filmTime.value < 12 ? 0 : filmTime.value < 26 ? 1 : 2)
const currentChapter = computed(() => chapters[chapterIndex.value]!)
const clock = computed(() => `00:${String(Math.floor(filmTime.value)).padStart(2, '0')}`)
function chooseChapter(index: number) { explore.value = false; viewer.value?.seek(chapters[index]!.time) }
function toggleExplore() { explore.value = !explore.value }
function scrub(event: Event) {
  viewer.value?.seek(Number((event.target as HTMLInputElement).value))
}
function scrubKey(event: KeyboardEvent) { if (/^(Arrow|Home|End|Page)/.test(event.key)) beginScrub() }
function keyboard(event: KeyboardEvent) {
  const element = event.target as HTMLElement
  if (/INPUT|BUTTON|A|TEXTAREA|SELECT/.test(element.tagName) || showAbout.value) return
  if (event.code === 'Space') { event.preventDefault(); if (ready.value && !explore.value) togglePlayback() }
  if (event.key.toLowerCase() === 'r') { explore.value = false; viewer.value?.seek(0) }
}
onMounted(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) playback.value.userPaused = true
  lowPower.value = window.innerWidth < 700
  window.addEventListener('keydown', keyboard)
  window.addEventListener('pointerup', endScrub)
  window.addEventListener('pointercancel', endScrub)
  window.addEventListener('blur', endScrub)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', keyboard)
  window.removeEventListener('pointerup', endScrub)
  window.removeEventListener('pointercancel', endScrub)
  window.removeEventListener('blur', endScrub)
})
</script>

<template>
  <div class="site-shell">
    <header class="site-header">
      <a href="#top" class="brand" aria-label="ODIN 首页"><img src="/favicon.svg" alt="" /><span>ODIN<span class="brand-sub">ANVIL / FAN ART</span></span></a>
      <nav aria-label="主导航"><a href="#top" class="nav-current">舰船展示</a><a href="#dossier">舰船档案</a><button @click="showAbout = true">关于创作</button></nav>
      <span class="fan-badge">UNOFFICIAL <strong>FAN ART</strong></span>
    </header>

    <main>
      <section id="top" class="hero" :class="{ 'is-exploring': explore }" aria-label="奥丁三维展示">
        <div class="scene-wrap">
          <ClientOnly>
            <OdinScene ref="viewer" :playing="playing" :explore="explore" :deployed="deployed" :low-power="lowPower" @ready="ready = true" @progress="progress = $event" @tick="filmTime = $event" @fail="error = $event" />
          </ClientOnly>
        </div>
        <div class="hero-shade" aria-hidden="true" />
        <div class="hero-heading">
          <p class="eyebrow"><span /> THE ALLFATHER OF WAR</p>
          <h1>ODIN<span class="title-star">✳</span></h1>
          <div class="hero-subtitle"><span>奥丁</span><span class="slash">/</span><span>战列巡洋舰</span></div>
          <p class="hero-copy">以雷霆之名，重塑战场。</p>
        </div>
        <div class="side-coordinate" aria-hidden="true">ANVIL · CAPITAL CLASS <span /> OD—77</div>

        <Transition name="fade">
          <div v-if="!ready && !error" class="loading-state" role="status"><span class="loading-mark" /><p>正在唤醒奥丁 <span>{{ Math.round(progress) }}%</span></p><div class="loading-track"><span :style="{ width: `${progress}%` }" /></div></div>
        </Transition>
        <div v-if="error" class="error-state" role="alert"><h2>三维场景暂时无法启动</h2><p>请使用支持 WebGL 2 的浏览器，并启用硬件加速。</p><button class="outline-button" @click="reloadNuxtApp({ force: true })">重新载入</button><details><summary>错误详情</summary>{{ error }}</details></div>

        <div v-if="ready" class="viewer-actions">
          <button class="explore-button" :class="{ selected: explore }" :aria-pressed="explore" @click="toggleExplore"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 0v18M4 7.5l8 5 8-5M4 16.5l8-4 8 4" /></svg>{{ explore ? '返回电影视角' : '自由探索' }}<span>↗</span></button>
          <Transition name="fade"><div v-if="explore" class="explore-tools"><span>拖动旋转 · 滚轮缩放</span><button :aria-pressed="deployed" @click="deployed = !deployed">{{ deployed ? '收拢武备' : '展开武备' }}</button><button @click="viewer?.reset()">复位视角</button></div></Transition>
        </div>

        <div class="hero-bottom">
          <div class="shot-caption"><span class="eyebrow">{{ explore ? 'YOUR PERSPECTIVE' : `0${chapterIndex + 1} / ${currentChapter.english}` }}</span><p>{{ explore ? '从你的视角，发现奥丁。' : currentChapter.caption }}</p></div>
          <div class="playback" :class="{ dimmed: explore }">
            <div class="playback-top"><button :disabled="!ready || explore" :aria-label="playing ? '暂停动画' : '播放动画'" @click="togglePlayback"><svg v-if="playing" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4v12M14 4v12" /></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m6 3 11 7-11 7Z" /></svg></button><span class="timecode">{{ clock }} <span>/ 00:40</span></span><span class="playback-label">CINEMATIC ORBIT</span><button class="quality-button" :aria-pressed="!lowPower" :aria-label="lowPower ? '开启高画质' : '开启流畅模式'" @click="lowPower = !lowPower">{{ lowPower ? '流畅' : '高画质' }}</button></div>
            <input class="timeline" type="range" min="0" max="39.99" step="0.1" :value="filmTime" :disabled="!ready || explore" aria-label="动画时间" :style="{ '--progress': `${filmTime / 40 * 100}%` }" @pointerdown="beginScrub" @pointerup="endScrub" @pointercancel="endScrub" @keydown="scrubKey" @keyup="endScrub" @change="endScrub" @input="scrub" />
            <div class="chapter-buttons"><button v-for="(chapter, index) in chapters" :key="chapter.name" :disabled="!ready" :class="{ active: !explore && chapterIndex === index }" @click="chooseChapter(index)"><span>0{{ index + 1 }}</span>{{ chapter.name }}</button></div>
          </div>
        </div>
        <a href="#dossier" class="scroll-cue"><span>探索舰船档案</span><span class="down-line" /></a>
      </section>

      <section id="dossier" class="dossier">
        <div class="section-heading"><p class="eyebrow">01 / THE BATTLECRUISER</p><span>ANVIL ODIN</span></div>
        <div class="dossier-intro"><h2>为战场而生。<br /><span>为胜利而铸。</span></h2><div><p>奥丁，将海军舰艇的轮廓带入星海。高耸的舰桥、纵贯舰身的装甲，以及隐藏于船体中的武备，共同构成 Anvil 的战列巡洋舰。</p><p class="subtle">这是一场致敬原作的视觉探索。从一束掠过装甲的光，到主炮缓缓升起的瞬间，重新感受这艘巨舰的尺度。</p><a class="text-link" href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">探索 RSI 官方概念 <span>↗</span></a></div></div>
        <div class="spec-row"><div><span class="spec-index">01 — ARMAMENT</span><strong>23<span>座</span></strong><h3>可操控炮塔</h3><p>协同火力，覆盖整片战场。</p></div><div><span class="spec-index">02 — SUPPORT</span><strong>6<span>座</span></strong><h3>侧向机库</h3><p>补给、整备，再次投入战斗。</p></div><div><span class="spec-index">03 — ENFORCER</span><strong>12<span>联</span></strong><h3>舰艏发射器</h3><p>汇聚于舰艏的反主力舰武备。</p></div></div>
        <p class="source-note">概念配置依据 RSI 官方介绍；最终配置以官方发布为准。</p>
      </section>

      <section class="concept-section" aria-label="奥丁官方概念艺术"><img src="/images/odin-battle.webp" alt="奥丁战列巡洋舰在行星轨道交战的官方概念艺术" loading="lazy" /><div class="concept-shade" /><div class="concept-caption"><p class="eyebrow">ANVIL AEROSPACE</p><h2>THE ALLFATHER<br />OF WAR.</h2><span>官方概念艺术 / Cloud Imperium Games</span></div><a href="#top" class="concept-link" @click="chooseChapter(0)">重返奥丁 <span>↑</span></a></section>
    </main>

    <footer class="site-footer"><a class="footer-wordmark" href="#top">ODIN<span>FAN ART PROJECT</span></a><p>本网站为独立粉丝艺术作品，与 Cloud Imperium Games 无隶属关系。<br />Star Citizen、Anvil、Odin 及官方概念艺术的权利归各自权利人所有。</p><a class="community-mark" href="https://robertsspaceindustries.com" target="_blank" rel="noopener noreferrer"><img src="/images/made-by-the-community.png" alt="Star Citizen — Made by the Community，星际公民社区制作" width="112" height="112" /></a><button @click="showAbout = true">创作与来源 ↗</button></footer>

    <Teleport to="body"><dialog ref="aboutDialog" class="about-dialog" aria-label="创作与来源" @close="showAbout = false" @cancel="showAbout = false"><div class="dialog-backdrop" @click="showAbout = false" /><section role="document"><button class="dialog-close" aria-label="关闭创作说明" @click="showAbout = false">×</button><p class="eyebrow">THE ART OF ODIN</p><h2>一次属于粉丝的<br />奥丁视觉创作。</h2><p>基于提供的奥丁模型，整理舰体、补充外观细节，并以光影、镜头与机械运动重新呈现它的力量。</p><p>场景在浏览器中实时渲染。舰船旋转、武备展开、推进器光效与镜头运动均由 Nuxt 中的 JavaScript 驱动。</p><div class="credits"><a href="https://www.youtube.com/watch?v=EKvbJh87rpY" target="_blank" rel="noopener noreferrer">动画灵感 / Space Tech <span>↗</span></a><a href="https://www.youtube.com/watch?v=CFoQp6wRjPo" target="_blank" rel="noopener noreferrer">官方开发者展示 / Star Citizen Live <span>↗</span></a><a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">舰船概念与资料 / RSI <span>↗</span></a></div><small>粉丝艺术外观模型，非官方生产级模型。</small></section></dialog></Teleport>
  </div>
</template>
