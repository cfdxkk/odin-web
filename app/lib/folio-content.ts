import { ODIN_ARTWORK } from './odin-artwork.ts'

// Secondary visual archive only. Official artwork is not a homepage hero.
// Selection follows a visual review of all 27 official images and 12 interior
// assets. Numeric claims retain the concept qualification and provenance in
// docs/review/v0.17.0/weapon-sources.json and v0.18.0/sources.json.
export const FOLIO_SOURCE =
  'https://robertsspaceindustries.com/en/comm-link/transmission/21133-Anvil-Odin'
export const FOLIO_NOTICE =
  '非官方奥丁作品档案。概念图版权归 Cloud Imperium Games 所有；舰船配置仍处概念阶段，以官方最终发布为准。'

type PercentPoint = readonly [number, number]
type CropWindow = readonly [x: number, y: number, width: number, height: number]
type Aspect = readonly [width: number, height: number]

export interface FolioImage {
  id: string
  src: string
  thumb: string
  width: number
  height: number
  title: string
  kicker: string
  caption: string
  alt: string
  source: string
  category: 'exterior' | 'interior' | 'technical'
  position: string
  mobilePosition: string
  crop: {
    desktopAspect: string
    mobileAspect: string
    desktop: CropWindow
    mobile: CropWindow
  }
  layout: { light: string; dark: string }
}

type ImageCopy = Pick<
  FolioImage,
  'id' | 'title' | 'kicker' | 'caption' | 'alt' | 'category' | 'layout'
> & {
  desktop: { aspect: Aspect; position: PercentPoint }
  mobile: { aspect: Aspect; position: PercentPoint }
}

// Exact source-space percentage windows for object-fit: cover at the stated
// aspect ratio. These are layout references, not edits to the source images.
function framing(width: number, height: number, copy: ImageCopy) {
  const windowFor = (aspect: Aspect, position: PercentPoint): CropWindow => {
    const sourceRatio = width / height
    const targetRatio = aspect[0] / aspect[1]
    const w = Math.min(100, (targetRatio / sourceRatio) * 100)
    const h = Math.min(100, (sourceRatio / targetRatio) * 100)
    const round = (value: number) => Math.round(value * 100) / 100
    return [
      round(((100 - w) * position[0]) / 100),
      round(((100 - h) * position[1]) / 100),
      round(w),
      round(h),
    ]
  }
  return {
    position: `${copy.desktop.position[0]}% ${copy.desktop.position[1]}%`,
    mobilePosition: `${copy.mobile.position[0]}% ${copy.mobile.position[1]}%`,
    crop: {
      desktopAspect: copy.desktop.aspect.join(' / '),
      mobileAspect: copy.mobile.aspect.join(' / '),
      desktop: windowFor(copy.desktop.aspect, copy.desktop.position),
      mobile: windowFor(copy.mobile.aspect, copy.mobile.position),
    },
  }
}

function official(filename: string, copy: ImageCopy): FolioImage {
  const image = ODIN_ARTWORK.find((item) => item.src.endsWith(filename))
  if (!image) throw new Error(`Missing existing Odin artwork: ${filename}`)
  const { desktop: _desktop, mobile: _mobile, ...editorial } = copy
  return {
    src: image.src,
    thumb: image.thumb,
    width: image.width,
    height: image.height,
    source: image.source,
    ...editorial,
    ...framing(image.width, image.height, copy),
  }
}

const schematicCopy: ImageCopy = {
  id: 'section',
  title: '穿过舰体。',
  kicker: 'SECTION / INTERNAL ARRANGEMENT',
  caption: '由舰桥向下，机库、货舱、交通与生活空间组成另一座城市。',
  alt: '奥丁侧面剖视概念图，以编号标出舰桥、船员舱室、医院、机库、轨道交通与货舱。',
  category: 'technical',
  desktop: { aspect: [3600, 1204], position: [50, 50] },
  mobile: { aspect: [3600, 1204], position: [50, 50] },
  layout: {
    light: '作为白底资料页的整幅折页，保留原图黑底；编号解释另排白色边栏。',
    dark: '完整横向展开，点击查看原图；保留舰艏与舰艉，不做竖幅裁切。',
  },
}

