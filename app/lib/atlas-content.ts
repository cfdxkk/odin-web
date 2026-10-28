import { ODIN_ARTWORK } from './odin-artwork.ts'

// Editorial copy for the Atlas presentation. Numeric claims retain the concept
// qualification recorded in docs/review/v0.17.0/weapon-sources.json and
// docs/review/v0.18.0/sources.json; no performance figures are inferred.
export type AtlasModeId = 'overview' | 'main' | 'secondary' | 'defense' | 'bridge' | 'engines'

export const ATLAS_SOURCE = 'https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin'
export const ATLAS_CONCEPT_NOTICE = '基于官方概念资料与粉丝模型制作。舰船配置仍处概念阶段，以 RSI 最终发布为准。'

export const ATLAS_MODES = [
  {
    id: 'overview', number: '01', label: '舰体总览', eyebrow: 'THE BATTLECRUISER',
    title: '秩序，铸成舰体。',
    body: '锐利的舰艏、层叠的装甲与高耸的舰桥，构成奥丁的轮廓。从全舰视角进入，逐一展开隐藏于舰体之中的机械结构。',
    detail: 'Anvil Aerospace · 战列巡洋舰', metric: 'ODIN', metricLabel: '奥丁',
  },
  {
    id: 'main', number: '02', label: '主炮阵列', eyebrow: 'PRIMARY BATTERIES',
    title: '沉默之下，重火力。',
    body: '两座三联装主炮分置舰背与舰腹。装甲先行打开，炮座随后升起；六门 S12 武器从舰体轮廓中显现。',
    detail: '2 座有人炮塔 · 每座 3 门 S12 · 概念配置', metric: '2 × 3', metricLabel: 'S12 主炮',
  },
  {
    id: 'secondary', number: '03', label: '副炮矩阵', eyebrow: 'SECONDARY BATTERIES',
    title: '沿舰体，展开锋芒。',
    body: '单联装副炮沿舰体分布。逐步打开覆盖装甲，观察炮架与炮管的收纳关系，细看舰艏、侧舷和舰艉各自的展开方式。',
    detail: '3 座有人 + 8 座遥控 · S10 · 概念配置', metric: '11', metricLabel: '单联装 S10 炮塔',
  },
  {
    id: 'defense', number: '04', label: '双联炮群', eyebrow: 'LAYERED ARMAMENT',
    title: '力量，分布于两舷。',
    body: '八座双联装炮塔各搭载两门 S8 武器。打开侧舷炮位，观察装甲、支承机构与炮管如何依次让出运动空间。',
    detail: '8 座有人炮塔 · 每座 2 门 S8 · 概念配置', metric: '8 × 2', metricLabel: 'S8 双联装武器',
  },
  {
    id: 'bridge', number: '05', label: '舰桥中枢', eyebrow: 'COMMAND & CONTROL',
    title: '舰队的目光所在。',
    body: '舰桥耸立于甲板之上，两侧布置四联装炮塔。靠近观察炮臂的伸展、炮管的转动，以及茶金色观察窗与固定护甲形成的层次。',
    detail: '2 座有人四联炮塔 · 每座 4 门 S8 · 概念配置', metric: '2 × 4', metricLabel: 'S8 舰桥武备',
  },
  {
    id: 'engines', number: '06', label: '推进系统', eyebrow: 'FORWARD, ALWAYS',
    title: '让庞然之躯启程。',
    body: '视线沿分层舰体抵达舰艉。主推进器与辅助喷口共同组成推进阵列，蓝色尾焰勾勒出奥丁驶向深空的姿态。',
    detail: '多引擎布局 · 巡洋舰速度为概念设计目标', metric: 'NAV', metricLabel: '航行配置',
  },
] as const satisfies readonly {
  id: AtlasModeId
  number: string
  label: string
  eyebrow: string
  title: string
  body: string
  detail: string
  metric: string
  metricLabel: string
}[]

export const ATLAS_STATS = [
  { value: '23', unit: '座', label: '可操控炮塔', note: '概念配置；不含点防御炮', source: ATLAS_SOURCE },
  { value: '20', unit: '套', label: 'S12 垂直发射系统', note: '概念配置', source: 'https://media.robertsspaceindustries.com/uhjpyw81y6eqe/source.jpg' },
  { value: '6 + 1', unit: '', label: '小型与中型机库', note: '概念规划', source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=1141s' },
  { value: '8,000', unit: 'SCU', label: '货物容量', note: '概念配置：主货舱 6000 + 升降平台 2000', source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=1546s' },
] as const

function artwork(filename: string) {
  const image = ODIN_ARTWORK.find(item => item.src.endsWith(filename))
  if (!image) throw new Error(`Missing existing Odin artwork: ${filename}`)
  return image
}

// The existing overlay was flattened to black during its original WebP export.
// Keep it on a dark background, or use screen blending; it is not an alpha cutout.
export const ATLAS_HERO_IMAGE = artwork('02-odin-ship-overlay.webp')

export const ATLAS_GALLERY = [
  {
    ...artwork('06-sc-anvil-odin-exterior-7.webp'),
    number: '01', title: '体量，成为风景。', eyebrow: 'HULL / EXTERIOR',
    description: '甲板、机库与展开的武备，共同勾勒出奥丁的全舰轮廓。',
    position: '50% 50%',
  },
  {
    ...artwork('20-sc-anvil-odin-exterior-4.webp'),
    number: '02', title: '驶向交锋之处。', eyebrow: 'ENGAGEMENT / ORBIT',
    description: '从舰艉望向战场，推进阵列与交错火线成为画面的两极。',
    position: '62% 50%',
  },
  {
    ...artwork('27-sc-anvil-odin-exterior-5.webp'),
    number: '03', title: '短暂的静默。', eyebrow: 'STATION / AT BERTH',
    description: '停泊在空间设施之间，完整侧影将战列巡洋舰的尺度显现出来。',
    position: '50% 50%',
  },
  {
    ...artwork('14-sc-anvil-odin-interior-5.webp'),
    number: '04', title: '从共同的意图出发。', eyebrow: 'INTERIOR / BRIEFING',
    description: '简报空间将船员聚集于同一处，连接舰内生活与下一次行动。',
    position: '50% 50%',
  },
] as const

export const ATLAS_INTERIOR_IMAGE = {
  src: '/images/odin-interiors/hangar-cargo-deck.webp',
  width: 2400, height: 1350,
  title: '一艘舰船，也是一座基地。',
  alt: '奥丁中央机库、两侧小型机库与后方货物升降平台的官方概念图。',
  body: '中央机库连接六座侧机库，为回收、补给与再次出动提供连续空间。',
  source: 'https://media.robertsspaceindustries.com/d8q6m2h9ecdeo/source.jpg',
} as const
