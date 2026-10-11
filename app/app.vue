<script setup lang="ts">
import { FILM_DURATION, MODES, isPlaying, nextPlayback, sampleOdinMotion } from '~/lib/odin-motion'
const viewer = ref<{ seek: (t: number) => void }>()
const reviewMode = ref(false)
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
const chapterIndex = computed(() => filmTime.value < MODES[1].time ? 0 : filmTime.value < MODES[2].time ? 1 : 2)
const currentChapter = computed(() => chapters[chapterIndex.value]!)
const configuration = computed(() => explore.value ? (deployed.value ? 'SCM' : 'NAV') : filmTime.value < 12 ? 'NAV' : filmTime.value < 32 ? 'SCM' : 'NAV')
const formatTime = (t: number) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`
const clock = computed(() => formatTime(filmTime.value))
function chooseChapter(index: number) { explore.value = false; viewer.value?.seek(chapters[index]!.time) }
function toggleExplore() {
  if (!explore.value) deployed.value = sampleOdinMotion(filmTime.value).mode === 'scm'
  explore.value = !explore.value
}
function scrub(event: Event) {
  viewer.value?.seek(Number((event.target as HTMLInputElement).value))
}
function scrubKey(event: KeyboardEvent) { if (/^(Arrow|Home|End|Page)/.test(event.key)) beginScrub() }
function keyboard(event: KeyboardEvent) {
  const element = event.target as HTMLElement
  if (/INPUT|BUTTON|A|TEXTAREA|SELECT/.test(element.tagName) || showAbout.value) return
  if (event.code === 'Space') { event.preventDefault(); if (ready.value && !explore.value) togglePlayback() }
  if (event.key.toLowerCase() === 'r' && !explore.value) viewer.value?.seek(0)
}
onMounted(() => {
  reviewMode.value = new URLSearchParams(window.location.search).get('review') === 'secondary'
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
  <ClientOnly v-if="reviewMode"><ArticulationReview /></ClientOnly>
  <div v-else class="site-shell">
    <header class="site-header">
      <a href="#top" class="brand" aria-label="ODIN 首页">
        <img src="/images/odin-founders-badge-v0.11.47.png" alt="" width="52" height="52" />
        <span>ODIN<span class="brand-sub">ANVIL / FAN STUDY</span></span>
      </a>
      <nav aria-label="主导航">
        <a href="#top" class="nav-current"><span>01</span>舰船展示</a>
        <a href="#dossier"><span>02</span>舰船档案</a>
        <button @click="showAbout = true"><span>03</span>关于创作</button>
      </nav>
      <span class="fan-badge">INDEPENDENT PROJECT<strong>非官方 · 粉丝作品</strong></span>
      <div class="identity-stripe" aria-hidden="true"><i /><i /><i /><i /></div>
    </header>

    <main>
      <section id="top" class="hero" :class="{ 'is-exploring': explore }" aria-label="奥丁三维展示">
        <span v-for="corner in ['tl','tr','bl','br']" :key="corner" class="fastener" :class="`fastener-${corner}`" aria-hidden="true" />
        <div class="hero-heading">
          <div class="hero-nameplate">
            <p class="eyebrow">01 / VEHICLE STUDY</p>
            <div class="hero-title-row"><h1>ODIN</h1><div class="hero-subtitle"><span>奥丁 / 战列巡洋舰</span><span>ANVIL AEROSPACE</span></div></div>
          </div>
          <p class="hero-copy">舰船外观、武备结构<br />与航行配置展示。</p>
          <div class="equipment-tag"><span>DISPLAY UNIT</span><strong>OD—77</strong><span>REV. 012 / FAN ART</span></div>
        </div>

        <div class="scene-wrap">
          <ClientOnly>
            <OdinScene ref="viewer" :playing="playing" :explore="explore" :deployed="deployed" :low-power="lowPower" @ready="ready = true" @progress="progress = $event" @tick="filmTime = $event" @fail="error = $event" />
          </ClientOnly>
        </div>
        <div class="viewport-label"><span class="hazard-mark" aria-hidden="true" /> <span>VIEWPORT 01 / REAL-TIME MODEL</span></div>
        <div class="viewport-direction" aria-hidden="true">↑ THIS SIDE UP <span>STOW 84S</span></div>
        <div class="viewport-corners" aria-hidden="true"><i /><i /><i /><i /></div>
        <div class="viewport-status"><span class="status-dot" />{{ !ready ? 'LOADING' : explore ? 'MANUAL VIEW' : playing ? 'PLAYBACK' : 'PAUSED' }}<span>{{ configuration }} / CONFIG</span></div>

        <Transition name="fade">
          <div v-if="!ready && !error" class="loading-state" role="status"><p class="eyebrow">MODEL / INITIALIZING</p><p>正在加载三维模型 <span>{{ Math.round(progress) }}%</span></p><div class="loading-track"><span :style="{ width: `${progress}%` }" /></div></div>
        </Transition>
        <div v-if="error" class="error-state" role="alert"><p class="eyebrow">DISPLAY / UNAVAILABLE</p><h2>三维场景暂时无法启动</h2><p>请使用支持 WebGL 2 的浏览器，并启用硬件加速。</p><button class="outline-button" @click="reloadNuxtApp({ force: true })">重新载入</button><details><summary>错误详情</summary>{{ error }}</details></div>

        <div v-if="ready" class="viewer-actions">
          <button class="explore-button" :class="{ selected: explore }" :aria-pressed="explore" @click="toggleExplore"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 0v18M4 7.5l8 5 8-5M4 16.5l8-4 8 4" /></svg><span>{{ explore ? '返回电影视角' : '自由探索' }}<small>{{ explore ? 'RETURN / AUTO' : 'INSPECT / MANUAL' }}</small></span><span aria-hidden="true">↗</span></button>
          <Transition name="fade"><div v-if="explore" class="explore-tools"><span>左键旋转 · 右键平移 · 滚轮缩放</span><span class="explore-mode">{{ deployed ? 'SCM / 战斗模式' : 'NAV / 航行模式' }}</span><button @click="deployed = !deployed">{{ deployed ? '切换为 NAV/航行模式' : '切换为 SCM/战斗模式' }} <span aria-hidden="true">→</span></button></div></Transition>
        </div>

        <div class="hero-bottom">
          <div class="shot-caption"><span class="eyebrow">{{ explore ? 'MANUAL / INSPECTION' : `0${chapterIndex + 1} / ${currentChapter.english}` }}</span><p>{{ explore ? '旋转视角，查看舰船细节。' : currentChapter.caption }}</p><span class="operator-note">先暂停，再看细节。</span></div>
          <div class="playback" :class="{ dimmed: explore }">
            <div class="playback-top"><button class="play-button" :disabled="!ready || explore" :aria-label="playing ? '暂停动画' : '播放动画'" @click="togglePlayback"><svg v-if="playing" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4v12M14 4v12" /></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m6 3 11 7-11 7Z" /></svg></button><span class="timecode">{{ clock }} <span>/ {{ formatTime(FILM_DURATION) }}</span></span><span class="playback-label">SEQUENCE / 60 SEC</span><button class="quality-button" :aria-pressed="!lowPower" :aria-label="lowPower ? '开启高画质' : '开启流畅模式'" @click="lowPower = !lowPower">{{ lowPower ? '流畅' : '高画质' }}<span aria-hidden="true">{{ lowPower ? 'LO' : 'HI' }}</span></button></div>
            <input class="timeline" type="range" min="0" :max="FILM_DURATION - .01" step="0.1" :value="filmTime" :disabled="!ready || explore" aria-label="动画时间" :style="{ '--progress': `${filmTime / FILM_DURATION * 100}%` }" @pointerdown="beginScrub" @pointerup="endScrub" @pointercancel="endScrub" @keydown="scrubKey" @keyup="endScrub" @change="endScrub" @input="scrub" />
            <div class="chapter-buttons"><button v-for="(chapter, index) in chapters" :key="chapter.name" :disabled="!ready" :class="{ active: !explore && chapterIndex === index }" @click="chooseChapter(index)"><span>0{{ index + 1 }}</span>{{ chapter.name }}</button></div>
          </div>
        </div>
        <div class="hero-footrail"><span>SPACE / 暂停 <b>·</b> R / 复位</span><a href="#dossier" class="scroll-cue">舰船档案 <span aria-hidden="true">↓</span></a></div>
      </section>

      <section id="dossier" class="dossier">
        <div class="section-heading"><p class="eyebrow">02 / VEHICLE DOSSIER</p><span>DOCUMENT OD—77 / SHEET 01</span></div>
        <div class="dossier-intro"><div><p class="dossier-class">ANVIL AEROSPACE / CAPITAL CLASS</p><h2>舰体与武备<span>奥丁战列巡洋舰</span></h2></div><div><p>奥丁是 Anvil 的战列巡洋舰概念。本页通过三维模型，展示舰体布局、武备结构，以及战斗与航行两种配置。</p><p class="subtle">拖动时间轴查看动作过程，或进入自由探索，近距离检查舰船细节。</p><a class="text-link" href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">RSI 官方概念与资料 <span>↗</span></a></div></div>
        <div class="spec-row"><div><span class="spec-index">A / ARMAMENT</span><strong>23<span>座</span></strong><h3>可操控炮塔</h3><p>多组炮塔，分布于舰体各处。</p></div><div><span class="spec-index">B / HANGARS</span><strong>6<span>座</span></strong><h3>侧向机库</h3><p>舰体两侧的舰载艇机库。</p></div><div><span class="spec-index">C / LAUNCHERS</span><strong>12<span>联</span></strong><h3>舰艏发射器</h3><p>舰艏的发射器阵列。</p></div></div>
        <div class="dossier-footnote"><span class="hazard-mark" aria-hidden="true" /><p class="source-note">概念配置依据 RSI 官方介绍；最终配置以官方发布为准。</p><span>REF. / RSI CONCEPT</span></div>
      </section>

      <section class="concept-section" aria-label="奥丁官方概念艺术">
        <div class="concept-image"><img src="/images/odin-battle.webp" alt="奥丁战列巡洋舰在行星轨道交战的官方概念艺术" loading="lazy" /><span>FIG. 01 / OFFICIAL CONCEPT ART</span></div>
        <div class="concept-caption"><p class="eyebrow">03 / IMAGE ARCHIVE</p><h2>官方概念图</h2><p>三维展示之外，看看官方概念图中的奥丁。</p><span>ANVIL ODIN<br />© CLOUD IMPERIUM GAMES</span><a href="#top" class="concept-link" @click="chooseChapter(0)">返回三维展示 <span aria-hidden="true">↑</span></a><div class="identity-stripe" aria-hidden="true"><i /><i /><i /><i /></div></div>
      </section>
    </main>

    <footer class="site-footer"><a class="footer-wordmark" href="#top">ODIN<span>INDEPENDENT FAN STUDY</span></a><p>本网站为独立粉丝艺术作品，与 Cloud Imperium Games 无隶属关系。<br />Star Citizen、Anvil、Odin 及官方概念艺术的权利归各自权利人所有。</p><a class="community-mark" href="https://robertsspaceindustries.com" target="_blank" rel="noopener noreferrer"><img src="/images/made-by-the-community.png" alt="Star Citizen — Made by the Community，星际公民社区制作" width="88" height="88" /></a><button @click="showAbout = true">创作与来源 <span aria-hidden="true">↗</span></button><div class="footer-register"><span>OD—77 / WEB DISPLAY</span><span>EDITION 012.0</span><span>END OF DOCUMENT / ↑</span></div></footer>

    <Teleport to="body"><dialog ref="aboutDialog" class="about-dialog" aria-label="创作与来源" @close="showAbout = false" @cancel="showAbout = false"><div class="dialog-backdrop" @click="showAbout = false" /><section role="document"><button class="dialog-close" aria-label="关闭创作说明" @click="showAbout = false">×</button><p class="eyebrow">PROJECT NOTES / OD—77</p><h2>关于这次展示</h2><p>本项目基于奥丁模型制作，整理舰体外观，并补充武备展开、收起与推进器效果。你看到的是可交互的三维模型。</p><p>页面视觉参考 70 年代 NASA 的规范手册与《星空》的界面：浅色设备面板、清晰编号，以及少量使用痕迹。</p><div class="credits"><a href="https://www.youtube.com/watch?v=EKvbJh87rpY" target="_blank" rel="noopener noreferrer">动画灵感 / Space Tech <span>↗</span></a><a href="https://www.youtube.com/watch?v=CFoQp6wRjPo" target="_blank" rel="noopener noreferrer">官方开发者展示 / Star Citizen Live <span>↗</span></a><a href="https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin" target="_blank" rel="noopener noreferrer">舰船概念与资料 / RSI <span>↗</span></a><a href="https://media.robertsspaceindustries.com/84qwqukbwkgsk/source.png" target="_blank" rel="noopener noreferrer">网站徽章 / 奥丁创始人俱乐部勋章 <span>↗</span></a><a href="https://www.nasa.gov/wp-content/uploads/2015/01/nasa_graphics_manual_nhb_1430-2_jan_1976.pdf" target="_blank" rel="noopener noreferrer">视觉参考 / NASA Graphics Standards Manual <span>↗</span></a><a href="https://bethesda.net/en-US/news/starfield-gameplay-reveal" target="_blank" rel="noopener noreferrer">界面参考 / Starfield 官方展示 <span>↗</span></a></div><small>粉丝艺术外观模型，非官方生产级模型。</small><span class="dialog-folio">NOTES / 01</span></section></dialog></Teleport>
  </div>
</template>