// Three featured plates first, followed by eight complementary archive images.
export const FOLIO_ARTWORK: readonly FolioImage[] = [
  official('15-sc-anvil-odin-exterior-2.webp', {
    id: 'frontline',
    title: '雷霆，迎面而来。',
    kicker: 'PLATE 01 / FRONTLINE',
    caption: '斜切的舰艏、展开的武备与火线，构成奥丁最鲜明的战斗肖像。',
    alt: '奥丁从舰艏方向逼近，白色装甲与展开的炮塔映着橙色炮火，背景为行星与护航战机。',
    category: 'exterior',
    desktop: { aspect: [4, 5], position: [62, 50] },
    mobile: { aspect: [3, 4], position: [66, 50] },
    layout: {
      light:
        '档案扉页右侧放大竖幅，左侧保留宽白边与小号图注；火线可触及版心边缘。',
      dark: '独立肖像式整版，标题置于画外；保留舰桥顶端与下方爆焰，允许右缘舰体出血。',
    },
  }),
  official('06-sc-anvil-odin-exterior-7.webp', {
    id: 'hull',
    title: '尺度，成为轮廓。',
    kicker: 'PLATE 02 / HULL STUDY',
    caption: '俯瞰舰桥、主炮与两侧机库；出动的小型舰船把体量变得可感。',
    alt: '俯瞰奥丁完整上层舰体，白色舰艏向右伸展，左侧机库附近有小型战机穿过红色设施。',
    category: 'exterior',
    desktop: { aspect: [21, 9], position: [54, 50] },
    mobile: { aspect: [4, 5], position: [54, 50] },
    layout: {
      light: '白底构型跨页用近原幅宽画面，图注置下；用留白呈现舰体的长轴。',
      dark: '横向铺满档案视窗；竖幅只取舰桥与主炮细节，并保留打开完整画面的入口。',
    },
  }),
  official('27-sc-anvil-odin-exterior-5.webp', {
    id: 'berth',
    title: '停泊时的重量。',
    kicker: 'PLATE 03 / AT BERTH',
    caption: '暖色天光之下，舰影横穿空间设施；短暂的静默显露出它的尺度。',
    alt: '暖色逆光中的奥丁侧影悬停在大型空间站结构之间，远处小型船只衬托舰体尺度。',
    category: 'exterior',
    desktop: { aspect: [21, 9], position: [50, 52] },
    mobile: { aspect: [4, 5], position: [62, 50] },
    layout: {
      light:
        '作为白底档案中的横向停顿页，保留上下设施的天然画框；说明放在宽下边距。',
      dark: '用暖色整幅画面结束一组冷色战场图；短标题可放在左上天空，避开舰桥与剪影。',
    },
  }),
  official('13-sc-anvil-odin-exterior-3.webp', {
    id: 'orbit',
    title: '交锋的弧线。',
    kicker: 'ORBIT / ENGAGEMENT',
    caption: '行星弧线、近处的奥丁与远处的交火目标，构成三重景深。',
    alt: '奥丁在前景向远处的大型敌舰开火，爆炸与曳光横跨行星弧线，护航舰分布于深空。',
    category: 'exterior',
    desktop: { aspect: [16, 9], position: [56, 50] },
    mobile: { aspect: [4, 5], position: [57, 50] },
    layout: {
      light: '画面占跨页约三分之二，细窄文字列置于外侧；让行星斜线贯穿版面。',
      dark: '用于叙事段落的横向战场画面，文字置画外；竖幅围绕爆炸、炮口与前景装甲裁切。',
    },
  }),
  official('20-sc-anvil-odin-exterior-4.webp', {
    id: 'fleet',
    title: '穿越火线。',
    kicker: 'FLEET / PROPULSION',
    caption: '由舰艉望向战场，蓝色推进光与橙色光束把两个方向连在一起。',
    alt: '从奥丁舰艉俯瞰交战，右侧蓝色推进器发光，橙色光束射向左侧的敌舰。',
    category: 'exterior',
    desktop: { aspect: [21, 9], position: [50, 50] },
    mobile: { aspect: [4, 5], position: [90, 50] },
    layout: {
      light: '与舰艏肖像形成前后对照，横幅保留两端的光色；图注和编号排在白边。',
      dark: '宽幅完整展示光束与尾焰；手机竖幅聚焦右侧推进阵列，避免小字号覆盖舰体。',
    },
  }),
  official('03-the-fight-within.webp', {
    id: 'departure',
    title: '从腹地，出发。',
    kicker: 'FLIGHT DECK / DEPARTURE',
    caption: '舰腹的红色机库向深空打开，小型舰船从巨舰的阴影中离开。',
    alt: '奥丁舰腹的机库在红色照明中开启，数艘小型舰船离开机库，远处可见蓝色行星弧光。',
    category: 'exterior',
    desktop: { aspect: [16, 9], position: [50, 50] },
    mobile: { aspect: [4, 5], position: [72, 50] },
    layout: {
      light: '置于机库说明旁的偏幅图片，保留红色灯光作为本页唯一高饱和色。',
      dark: '从外景过渡到舰内的整版近景；竖幅聚焦右下机库与离舰飞船。',
    },
  }),
  official('14-sc-anvil-odin-interior-5.webp', {
    id: 'briefing',
    title: '共享一个坐标。',
    kicker: 'WITHIN / BRIEFING ROOM',
    caption: '环形座席、中央全息图与头顶的光，把行动之前的人聚集起来。',
    alt: '奥丁圆形简报室中，船员围坐在中央全息星图周围，演讲者站在明亮的圆形天窗下。',
    category: 'interior',
    desktop: { aspect: [4, 3], position: [50, 50] },
    mobile: { aspect: [4, 5], position: [53, 50] },
    layout: {
      light: '以近方幅嵌入宽白边，保留前景两个人物作为观看入口，标题排在下缘。',
      dark: '对称整版，围绕天窗、演讲者与星图构成纵轴；不要把标题压在全息图上。',
    },
  }),
  official('16-sc-anvil-odin-interior-9.webp', {
    id: 'operator',
    title: '机器之中，一双手。',
    kicker: 'WITHIN / THE HUMAN ELEMENT',
    caption: '操控者与高耸的弹药存储结构并置，巨舰的力量回到人的尺度。',
    alt: '一名船员坐在弹药存储区的操控座椅上，四周为红色照明的高大弹药架与钢制支撑结构。',
    category: 'interior',
    desktop: { aspect: [4, 5], position: [68, 50] },
    mobile: { aspect: [4, 5], position: [68, 50] },
    layout: {
      light:
        '作为人物竖幅，与宽幅机械空间错落排列；裁切围绕座椅与操控者，文字置外侧。',
      dark: '人物特写式纵幅，保留头顶结构和脚下平台；用少量暖色图注呼应环境灯。',
    },
  }),
  official('17-sc-anvil-odin-interior-7.webp', {
    id: 'magazine',
    title: '力量的储藏室。',
    kicker: 'WITHIN / MAGAZINE HALL',
    caption: '弹药、桁架与行走的人物，在同一幅画面里给出巨大与日常。',
    alt: '高大的弹药存储大厅中，中央钢制圆形结构包围操控席，一名船员走过左侧通道，右侧堆叠着弹药。',
    category: 'interior',
    desktop: { aspect: [21, 9], position: [50, 50] },
    mobile: { aspect: [4, 5], position: [41, 50] },
    layout: {
      light:
        '以原幅横跨两栏，左下行走人物和中部桁架均须保留；图注可独占下一行。',
      dark: '用橙红与青绿的纵深组织整幅空间；竖幅取左侧人物和中央操控结构。',
    },
  }),
  official('19-75-copy.webp', {
    id: 'hangar',
    title: '归航的空间。',
    kicker: 'WITHIN / HANGAR & CARGO',
    caption: '小型舰船沿两侧列队，中央机库与货物升降平台构成舰内的纵深。',
    alt: '奥丁机库内，红色中央甲板停放着小型舰船，两侧为高一层的机库平台，远端为大型舱门。',
    category: 'interior',
    desktop: { aspect: [16, 9], position: [50, 50] },
    mobile: { aspect: [4, 5], position: [50, 50] },
    layout: {
      light:
        '以满栏彩色图对照简洁机库数据，保留左右对称结构，文字不盖住中央平台。',
      dark: '作为舰内组图的开场长景，中央消失点居中；竖幅保留舱门与前景舰船。',
    },
  }),
  {
    src: '/images/odin-interiors/schematic-overview.webp',
    thumb: '/images/odin-interiors/schematic-overview.webp',
    width: 3600,
    height: 1204,
    source: 'https://media.robertsspaceindustries.com/6lpt2i7q80sdz/source.jpg',
    id: schematicCopy.id,
    title: schematicCopy.title,
    kicker: schematicCopy.kicker,
    caption: schematicCopy.caption,
    alt: schematicCopy.alt,
    category: schematicCopy.category,
    layout: schematicCopy.layout,
    ...framing(3600, 1204, schematicCopy),
  },
]

export const FOLIO_INTERIORS = FOLIO_ARTWORK.filter(
  (image) => image.category === 'interior',
)

export interface FolioFact {
  id: string
  value: string
  label: string
  detail: string
  source: string
  mode?: 'overview' | 'main' | 'secondary' | 'defense' | 'bridge' | 'engines'
}

const weaponSource =
  'https://media.robertsspaceindustries.com/uhjpyw81y6eqe/source.jpg'

export const FOLIO_FACTS: readonly FolioFact[] = [
  {
    id: 'class',
    value: 'ODIN',
    label: 'Anvil 战列巡洋舰',
    detail: '由 Anvil Aerospace 提出的战列巡洋舰概念。',
    source: FOLIO_SOURCE,
    mode: 'overview',
  },
  {
    id: 'turrets',
    value: '23',
    label: '座可操控炮塔',
    detail: '概念配置；包含有人与遥控炮塔，点防御炮塔另计。',
    source: FOLIO_SOURCE,
  },
  {
    id: 'main',
    value: '2 × 3',
    label: 'S12 主炮',
    detail: '2 座有人三联装炮塔，每座配备 3 门 S12 武器。',
    source: weaponSource,
    mode: 'main',
  },
  {
    id: 'secondary',
    value: '3 + 8',
    label: 'S10 单联装副炮',
    detail: '3 座有人炮塔与 8 座遥控炮塔，每座配备 1 门 S10 武器。',
    source: weaponSource,
    mode: 'secondary',
  },
  {
    id: 'twin',
    value: '8 × 2',
    label: 'S8 双联装炮塔',
    detail: '8 座有人双联装炮塔，每座配备 2 门 S8 武器；与 S2 点防御炮分列。',
    source: weaponSource,
    mode: 'defense',
  },
  {
    id: 'quad',
    value: '2 × 4',
    label: 'S8 舰桥四联装',
    detail: '舰桥两侧共 2 座有人四联装炮塔，每座配备 4 门 S8 武器。',
    source: weaponSource,
    mode: 'bridge',
  },
  {
    id: 'point-defense',
    value: '42',
    label: '座 S2 点防御炮塔',
    detail: '官方武备表单独列出的点防御系统，不计入 23 座可操控炮塔。',
    source: weaponSource,
  },
  {
    id: 'bow-beam',
    value: '1 × S12',
    label: '驾驶员控制的舰艏光束',
    detail: '12 个舰艏发射器组成 1 套 S12 光束武器。',
    source: weaponSource,
  },
  {
    id: 'vertical-launch',
    value: '20',
    label: '套 S12 垂直发射系统',
    detail: '概念武备配置；发射系统数量不等同于舰上总弹药容量。',
    source: weaponSource,
  },
  {
    id: 'hangars',
    value: '6 + 1',
    label: '小型与中型机库',
    detail: '每侧 3 个小型机库，共 6 个，另设 1 个中型机库。',
    source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=1141s',
  },
  {
    id: 'cargo',
    value: '8,000 SCU',
    label: '概念货物容量',
    detail: '主货舱 6,000 SCU，加货物升降平台 2,000 SCU。',
    source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=1546s',
  },
  {
    id: 'life-aboard',
    value: '舰内生活',
    label: '医院、食堂与船员舱室',
    detail:
      '官方剖面概念图在舰桥下方规划了医院、食堂、船员舱室，以及连接舰内空间的轨道交通。',
    source: 'https://media.robertsspaceindustries.com/6lpt2i7q80sdz/source.jpg',
  },
]

export const FOLIO_FACT_NOTE =
  '概念阶段配置，可能随开发调整。S8、S10、S12 是游戏内规格等级，不是毫米口径。'
